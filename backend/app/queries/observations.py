"""Observation query functions for timeseries endpoint."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pipeline.db.models import Observation


def get_raw_observations(
    db: Session,
    lake_id: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list:
    """Fetch raw observations for a lake, optionally filtered by date range."""
    stmt = (
        select(Observation)
        .where(Observation.lake_id == lake_id)
        .order_by(Observation.observation_date.asc())
    )
    if from_date is not None:
        stmt = stmt.where(Observation.observation_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(Observation.observation_date <= to_date)
    return list(db.execute(stmt).scalars().all())


def get_aggregated_observations(
    db: Session,
    lake_id: str,
    interval: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list:
    """Fetch observations aggregated by date_trunc interval (month/year).

    Uses SQL date_trunc + AVG GROUP BY for server-side aggregation.
    """
    truncated = func.date_trunc(interval, Observation.observation_date).label(
        "period"
    )
    stmt = (
        select(
            truncated,
            func.avg(Observation.water_area_m2).label("water_area_m2"),
            func.avg(Observation.mean_ndwi).label("mean_ndwi"),
            func.avg(Observation.algae_fraction).label("algae_fraction"),
            func.avg(Observation.cloud_pct).label("cloud_pct"),
        )
        .where(Observation.lake_id == lake_id)
        .group_by(truncated)
        .order_by(truncated.asc())
    )
    if from_date is not None:
        stmt = stmt.where(Observation.observation_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(Observation.observation_date <= to_date)
    return list(db.execute(stmt).all())
