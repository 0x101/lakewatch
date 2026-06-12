"""GIF and video assembly with size optimization.

Assembles rendered PNG frames into shareable GIF and video artifacts.
GIF in two sizes: full (<15MB for Twitter) and share (<5MB for WhatsApp).
Video as two-pass H.264 MP4 with optional royalty-free background music.

Place a royalty-free MP3 at pipeline/assets/music/ambient-track.mp3.
Download from Pixabay (CC0, no attribution required).
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import imageio.v3 as iio
import numpy as np
from PIL import Image
from pygifsicle import optimize as gifsicle_optimize

logger = logging.getLogger(__name__)

# Watermark stamped onto timelapse frames. Set LAKEWATCH_WATERMARK to your
# brand (e.g. "Namma Lakes"); defaults to the project name.
WATERMARK_TEXT = os.getenv("LAKEWATCH_WATERMARK", "LakeWatch")


def _stamp_watermark(img: Image.Image, text: str = WATERMARK_TEXT) -> None:
    """Add a subtle watermark to the bottom-right of a PIL Image (in-place)."""
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except (OSError, IOError):
            font = ImageFont.load_default(size=14)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = img.width - tw - 12
    y = img.height - 24
    draw.text(
        (x, y), text,
        fill=(255, 255, 255, 140),
        font=font,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 100),
    )


def assemble_gif(
    frame_paths: list[Path],
    output_path: Path,
    duration_ms: int = 200,
    max_size_mb: float = 15.0,
    target_width: int | None = None,
) -> Path:
    """Assemble PNG frames into an optimized animated GIF.

    Loads frames, optionally resizes them, writes a raw GIF with imageio,
    then optimizes with gifsicle. If the result exceeds max_size_mb,
    applies lossy compression with reduced color palette.

    Args:
        frame_paths: Ordered list of PNG frame paths.
        output_path: Where to write the output GIF.
        duration_ms: Duration per frame in milliseconds. Default 200.
        max_size_mb: Maximum file size target in MB. Default 15.0.
        target_width: If set, resize all frames to this width (maintain aspect ratio).

    Returns:
        Path to the output GIF.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frames = []
    for path in sorted(frame_paths):
        img = Image.open(path)
        if target_width:
            ratio = target_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize(
                (target_width, new_height),
                Image.Resampling.LANCZOS,
            )
        # Add watermark to each frame
        _stamp_watermark(img)
        frames.append(np.array(img))

    # Write raw GIF with imageio v3 API
    iio.imwrite(
        output_path,
        frames,
        extension=".gif",
        duration=duration_ms,
        loop=0,
    )

    # Optimize with gifsicle (lossless first pass)
    gifsicle_optimize(str(output_path))

    # Check size and apply lossy compression if needed
    size_mb = output_path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        logger.info(
            "GIF %.1fMB exceeds %.1fMB target, applying lossy compression (128 colors)",
            size_mb,
            max_size_mb,
        )
        subprocess.run(
            [
                "gifsicle",
                "--lossy=80",
                "--colors",
                "128",
                "-O3",
                str(output_path),
                "-o",
                str(output_path),
            ],
            check=True,
        )

    # If still too large, try 64 colors
    size_mb = output_path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        logger.warning(
            "GIF still %.1fMB after 128 colors, reducing to 64 colors",
            size_mb,
        )
        subprocess.run(
            [
                "gifsicle",
                "--lossy=80",
                "--colors",
                "64",
                "-O3",
                str(output_path),
                "-o",
                str(output_path),
            ],
            check=True,
        )

    final_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("GIF assembled: %s (%.2fMB)", output_path.name, final_size_mb)
    return output_path


def generate_gif_versions(
    frame_paths: list[Path],
    output_dir: Path,
    lake_id: str,
) -> tuple[Path, Path]:
    """Generate full and share GIF versions of a timelapse.

    Full version: original resolution, <15MB target (Twitter).
    Share version: 400px wide, <5MB target (WhatsApp).

    Args:
        frame_paths: Ordered list of PNG frame paths.
        output_dir: Directory for output GIFs.
        lake_id: Lake identifier for filenames.

    Returns:
        Tuple of (full_path, share_path).
    """
    full_path = assemble_gif(
        frame_paths,
        output_dir / f"{lake_id}-timelapse-full.gif",
        duration_ms=200,
        max_size_mb=15.0,
    )
    share_path = assemble_gif(
        frame_paths,
        output_dir / f"{lake_id}-timelapse-share.gif",
        duration_ms=200,
        max_size_mb=5.0,
        target_width=400,
    )
    return (full_path, share_path)


def generate_thumbnail(
    frame_paths: list[Path],
    output_path: Path,
) -> Path:
    """Generate a thumbnail from the most recent (last) frame.

    Opens the last frame, resizes to fit within 800x600 using
    high-quality LANCZOS resampling, and saves as PNG.

    Args:
        frame_paths: Ordered list of PNG frame paths (last = most recent).
        output_path: Where to write the thumbnail PNG.

    Returns:
        Path to the thumbnail.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_frame = Image.open(frame_paths[-1])
    last_frame.thumbnail((800, 600), Image.Resampling.LANCZOS)
    last_frame.save(output_path, "PNG")

    logger.info("Thumbnail generated: %s", output_path.name)
    return output_path


def assemble_video(
    frame_dir: Path,
    output_path: Path,
    music_path: Path | None = None,
    fps: int = 6,
    bitrate: str = "2M",
) -> Path:
    """Assemble PNG frames into H.264 MP4 video using two-pass ffmpeg encoding.

    Frames must be named with ISO dates (YYYY-MM-DD.png) so that alphabetical
    glob ordering matches chronological order.

    Args:
        frame_dir: Directory containing PNG frames (globbed as *.png).
        output_path: Where to write the output MP4.
        music_path: Optional path to a background music file. If provided
            and the file exists, audio is overlaid with -shortest flag.
        fps: Frames per second. Default 6.
        bitrate: Target video bitrate. Default "2M".

    Returns:
        Path to the output MP4.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    input_pattern = str(frame_dir / "*.png")

    # Pass 1: analysis
    pass1_cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-pattern_type",
        "glob",
        "-i",
        input_pattern,
        "-c:v",
        "libx264",
        "-b:v",
        bitrate,
        "-pix_fmt",
        "yuv420p",
        "-pass",
        "1",
        "-f",
        "mp4",
        "/dev/null",
    ]
    logger.info("ffmpeg Pass 1 (analysis): %s", " ".join(pass1_cmd))
    subprocess.run(pass1_cmd, check=True, capture_output=True)

    # Pass 2: encode (with optional music)
    pass2_cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-pattern_type",
        "glob",
        "-i",
        input_pattern,
    ]

    if music_path and Path(music_path).exists():
        pass2_cmd.extend(["-i", str(music_path)])

    pass2_cmd.extend(
        [
            "-c:v",
            "libx264",
            "-b:v",
            bitrate,
            "-pix_fmt",
            "yuv420p",
            "-pass",
            "2",
        ]
    )

    if music_path and Path(music_path).exists():
        pass2_cmd.extend(["-c:a", "aac", "-b:a", "128k", "-shortest"])

    pass2_cmd.append(str(output_path))

    logger.info("ffmpeg Pass 2 (encode): %s", " ".join(pass2_cmd))
    subprocess.run(pass2_cmd, check=True, capture_output=True)

    # Clean up ffmpeg two-pass log files
    for log_file in Path.cwd().glob("ffmpeg2pass*"):
        log_file.unlink(missing_ok=True)

    final_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("Video assembled: %s (%.2fMB)", output_path.name, final_size_mb)
    return output_path


def generate_video_versions(
    frame_dir: Path,
    output_dir: Path,
    lake_id: str,
    music_path: Path | None = None,
) -> tuple[Path, Path]:
    """Generate full and share video versions of a timelapse.

    Full version: original resolution, 2M bitrate.
    Share version: 400px wide (resized frames), 800k bitrate.

    Args:
        frame_dir: Directory containing PNG frames.
        output_dir: Directory for output MP4s.
        lake_id: Lake identifier for filenames.
        music_path: Optional path to background music file.

    Returns:
        Tuple of (full_path, share_path).
    """
    # Full version
    full_path = assemble_video(
        frame_dir,
        output_dir / f"{lake_id}-timelapse-full.mp4",
        music_path=music_path,
        fps=6,
        bitrate="2M",
    )

    # Share version: resize frames to 400px wide in a temp directory
    share_frame_dir = Path(tempfile.mkdtemp(prefix="timelapse-share-"))
    try:
        for frame_path in sorted(frame_dir.glob("*.png")):
            img = Image.open(frame_path)
            ratio = 400 / img.width
            new_height = int(img.height * ratio)
            # Ensure even dimensions for H.264 (must be divisible by 2)
            new_height = new_height if new_height % 2 == 0 else new_height + 1
            img = img.resize((400, new_height), Image.Resampling.LANCZOS)
            img.save(share_frame_dir / frame_path.name)

        share_path = assemble_video(
            share_frame_dir,
            output_dir / f"{lake_id}-timelapse-share.mp4",
            music_path=music_path,
            fps=6,
            bitrate="800k",
        )
    finally:
        shutil.rmtree(share_frame_dir, ignore_errors=True)

    return (full_path, share_path)
