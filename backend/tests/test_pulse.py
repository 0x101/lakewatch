"""Integration tests for the /api/insights/pulse endpoint."""

from unittest.mock import patch


def _populated_pulse():
    """A fully-populated pulse payload, as get_pulse would return."""
    return {
        "as_of": "2026-06-01",
        "observation_window": {"start": "2026-02-01", "end": "2026-06-01"},
        "gainers": [
            {
                "lake_id": "lake-a",
                "lake_name": "Lake A",
                "water_area_m2": 50000,
                "area_change_m2": 42000,
                "area_change_pct": 525.0,
                "algae_fraction": 0.05,
                "algae_trend": -0.01,
            },
            {
                "lake_id": "lake-b",
                "lake_name": "Lake B",
                "water_area_m2": 30000,
                "area_change_m2": 8000,
                "area_change_pct": 36.36,
                "algae_fraction": 0.08,
                "algae_trend": 0.0,
            },
        ],
        "shrinkers": [
            {
                "lake_id": "lake-c",
                "lake_name": "Lake C",
                "water_area_m2": 12000,
                "area_change_m2": -19000,
                "area_change_pct": -61.29,
                "algae_fraction": 0.22,
                "algae_trend": 0.03,
            },
        ],
        "algae_watch": [
            {
                "lake_id": "lake-c",
                "lake_name": "Lake C",
                "water_area_m2": 12000,
                "area_change_m2": -19000,
                "area_change_pct": -61.29,
                "algae_fraction": 0.22,
                "algae_trend": 0.03,
            },
            {
                "lake_id": "lake-b",
                "lake_name": "Lake B",
                "water_area_m2": 30000,
                "area_change_m2": 8000,
                "area_change_pct": 36.36,
                "algae_fraction": 0.08,
                "algae_trend": None,
            },
        ],
        "city": {
            "total_water_area_now_m2": 92000,
            "total_water_area_1yr_ago_m2": 80000,
            "net_change_m2": 12000,
        },
    }


def _empty_pulse():
    """An empty pulse payload — no qualifying lakes."""
    return {
        "as_of": None,
        "observation_window": {"start": None, "end": None},
        "gainers": [],
        "shrinkers": [],
        "algae_watch": [],
        "city": {
            "total_water_area_now_m2": None,
            "total_water_area_1yr_ago_m2": None,
            "net_change_m2": None,
        },
    }


def test_pulse_populated(client):
    """GET /api/insights/pulse serializes a full payload."""
    with patch(
        "app.routers.insights.get_pulse", return_value=_populated_pulse()
    ):
        resp = client.get("/api/insights/pulse")

    assert resp.status_code == 200
    data = resp.json()

    assert data["as_of"] == "2026-06-01"
    assert data["observation_window"]["start"] == "2026-02-01"
    assert data["observation_window"]["end"] == "2026-06-01"

    assert len(data["gainers"]) == 2
    assert data["gainers"][0]["lake_id"] == "lake-a"
    assert data["gainers"][0]["area_change_m2"] == 42000

    assert len(data["shrinkers"]) == 1
    assert data["shrinkers"][0]["lake_id"] == "lake-c"
    assert data["shrinkers"][0]["area_change_m2"] == -19000

    assert len(data["algae_watch"]) == 2
    assert data["algae_watch"][0]["lake_id"] == "lake-c"
    assert data["algae_watch"][0]["algae_fraction"] == 0.22
    assert data["algae_watch"][0]["algae_trend"] == 0.03

    assert data["city"]["net_change_m2"] == 12000
    assert data["city"]["total_water_area_now_m2"] == 92000


def test_pulse_empty(client):
    """GET /api/insights/pulse with no qualifying lakes returns empty lists."""
    with patch(
        "app.routers.insights.get_pulse", return_value=_empty_pulse()
    ):
        resp = client.get("/api/insights/pulse")

    assert resp.status_code == 200
    data = resp.json()

    assert data["as_of"] is None
    assert data["gainers"] == []
    assert data["shrinkers"] == []
    assert data["algae_watch"] == []
    assert data["city"]["net_change_m2"] is None
    assert data["observation_window"]["start"] is None


def test_pulse_window_days_bounds(client):
    """window_days outside [30, 365] is rejected by FastAPI validation."""
    with patch(
        "app.routers.insights.get_pulse", return_value=_empty_pulse()
    ):
        too_small = client.get("/api/insights/pulse?window_days=10")
        too_large = client.get("/api/insights/pulse?window_days=999")
        ok = client.get("/api/insights/pulse?window_days=90")

    assert too_small.status_code == 422
    assert too_large.status_code == 422
    assert ok.status_code == 200
