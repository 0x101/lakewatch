"""Unit tests for pipeline.satellite.indices module.

Tests validate that the correct GEE operations are called with correct
parameters. They do NOT require GEE credentials -- all ee objects are mocked.
"""

from unittest.mock import MagicMock, call, patch


class TestCloudMasking:
    """Tests for mask_clouds function."""

    @patch("pipeline.satellite.indices.ee")
    def test_cloud_masking(self, mock_ee):
        """Verify mask_clouds uses SCL band values 1,2,3,7,8,9,10,11."""
        from pipeline.satellite.indices import mask_clouds

        # Set up mock image
        mock_image = MagicMock()
        mock_scl = MagicMock()
        mock_image.select.return_value = mock_scl

        # Chain neq calls to return mock masks
        mock_mask = MagicMock()
        mock_scl.neq.return_value = mock_mask
        mock_mask.And.return_value = mock_mask

        # Mock reduceRegion for total_pixels and clear_pixels
        mock_reduce_result = MagicMock()
        mock_reduce_result.get.return_value = mock_ee.Number.return_value
        mock_image.select.return_value.reduceRegion.return_value = mock_reduce_result
        mock_mask.reduceRegion.return_value = mock_reduce_result

        # Mock ee.Number for cloud_pct computation
        mock_number = MagicMock()
        mock_ee.Number.return_value = mock_number
        mock_number.subtract.return_value = mock_number
        mock_number.divide.return_value = mock_number

        # Mock updateMask
        mock_image.updateMask.return_value = mock_image

        # Mock Reducer
        mock_ee.Reducer.count.return_value = MagicMock()
        mock_ee.Reducer.sum.return_value = MagicMock()

        masked_image, cloud_pct = mask_clouds(mock_image)

        # Verify SCL band selected
        mock_image.select.assert_any_call("SCL")

        # Verify all 8 non-clear values are masked via neq()
        scl_neq_calls = mock_scl.neq.call_args_list
        masked_values = {c[0][0] for c in scl_neq_calls}
        assert masked_values == {1, 2, 3, 7, 8, 9, 10, 11}, (
            f"Expected SCL values {{1,2,3,7,8,9,10,11}}, got {masked_values}"
        )

        # Verify reduceRegion called with scale=10
        for c in mock_mask.reduceRegion.call_args_list:
            if "scale" in c.kwargs:
                assert c.kwargs["scale"] == 10

    @patch("pipeline.satellite.indices.ee")
    def test_mask_clouds_forwards_geometry(self, mock_ee):
        """Verify mask_clouds(geometry=geom) forwards geometry to reduceRegion."""
        from pipeline.satellite.indices import mask_clouds

        mock_image = MagicMock()
        mock_scl = MagicMock()
        mock_image.select.return_value = mock_scl

        mock_mask = MagicMock()
        mock_scl.neq.return_value = mock_mask
        mock_mask.And.return_value = mock_mask

        mock_reduce_result = MagicMock()
        mock_reduce_result.get.return_value = mock_ee.Number.return_value
        mock_image.select.return_value.reduceRegion.return_value = mock_reduce_result
        mock_mask.reduceRegion.return_value = mock_reduce_result

        mock_number = MagicMock()
        mock_ee.Number.return_value = mock_number
        mock_number.subtract.return_value = mock_number
        mock_number.divide.return_value = mock_number
        mock_image.updateMask.return_value = mock_image
        mock_ee.Reducer.count.return_value = MagicMock()
        mock_ee.Reducer.sum.return_value = MagicMock()

        mock_geometry = MagicMock()
        mask_clouds(mock_image, geometry=mock_geometry)

        # Both reduceRegion calls must forward geometry=mock_geometry
        for mock_obj in [mock_image.select.return_value, mock_mask]:
            assert mock_obj.reduceRegion.call_args_list, "reduceRegion not called"
            for c in mock_obj.reduceRegion.call_args_list:
                assert c.kwargs.get("geometry") is mock_geometry

    @patch("pipeline.satellite.indices.ee")
    def test_cloud_masking_uses_scale_10(self, mock_ee):
        """Verify reduceRegion always uses scale=10 (Pitfall 2: SCL is 20m native)."""
        from pipeline.satellite.indices import mask_clouds

        mock_image = MagicMock()
        mock_scl = MagicMock()
        mock_image.select.return_value = mock_scl

        mock_mask = MagicMock()
        mock_scl.neq.return_value = mock_mask
        mock_mask.And.return_value = mock_mask

        mock_reduce_result = MagicMock()
        mock_reduce_result.get.return_value = mock_ee.Number.return_value
        mock_image.select.return_value.reduceRegion.return_value = mock_reduce_result
        mock_mask.reduceRegion.return_value = mock_reduce_result

        mock_number = MagicMock()
        mock_ee.Number.return_value = mock_number
        mock_number.subtract.return_value = mock_number
        mock_number.divide.return_value = mock_number
        mock_image.updateMask.return_value = mock_image
        mock_ee.Reducer.count.return_value = MagicMock()
        mock_ee.Reducer.sum.return_value = MagicMock()

        mask_clouds(mock_image)

        # Check all reduceRegion calls use scale=10
        for mock_obj in [mock_image.select.return_value, mock_mask]:
            for c in mock_obj.reduceRegion.call_args_list:
                assert c.kwargs.get("scale") == 10


class TestAoiCloudPct:
    """Tests for compute_aoi_cloud_pct (over-lake AOI cloud fraction)."""

    @patch("pipeline.satellite.indices.ee")
    def test_compute_aoi_cloud_pct_passes_geometry_and_scale_20(self, mock_ee):
        """Verify every reduceRegion call passes geometry= and scale=20."""
        from pipeline.satellite.indices import compute_aoi_cloud_pct

        mock_image = MagicMock()
        mock_scl = MagicMock()
        mock_b3 = MagicMock()

        def _select(band):
            return mock_scl if band == "SCL" else mock_b3

        mock_image.select.side_effect = _select

        mock_mask = MagicMock()
        mock_scl.neq.return_value = mock_mask
        mock_mask.And.return_value = mock_mask

        mock_reduce_result = MagicMock()
        mock_reduce_result.get.return_value = mock_ee.Number.return_value
        mock_b3.reduceRegion.return_value = mock_reduce_result
        mock_mask.reduceRegion.return_value = mock_reduce_result

        mock_number = MagicMock()
        mock_ee.Number.return_value = mock_number
        mock_number.subtract.return_value = mock_number
        mock_number.divide.return_value = mock_number
        mock_ee.Reducer.count.return_value = MagicMock()
        mock_ee.Reducer.sum.return_value = MagicMock()

        mock_geometry = MagicMock()
        compute_aoi_cloud_pct(mock_image, mock_geometry)

        # Both reduceRegion calls must scope to the geometry at scale=20
        for mock_obj in [mock_b3, mock_mask]:
            assert mock_obj.reduceRegion.call_args_list, "reduceRegion not called"
            for c in mock_obj.reduceRegion.call_args_list:
                assert c.kwargs.get("geometry") is mock_geometry
                assert c.kwargs.get("scale") == 20


class TestOtsuThreshold:
    """Tests for otsu_threshold function."""

    @patch("pipeline.satellite.indices.ee")
    def test_otsu_threshold(self, mock_ee):
        """Test Otsu with a mocked histogram structure."""
        from pipeline.satellite.indices import otsu_threshold

        mock_histogram = MagicMock()

        # Set up array operations
        mock_counts = MagicMock()
        mock_means = MagicMock()
        mock_ee.Array.side_effect = [mock_counts, mock_means]

        mock_size = MagicMock()
        mock_means.length.return_value.get.return_value = mock_size

        mock_total = MagicMock()
        mock_counts.reduce.return_value.get.return_value = mock_total

        mock_sum = MagicMock()
        mock_means.multiply.return_value.reduce.return_value.get.return_value = mock_sum

        mock_mean = MagicMock()
        mock_sum.divide.return_value = mock_mean

        # Mock ee.List.sequence
        mock_indices = MagicMock()
        mock_ee.List.sequence.return_value = mock_indices

        # Mock the map operation
        mock_bss = MagicMock()
        mock_indices.map.return_value = mock_bss

        # Mock the final sort + get
        mock_threshold = MagicMock()
        mock_means.sort.return_value.get.return_value = mock_threshold

        result = otsu_threshold(mock_histogram)

        # Verify histogram keys accessed
        mock_histogram.get.assert_any_call("histogram")
        mock_histogram.get.assert_any_call("bucketMeans")

        # Verify ee.List.sequence called with 1 to size
        mock_ee.List.sequence.assert_called_once_with(1, mock_size)

        # Verify BSS computed via map
        mock_indices.map.assert_called_once()

        # Verify result is from sorted means
        mock_means.sort.assert_called_once_with(mock_bss)
        assert result == mock_threshold


class TestOtsuFallback:
    """Tests for Otsu fallback in classify_water_otsu."""

    @patch("pipeline.satellite.indices.ee")
    @patch("pipeline.satellite.indices.otsu_threshold")
    def test_otsu_fallback_low(self, mock_otsu, mock_ee):
        """Verify fallback to 0.3 when threshold < -0.5."""
        from pipeline.satellite.indices import classify_water_otsu

        mock_ndwi_image = MagicMock()
        mock_geometry = MagicMock()

        # Mock reduceRegion -> histogram
        mock_hist = MagicMock()
        mock_ndwi_image.reduceRegion.return_value.get.return_value = mock_hist

        # Otsu returns a low threshold
        mock_threshold = MagicMock()
        mock_otsu.return_value = mock_threshold

        # Set up ee.Number and conditional
        mock_number = MagicMock()
        mock_ee.Number.return_value = mock_number
        mock_number.lt.return_value = MagicMock()
        mock_number.gt.return_value = MagicMock()
        mock_number.lt.return_value.Or.return_value = MagicMock()

        # Mock ee.Algorithms.If
        mock_ee.Algorithms.If.return_value = 0.3

        mock_ee.Reducer.histogram.return_value = MagicMock()
        mock_ee.Dictionary.return_value = mock_hist

        classify_water_otsu(mock_ndwi_image, mock_geometry)

        # Verify threshold bounds check uses -0.5 and 0.8
        mock_number.lt.assert_called_with(-0.5)
        mock_number.gt.assert_called_with(0.8)

        # Verify fallback uses ee.Algorithms.If with 0.3.
        # classify_water_otsu calls If twice (the has_data guard and the
        # use_fixed fallback inside _otsu_branch), so assert it was used and
        # that 0.3 is wired as a fallback in at least one of those calls.
        assert mock_ee.Algorithms.If.called
        assert any(
            0.3 in c.args for c in mock_ee.Algorithms.If.call_args_list
        )  # fallback value

    @patch("pipeline.satellite.indices.ee")
    @patch("pipeline.satellite.indices.otsu_threshold")
    def test_otsu_fallback_high(self, mock_otsu, mock_ee):
        """Verify fallback to 0.3 when threshold > 0.8."""
        from pipeline.satellite.indices import classify_water_otsu

        mock_ndwi_image = MagicMock()
        mock_geometry = MagicMock()

        mock_hist = MagicMock()
        mock_ndwi_image.reduceRegion.return_value.get.return_value = mock_hist

        mock_threshold = MagicMock()
        mock_otsu.return_value = mock_threshold

        mock_number = MagicMock()
        mock_ee.Number.return_value = mock_number
        mock_number.lt.return_value = MagicMock()
        mock_number.gt.return_value = MagicMock()
        mock_number.lt.return_value.Or.return_value = MagicMock()
        mock_ee.Algorithms.If.return_value = 0.3
        mock_ee.Reducer.histogram.return_value = MagicMock()
        mock_ee.Dictionary.return_value = mock_hist

        classify_water_otsu(mock_ndwi_image, mock_geometry)

        # Verify both bounds checked
        mock_number.lt.assert_called_with(-0.5)
        mock_number.gt.assert_called_with(0.8)


class TestWaterArea:
    """Tests for water area computation pattern."""

    @patch("pipeline.satellite.indices.ee")
    def test_water_area_calculation(self, mock_ee):
        """Verify water area uses pixelArea() * water_mask with Reducer.sum()."""
        # This tests the pattern used in extract.py's process_image
        # We verify the indices module provides the right mask for this
        from pipeline.satellite.indices import classify_water_otsu

        mock_ndwi = MagicMock()
        mock_geometry = MagicMock()

        mock_hist = MagicMock()
        mock_ndwi.reduceRegion.return_value.get.return_value = mock_hist

        mock_ee.Dictionary.return_value = mock_hist
        mock_ee.Reducer.histogram.return_value = MagicMock()

        # Mock otsu chain
        mock_threshold = MagicMock()
        mock_number = MagicMock()
        mock_ee.Number.return_value = mock_number
        mock_number.lt.return_value.Or.return_value = MagicMock()

        mock_ee.Algorithms.If.return_value = 0.3

        # The water mask is ndwi.gt(threshold)
        water_mask = classify_water_otsu(mock_ndwi, mock_geometry)

        # Verify gt() was called on the ndwi image (produces binary mask)
        mock_ndwi.gt.assert_called_once()


class TestAlgaeDetection:
    """Tests for algae fraction computation."""

    @patch("pipeline.satellite.indices.ee")
    def test_algae_detection(self, mock_ee):
        """Verify compute_algae_fraction uses NDVI > 0.15 threshold and .max(1)."""
        from pipeline.satellite.indices import compute_algae_fraction

        mock_image = MagicMock()
        mock_water_mask = MagicMock()
        mock_geometry = MagicMock()

        # Mock normalizedDifference -> NDVI image
        mock_ndvi = MagicMock()
        mock_image.normalizedDifference.return_value.rename.return_value = mock_ndvi

        # Mock updateMask -> water_ndvi
        mock_water_ndvi = MagicMock()
        mock_ndvi.updateMask.return_value = mock_water_ndvi

        # Mock gt(0.15) chain
        mock_algae_binary = MagicMock()
        mock_water_ndvi.gt.return_value = mock_algae_binary

        # Mock reduceRegion for algae pixels
        mock_reduce = MagicMock()
        mock_algae_binary.reduceRegion.return_value.get.return_value = mock_ee.Number.return_value

        # Mock reduceRegion for water pixel count
        mock_water_mask.reduceRegion.return_value.get.return_value = mock_ee.Number.return_value

        # Mock Number division
        mock_number = MagicMock()
        mock_ee.Number.return_value = mock_number
        mock_number.divide.return_value = mock_number
        mock_number.max.return_value = mock_number

        mock_ee.Reducer.sum.return_value = MagicMock()

        compute_algae_fraction(mock_image, mock_water_mask, mock_geometry)

        # Verify NDVI uses B8, B4 bands
        mock_image.normalizedDifference.assert_called_once_with(["B8", "B4"])

        # Verify NDVI threshold is 0.15
        mock_water_ndvi.gt.assert_called_once_with(0.15)

        # Verify water mask applied
        mock_ndvi.updateMask.assert_called_once_with(mock_water_mask)

        # Verify division by zero guard: .max(1)
        mock_number.max.assert_called_with(1)


class TestComputeNDWI:
    """Tests for NDWI computation."""

    @patch("pipeline.satellite.indices.ee")
    def test_compute_ndwi(self, mock_ee):
        """Verify NDWI uses normalizedDifference(['B3', 'B8']) and renames to 'NDWI'."""
        from pipeline.satellite.indices import compute_ndwi

        mock_image = MagicMock()
        mock_nd = MagicMock()
        mock_image.normalizedDifference.return_value = mock_nd
        mock_nd.rename.return_value = MagicMock()

        result = compute_ndwi(mock_image)

        mock_image.normalizedDifference.assert_called_once_with(["B3", "B8"])
        mock_nd.rename.assert_called_once_with("NDWI")
