"""GEE GeoTIFF export for timelapse frame generation.

Downloads multi-band GeoTIFFs (NDWI + RGB) from Google Earth Engine
via getDownloadURL. Each export contains 4 bands: NDWI, B4 (Red),
B3 (Green), B2 (Blue) at 10m resolution.
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

import ee

from pipeline.satellite.indices import compute_aoi_cloud_pct
from pipeline.satellite.query import query_sentinel2

logger = logging.getLogger(__name__)


def get_image_for_date(geometry: ee.Geometry, target_date: str) -> ee.Image:
    """Get the image clearest over the lake near a target date.

    Queries progressively wider windows (1 day → 5 → 15 → 30) until
    an image is found. Within each window, ranks candidates by their
    over-lake (AOI) cloud fraction — not the tile-level cloud percentage —
    and returns the one clearest directly over the lake polygon.

    The over-lake ranking is done server-side via collection.map(), so the
    quota cost stays at a single size().getInfo() per window.

    Args:
        geometry: GEE geometry of the lake polygon (also used to filter bounds).
        target_date: ISO date string, e.g. "2024-01-15".

    Returns:
        ee.Image with the lowest over-lake cloud cover near that date.

    Raises:
        RuntimeError: If no image found within 30 days.
    """
    dt = datetime.strptime(target_date, "%Y-%m-%d")

    for window_days in [1, 5, 15, 30]:
        start = (dt - timedelta(days=window_days // 2)).strftime("%Y-%m-%d")
        end = (dt + timedelta(days=max(window_days // 2, 1))).strftime("%Y-%m-%d")

        collection = query_sentinel2(geometry, start, end)
        count = collection.size().getInfo()

        if count > 0:
            if window_days > 1:
                logger.info(
                    "No image on %s, found %d within ±%d days",
                    target_date, count, window_days // 2,
                )
            # Tag each candidate with its over-lake cloud fraction (server-side)
            # and pick the clearest over the lake.
            tagged = collection.map(
                lambda img: img.set(
                    "aoi_cloud_pct", compute_aoi_cloud_pct(img, geometry)
                )
            )
            return tagged.sort("aoi_cloud_pct").first()

    raise RuntimeError(f"No Sentinel-2 image found within 30 days of {target_date}")


def export_observation_geotiff(
    image: ee.Image,
    geometry: ee.Geometry,
    observation_date: str,
    output_dir: Path,
) -> Path:
    """Export a multi-band GeoTIFF (NDWI + RGB) from GEE.

    Computes NDWI server-side and bundles it with the true-color
    RGB bands (B4, B3, B2) into a single 4-band GeoTIFF download.

    Args:
        image: Sentinel-2 ee.Image to export.
        geometry: ee.Geometry defining the export region.
        observation_date: ISO date string for filename.
        output_dir: Local directory for the downloaded GeoTIFF.

    Returns:
        Path to the downloaded GeoTIFF file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{observation_date}.tif"

    if output_path.exists():
        logger.info("GeoTIFF already exists: %s", output_path)
        return output_path

    # Compute NDWI server-side: (B3 - B8) / (B3 + B8)
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("NDWI")

    # Bundle NDWI + true-color RGB bands
    export_image = ndwi.addBands(image.select(["B4", "B3", "B2"]))

    logger.info("Requesting GeoTIFF download for %s", observation_date)

    url = export_image.getDownloadURL(
        {
            "bands": ["NDWI", "B4", "B3", "B2"],
            "region": geometry,
            "scale": 10,
            "format": "GEO_TIFF",
        }
    )

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    output_path.write_bytes(response.content)
    logger.info("Saved GeoTIFF: %s (%d bytes)", output_path, len(response.content))

    # Rate limit: 1.5s between exports to avoid GEE throttling
    time.sleep(1.5)

    return output_path
