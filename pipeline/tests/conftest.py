"""Shared test fixtures for pipeline tests."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: requires GEE credentials")


@pytest.fixture
def mock_ee():
    """Mock the ee module for unit testing without GEE credentials."""
    with patch("pipeline.satellite.indices.ee") as mock:
        yield mock


@pytest.fixture
def sample_observation_dicts():
    """Sample observation dicts as returned by extract_observations_for_year."""
    return [
        {
            "date": "2024-01-05",
            "cloud_pct": 0.10,
            "water_area_m2": 150000.0,
            "mean_ndwi": 0.45,
            "algae_fraction": 0.08,
        },
        {
            "date": "2024-01-15",
            "cloud_pct": 0.05,
            "water_area_m2": 148000.0,
            "mean_ndwi": 0.42,
            "algae_fraction": 0.12,
        },
        {
            "date": "2024-01-25",
            "cloud_pct": 0.50,
            "water_area_m2": None,
            "mean_ndwi": None,
            "algae_fraction": None,
        },
        {
            "date": "2024-02-04",
            "cloud_pct": 0.02,
            "water_area_m2": 152000.0,
            "mean_ndwi": 0.48,
            "algae_fraction": 0.05,
        },
    ]


@pytest.fixture
def sample_observations():
    """Sample Observation-like objects for metrics tests."""
    return [
        SimpleNamespace(
            observation_date=date(2024, 1, 5),
            water_area_m2=150000.0,
            mean_ndwi=0.45,
            algae_fraction=0.08,
            cloud_pct=0.10,
        ),
        SimpleNamespace(
            observation_date=date(2024, 1, 15),
            water_area_m2=148000.0,
            mean_ndwi=0.42,
            algae_fraction=0.12,
            cloud_pct=0.05,
        ),
        SimpleNamespace(
            observation_date=date(2024, 2, 4),
            water_area_m2=152000.0,
            mean_ndwi=0.48,
            algae_fraction=0.05,
            cloud_pct=0.02,
        ),
    ]
