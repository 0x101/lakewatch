"""Multi-lake batch backfill orchestrator.

Processes the top N lakes by area in configurable batch sizes with
pauses between batches to avoid overloading the GEE API. Each lake
gets a full historical backfill (2015-present) followed by a stats
refresh.
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


def get_top_lakes(session, limit: int | None = None) -> list:
    """Query the top lakes by area_hectares descending.

    Args:
        session: SQLAlchemy session.
        limit: Maximum number of lakes to return. ``None`` returns all lakes.

    Returns:
        List of Lake ORM objects ordered by area descending.
    """
    query = session.query(Lake).order_by(Lake.area_hectares.desc().nullslast(), Lake.id)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def batch_backfill(
    batch_size: int = 10,
    pause_seconds: int = 60,
    lake_limit: int | None = None,
) -> dict:
    """Run historical backfill for multiple lakes in batches.

    Processes lakes in groups of batch_size, sleeping between batches
    to avoid GEE rate limits. Each lake gets backfill_lake() followed
    by refresh_lake_stats().

    Args:
        batch_size: Number of lakes to process per batch.
        pause_seconds: Seconds to sleep between batches.
        lake_limit: Maximum number of lakes to process. ``None`` = all lakes.

    Returns:
        Summary dict with lakes_processed, total_observations, failed.
    """
    initialize_gee()
    session = get_session()
    lakes = get_top_lakes(session, limit=lake_limit)

    total_observations = 0
    lakes_processed = 0
    failed = []

    logger.info(
        "Starting batch backfill: %d lakes, batch_size=%d, pause=%ds",
        len(lakes),
        batch_size,
        pause_seconds,
    )

    for batch_idx in range(0, len(lakes), batch_size):
        batch = lakes[batch_idx : batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        logger.info("Processing batch %d (%d lakes)", batch_num, len(batch))

        for lake in batch:
            try:
                geometry = lake_to_ee_geometry(lake)
                result = backfill_lake(lake.id, geometry, session=session)
                refresh_lake_stats(lake.id, session=session)

                total_observations += result.get("total_observations", 0)
                lakes_processed += 1

                logger.info(
                    "Lake %s complete: %d observations",
                    lake.id,
                    result.get("total_observations", 0),
                )
            except Exception:
                logger.exception("Failed to process lake %s", lake.id)
                # Keep the shared session usable for the remaining lakes.
                session.rollback()
                failed.append(lake.id)

        logger.info("Batch %d complete (%d/%d lakes done)", batch_num, batch_idx + len(batch), len(lakes))

        # Sleep between batches (not after the last one)
        if batch_idx + batch_size < len(lakes):
            logger.info("Pausing %d seconds before next batch...", pause_seconds)
            time.sleep(pause_seconds)

    session.close()

    summary = {
        "lakes_processed": lakes_processed,
        "total_observations": total_observations,
        "failed": failed,
    }

    logger.info("Batch backfill complete: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Batch backfill lakes with satellite data")
    parser.add_argument("--batch-size", type=int, default=10, help="Lakes per batch (default: 10)")
    parser.add_argument("--pause-seconds", type=int, default=60, help="Pause between batches (default: 60)")
    parser.add_argument(
        "--lake-limit",
        type=int,
        default=None,
        help="Max lakes to process, largest first (default: all lakes)",
    )

    args = parser.parse_args()
    batch_backfill(
        batch_size=args.batch_size,
        pause_seconds=args.pause_seconds,
        lake_limit=args.lake_limit,
    )
