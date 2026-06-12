"""Incremental ingestion since last observation date.

Queries only new satellite imagery since each lake's most recent
observation, avoiding expensive full-year re-processing. Designed
to run on a 5-day cron schedule via GitHub Actions.
"""

import argparse
import logging
from datetime import date, timedelta

from pipeline.db.database import get_session
from pipeline.db.models import Lake, LakeStats
from pipeline.gee.auth import initialize_gee
from pipeline.metrics.refresh import refresh_lake_stats
from pipeline.satellite.extract import extract_observations_for_year, lake_to_ee_geometry
from pipeline.satellite.store import filter_cloudy, upsert_observations

logger = logging.getLogger(__name__)


def incremental_ingest_lake(lake, session) -> int:
    """Ingest new observations for a single lake since its last observation.

    Reads latest_observation_date from lake_stats, then extracts only
    imagery captured after that date. Lakes with no prior observations
    are skipped (use batch_backfill for initial population).

    Args:
        lake: Lake ORM object.
        session: SQLAlchemy session.

    Returns:
        Number of new observations upserted.
    """
    latest_date = (
        session.query(LakeStats.latest_observation_date)
        .filter_by(lake_id=lake.id)
        .scalar()
    )

    if latest_date is None:
        logger.warning(
            "No prior observations for %s, skipping (use batch_backfill instead)",
            lake.id,
        )
        return 0

    start_date = latest_date + timedelta(days=1)
    end_date = date.today()

    if start_date >= end_date:
        logger.info("No new dates to process for %s", lake.id)
        return 0

    geometry = lake_to_ee_geometry(lake)
    total_upserted = 0

    for year in range(start_date.year, end_date.year + 1):
        observations = extract_observations_for_year(geometry, year)

        # Filter to only observations after the cutoff date
        new_obs = [
            obs for obs in observations
            if obs.get("date", "") >= start_date.isoformat()
        ]

        usable = filter_cloudy(new_obs)
        count = upsert_observations(session, usable, lake.id)
        total_upserted += count

        logger.info(
            "Year %d for %s: %d new, %d usable, %d upserted",
            year, lake.id, len(new_obs), len(usable), count,
        )

    logger.info("Incremental ingest for %s: %d total observations", lake.id, total_upserted)
    return total_upserted


def incremental_ingest_all(lake_limit: int = 50) -> dict:
    """Run incremental ingestion for all tracked lakes.

    Args:
        lake_limit: Maximum number of lakes to process.

    Returns:
        Summary dict with per-lake results.
    """
    initialize_gee()
    session = get_session()

    lakes = (
        session.query(Lake)
        .order_by(Lake.area_hectares.desc().nullslast())
        .limit(lake_limit)
        .all()
    )

    results = {}
    total_observations = 0

    logger.info("Starting incremental ingestion for %d lakes", len(lakes))

    for lake in lakes:
        try:
            count = incremental_ingest_lake(lake, session)
            refresh_lake_stats(lake.id, session=session)
            results[lake.id] = {"observations": count, "status": "ok"}
            total_observations += count
            logger.info("Lake %s: %d new observations", lake.id, count)
        except Exception:
            logger.exception("Failed incremental ingest for %s", lake.id)
            results[lake.id] = {"observations": 0, "status": "error"}

    error_count = sum(1 for r in results.values() if r["status"] == "error")
    summary = {
        "lakes_processed": len(lakes),
        "total_observations": total_observations,
        "errors": error_count,
        "results": results,
    }

    logger.info("Incremental ingestion complete: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Incremental satellite data ingestion")
    parser.add_argument("--lake-limit", type=int, default=50, help="Max lakes to process (default: 50)")

    args = parser.parse_args()
    result = incremental_ingest_all(lake_limit=args.lake_limit)

    # Fail loudly in CI when lakes errored — a green run must mean real data.
    if result["errors"] > 0:
        logger.error(
            "%d of %d lakes failed — exiting nonzero so CI surfaces it",
            result["errors"], result["lakes_processed"],
        )
        raise SystemExit(1)
