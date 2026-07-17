"""Test fixtures for backend integration tests."""

import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.deps import get_db
from app.main import app


def make_lake(**overrides):
    """Create a fake Lake-like object for testing."""
    defaults = {
        "id": "bellandur-lake",
        "name": "Bellandur Lake",
        "name_local": None,
        "latitude": 12.9373,
        "longitude": 77.6695,
        "boundary_geojson": json.dumps(
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.66, 12.93],
                        [77.67, 12.93],
                        [77.67, 12.94],
                        [77.66, 12.94],
                        [77.66, 12.93],
                    ]
                ],
            }
        ),
        "boundary_area_m2": 9_000_000.0,
        "ward": "Bellandur",
        "custodian": "BDA",
        "citizen_group": "BCLAP",
        "area_hectares": 892.0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_stats(**overrides):
    """Create a fake LakeStats-like object for testing."""
    defaults = {
        "lake_id": "bellandur-lake",
        "health_score": 42.5,
        "latest_water_area_m2": 5_000_000.0,
        "area_change_1yr_pct": -2.3,
        "area_change_5yr_pct": -8.1,
        "mean_algae_fraction": 0.35,
        "seasonal_amplitude": 0.15,
        "peak_algae_month": 9,
        "observation_count": 150,
        "latest_observation_date": date(2026, 3, 15),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture()
def mock_db():
    """Provide a mock DB session (not actually used by mocked queries)."""
    db = MagicMock()
    return db


@pytest.fixture()
def client(mock_db):
    """FastAPI test client with mocked DB dependency."""

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
