"""Observation persistence layer with duplicate-safe upserts.

Stores satellite observation records in PostGIS using PostgreSQL's
ON CONFLICT ... DO UPDATE pattern. Includes cloud filtering to
reject observations with excessive cloud cover before storage.
"""

import logging
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from pipeline.db.models import Observation

logger = logging.getLogger(__name__)


def filter_cloudy(
    observations: list[dict], max_cloud_pct: float = 0.30
) -> list[dict]:
    """Filter out observations with cloud cover above threshold.

    The ``cloud_pct`` filtered on is the over-lake (AOI) cloud fraction
    computed over the lake polygon, not the full Sentinel-2 tile footprint.

    Args:
        observations: List of observation dicts from extract pipeline.
        max_cloud_pct: Maximum allowed over-lake cloud fraction (0.0-1.0).
            Observations at exactly the threshold are kept.

    Returns:
        Filtered list containing only observations with
        cloud_pct <= max_cloud_pct.
    """
    usable = [
        obs for obs in observations if obs.get("cloud_pct", 1.0) <= max_cloud_pct
    ]
    logger.info(
        "Cloud filter: %d/%d observations usable (threshold %.0f%%)",
        len(usable),
        len(observations),
        max_cloud_pct * 100,
    )
    return usable


def upsert_observations(
    session, observations: list[dict], lake_id: str
) -> int:
    """Insert or update observation records with ON CONFLICT safety.

    Uses PostgreSQL's INSERT ... ON CONFLICT (lake_id, observation_date)
    DO UPDATE to handle duplicate dates gracefully. Re-running the
    pipeline for the same dates will update existing records rather
    than failing on unique constraint violations.

    Args:
        session: SQLAlchemy session.
        observations: List of observation dicts with keys:
            date, water_area_m2, mean_ndwi, algae_fraction, cloud_pct.
        lake_id: Lake identifier (foreign key to lakes table).

    Returns:
        Number of rows upserted.
    """
    if not observations:
        logger.info("No observations to upsert for %s", lake_id)
        return 0

    count = 0
    for obs in observations:
        observation_date = datetime.strptime(obs["date"], "%Y-%m-%d").date()

        stmt = pg_insert(Observation).values(
            lake_id=lake_id,
            observation_date=observation_date,
            water_area_m2=obs.get("water_area_m2"),
            mean_ndwi=obs.get("mean_ndwi"),
            algae_fraction=obs.get("algae_fraction"),
            cloud_pct=obs.get("cloud_pct"),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["lake_id", "observation_date"],
            set_={
                "water_area_m2": stmt.excluded.water_area_m2,
                "mean_ndwi": stmt.excluded.mean_ndwi,
                "algae_fraction": stmt.excluded.algae_fraction,
                "cloud_pct": stmt.excluded.cloud_pct,
            },
        )

        session.execute(stmt)
        count += 1

    session.commit()
    logger.info("Upserted %d observations for %s", count, lake_id)
    return count
