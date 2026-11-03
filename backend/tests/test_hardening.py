"""Tests for API hardening: error shape, CORS, input validation."""

from datetime import date
from unittest.mock import patch


def test_unknown_route_uses_error_shape(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404
    assert resp.json() == {"error": "Not Found"}


def test_invalid_ranking_category_is_400(client):
    resp = client.get("/api/insights/rankings?category=bogus")
    assert resp.status_code == 400
    assert "Invalid category" in resp.json()["error"]


def test_movers_defaults_to_last_full_year(client):
    with patch("app.routers.insights.get_movers") as mock_movers:
        mock_movers.return_value = {"year": 0, "improvers": [], "decliners": []}
        resp = client.get("/api/insights/movers")
    assert resp.status_code == 200
    assert mock_movers.call_args.args[1] == date.today().year - 1


def test_movers_rejects_future_year(client):
    resp = client.get(f"/api/insights/movers?year={date.today().year + 1}")
    assert resp.status_code == 400


def test_cors_is_read_only_and_uncredentialed(client):
    resp = client.options(
        "/api/lakes",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "POST" not in resp.headers.get("access-control-allow-methods", "")
    assert "access-control-allow-credentials" not in resp.headers
