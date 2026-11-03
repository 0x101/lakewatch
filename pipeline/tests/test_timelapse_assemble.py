"""Tests for timelapse GIF and video assembly."""

import subprocess

import pytest
from PIL import Image

from pipeline.timelapse.assemble import (
    assemble_gif,
    assemble_video,
    generate_gif_versions,
    generate_thumbnail,
    generate_video_versions,
)


@pytest.fixture
def sample_frames(tmp_path):
    """Generate 5 small colored PNG frames in a temp directory.

    Frames are named with ISO-style dates so alphabetical sort
    equals chronological sort.
    """
    colors = [
        (255, 0, 0),    # red
        (0, 255, 0),    # green
        (0, 0, 255),    # blue
        (255, 255, 0),  # yellow
        (128, 0, 128),  # purple
    ]
    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()

    paths = []
    for i, color in enumerate(colors, start=1):
        img = Image.new("RGB", (50, 40), color=color)
        path = frame_dir / f"2020-0{i}.png"
        img.save(path)
        paths.append(path)

    return paths


@pytest.fixture
def frame_dir(sample_frames):
    """Return the directory containing the sample frames."""
    return sample_frames[0].parent


# ---------- GIF Tests ----------


def test_assemble_gif_creates_file(sample_frames, tmp_path):
    """assemble_gif should produce a valid GIF file."""
    output = tmp_path / "output.gif"
    result = assemble_gif(sample_frames, output)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0

    # Verify it's a valid GIF
    img = Image.open(output)
    assert img.format == "GIF"


def test_assemble_gif_respects_target_width(sample_frames, tmp_path):
    """assemble_gif with target_width should produce a resized GIF."""
    output = tmp_path / "resized.gif"
    result = assemble_gif(sample_frames, output, target_width=30)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0


def test_generate_gif_versions_creates_two_files(sample_frames, tmp_path):
    """generate_gif_versions should create both full and share GIFs."""
    full_path, share_path = generate_gif_versions(
        sample_frames, tmp_path, "bellandur-lake"
    )

    assert full_path.exists()
    assert share_path.exists()
    assert "full" in full_path.name
    assert "share" in share_path.name
    assert full_path.stat().st_size > 0
    assert share_path.stat().st_size > 0


def test_generate_thumbnail_creates_png(sample_frames, tmp_path):
    """generate_thumbnail should create a PNG within 800x600 bounds."""
    output = tmp_path / "thumb.png"
    result = generate_thumbnail(sample_frames, output)

    assert result == output
    assert output.exists()

    img = Image.open(output)
    assert img.format == "PNG"
    assert img.width <= 800
    assert img.height <= 600


# ---------- Video Tests ----------


@pytest.mark.integration
def test_assemble_video_creates_mp4(frame_dir, tmp_path):
    """assemble_video should produce a valid MP4 file (no music)."""
    output = tmp_path / "output.mp4"
    result = assemble_video(frame_dir, output)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0


@pytest.mark.integration
def test_assemble_video_with_music(frame_dir, tmp_path):
    """assemble_video with a music file should produce an MP4 with audio."""
    # Create a tiny silent WAV for testing
    music_path = tmp_path / "silence.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "1",
            str(music_path),
        ],
        check=True,
        capture_output=True,
    )
    assert music_path.exists()

    output = tmp_path / "output_music.mp4"
    result = assemble_video(frame_dir, output, music_path=music_path)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0


@pytest.mark.integration
def test_generate_video_versions_creates_two_files(frame_dir, tmp_path):
    """generate_video_versions should create both full and share MP4s."""
    full_path, share_path = generate_video_versions(
        frame_dir, tmp_path, "bellandur-lake"
    )

    assert full_path.exists()
    assert share_path.exists()
    assert "full" in full_path.name
    assert "share" in share_path.name
    assert full_path.stat().st_size > 0
    assert share_path.stat().st_size > 0
