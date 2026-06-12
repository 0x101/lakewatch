"""Year-by-year historical backfill with checkpoint resumability.

Processes satellite observations for a lake one year at a time,
tracking completed years in a checkpoint file so the process can
be interrupted and resumed without re-processing finished years.
"""

import json
import logging
from pathlib import Path

from pipeline.db.database import get_session
from pipeline.satellite.extract import extract_observations_for_year
from pipeline.satellite.store import filter_cloudy, upsert_observations

logger = logging.getLogger(__name__)

CHECKPOINT_FILE = Path("pipeline/.backfill_checkpoint.json")


def load_checkpoint(lake_id: str) -> set[int]:
    """Load set of completed years for a lake from checkpoint file.

    Args:
        lake_id: Lake identifier.

    Returns:
        Set of year integers that have been successfully processed.
        Empty set if checkpoint file doesn't exist.
    """
    if not CHECKPOINT_FILE.exists():
        return set()

    data = json.loads(CHECKPOINT_FILE.read_text())
    years = data.get(lake_id, [])
    return set(years)


def save_checkpoint(lake_id: str, year: int) -> None:
    """Record a completed year in the checkpoint file.

    Creates the checkpoint file if it doesn't exist. Appends the
    year to the lake's completed list.

    Args:
        lake_id: Lake identifier.
        year: Year that was successfully processed.
    """
    data = {}
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text())

    if lake_id not in data:
        data[lake_id] = []

    if year not in data[lake_id]:
        data[lake_id].append(year)

    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(data, indent=2))
    logger.debug("Checkpoint saved: %s year %d", lake_id, year)


def backfill_lake(
    lake_id: str,
    lake_geometry,
    start_year: int = 2015,
    end_year: int = 2026,
    session=None,
) -> dict:
    """Run historical backfill for a single lake, year by year.

    Processes each year independently so failures in one year don't
    block others. Completed years are tracked via checkpoint file
    and skipped on re-run.

    Args:
        lake_id: Lake identifier (slug).
        lake_geometry: ee.Geometry of the lake polygon.
        start_year: First year to process (inclusive).
        end_year: Last year to process (inclusive).
        session: SQLAlchemy session. Created via get_session() if None.

    Returns:
        Summary dict with keys: lake_id, total_observations,
        years_completed, years_failed.
    """
    if session is None:
        session = get_session()

    completed = load_checkpoint(lake_id)
    total_observations = 0
    years_completed = []
    years_failed = []

    logger.info(
        "Starting backfill for %s: years %d-%d (%d already done)",
        lake_id,
        start_year,
        end_year,
        len(completed),
    )

    for year in range(start_year, end_year + 1):
        if year in completed:
            logger.info("Skipping year %d (already completed)", year)
            continue

        try:
            logger.info("Processing year %d for %s", year, lake_id)
            observations = extract_observations_for_year(lake_geometry, year)
            usable = filter_cloudy(observations)
            count = upsert_observations(session, usable, lake_id)

            save_checkpoint(lake_id, year)
            years_completed.append(year)
            total_observations += count

            logger.info(
                "Year %d complete: %d usable / %d total observations",
                year,
                count,
                len(observations),
            )

        except Exception:
            logger.exception("Failed to process year %d for %s", year, lake_id)
            years_failed.append(year)

    summary = {
        "lake_id": lake_id,
        "total_observations": total_observations,
        "years_completed": years_completed,
        "years_failed": years_failed,
    }

    logger.info("Backfill complete for %s: %s", lake_id, summary)
    return summary
