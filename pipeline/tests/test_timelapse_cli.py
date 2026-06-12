"""Behavioral tests for the timelapse CLI orchestrator.

All external dependencies are mocked: GEE, database, export, render,
assemble, upload. Tests verify the orchestration flow, not the
individual components.
"""

import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Set a dummy DATABASE_URL so pipeline.db.database doesn't fail on import
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Pre-mock GEE module which requires credentials to import properly.
# All other dependencies are installed in the venv.
if "ee" not in sys.modules:
    sys.modules["ee"] = MagicMock()

from PIL import Image  # noqa: E402

# Force-import the CLI module now so it's cached in sys.modules
# (before patch() tries to resolve it during fixture setup)
import pipeline.timelapse.cli  # noqa: E402, F401


def _create_test_frames(tmp_path, lake_id="test-lake"):
    """Create small test PNG frames in the expected directory structure."""
    frames_dir = tmp_path / "frames" / lake_id
    frames_dir.mkdir(parents=True)

    dates = ["2020-01-15", "2020-02-15", "2020-03-15"]
    paths = []
    for d in dates:
        path = frames_dir / f"{d}.png"
        img = Image.new("RGB", (20, 20), color="blue")
        img.save(path)
        paths.append(path)
    return frames_dir, paths


def _mock_lake(lake_id="test-lake", name="Test Lake"):
    """Create a mock Lake ORM object."""
    lake = MagicMock()
    lake.id = lake_id
    lake.name = name
    lake.boundary = MagicMock()
    return lake


@pytest.fixture
def cli_mocks(tmp_path):
    """Set up all mocks for the CLI orchestrator."""
    lake_id = "test-lake"
    frames_dir, frame_paths = _create_test_frames(tmp_path, lake_id)
    mock_lake = _mock_lake(lake_id)

    # Create dummy output files for assembly mocks
    assets_dir = tmp_path / "assets" / lake_id
    assets_dir.mkdir(parents=True)
    for name in ["full.gif", "share.gif", "full.mp4", "share.mp4", "thumb.png"]:
        (assets_dir / name).write_bytes(b"\x00" * 100)

    observations = [
        {"id": 1, "observation_date": date(2020, 1, 15), "cloud_pct": 0.1},
        {"id": 2, "observation_date": date(2020, 2, 15), "cloud_pct": 0.05},
        {"id": 3, "observation_date": date(2020, 3, 15), "cloud_pct": 0.08},
    ]

    patches = {
        "gee": patch("pipeline.timelapse.cli.initialize_gee"),
        "get_session": patch("pipeline.timelapse.cli.get_session"),
        "select": patch("pipeline.timelapse.cli.select_best_per_month"),
        "lake_to_ee": patch("pipeline.timelapse.cli.lake_to_ee_geometry"),
        "get_image": patch("pipeline.timelapse.cli.get_image_for_date"),
        "export": patch("pipeline.timelapse.cli.export_observation_geotiff"),
        "render": patch("pipeline.timelapse.cli.render_frame"),
        "gif": patch("pipeline.timelapse.cli.generate_gif_versions"),
        "video": patch("pipeline.timelapse.cli.generate_video_versions"),
        "thumbnail": patch("pipeline.timelapse.cli.generate_thumbnail"),
        "upload": patch("pipeline.timelapse.cli.upload_timelapse_assets"),
        "get_r2": patch("pipeline.timelapse.cli.get_r2_client"),
    }

    started = {k: p.start() for k, p in patches.items()}

    # Configure mock session
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = (
        mock_lake
    )
    started["get_session"].return_value = mock_session

    # Configure select to return observations
    started["select"].return_value = observations

    # Configure render to return the pre-created PNG path
    started["render"].side_effect = lambda *a, **kw: a[1]

    # Configure assembly mocks
    started["gif"].return_value = (
        assets_dir / "full.gif",
        assets_dir / "share.gif",
    )
    started["video"].return_value = (
        assets_dir / "full.mp4",
        assets_dir / "share.mp4",
    )
    started["thumbnail"].return_value = assets_dir / "thumb.png"
    started["upload"].return_value = []

    yield {
        "mocks": started,
        "session": mock_session,
        "lake": mock_lake,
        "lake_id": lake_id,
        "tmp_path": tmp_path,
        "frames_dir": frames_dir,
        "frame_paths": frame_paths,
        "observations": observations,
        "patches": patches,
    }

    for p in patches.values():
        p.stop()


def test_generate_timelapse_returns_expected_keys(cli_mocks):
    """generate_timelapse returns dict with all expected keys."""
    from pipeline.timelapse.cli import generate_timelapse

    result = generate_timelapse(
        lake_id=cli_mocks["lake_id"],
        output_dir=cli_mocks["tmp_path"],
        skip_export=True,
        skip_upload=True,
    )

    expected_keys = {
        "lake_id",
        "lake_name",
        "frame_count",
        "gif_full_path",
        "gif_share_path",
        "video_full_path",
        "video_share_path",
        "thumbnail_path",
        "r2_urls",
    }
    assert set(result.keys()) == expected_keys
    assert result["lake_id"] == "test-lake"
    assert result["lake_name"] == "Test Lake"
    assert result["frame_count"] == 3


def test_generate_timelapse_calls_select_best_per_month(cli_mocks):
    """generate_timelapse calls select_best_per_month with correct args."""
    from pipeline.timelapse.cli import generate_timelapse

    generate_timelapse(
        lake_id=cli_mocks["lake_id"],
        output_dir=cli_mocks["tmp_path"],
        skip_export=True,
        skip_upload=True,
    )

    cli_mocks["mocks"]["select"].assert_called_once_with(
        cli_mocks["session"], cli_mocks["lake_id"]
    )


def test_generate_timelapse_calls_gif_and_video_assembly(cli_mocks):
    """generate_timelapse calls both GIF and video assembly."""
    from pipeline.timelapse.cli import generate_timelapse

    generate_timelapse(
        lake_id=cli_mocks["lake_id"],
        output_dir=cli_mocks["tmp_path"],
        skip_export=True,
        skip_upload=True,
    )

    cli_mocks["mocks"]["gif"].assert_called_once()
    cli_mocks["mocks"]["video"].assert_called_once()


def test_generate_timelapse_skip_upload_does_not_call_upload(cli_mocks):
    """With skip_upload=True, upload_timelapse_assets is NOT called."""
    from pipeline.timelapse.cli import generate_timelapse

    generate_timelapse(
        lake_id=cli_mocks["lake_id"],
        output_dir=cli_mocks["tmp_path"],
        skip_export=True,
        skip_upload=True,
    )

    cli_mocks["mocks"]["upload"].assert_not_called()
    cli_mocks["mocks"]["get_r2"].assert_not_called()


def test_generate_timelapse_upserts_timelapse_frame_records(cli_mocks):
    """generate_timelapse upserts TimelapseFrame records for each frame."""
    from pipeline.timelapse.cli import generate_timelapse

    generate_timelapse(
        lake_id=cli_mocks["lake_id"],
        output_dir=cli_mocks["tmp_path"],
        skip_export=True,
        skip_upload=True,
    )

    # session.execute should be called once per frame (3 frames)
    execute_calls = cli_mocks["session"].execute.call_args_list
    assert len(execute_calls) == 3

    # Verify commit was called (for the TimelapseFrame upserts)
    cli_mocks["session"].commit.assert_called()


def test_generate_timelapse_skip_export_skips_gee(cli_mocks):
    """With skip_export=True, GEE initialization and export are skipped."""
    from pipeline.timelapse.cli import generate_timelapse

    generate_timelapse(
        lake_id=cli_mocks["lake_id"],
        output_dir=cli_mocks["tmp_path"],
        skip_export=True,
        skip_upload=True,
    )

    cli_mocks["mocks"]["gee"].assert_not_called()
    cli_mocks["mocks"]["export"].assert_not_called()
    cli_mocks["mocks"]["get_image"].assert_not_called()
