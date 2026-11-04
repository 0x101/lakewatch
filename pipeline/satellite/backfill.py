"""Year-by-year historical backfill with checkpoint resumability.

Processes satellite observations for a lake one year at a time,
tracking completed years in a checkpoint file so the process can
be interrupted and resumed without re-processing finished years.
"""

import json
import logging
import os
from datetime import date
from pathlib import Path

from pipeline.db.database import get_session
from pipeline.satellite.extract import extract_observations_for_year
from pipeline.satellite.store import filter_cloudy, upsert_observations

logger = logging.getLogger(__name__)

# Anchored to the pipeline package directory (not the CWD), so the checkpoint
# lands in the same gitignored spot whether you run from the repo root or from
# pipeline/. Override with LAKEWATCH_CHECKPOINT_FILE if you need it elsewhere.
CHECKPOINT_FILE = Path(
    os.getenv(
        "LAKEWATCH_CHECKPOINT_FILE",
        str(Path(__file__).resolve().parent.parent / ".backfill_checkpoint.json"),
    )
)


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
    # Write atomically so an interrupted run can't leave a truncated JSON file
    # that breaks every subsequent resume.
    tmp = CHECKPOINT_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(CHECKPOINT_FILE)
    logger.debug("Checkpoint saved: %s year %d", lake_id, year)


def backfill_lake(
    lake_id: str,
    lake_geometry,
    start_year: int = 2015,
    end_year: int | None = None,
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
        end_year: Last year to process (inclusive). Defaults to the
            current year.
        session: SQLAlchemy session. Created via get_session() if None.

    Returns:
        Summary dict with keys: lake_id, total_observations,
        years_completed, years_failed.

    Note:
        The current (still-in-progress) year and any future year are never
        written to the checkpoint: they will gain new imagery, so a later
        re-run must process them again instead of skipping them forever.
    """
    if session is None:
        session = get_session()
    current_year = date.today().year
    if end_year is None:
        end_year = current_year

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

            if year < current_year:
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
            # A failed DB write leaves the session unusable until rolled back;
            # without this every later year (and lake) would fail too.
            session.rollback()
            years_failed.append(year)

    summary = {
        "lake_id": lake_id,
        "total_observations": total_observations,
        "years_completed": years_completed,
        "years_failed": years_failed,
    }

    logger.info("Backfill complete for %s: %s", lake_id, summary)
    return summary
