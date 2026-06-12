"""Integration tests for lake endpoints."""

from unittest.mock import patch

from tests.conftest import make_lake, make_stats


def test_list_lakes(client):
    """GET /api/lakes returns lake list with stats."""
    lake = make_lake()
    stats = make_stats()

    with patch("app.routers.lakes.get_all_lakes_with_stats", return_value=[(lake, stats)]):
        resp = client.get("/api/lakes")

    assert resp.status_code == 200
    data = resp.json()
    assert "lakes" in data
    assert len(data["lakes"]) == 1

    item = data["lakes"][0]
    assert item["id"] == "bellandur-lake"
    assert item["name"] == "Bellandur Lake"
    assert item["health_score"] == 42.5
    assert item["latest_water_area_m2"] == 5_000_000.0
    assert item["area_change_1yr_pct"] == -2.3
    assert item["area_change_5yr_pct"] == -8.1
    assert item["mean_algae_fraction"] == 0.35
    assert item["observation_count"] == 150


def test_list_lakes_empty(client):
    """GET /api/lakes returns empty list when no lakes exist."""
    with patch("app.routers.lakes.get_all_lakes_with_stats", return_value=[]):
        resp = client.get("/api/lakes")

    assert resp.status_code == 200
    data = resp.json()
    assert data["lakes"] == []


def test_lake_detail(client):
    """GET /api/lakes/:id returns full detail with GeoJSON boundary."""
    lake = make_lake()
    stats = make_stats()

    with patch("app.routers.lakes.get_lake_by_id", return_value=(lake, stats)):
        resp = client.get("/api/lakes/bellandur-lake")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "bellandur-lake"
    assert data["boundary_geojson"]["type"] == "Polygon"
    assert "coordinates" in data["boundary_geojson"]
    assert data["ward"] == "Bellandur"
    assert data["area_hectares"] == 892.0
    assert data["latest_observation_date"] == "2026-03-15"
    assert data["peak_algae_month"] == 9


def test_lake_detail_no_stats(client):
    """GET /api/lakes/:id handles missing stats gracefully."""
    lake = make_lake()

    with patch("app.routers.lakes.get_lake_by_id", return_value=(lake, None)):
        resp = client.get("/api/lakes/bellandur-lake")

    assert resp.status_code == 200
    data = resp.json()
    assert data["health_score"] is None
    assert data["mean_algae_fraction"] is None
    assert data["observation_count"] == 0


def test_lake_not_found(client):
    """GET /api/lakes/:id returns 404 for nonexistent lake."""
    with patch("app.routers.lakes.get_lake_by_id", return_value=None):
        resp = client.get("/api/lakes/nonexistent")

    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert data["error"] == "Lake not found"
