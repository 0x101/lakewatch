"""Leaderboard query functions — category-specific rankings."""

from sqlalchemy import literal, select
from sqlalchemy.orm import Session

# EMPRIRecord is a city extension (field-survey ground truth). It only exists
# when a city ships models_ext.py; HAS_CITY_EXTENSIONS gates its use so this
# shared file degrades cleanly to "no pollution_level" in the upstream build.
from pipeline.db.models import HAS_CITY_EXTENSIONS, EMPRIRecord, Lake, LakeStats

CATEGORY_CONFIG = {
    "shrinking": {
        "order": LakeStats.area_change_5yr_pct.asc(),
        "metric_col": LakeStats.area_change_5yr_pct,
        "metric_name": "area_change_5yr_pct",
        "filter": LakeStats.area_change_5yr_pct < 0,
    },
    "recovering": {
        "order": LakeStats.area_change_5yr_pct.desc(),
        "metric_col": LakeStats.area_change_5yr_pct,
        "metric_name": "area_change_5yr_pct",
        "filter": LakeStats.area_change_5yr_pct > 0,
    },
    "polluted": {
        "order": LakeStats.mean_algae_fraction.desc(),
        "metric_col": LakeStats.mean_algae_fraction,
        "metric_name": "mean_algae_fraction",
        "filter": LakeStats.mean_algae_fraction.isnot(None),
    },
    "volatile": {
        "order": LakeStats.seasonal_amplitude.desc().nullslast(),
        "metric_col": LakeStats.seasonal_amplitude,
        "metric_name": "seasonal_amplitude",
        "filter": LakeStats.seasonal_amplitude.isnot(None),
    },
}

VALID_CATEGORIES = set(CATEGORY_CONFIG.keys())


def get_leaderboard(db: Session, category: str, limit: int = 20) -> list:
    """Fetch ranked lakes for a leaderboard category.

    Returns list of rows with: lake_id, lake_name, metric_value,
    health_score, area_change_5yr_pct, observation_count.
    """
    if category not in CATEGORY_CONFIG:
        raise ValueError(f"Invalid category: {category}")

    config = CATEGORY_CONFIG[category]

    # pollution_level comes from the EMPRI city extension when present; the
    # upstream build selects a NULL literal so the result row still carries the
    # attribute (schema field is Optional and defaults to None).
    pollution_col = (
        EMPRIRecord.pollution_level
        if HAS_CITY_EXTENSIONS
        else literal(None).label("pollution_level")
    )

    stmt = (
        select(
            Lake.id,
            Lake.name,
            config["metric_col"].label("metric_value"),
            LakeStats.health_score,
            LakeStats.area_change_5yr_pct,
            LakeStats.observation_count,
            pollution_col,
        )
        .join(LakeStats, Lake.id == LakeStats.lake_id)
        .where(config["filter"])
        .order_by(config["order"])
        .limit(limit)
    )

    if HAS_CITY_EXTENSIONS:
        stmt = stmt.outerjoin(EMPRIRecord, Lake.id == EMPRIRecord.lake_id)

    return list(db.execute(stmt).all())
