"""Lake stats refresh: compute metrics and upsert into lake_stats table.

After a pipeline backfill run, this module queries all observations for
a lake, computes health score and derived stats, then upserts the
results into the lake_stats materialized table.
"""

import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from pipeline.db.database import get_session
from pipeline.db.models import LakeStats, Observation
from pipeline.metrics.derived_stats import compute_derived_stats
from pipeline.metrics.health_score import compute_health_score

logger = logging.getLogger(__name__)


def refresh_lake_stats(lake_id: str, session=None) -> dict:
    """Compute and upsert lake_stats for a given lake.

    Queries all observations, computes health score and derived
    statistics, then upserts the result into the lake_stats table
    using ON CONFLICT DO UPDATE on lake_id.

    Args:
        lake_id: Lake identifier (e.g., "bellandur-lake").
        session: SQLAlchemy session. Created via get_session() if None.

    Returns:
        Dict summarizing what was written to lake_stats.
    """
    own_session = session is None
    if own_session:
        session = get_session()

    try:
        observations = (
            session.query(Observation)
            .filter_by(lake_id=lake_id)
            .order_by(Observation.observation_date)
            .all()
        )

        health_score = compute_health_score(observations)
        stats = compute_derived_stats(observations)

        # Compute mean algae fraction across all observations with non-None values
        algae_values = [
            o.algae_fraction for o in observations if o.algae_fraction is not None
        ]
        mean_algae_fraction = (
            sum(algae_values) / len(algae_values) if algae_values else None
        )

        values = {
            "lake_id": lake_id,
            "health_score": health_score,
            "latest_water_area_m2": (
                observations[-1].water_area_m2 if observations else None
            ),
            "area_change_1yr_pct": stats["area_change_1yr_pct"],
            "area_change_5yr_pct": stats["area_change_5yr_pct"],
            "seasonal_amplitude": stats["seasonal_amplitude"],
            "peak_algae_month": stats["peak_algae_month"],
            "mean_algae_fraction": mean_algae_fraction,
            "observation_count": len(observations),
            "latest_observation_date": (
                observations[-1].observation_date if observations else None
            ),
        }

        # Upsert: insert or update on conflict with lake_id PK
        update_fields = {k: v for k, v in values.items() if k != "lake_id"}
        stmt = pg_insert(LakeStats).values(**values).on_conflict_do_update(
            index_elements=["lake_id"],
            set_=update_fields,
        )
        session.execute(stmt)
        session.commit()

        logger.info(
            "Lake stats refreshed for %s: health_score=%s, obs_count=%d",
            lake_id,
            health_score,
            len(observations),
        )

        return {
            "lake_id": lake_id,
            "health_score": health_score,
            "observation_count": len(observations),
            "area_change_1yr_pct": stats["area_change_1yr_pct"],
            "area_change_5yr_pct": stats["area_change_5yr_pct"],
            "seasonal_amplitude": stats["seasonal_amplitude"],
            "peak_algae_month": stats["peak_algae_month"],
        }

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
