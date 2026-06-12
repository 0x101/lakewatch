"""Sentinel-2 ImageCollection querying via Google Earth Engine.

Provides filtered access to the COPERNICUS/S2_SR_HARMONIZED collection
by geographic bounds and date range. All operations are server-side --
no getInfo() calls happen here.
"""

import logging

import ee

logger = logging.getLogger(__name__)


def query_sentinel2(
    geometry: ee.Geometry,
    start_date: str,
    end_date: str,
) -> ee.ImageCollection:
    """Query Sentinel-2 L2A imagery for a geometry and date range.

    Uses the harmonized Surface Reflectance collection which provides
    consistent band naming across the entire Sentinel-2 archive.

    Args:
        geometry: GEE geometry (polygon or point) to filter by bounds.
        start_date: ISO date string, e.g. "2024-01-01".
        end_date: ISO date string, e.g. "2024-12-31".

    Returns:
        Filtered ee.ImageCollection (lazy -- no server call until evaluated).
    """
    logger.info("Querying S2_SR_HARMONIZED: %s to %s", start_date, end_date)

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )

    return collection
