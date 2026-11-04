"""Full backfill pipeline: GEE auth → batch backfill → stats refresh → export.

One command to populate every loaded lake with real satellite data.

Usage:
  python -m pipeline.scripts.full_backfill                     # default: all lakes
  python -m pipeline.scripts.full_backfill --lakes 100         # top 100
  python -m pipeline.scripts.full_backfill --batch-size 3      # smaller batches
  python -m pipeline.scripts.full_backfill --dry-run            # just verify setup
"""

import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("full_backfill")


def verify_gee():
    """Verify GEE authentication works."""
    logger.info("Step 1/4: Verifying GEE authentication...")
    from pipeline.gee.auth import initialize_gee

    initialize_gee()
    logger.info("GEE initialized successfully")


def verify_database():
    """Verify database is up and has lake boundaries."""
    logger.info("Step 2/4: Verifying database...")
    from pipeline.db.database import get_session
    from pipeline.db.models import Lake

    session = get_session()
    count = session.query(Lake).count()
    session.close()

    if count == 0:
        raise RuntimeError("No lakes loaded in database. Run load_lakes.py first.")

    logger.info(f"Database OK: {count} lakes loaded")
    return count


def run_backfill(lake_limit: int | None, batch_size: int, pause_seconds: int):
    """Run the batch backfill."""
    logger.info("Step 3/4: Running batch backfill...")
    from pipeline.scripts.batch_backfill import batch_backfill

    summary = batch_backfill(
        batch_size=batch_size,
        pause_seconds=pause_seconds,
        lake_limit=lake_limit,
    )

    logger.info(
        "Backfill complete: %d lakes, %d observations, %d failed",
        summary["lakes_processed"],
        summary["total_observations"],
        len(summary["failed"]),
    )

    if summary["failed"]:
        logger.warning("Failed lakes: %s", summary["failed"])

    return summary


def export_data():
    """Export updated data to JSON."""
    logger.info("Step 4/4: Exporting data...")
    from pipeline.scripts.export_data import (
        export_lake_stats,
        export_observations,
    )
    from pipeline.db.database import get_session

    session = get_session()
    try:
        export_observations(session)
        export_lake_stats(session)
    finally:
        session.close()

    logger.info("Export complete")


def main():
    parser = argparse.ArgumentParser(
        description="Full backfill pipeline: GEE → backfill → stats → export"
    )
    parser.add_argument(
        "--lakes",
        type=int,
        default=None,
        help="Number of lakes to process, largest first (default: all)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=5, help="Lakes per batch (default: 5)"
    )
    parser.add_argument(
        "--pause", type=int, default=30, help="Seconds between batches (default: 30)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Just verify setup, don't run backfill"
    )
    args = parser.parse_args()

    start = time.time()

    try:
        verify_gee()
        lake_count = verify_database()

        if args.dry_run:
            logger.info(
                "DRY RUN: Would process top %d of %d lakes",
                min(args.lakes or lake_count, lake_count),
                lake_count,
            )
            return

        summary = run_backfill(args.lakes, args.batch_size, args.pause)
        export_data()

        elapsed = time.time() - start
        logger.info(
            "\n=== FULL BACKFILL COMPLETE ===\n"
            "  Lakes processed: %d\n"
            "  Total observations: %d\n"
            "  Failed: %d\n"
            "  Duration: %.1f minutes\n",
            summary["lakes_processed"],
            summary["total_observations"],
            len(summary["failed"]),
            elapsed / 60,
        )

    except Exception:
        logger.exception("Full backfill failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
