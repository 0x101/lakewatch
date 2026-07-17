"""Import exported JSON data into a fresh PostgreSQL database.

Reads from data/export/*.json and populates all tables.
Run this on production after creating the database and running migrations.

Usage:
  python -m pipeline.scripts.import_data                    # import all
  python -m pipeline.scripts.import_data --lake my-lake-id      # single lake
  python -m pipeline.scripts.import_data --dry-run          # show counts only
"""

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

load_dotenv()

from pipeline.db.database import engine, get_session
from pipeline.db.models import (
    Base,
    Lake,
    LakeStats,
    Observation,
    TimelapseAsset,
    TimelapseFrame,
)

EXPORT_DIR = Path("data/export")


def ensure_tables():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)
    print("  Tables ensured (CREATE IF NOT EXISTS)")


def import_lakes(session, lake_filter=None, dry_run=False):
    """Import lakes from GeoJSON FeatureCollection."""
    path = EXPORT_DIR / "lakes.json"
    if not path.exists():
        print("  SKIP lakes.json — not found")
        return 0

    data = json.loads(path.read_text())
    features = data.get("features", [])
    if lake_filter:
        features = [f for f in features if f["properties"]["id"] == lake_filter]

    if dry_run:
        print(f"  lakes.json — {len(features)} lakes (dry run)")
        return len(features)

    count = 0
    for feat in features:
        props = feat["properties"]
        geojson_str = json.dumps(feat["geometry"])

        stmt = pg_insert(Lake).values(
            id=props["id"],
            name=props["name"],
            name_local=props.get("name_local") or props.get("name_kannada"),
            latitude=props["latitude"],
            longitude=props["longitude"],
            boundary_geojson=geojson_str,
            ward=props.get("ward"),
            custodian=props.get("custodian"),
            citizen_group=props.get("citizen_group"),
            area_hectares=props.get("area_hectares"),
            boundary_area_m2=props.get("boundary_area_m2"),
        ).on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": props["name"],
                "latitude": props["latitude"],
                "longitude": props["longitude"],
                "boundary_geojson": geojson_str,
                "area_hectares": props.get("area_hectares"),
                "boundary_area_m2": props.get("boundary_area_m2"),
            },
        )
        session.execute(stmt)
        count += 1

    session.commit()
    print(f"  lakes.json — {count} lakes imported")
    return count


def import_observations(session, lake_filter=None, dry_run=False):
    """Import observations from JSON array."""
    path = EXPORT_DIR / "observations.json"
    if not path.exists():
        print("  SKIP observations.json — not found")
        return 0

    records = json.loads(path.read_text())
    if lake_filter:
        records = [r for r in records if r["lake_id"] == lake_filter]

    if dry_run:
        print(f"  observations.json — {len(records)} records (dry run)")
        return len(records)

    batch_size = 500
    count = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        for rec in batch:
            stmt = pg_insert(Observation).values(
                lake_id=rec["lake_id"],
                observation_date=date.fromisoformat(rec["observation_date"]),
                water_area_m2=rec.get("water_area_m2"),
                mean_ndwi=rec.get("mean_ndwi"),
                algae_fraction=rec.get("algae_fraction"),
                cloud_pct=rec.get("cloud_pct"),
                health_score=rec.get("health_score"),
            ).on_conflict_do_update(
                index_elements=["lake_id", "observation_date"],
                set_={
                    "water_area_m2": rec.get("water_area_m2"),
                    "mean_ndwi": rec.get("mean_ndwi"),
                    "algae_fraction": rec.get("algae_fraction"),
                    "cloud_pct": rec.get("cloud_pct"),
                    "health_score": rec.get("health_score"),
                },
            )
            session.execute(stmt)
            count += 1
        session.commit()

    print(f"  observations.json — {count} records imported")
    return count


def import_lake_stats(session, lake_filter=None, dry_run=False):
    """Import lake_stats from JSON array."""
    path = EXPORT_DIR / "lake_stats.json"
    if not path.exists():
        print("  SKIP lake_stats.json — not found")
        return 0

    records = json.loads(path.read_text())
    if lake_filter:
        records = [r for r in records if r["lake_id"] == lake_filter]

    if dry_run:
        print(f"  lake_stats.json — {len(records)} records (dry run)")
        return len(records)

    count = 0
    for rec in records:
        stmt = pg_insert(LakeStats).values(
            lake_id=rec["lake_id"],
            health_score=rec.get("health_score"),
            latest_water_area_m2=rec.get("latest_water_area_m2"),
            area_change_1yr_pct=rec.get("area_change_1yr_pct"),
            area_change_5yr_pct=rec.get("area_change_5yr_pct"),
            seasonal_amplitude=rec.get("seasonal_amplitude"),
            peak_algae_month=rec.get("peak_algae_month"),
            mean_algae_fraction=rec.get("mean_algae_fraction"),
            observation_count=rec.get("observation_count", 0),
            latest_observation_date=date.fromisoformat(rec["latest_observation_date"])
            if rec.get("latest_observation_date") else None,
        ).on_conflict_do_update(
            index_elements=["lake_id"],
            set_={
                "health_score": rec.get("health_score"),
                "latest_water_area_m2": rec.get("latest_water_area_m2"),
                "area_change_1yr_pct": rec.get("area_change_1yr_pct"),
                "area_change_5yr_pct": rec.get("area_change_5yr_pct"),
                "observation_count": rec.get("observation_count", 0),
            },
        )
        session.execute(stmt)
        count += 1

    session.commit()
    print(f"  lake_stats.json — {count} records imported")
    return count


def import_timelapse_assets(session, lake_filter=None, dry_run=False):
    """Import timelapse_assets from JSON array."""
    path = EXPORT_DIR / "timelapse_assets.json"
    if not path.exists():
        print("  SKIP timelapse_assets.json — not found")
        return 0

    records = json.loads(path.read_text())
    if lake_filter:
        records = [r for r in records if r["lake_id"] == lake_filter]

    if dry_run:
        print(f"  timelapse_assets.json — {len(records)} records (dry run)")
        return len(records)

    count = 0
    for rec in records:
        stmt = pg_insert(TimelapseAsset).values(
            lake_id=rec["lake_id"],
            asset_type=rec["asset_type"],
            r2_url=rec["r2_url"],
            file_size_bytes=rec.get("file_size_bytes"),
        ).on_conflict_do_update(
            index_elements=["lake_id", "asset_type"],
            set_={"r2_url": rec["r2_url"], "file_size_bytes": rec.get("file_size_bytes")},
        )
        session.execute(stmt)
        count += 1

    session.commit()
    print(f"  timelapse_assets.json — {count} records imported")
    return count


def import_timelapse_frames(session, lake_filter=None, dry_run=False):
    """Import timelapse_frames from JSON array."""
    path = EXPORT_DIR / "timelapse_frames.json"
    if not path.exists():
        print("  SKIP timelapse_frames.json — not found")
        return 0

    records = json.loads(path.read_text())
    if lake_filter:
        records = [r for r in records if r["lake_id"] == lake_filter]

    if dry_run:
        print(f"  timelapse_frames.json — {len(records)} records (dry run)")
        return len(records)

    count = 0
    for rec in records:
        stmt = pg_insert(TimelapseFrame).values(
            lake_id=rec["lake_id"],
            observation_date=date.fromisoformat(rec["observation_date"]),
            frame_url=rec["frame_url"],
            thumbnail_url=rec.get("thumbnail_url"),
            frame_order=rec["frame_order"],
        ).on_conflict_do_update(
            index_elements=["lake_id", "observation_date"],
            set_={"frame_url": rec["frame_url"], "frame_order": rec["frame_order"]},
        )
        session.execute(stmt)
        count += 1

    session.commit()
    print(f"  timelapse_frames.json — {count} records imported")
    return count


def main():
    parser = argparse.ArgumentParser(description="Import Lake Watch data from JSON exports")
    parser.add_argument("--lake", type=str, default=None,
                        help="Import data for a single lake ID only")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show counts without importing")
    parser.add_argument("--skip-lakes", action="store_true",
                        help="Skip lake boundary import (if already loaded)")
    args = parser.parse_args()

    print(f"\nImporting Lake Watch data from {EXPORT_DIR}/")
    if args.lake:
        print(f"  Filter: {args.lake}")
    if args.dry_run:
        print("  Mode: DRY RUN")
    print()

    if not args.dry_run:
        ensure_tables()

    session = get_session()
    try:
        if not args.skip_lakes:
            import_lakes(session, args.lake, args.dry_run)
        import_observations(session, args.lake, args.dry_run)
        import_lake_stats(session, args.lake, args.dry_run)
        import_timelapse_assets(session, args.lake, args.dry_run)
        import_timelapse_frames(session, args.lake, args.dry_run)
    finally:
        session.close()

    print("\nDone.")
    if not args.dry_run:
        print("Data is now in the database. Run the backend to serve it:")
        print("  uvicorn backend.app.main:app --reload")


if __name__ == "__main__":
    main()
