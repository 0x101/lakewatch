"""Satellite imagery processing modules for GEE-based lake analysis."""

from pipeline.satellite.extract import extract_observations_for_year, lake_to_ee_geometry
from pipeline.satellite.indices import (
    classify_water_otsu,
    compute_algae_fraction,
    compute_ndwi,
    mask_clouds,
    otsu_threshold,
)
from pipeline.satellite.query import query_sentinel2

__all__ = [
    "extract_observations_for_year",
    "lake_to_ee_geometry",
    "classify_water_otsu",
    "compute_algae_fraction",
    "compute_ndwi",
    "mask_clouds",
    "otsu_threshold",
    "query_sentinel2",
]
