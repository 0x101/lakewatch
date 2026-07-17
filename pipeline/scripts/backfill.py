"""Convenience CLI entry point for historical backfill.

Usage:
    python -m pipeline.scripts.backfill --lake my-lake-id
    python -m pipeline.scripts.backfill --lake my-lake-id --start-year 2020

Delegates to pipeline.scripts.run_pipeline.main().
"""

from pipeline.scripts.run_pipeline import main

if __name__ == "__main__":
    main()
