"""Integration tests for satellite pipeline (require GEE credentials).

These tests are marked with @pytest.mark.integration and will be
skipped when GEE credentials are not configured.
"""

import pytest

# Skip entire module if ee is not available or not authenticated
try:
    import ee

    ee.Initialize()
    GEE_AVAILABLE = True
except Exception:
    GEE_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not GEE_AVAILABLE, reason="GEE credentials not configured")
class TestQueryBellandur:
    """Integration tests for Sentinel-2 querying."""

    def test_query_bellandur(self):
        """Query Sentinel-2 for Bellandur Lake bbox and verify non-empty results."""
        from pipeline.satellite.query import query_sentinel2

        # Bellandur Lake approximate bounding box
        bbox = ee.Geometry.Rectangle([77.63, 12.92, 77.70, 12.95])

        collection = query_sentinel2(bbox, "2024-01-01", "2024-01-31")
        size = collection.size().getInfo()

        assert size > 0, "Expected at least one Sentinel-2 image for Bellandur in Jan 2024"


@pytest.mark.integration
@pytest.mark.skipif(not GEE_AVAILABLE, reason="GEE credentials not configured")
class TestExtractSingleYear:
    """Integration tests for full observation extraction."""

    def test_extract_single_year(self):
        """Extract observations for Bellandur 2024 and verify output shape."""
        from pipeline.satellite.extract import extract_observations_for_year

        # Bellandur Lake approximate bounding box
        bbox = ee.Geometry.Rectangle([77.63, 12.92, 77.70, 12.95])

        observations = extract_observations_for_year(bbox, 2024)

        assert isinstance(observations, list)
        assert len(observations) > 0, "Expected observations for Bellandur 2024"

        # Verify each observation has expected keys. The key set is unchanged
        # by the AOI-aware cloud work; cloud_pct is now the over-lake (AOI)
        # cloud fraction rather than the tile-level value, but the shape is the same.
        expected_keys = {"date", "cloud_pct", "water_area_m2", "mean_ndwi", "algae_fraction"}
        for obs in observations:
            assert set(obs.keys()) == expected_keys, f"Unexpected keys: {set(obs.keys())}"
            assert obs["date"] is not None, "Date should never be None"
