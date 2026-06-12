"""Best-per-month frame selection for timelapse assembly.

Selects one observation per calendar month with the lowest cloud cover,
filtering out cloudy (>30%) and null water-area observations. The
``cloud_pct`` used for ranking and the < 0.30 threshold is the over-lake
(AOI) cloud fraction computed over the lake polygon, not the full tile.
Uses PostgreSQL DISTINCT ON for efficiency, with a Python fallback for
non-PostgreSQL databases (e.g., SQLite in tests).
"""

import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def select_best_per_month(session: Session, lake_id: str) -> list[dict]:
    """Select the best observation per month for timelapse frames.

    Picks one observation per calendar month with the lowest over-lake (AOI)
    cloud cover, skipping months where all observations have >30% over-lake
    cloud or null water area. The cloud_pct used for ranking and the < 0.30
    threshold is the over-lake AOI fraction, not the tile-level cloud.

    Uses PostgreSQL DISTINCT ON when available, falls back to a subquery
    approach for other databases.

    Args:
        session: SQLAlchemy database session.
        lake_id: Lake identifier to select frames for.

    Returns:
        List of dicts with keys: id, observation_date, cloud_pct.
        Ordered chronologically.
    """
    dialect = session.bind.dialect.name if session.bind else "unknown"

    if dialect == "postgresql":
        results = _select_best_per_month_sql(session, lake_id)
    else:
        results = _select_best_per_month_fallback(session, lake_id)

    logger.info("Selected %d frames for lake %s", len(results), lake_id)
    return results


def _select_best_per_month_sql(session: Session, lake_id: str) -> list[dict]:
    """PostgreSQL-optimized selection using DISTINCT ON.

    Ranks/thresholds on cloud_pct, the over-lake (AOI) cloud fraction.
    """
    query = text("""
        SELECT DISTINCT ON (date_trunc('month', observation_date))
            id, observation_date, cloud_pct
        FROM observations
        WHERE lake_id = :lake_id
            AND cloud_pct < 0.30
            AND water_area_m2 IS NOT NULL
        ORDER BY date_trunc('month', observation_date), cloud_pct ASC
    """)

    rows = session.execute(query, {"lake_id": lake_id}).fetchall()
    return [
        {"id": row[0], "observation_date": row[1], "cloud_pct": row[2]}
        for row in rows
    ]


def _select_best_per_month_fallback(session: Session, lake_id: str) -> list[dict]:
    """Fallback selection using subquery with MIN + GROUP BY (SQLite compatible).

    Ranks/thresholds on cloud_pct, the over-lake (AOI) cloud fraction.
    """
    query = text("""
        SELECT o.id, o.observation_date, o.cloud_pct
        FROM observations o
        INNER JOIN (
            SELECT
                strftime('%Y-%m', observation_date) AS month_key,
                MIN(cloud_pct) AS min_cloud
            FROM observations
            WHERE lake_id = :lake_id
                AND cloud_pct < 0.30
                AND water_area_m2 IS NOT NULL
            GROUP BY strftime('%Y-%m', observation_date)
        ) best ON strftime('%Y-%m', o.observation_date) = best.month_key
            AND o.cloud_pct = best.min_cloud
        WHERE o.lake_id = :lake_id
            AND o.water_area_m2 IS NOT NULL
        ORDER BY o.observation_date
    """)

    rows = session.execute(query, {"lake_id": lake_id}).fetchall()
    return [
        {"id": row[0], "observation_date": row[1], "cloud_pct": row[2]}
        for row in rows
    ]


def _select_best_per_month_python(observations: list[dict]) -> list[dict]:
    """Pure Python fallback for best-per-month selection.

    Groups observations by (year, month) and picks the one with the
    lowest cloud_pct per group, where cloud_pct is the over-lake (AOI)
    cloud fraction. Useful for testing without a database.

    Args:
        observations: List of dicts with keys: id, observation_date, cloud_pct,
            water_area_m2.

    Returns:
        List of dicts with keys: id, observation_date, cloud_pct.
    """
    # Filter: cloud_pct < 0.30 and water_area_m2 is not None
    valid = [
        obs
        for obs in observations
        if obs.get("cloud_pct") is not None
        and obs["cloud_pct"] < 0.30
        and obs.get("water_area_m2") is not None
    ]

    # Group by (year, month)
    groups: dict[tuple[int, int], list[dict]] = {}
    for obs in valid:
        obs_date = obs["observation_date"]
        if isinstance(obs_date, str):
            parts = obs_date.split("-")
            key = (int(parts[0]), int(parts[1]))
        elif isinstance(obs_date, date):
            key = (obs_date.year, obs_date.month)
        else:
            continue
        groups.setdefault(key, []).append(obs)

    # Pick lowest cloud_pct per month
    results = []
    for key in sorted(groups.keys()):
        best = min(groups[key], key=lambda x: x["cloud_pct"])
        results.append(
            {
                "id": best.get("id"),
                "observation_date": best["observation_date"],
                "cloud_pct": best["cloud_pct"],
            }
        )

    return results
