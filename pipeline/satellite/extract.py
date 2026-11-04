"""Observation extraction orchestration for lake satellite analysis.

Ties together query, cloud masking, water classification, and algae
detection into a single server-side GEE pipeline. Uses the
ImageCollection.map() + single getInfo() pattern to avoid per-image
round trips.

All heavy computation happens on the GEE server. Only the final
FeatureCollection of summary statistics is transferred to the client.

Cloud selection is lake-aware: candidates are ranked by their over-lake
(AOI) cloud fraction and the stored ``cloud_pct`` is computed over the lake
polygon, not the full Sentinel-2 tile footprint.
"""

import json
import logging

import ee

from pipeline.satellite.indices import (
    classify_water_otsu,
    compute_algae_fraction,
    compute_aoi_cloud_pct,
    compute_ndwi,
    mask_clouds,
)
from pipeline.satellite.query import query_sentinel2

logger = logging.getLogger(__name__)


def lake_to_ee_geometry(lake) -> ee.Geometry:
    """Convert a Lake ORM object's boundary_geojson to a GEE Geometry.

    Parses the stored GeoJSON geometry (Polygon or MultiPolygon).
    MultiPolygons are passed through as-is so detached lake sections
    still count toward water area.

    Args:
        lake: Lake ORM instance with a .boundary_geojson text attribute.

    Returns:
        ee.Geometry suitable for GEE operations.
    """
    geom = json.loads(lake.boundary_geojson)
    # Accept full Feature objects as well as bare geometries
    if geom.get("type") == "Feature":
        geom = geom["geometry"]

    gtype = geom["type"]
    coords = geom["coordinates"]
    if gtype == "Polygon":
        return ee.Geometry.Polygon(coords)
    if gtype == "MultiPolygon":
        return ee.Geometry.MultiPolygon(coords)
    raise ValueError(f"Unsupported boundary geometry type: {gtype}")


def process_image(image: ee.Image, lake_geometry: ee.Geometry) -> ee.Feature:
    """Process a single Sentinel-2 image into observation statistics.

    This function is designed to be mapped over an ImageCollection.
    All operations are GEE server-side -- no getInfo() calls.

    Pipeline per image:
        1. Cloud mask via SCL band
        2. Compute NDWI on clear pixels
        3. Classify water via Otsu adaptive threshold
        4. Compute water area from pixel count * pixel area
        5. Compute mean NDWI over lake
        6. Compute algae fraction via NDVI on water pixels

    Args:
        image: Sentinel-2 ee.Image.
        lake_geometry: ee.Geometry of the lake polygon.

    Returns:
        ee.Feature with properties: date, cloud_pct, water_area_m2,
        mean_ndwi, algae_fraction. cloud_pct is the over-lake AOI cloud
        fraction (computed over lake_geometry, not the full tile footprint).
    """
    # 1. Cloud masking — cloud_pct scoped to the lake AOI, not the full tile
    masked_image, cloud_pct = mask_clouds(image, geometry=lake_geometry)

    # 2. NDWI on clear pixels
    ndwi = compute_ndwi(masked_image)

    # 3. Water classification with Otsu adaptive threshold
    water_mask = classify_water_otsu(ndwi, lake_geometry, scale=10)

    # 4. Water area: sum of pixel areas where water_mask = 1
    water_area = water_mask.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=lake_geometry,
        scale=10,
        maxPixels=1e9,
    ).get("NDWI")

    # 5. Mean NDWI over the lake polygon
    mean_ndwi = ndwi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=lake_geometry,
        scale=10,
        maxPixels=1e9,
    ).get("NDWI")

    # 6. Algae detection via NDVI on water pixels
    algae_fraction = compute_algae_fraction(
        masked_image, water_mask, lake_geometry, scale=10
    )

    return ee.Feature(
        None,
        {
            "date": ee.Date(image.get("system:time_start")).format("YYYY-MM-dd"),
            "cloud_pct": cloud_pct,
            "water_area_m2": water_area,
            "mean_ndwi": mean_ndwi,
            "algae_fraction": algae_fraction,
        },
    )


def _extract_best_for_month(
    lake_geometry: ee.Geometry,
    year: int,
    month: int,
) -> dict | None:
    """Extract the single best (least cloudy over the lake) observation for one month.

    Queries GEE for the month, tags each candidate with its over-lake
    (AOI) cloud fraction server-side, sorts by that metric, and processes
    only the best image. All per-image work happens inside collection.map(),
    so this stays at one lightweight getInfo() call per month.

    Returns observation dict or None if no usable image exists.
    """
    import time

    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"

    collection = query_sentinel2(lake_geometry, start, end)

    # Tag each image with its over-lake cloud fraction (server-side) and pick
    # the clearest over the lake — not the lowest tile-level cloud percentage.
    def _tag(img):
        return img.set("aoi_cloud_pct", compute_aoi_cloud_pct(img, lake_geometry))

    tagged = collection.map(_tag)
    best = tagged.sort("aoi_cloud_pct").first()

    # Check if any image exists this month
    feature = process_image(best, lake_geometry)

    for attempt in range(3):
        try:
            result = feature.getInfo()
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Too many" in err_str:
                wait = 30 * (attempt + 1)
                logger.warning("Rate limited on %d-%02d, waiting %ds...", year, month, wait)
                time.sleep(wait)
            elif any(s in err_str for s in ("No images", "empty", "null", "bucketMeans")):
                logger.debug("Skipping %d-%02d: %s", year, month, err_str[:80])
                return None
            else:
                logger.warning("GEE error for %d-%02d: %s", year, month, err_str[:120])
                return None
    else:
        logger.error("Failed after 3 retries for %d-%02d", year, month)
        return None

    if result is None or "properties" not in result:
        return None

    props = result["properties"]
    # Skip if date is None (empty collection)
    if not props.get("date"):
        return None

    return {
        "date": props.get("date"),
        "cloud_pct": props.get("cloud_pct"),
        "water_area_m2": props.get("water_area_m2"),
        "mean_ndwi": props.get("mean_ndwi"),
        "algae_fraction": props.get("algae_fraction"),
    }


def extract_observations_for_year(
    lake_geometry: ee.Geometry,
    year: int,
    months: range | list[int] | None = None,
) -> list[dict]:
    """Extract best-per-month observations for a lake in a given year.

    Instead of fetching all ~70 images and filtering later, queries
    the single image per month that is clearest over the lake (lowest
    over-lake AOI cloud fraction). This is ~12 small getInfo() calls —
    much friendlier on GEE free-tier quota. The returned cloud_pct is the
    over-lake AOI cloud fraction.

    Args:
        lake_geometry: ee.Geometry of the lake polygon.
        year: Calendar year to process (e.g. 2024).
        months: Optional subset of months (1-12) to query. Defaults to the
            whole year. Incremental ingestion uses this to avoid re-querying
            months that are already stored.

    Returns:
        List of dicts (up to 12) with keys: date, cloud_pct,
        water_area_m2, mean_ndwi, algae_fraction.
    """
    import time

    logger.info("Extracting best-per-month observations for year %d", year)

    observations = []
    for month in months if months is not None else range(1, 13):
        obs = _extract_best_for_month(lake_geometry, year, month)
        if obs:
            observations.append(obs)
            logger.info("  %d-%02d: %s (cloud %.0f%%)",
                        year, month, obs["date"], (obs.get("cloud_pct") or 0) * 100)
        else:
            logger.info("  %d-%02d: no usable image", year, month)
        # Brief pause between months to stay under rate limits
        time.sleep(2)

    logger.info("Extracted %d observations for year %d", len(observations), year)
    return observations
