"""Top-level pipeline orchestrator: GEE auth -> lake lookup -> backfill.

Ties together authentication, database lookup, and the year-by-year
backfill into a single command. This is the main entry point for
running the satellite observation pipeline for a lake.
"""

import argparse
import logging
import time

from pipeline.db.database import get_session
from pipeline.db.models import Lake
from pipeline.gee.auth import initialize_gee
from pipeline.metrics.refresh import refresh_lake_stats
from pipeline.satellite.backfill import backfill_lake
from pipeline.satellite.extract import lake_to_ee_geometry

logger = logging.getLogger(__name__)


def run_pipeline(
    lake_slug: str, start_year: int = 2015, end_year: int = 2026
) -> dict:
    """Run the full satellite observation pipeline for a lake.

    Steps:
        1. Initialize GEE authentication
        2. Look up lake boundary from database
        3. Convert boundary to GEE geometry
        4. Run year-by-year backfill with checkpoint resumability

    Args:
        lake_slug: Lake identifier (e.g., "my-lake-id").
        start_year: First year to process (inclusive).
        end_year: Last year to process (inclusive).

    Returns:
        Backfill summary dict from backfill_lake().

    Raises:
        ValueError: If lake not found in database.
    """
    t0 = time.time()
    logger.info("Starting pipeline for %s (%d-%d)", lake_slug, start_year, end_year)

    # 1. GEE authentication
    initialize_gee()
    logger.info("GEE initialized")

    # 2. Lake lookup
    session = get_session()
    lake = session.query(Lake).filter_by(id=lake_slug).first()
    if lake is None:
        raise ValueError(
            f"Lake '{lake_slug}' not found in database. "
            f"Run lake loading first (pipeline/scripts/load_lakes.py)."
        )

    # 3. Convert boundary to GEE geometry
    geometry = lake_to_ee_geometry(lake)
    logger.info("Lake boundary converted to GEE geometry")

    # 4. Backfill
    result = backfill_lake(lake_slug, geometry, start_year, end_year, session)

    # 5. Refresh lake_stats (health score + derived metrics)
    logger.info("Computing metrics for %s", lake_slug)
    metrics_result = refresh_lake_stats(lake_slug, session)
    result["metrics"] = metrics_result
    logger.info(
        "Metrics computed: health_score=%s, obs_count=%d",
        metrics_result.get("health_score"),
        metrics_result.get("observation_count", 0),
    )

    elapsed = time.time() - t0
    logger.info("Pipeline complete for %s in %.1f seconds", lake_slug, elapsed)
    result["elapsed_seconds"] = round(elapsed, 1)

    return result


def main():
    """CLI entry point with argparse."""
    parser = argparse.ArgumentParser(
        description="Run satellite observation pipeline for a lake"
    )
    parser.add_argument(
        "--lake",
        required=True,
        help='Lake slug identifier (e.g., "my-lake-id")',
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2015,
        help="Start year for backfill (default: 2015)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2026,
        help="End year for backfill (default: 2026)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    result = run_pipeline(args.lake, args.start_year, args.end_year)
    print(f"\nPipeline Summary for {args.lake}:")
    print(f"  Total observations stored: {result['total_observations']}")
    print(f"  Years completed: {result['years_completed']}")
    print(f"  Years failed: {result['years_failed']}")
    print(f"  Elapsed: {result['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
