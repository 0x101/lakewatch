"""Integration tests for leaderboard endpoint."""

from types import SimpleNamespace
from unittest.mock import patch


def _make_leaderboard_row(
    lake_id, name, metric_value, health_score=50.0, area_5yr=-5.0, obs_count=100, pollution_level="Moderate"
):
    """Create a fake leaderboard query result row."""
    return SimpleNamespace(
        id=lake_id,
        name=name,
        metric_value=metric_value,
        health_score=health_score,
        area_change_5yr_pct=area_5yr,
        observation_count=obs_count,
        pollution_level=pollution_level,
    )


def test_leaderboard_shrinking(client):
    """GET /api/leaderboard?category=shrinking returns lakes by most shrunk."""
    rows = [
        _make_leaderboard_row("lake-a", "Lake A", -20.0, area_5yr=-20.0),
        _make_leaderboard_row("lake-b", "Lake B", -15.0, area_5yr=-15.0),
        _make_leaderboard_row("lake-c", "Lake C", -5.0, area_5yr=-5.0),
    ]

    with patch("app.routers.leaderboard.get_leaderboard", return_value=rows):
        resp = client.get("/api/leaderboard?category=shrinking")

    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "shrinking"
    assert len(data["entries"]) == 3
    assert data["entries"][0]["rank"] == 1
    assert data["entries"][0]["lake_id"] == "lake-a"
    assert data["entries"][0]["metric_value"] == -20.0
    assert data["entries"][0]["metric_name"] == "area_change_5yr_pct"
    assert data["entries"][1]["rank"] == 2
    assert data["entries"][2]["rank"] == 3


def test_leaderboard_recovering(client):
    """GET /api/leaderboard?category=recovering returns lakes by most recovered."""
    rows = [
        _make_leaderboard_row("lake-x", "Lake X", 25.0, area_5yr=25.0),
        _make_leaderboard_row("lake-y", "Lake Y", 10.0, area_5yr=10.0),
    ]

    with patch("app.routers.leaderboard.get_leaderboard", return_value=rows):
        resp = client.get("/api/leaderboard?category=recovering")

    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "recovering"
    assert data["entries"][0]["metric_value"] == 25.0
    assert data["entries"][0]["metric_name"] == "area_change_5yr_pct"


def test_leaderboard_polluted(client):
    """GET /api/leaderboard?category=polluted returns lakes by highest algae."""
    rows = [
        _make_leaderboard_row("lake-p1", "Lake P1", 0.85, area_5yr=-3.0),
        _make_leaderboard_row("lake-p2", "Lake P2", 0.60, area_5yr=-1.0),
        _make_leaderboard_row("lake-p3", "Lake P3", 0.35, area_5yr=2.0),
    ]

    with patch("app.routers.leaderboard.get_leaderboard", return_value=rows):
        resp = client.get("/api/leaderboard?category=polluted")

    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "polluted"
    assert data["entries"][0]["metric_value"] == 0.85
    assert data["entries"][0]["metric_name"] == "mean_algae_fraction"


def test_leaderboard_volatile(client):
    """GET /api/leaderboard?category=volatile returns lakes by seasonal amplitude."""
    rows = [
        _make_leaderboard_row("lake-v1", "Lake V1", 0.45, area_5yr=-2.0),
        _make_leaderboard_row("lake-v2", "Lake V2", 0.30, area_5yr=-1.0),
    ]

    with patch("app.routers.leaderboard.get_leaderboard", return_value=rows):
        resp = client.get("/api/leaderboard?category=volatile")

    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "volatile"
    assert data["entries"][0]["metric_value"] == 0.45
    assert data["entries"][0]["metric_name"] == "seasonal_amplitude"


def test_leaderboard_default_category(client):
    """GET /api/leaderboard with no params defaults to shrinking."""
    rows = [
        _make_leaderboard_row("lake-d", "Lake D", -10.0),
    ]

    with patch("app.routers.leaderboard.get_leaderboard", return_value=rows) as mock_get:
        resp = client.get("/api/leaderboard")

    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "shrinking"
    # Verify it was called with "shrinking"
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert call_args[0][1] == "shrinking"


def test_leaderboard_invalid_category(client):
    """GET /api/leaderboard?category=invalid returns 400."""
    resp = client.get("/api/leaderboard?category=invalid")

    assert resp.status_code == 400
    data = resp.json()
    assert "Invalid category" in data["error"]
