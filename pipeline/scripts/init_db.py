"""Create the LakeWatch database schema.

Runs `Base.metadata.create_all`, which creates every table the ORM knows
about (lakes, observations, lake_stats, timelapse_frames, timelapse_assets)
plus any city-extension tables you define in pipeline/db/models_ext.py.
Existing tables are left untouched — this is safe to re-run.

We deliberately ship plain create_all rather than migrations: the schema is
small and stable, and a fork's first run should be one command, not a
migration toolchain. If your fork's schema starts evolving, add Alembic then.

Usage:
    # Requires DATABASE_URL in your environment / .env, e.g.
    #   postgresql://user:pass@host:5432/lakewatch
    python -m pipeline.scripts.init_db

Next steps:
    python -m pipeline.scripts.load_lakes examples/sample-lakes.geojson
    python -m pipeline.scripts.full_backfill
"""

import os

from dotenv import load_dotenv

load_dotenv()

from pipeline.db.database import engine  # noqa: E402
from pipeline.db.models import Base  # noqa: E402


def init_db() -> None:
    """Create all tables defined on Base.metadata (idempotent)."""
    if not os.getenv("DATABASE_URL"):
        raise SystemExit(
            "DATABASE_URL is not set. Add it to your .env, e.g.\n"
            "  DATABASE_URL=postgresql://user:pass@localhost:5432/lakewatch"
        )
    Base.metadata.create_all(engine)
    tables = ", ".join(sorted(Base.metadata.tables.keys()))
    print(f"Schema ready. Tables: {tables}")


if __name__ == "__main__":
    init_db()
