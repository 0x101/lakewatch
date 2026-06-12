"""Integration tests for timeseries endpoint."""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from tests.conftest import make_lake, make_stats


def _make_obs(obs_date, water_area=1000.0, ndwi=0.4, algae=0.1, cloud=5.0):
    """Create a fake Observation-like object."""
    return SimpleNamespace(
        observation_date=obs_date,
        water_area_m2=water_area,
        mean_ndwi=ndwi,
        algae_fraction=algae,
        cloud_pct=cloud,
    )


def _make_agg_row(period, water_area=1000.0, ndwi=0.4, algae=0.1, cloud=5.0):
    """Create a fake aggregated row (from date_trunc query)."""
    return SimpleNamespace(
        period=period,
        water_area_m2=water_area,
        mean_ndwi=ndwi,
        algae_fraction=algae,
        cloud_pct=cloud,
    )


def test_timeseries_raw(client):
    """GET /api/lakes/:id/timeseries returns raw observations in order."""
    lake = make_lake()
    stats = make_stats()
    observations = [
        _make_obs(date(2024, 1, 15)),
        _make_obs(date(2024, 2, 10)),
        _make_obs(date(2024, 3, 5)),
    ]

    with (
        patch("app.routers.timeseries.get_lake_by_id", return_value=(lake, stats)),
        patch("app.routers.timeseries.get_raw_observations", return_value=observations),
    ):
        resp = client.get("/api/lakes/bellandur-lake/timeseries")

    assert resp.status_code == 200
    data = resp.json()
    assert data["lake_id"] == "bellandur-lake"
    assert data["interval"] == "raw"
    assert data["count"] == 3
    assert len(data["observations"]) == 3
    assert data["observations"][0]["date"] == "2024-01-15"
    assert data["observations"][0]["water_area_m2"] == 1000.0


def test_timeseries_monthly(client):
    """GET /api/lakes/:id/timeseries?interval=monthly returns monthly averages."""
    lake = make_lake()
    stats = make_stats()
    agg_rows = [
        _make_agg_row(datetime(2024, 1, 1), water_area=900.0),
        _make_agg_row(datetime(2024, 2, 1), water_area=1100.0),
    ]

    with (
        patch("app.routers.timeseries.get_lake_by_id", return_value=(lake, stats)),
        patch("app.routers.timeseries.get_aggregated_observations", return_value=agg_rows),
    ):
        resp = client.get("/api/lakes/bellandur-lake/timeseries?interval=monthly")

    assert resp.status_code == 200
    data = resp.json()
    assert data["interval"] == "monthly"
    assert data["count"] == 2
    assert data["observations"][0]["date"] == "2024-01-01"
    assert data["observations"][0]["water_area_m2"] == 900.0


def test_timeseries_yearly(client):
    """GET /api/lakes/:id/timeseries?interval=yearly returns yearly averages."""
    lake = make_lake()
    stats = make_stats()
    agg_rows = [
        _make_agg_row(datetime(2023, 1, 1), water_area=800.0),
        _make_agg_row(datetime(2024, 1, 1), water_area=1000.0),
    ]

    with (
        patch("app.routers.timeseries.get_lake_by_id", return_value=(lake, stats)),
        patch("app.routers.timeseries.get_aggregated_observations", return_value=agg_rows),
    ):
        resp = client.get("/api/lakes/bellandur-lake/timeseries?interval=yearly")

    assert resp.status_code == 200
    data = resp.json()
    assert data["interval"] == "yearly"
    assert data["count"] == 2


def test_timeseries_with_date_filter(client):
    """GET /api/lakes/:id/timeseries with from/to date filters."""
    lake = make_lake()
    stats = make_stats()
    observations = [_make_obs(date(2023, 6, 15))]

    with (
        patch("app.routers.timeseries.get_lake_by_id", return_value=(lake, stats)),
        patch("app.routers.timeseries.get_raw_observations", return_value=observations) as mock_raw,
    ):
        resp = client.get(
            "/api/lakes/bellandur-lake/timeseries?from=2023-01-01&to=2024-01-01"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    # Verify the date filter params were passed through
    call_args = mock_raw.call_args
    assert call_args[0][1] == "bellandur-lake"
    assert call_args[0][2] == date(2023, 1, 1)
    assert call_args[0][3] == date(2024, 1, 1)


def test_timeseries_lake_not_found(client):
    """GET /api/lakes/:id/timeseries returns 404 for nonexistent lake."""
    with patch("app.routers.timeseries.get_lake_by_id", return_value=None):
        resp = client.get("/api/lakes/nonexistent/timeseries")

    assert resp.status_code == 404
    data = resp.json()
    assert data["error"] == "Lake not found"


def test_timeseries_invalid_interval(client):
    """GET /api/lakes/:id/timeseries with invalid interval returns 400."""
    lake = make_lake()
    stats = make_stats()

    with patch("app.routers.timeseries.get_lake_by_id", return_value=(lake, stats)):
        resp = client.get("/api/lakes/bellandur-lake/timeseries?interval=weekly")

    assert resp.status_code == 400
    data = resp.json()
    assert "Invalid interval" in data["error"]
