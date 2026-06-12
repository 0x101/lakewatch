"""Tests for timelapse best-per-month frame selection."""

from datetime import date

import pytest
from sqlalchemy import Column, Date, Float, Integer, String, create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from pipeline.timelapse.select import (
    _select_best_per_month_python,
    select_best_per_month,
)

Base = declarative_base()


class FakeObservation(Base):
    """Minimal observation table for testing (SQLite compatible)."""

    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lake_id = Column(String, nullable=False)
    observation_date = Column(Date, nullable=False)
    water_area_m2 = Column(Float, nullable=True)
    cloud_pct = Column(Float, nullable=True)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database with observation table."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _insert_obs(session, lake_id, obs_date, cloud_pct, water_area=150000.0):
    """Helper to insert an observation."""
    session.execute(
        text(
            "INSERT INTO observations (lake_id, observation_date, cloud_pct, water_area_m2) "
            "VALUES (:lake_id, :obs_date, :cloud_pct, :water_area)"
        ),
        {
            "lake_id": lake_id,
            "obs_date": obs_date,
            "cloud_pct": cloud_pct,
            "water_area": water_area,
        },
    )
    session.commit()


def test_select_best_per_month_picks_lowest_cloud(db_session):
    """Should pick the observation with the lowest cloud_pct in a month."""
    _insert_obs(db_session, "bellandur", "2024-01-05", 0.10)
    _insert_obs(db_session, "bellandur", "2024-01-15", 0.20)
    _insert_obs(db_session, "bellandur", "2024-01-25", 0.05)

    results = select_best_per_month(db_session, "bellandur")

    assert len(results) == 1
    assert results[0]["cloud_pct"] == 0.05


def test_select_best_per_month_skips_cloudy(db_session):
    """Observations with cloud_pct >= 0.30 should be excluded."""
    _insert_obs(db_session, "bellandur", "2024-01-15", 0.50)

    results = select_best_per_month(db_session, "bellandur")

    assert len(results) == 0


def test_select_best_per_month_skips_null_water_area(db_session):
    """Observations with NULL water_area_m2 should be excluded."""
    _insert_obs(db_session, "bellandur", "2024-01-15", 0.10, water_area=None)

    results = select_best_per_month(db_session, "bellandur")

    assert len(results) == 0


def test_select_best_per_month_multiple_months(db_session):
    """Should return one observation per month across multiple months."""
    _insert_obs(db_session, "bellandur", "2024-01-15", 0.10)
    _insert_obs(db_session, "bellandur", "2024-02-10", 0.05)
    _insert_obs(db_session, "bellandur", "2024-03-20", 0.15)

    results = select_best_per_month(db_session, "bellandur")

    assert len(results) == 3
    dates = [r["observation_date"] for r in results]
    # Verify chronological order
    assert dates == sorted(dates)


def test_python_fallback_picks_lowest_cloud():
    """Pure Python fallback should pick lowest cloud_pct per month."""
    observations = [
        {
            "id": 1,
            "observation_date": "2024-01-05",
            "cloud_pct": 0.10,
            "water_area_m2": 150000.0,
        },
        {
            "id": 2,
            "observation_date": "2024-01-15",
            "cloud_pct": 0.05,
            "water_area_m2": 148000.0,
        },
        {
            "id": 3,
            "observation_date": "2024-02-04",
            "cloud_pct": 0.02,
            "water_area_m2": 152000.0,
        },
    ]

    results = _select_best_per_month_python(observations)

    assert len(results) == 2
    assert results[0]["cloud_pct"] == 0.05  # Jan best
    assert results[1]["cloud_pct"] == 0.02  # Feb best


def test_python_fallback_excludes_cloudy_and_null():
    """Pure Python fallback should skip cloudy and null water_area obs."""
    observations = [
        {
            "id": 1,
            "observation_date": "2024-01-05",
            "cloud_pct": 0.50,
            "water_area_m2": 150000.0,
        },
        {
            "id": 2,
            "observation_date": "2024-02-10",
            "cloud_pct": 0.10,
            "water_area_m2": None,
        },
    ]

    results = _select_best_per_month_python(observations)

    assert len(results) == 0
