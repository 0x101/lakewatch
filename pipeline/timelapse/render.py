"""NDWI colormap frame rendering with true-color base and text overlay.

Reads a 4-band GeoTIFF (NDWI, B4, B3, B2), renders NDWI as a colormap
overlay on the true-color Sentinel-2 base image, and adds date/lake name
text labels using Pillow.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import Normalize
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def render_frame(
    geotiff_path: Path,
    output_path: Path,
    lake_name: str,
    observation_date: str,
    colormap: str = "RdYlGn",
    alpha: float = 0.6,
) -> Path:
    """Render an NDWI colormap frame overlaid on true-color Sentinel-2 base.

    Reads a 4-band GeoTIFF where:
        Band 1: NDWI values (-1 to 1)
        Bands 2-4: B4 (Red), B3 (Green), B2 (Blue) surface reflectance

    Water pixels (NDWI > 0) get the colormap overlay blended with the
    true-color base. Non-water pixels show the true-color image only.

    Args:
        geotiff_path: Path to the 4-band GeoTIFF.
        output_path: Path for the output PNG frame.
        lake_name: Lake name for the top-left text overlay.
        observation_date: Date string for the bottom-left text overlay.
        colormap: Matplotlib colormap name. Default "RdYlGn".
        alpha: Blend factor for NDWI overlay on water pixels. Default 0.6.

    Returns:
        Path to the rendered PNG frame.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(geotiff_path) as src:
        ndwi = src.read(1).astype(np.float32)
        b4 = src.read(2).astype(np.float32)  # Red
        b3 = src.read(3).astype(np.float32)  # Green
        b2 = src.read(4).astype(np.float32)  # Blue

    # Normalize RGB from Sentinel-2 surface reflectance to 0-1
    # Sentinel-2 L2A values are typically 0-10000, divide by 3000 for good contrast
    rgb = np.stack(
        [
            np.clip(b4 / 3000.0, 0, 1),
            np.clip(b3 / 3000.0, 0, 1),
            np.clip(b2 / 3000.0, 0, 1),
        ],
        axis=-1,
    )

    # Apply colormap to NDWI
    cmap = plt.get_cmap(colormap)
    norm = Normalize(vmin=-0.5, vmax=1.0)
    ndwi_colored = cmap(norm(ndwi))[:, :, :3]  # Drop alpha channel

    # Water mask: NDWI > 0 indicates water
    water_mask = ndwi > 0.0

    # Composite: blend colormap with true-color on water pixels
    composite = rgb.copy()
    for c in range(3):
        composite[:, :, c] = np.where(
            water_mask,
            (1 - alpha) * rgb[:, :, c] + alpha * ndwi_colored[:, :, c],
            rgb[:, :, c],
        )

    # Render with matplotlib
    fig, ax = plt.subplots(1, 1, figsize=(8, 6), dpi=150)
    ax.imshow(composite)
    ax.axis("off")
    fig.savefig(str(output_path), bbox_inches="tight", pad_inches=0, dpi=150)
    plt.close(fig)

    # Add text overlay
    _add_text_overlay(output_path, lake_name, observation_date)

    logger.info("Rendered frame: %s", output_path)
    return output_path


def _add_text_overlay(image_path: Path, lake_name: str, date_str: str) -> None:
    """Add lake name and date text overlay to a rendered frame.

    Places the lake name in the top-left corner and the date in the
    bottom-left corner, both in white with black stroke for readability.

    Args:
        image_path: Path to the PNG image to overlay text on.
        lake_name: Lake name for top-left.
        date_str: Date string for bottom-left.
    """
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # Try system font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except (OSError, IOError):
        font = ImageFont.load_default(size=24)

    # Top-left: lake name
    draw.text(
        (10, 10),
        lake_name,
        fill="white",
        font=font,
        stroke_width=2,
        stroke_fill="black",
    )

    # Bottom-left: date
    draw.text(
        (10, img.height - 40),
        date_str,
        fill="white",
        font=font,
        stroke_width=2,
        stroke_fill="black",
    )

    # Watermark: bottom-right
    _add_watermark(draw, img, font)

    img.save(image_path)


def _add_watermark(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text: str = "LakeWatch",
) -> None:
    """Add a subtle watermark in the bottom-right corner."""
    try:
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except (OSError, IOError):
        small_font = ImageFont.load_default(size=14)

    bbox = draw.textbbox((0, 0), text, font=small_font)
    tw = bbox[2] - bbox[0]
    x = img.width - tw - 12
    y = img.height - 24

    draw.text(
        (x, y),
        text,
        fill=(255, 255, 255, 140),
        font=small_font,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 100),
    )
