"""Tests for timelapse frame rendering."""


import numpy as np
import pytest
import rasterio
from PIL import Image
from rasterio.transform import from_bounds

from pipeline.timelapse.render import render_frame


@pytest.fixture
def sample_geotiff(tmp_path):
    """Create a synthetic 4-band GeoTIFF for testing.

    Band 1: NDWI values ranging from -0.5 to 1.0
    Bands 2-4: RGB values around 1500 (mid-range Sentinel-2)
    """
    tif_path = tmp_path / "sample_ndwi.tif"
    height, width = 20, 20
    transform = from_bounds(77.63, 12.92, 77.64, 12.93, width, height)

    # Band 1: NDWI gradient from -0.5 to 1.0
    ndwi = np.linspace(-0.5, 1.0, height * width, dtype=np.float32).reshape(
        height, width
    )

    # Bands 2-4: Simulated Sentinel-2 surface reflectance (~1500)
    b4 = np.full((height, width), 1500, dtype=np.float32)  # Red
    b3 = np.full((height, width), 1800, dtype=np.float32)  # Green
    b2 = np.full((height, width), 1200, dtype=np.float32)  # Blue

    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=4,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(ndwi, 1)
        dst.write(b4, 2)
        dst.write(b3, 3)
        dst.write(b2, 4)

    return tif_path


def test_render_frame_creates_png(sample_geotiff, tmp_path):
    """render_frame should produce a valid PNG file."""
    output = tmp_path / "frame.png"
    result = render_frame(
        sample_geotiff,
        output,
        lake_name="Bellandur Lake",
        observation_date="2024-01-15",
    )

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0

    # Verify it's a valid image
    img = Image.open(output)
    assert img.format == "PNG"


def test_render_frame_has_text_overlay(sample_geotiff, tmp_path):
    """Rendered frame should have reasonable dimensions for text overlay."""
    output = tmp_path / "frame_overlay.png"
    render_frame(
        sample_geotiff,
        output,
        lake_name="Bellandur Lake",
        observation_date="2024-01-15",
    )

    img = Image.open(output)
    # At 150 DPI with figsize=(8,6), expect at least 100x100
    assert img.width > 100
    assert img.height > 100


def test_render_frame_custom_colormap(sample_geotiff, tmp_path):
    """render_frame should accept alternative colormaps without error."""
    output = tmp_path / "frame_viridis.png"
    result = render_frame(
        sample_geotiff,
        output,
        lake_name="Ulsoor Lake",
        observation_date="2024-06-01",
        colormap="viridis",
    )

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0
