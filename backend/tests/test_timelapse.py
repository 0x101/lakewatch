"""Integration tests for timelapse endpoint."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from tests.conftest import make_lake, make_stats


def _make_frame(obs_date, order, url="https://r2.example.com/frame.png"):
    """Create a fake TimelapseFrame-like object."""
    return SimpleNamespace(
        observation_date=obs_date,
        frame_url=url,
        thumbnail_url=f"{url}.thumb.jpg",
        frame_order=order,
    )


def _make_asset(asset_type, url="https://r2.example.com/asset", size=1024):
    """Create a fake TimelapseAsset-like object."""
    return SimpleNamespace(
        asset_type=asset_type,
        r2_url=url,
        file_size_bytes=size,
    )


def test_timelapse_returns_frames_and_assets(client):
    """GET /api/lakes/:id/timelapse returns frames and assets."""
    lake = make_lake()
    stats = make_stats()
    frames = [
        _make_frame(date(2024, 1, 15), 0),
        _make_frame(date(2024, 2, 10), 1),
    ]
    assets = [
        _make_asset("gif-full", "https://r2.example.com/full.gif", 5_000_000),
        _make_asset("video-full", "https://r2.example.com/full.mp4", 10_000_000),
    ]

    with (
        patch("app.routers.timelapse.get_lake_by_id", return_value=(lake, stats)),
        patch("app.routers.timelapse.get_timelapse_frames", return_value=frames),
        patch("app.routers.timelapse.get_timelapse_assets", return_value=assets),
    ):
        resp = client.get("/api/lakes/bellandur-lake/timelapse")

    assert resp.status_code == 200
    data = resp.json()
    assert data["lake_id"] == "bellandur-lake"
    assert len(data["frames"]) == 2
    assert data["frames"][0]["observation_date"] == "2024-01-15"
    assert data["frames"][0]["frame_order"] == 0
    assert len(data["assets"]) == 2
    assert data["assets"][0]["asset_type"] == "gif-full"
    assert data["assets"][0]["file_size_bytes"] == 5_000_000


def test_timelapse_lake_not_found(client):
    """GET /api/lakes/:id/timelapse returns 404 for nonexistent lake."""
    with patch("app.routers.timelapse.get_lake_by_id", return_value=None):
        resp = client.get("/api/lakes/nonexistent/timelapse")

    assert resp.status_code == 404
    data = resp.json()
    assert data["error"] == "Lake not found"


def test_timelapse_empty(client):
    """GET /api/lakes/:id/timelapse returns empty lists when no frames exist."""
    lake = make_lake()
    stats = make_stats()

    with (
        patch("app.routers.timelapse.get_lake_by_id", return_value=(lake, stats)),
        patch("app.routers.timelapse.get_timelapse_frames", return_value=[]),
        patch("app.routers.timelapse.get_timelapse_assets", return_value=[]),
    ):
        resp = client.get("/api/lakes/bellandur-lake/timelapse")

    assert resp.status_code == 200
    data = resp.json()
    assert data["frames"] == []
    assert data["assets"] == []
