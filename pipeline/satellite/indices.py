"""Index computation and classification for satellite imagery.

All functions operate on GEE server-side objects (ee.Image, ee.Number, etc.).
No getInfo() calls -- these are designed to be used inside ImageCollection.map().

Implements:
- Cloud masking via SCL band (D-03)
- NDWI computation for water detection
- Otsu adaptive threshold for water classification (D-04)
- Fallback to fixed threshold when Otsu is unreliable (D-05)
- NDVI-based algae fraction on water pixels (D-06)
"""

import logging

import ee

logger = logging.getLogger(__name__)


def _clear_mask(scl: ee.Image) -> ee.Image:
    """Build the SCL clear-sky mask (1=clear, 0=cloud/shadow/snow).

    A pixel is clear when it does NOT match any of the non-clear SCL
    classes 1,2,3,7,8,9,10,11.
    """
    return (
        scl.neq(1)
        .And(scl.neq(2))
        .And(scl.neq(3))
        .And(scl.neq(7))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )


def compute_aoi_cloud_pct(
    image: ee.Image,
    geometry: ee.Geometry,
    scale: int = 20,
) -> ee.Number:
    """Compute the over-lake (AOI) cloud fraction for an image.

    Builds the same SCL clear-mask as ``mask_clouds`` (non-clear classes
    1,2,3,7,8,9,10,11) and returns the fraction of non-clear pixels within
    the supplied lake geometry. Both reduceRegion calls are scoped to
    ``geometry`` at ``scale=20`` (SCL is 20m native), so the metric reflects
    cloud cover directly over the water rather than over the whole tile.

    This is a server-side ee.Number — no getInfo() — so it can be set as a
    property inside ImageCollection.map() and used for sorting candidates by
    over-lake cloudiness without per-image round trips.

    Args:
        image: Sentinel-2 ee.Image with SCL and B3 bands.
        geometry: Lake polygon ee.Geometry to scope the computation to.
        scale: Pixel resolution in meters (default 20, SCL native).

    Returns:
        ee.Number -- over-lake cloud fraction in [0, 1].
    """
    scl = image.select("SCL")
    clear_mask = _clear_mask(scl)

    total_pixels = ee.Number(
        image.select("B3")
        .reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=geometry,
            scale=scale,
            maxPixels=1e9,
        )
        .get("B3")
    )

    clear_pixels = ee.Number(
        clear_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=scale,
            maxPixels=1e9,
        )
        .get("SCL")
    )

    return ee.Number(1).subtract(clear_pixels.divide(total_pixels))


def mask_clouds(
    image: ee.Image,
    geometry: ee.Geometry | None = None,
) -> tuple[ee.Image, ee.Number]:
    """Mask clouds using the Scene Classification Layer (SCL) band.

    SCL non-clear values (masked out):
        1: Saturated/defective
        2: Dark area pixels
        3: Cloud shadows
        7: Unclassified
        8: Cloud medium probability
        9: Cloud high probability
        10: Thin cirrus
        11: Snow/ice

    The SCL masking logic (D-03) is unchanged. When ``geometry`` is supplied,
    the returned ``cloud_pct`` is the over-lake AOI cloud fraction (both
    reduceRegion calls are scoped to the lake polygon); when ``geometry`` is
    None the cloud_pct is computed over the full image footprint exactly as
    before, so existing callers are unaffected.

    Args:
        image: Sentinel-2 ee.Image with SCL band.
        geometry: Optional lake polygon ee.Geometry. When provided, cloud_pct
            is scoped to the lake (over-lake AOI fraction); when None, cloud_pct
            is computed over the full image footprint.

    Returns:
        Tuple of (masked_image, cloud_pct) where cloud_pct is the 0-1 fraction
        of non-clear pixels over the lake AOI (if geometry given) or the full
        image extent (if not).
    """
    scl = image.select("SCL")

    # Build clear-sky mask: pixel is clear if it does NOT match any cloud/shadow class
    clear_mask = _clear_mask(scl)

    # Compute cloud percentage over the lake AOI (if geometry) or full footprint.
    # Pitfall 2: SCL is 20m native but we force scale=10 for consistency
    total_pixels = ee.Number(
        image.select("B3")
        .reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=geometry,
            scale=10,
            maxPixels=1e9,
        )
        .get("B3")
    )

    clear_pixels = ee.Number(
        clear_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=10,
            maxPixels=1e9,
        )
        .get("SCL")
    )

    cloud_pct = ee.Number(1).subtract(clear_pixels.divide(total_pixels))

    masked_image = image.updateMask(clear_mask)

    return masked_image, cloud_pct


def compute_ndwi(image: ee.Image) -> ee.Image:
    """Compute Normalized Difference Water Index (NDWI).

    NDWI = (B3 - B8) / (B3 + B8)
    where B3 = Green, B8 = NIR.

    Higher values indicate water presence.

    Args:
        image: Sentinel-2 ee.Image with B3 and B8 bands.

    Returns:
        Single-band ee.Image named "NDWI" with values in [-1, 1].
    """
    return image.normalizedDifference(["B3", "B8"]).rename("NDWI")


def otsu_threshold(histogram: ee.Dictionary) -> ee.Number:
    """Compute Otsu's optimal threshold from a GEE histogram.

    Runs entirely server-side using ee.Array operations.
    Maximizes between-class variance to find the threshold that
    best separates a bimodal distribution (water vs. land).

    Args:
        histogram: ee.Dictionary with 'histogram' (counts) and
            'bucketMeans' (bin centers) from ee.Reducer.histogram().

    Returns:
        ee.Number -- the optimal threshold value.
    """
    counts = ee.Array(histogram.get("histogram"))
    means = ee.Array(histogram.get("bucketMeans"))
    size = means.length().get([0])
    total = counts.reduce(ee.Reducer.sum(), [0]).get([0])
    sum_val = means.multiply(counts).reduce(ee.Reducer.sum(), [0]).get([0])
    mean = sum_val.divide(total)

    indices = ee.List.sequence(1, size)

    def compute_bss(i):
        """Compute between-class sum of squares for split at index i."""
        i = ee.Number(i).int()
        a_counts = counts.slice(0, 0, i)
        a_count = a_counts.reduce(ee.Reducer.sum(), [0]).get([0])
        a_means = means.slice(0, 0, i)
        a_mean = (
            a_means.multiply(a_counts)
            .reduce(ee.Reducer.sum(), [0])
            .get([0])
            .divide(a_count)
        )
        b_count = total.subtract(a_count)
        b_mean = sum_val.subtract(a_count.multiply(a_mean)).divide(b_count)
        return a_count.multiply(a_mean.subtract(mean).pow(2)).add(
            b_count.multiply(b_mean.subtract(mean).pow(2))
        )

    bss = indices.map(compute_bss)
    return means.sort(bss).get([-1])


def classify_water_otsu(
    ndwi_image: ee.Image,
    geometry: ee.Geometry,
    scale: int = 10,
) -> ee.Image:
    """Classify water pixels using Otsu's adaptive threshold.

    Computes a histogram of NDWI values over the geometry, finds the
    optimal threshold via Otsu's method, then falls back to a fixed
    threshold of 0.3 if Otsu gives an unreasonable value.

    Fallback conditions (D-05):
        - threshold < -0.5 (nonsensical, likely no bimodal distribution)
        - threshold > 0.8 (too high, would miss most water)

    Args:
        ndwi_image: Single-band NDWI ee.Image.
        geometry: Lake polygon ee.Geometry for histogram computation.
        scale: Pixel resolution in meters (default 10).

    Returns:
        Binary ee.Image (1=water, 0=not water).
    """
    hist_result = ndwi_image.reduceRegion(
        reducer=ee.Reducer.histogram(255, 2),
        geometry=geometry,
        scale=scale,
        maxPixels=1e9,
    ).get("NDWI")

    # Guard against empty histogram (fully cloudy image, no clear pixels).
    # ee.Algorithms.If checks if the histogram dict contains bucketMeans.
    has_data = ee.Dictionary(hist_result).contains("bucketMeans")

    def _otsu_branch():
        histogram = ee.Dictionary(hist_result)
        threshold = otsu_threshold(histogram)
        threshold = ee.Number(threshold)
        use_fixed = threshold.lt(-0.5).Or(threshold.gt(0.8))
        return ee.Number(ee.Algorithms.If(use_fixed, 0.3, threshold))

    final_threshold = ee.Number(
        ee.Algorithms.If(has_data, _otsu_branch(), 0.3)
    )

    return ndwi_image.gt(final_threshold)


def compute_algae_fraction(
    image: ee.Image,
    water_mask: ee.Image,
    geometry: ee.Geometry,
    scale: int = 10,
) -> ee.Number:
    """Compute algae fraction on water pixels using NDVI.

    NDVI = (B8 - B4) / (B8 + B4)
    Pixels with NDVI > 0.15 on water areas indicate algae/eutrophication.

    Args:
        image: Sentinel-2 ee.Image with B8 and B4 bands.
        water_mask: Binary water mask (1=water, 0=land).
        geometry: Lake polygon ee.Geometry.
        scale: Pixel resolution in meters (default 10).

    Returns:
        ee.Number -- fraction of water pixels with algae (0 to 1).
        Returns 0 if no water pixels (division by zero guarded with .max(1)).
    """
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    water_ndvi = ndvi.updateMask(water_mask)

    # Count water pixels with NDVI > 0.15 (algae indicator)
    algae_pixels = ee.Number(
        water_ndvi.gt(0.15)
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=scale,
            maxPixels=1e9,
        )
        .get("NDVI")
    )

    water_pixel_count = ee.Number(
        water_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=scale,
            maxPixels=1e9,
        )
        .get("NDWI")
    )

    # Guard against division by zero when lake is fully cloudy
    return algae_pixels.divide(water_pixel_count.max(1))
