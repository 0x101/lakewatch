"""Export all database data to portable formats for production migration.

Exports:
  data/export/lakes.json         - Lake boundaries as GeoJSON FeatureCollection
  data/export/observations.json  - All observation records
  data/export/lake_stats.json    - Pre-computed stats per lake
  data/export/timelapse_assets.json - Timelapse GIF/video R2 URLs
  data/export/timelapse_frames.json - Per-frame references
  data/export/lakewatch_dump.sql - Full pg_dump for direct PostgreSQL restore

Usage:
  python -m pipeline.scripts.export_data                    # export all
  python -m pipeline.scripts.export_data --format json      # JSON only
  python -m pipeline.scripts.export_data --format sql       # SQL dump only
  python -m pipeline.scripts.export_data --lake my-lake-id      # single lake
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, text

load_dotenv()

from pipeline.db.database import get_session

# Generic tables (always present). The city ext tables (EMPRIRecord,
# KSPCBMeasurement, Stream, StreamLakeConnection) are imported via the
# HAS_CITY_EXTENSIONS guard so this SHARED script imports cleanly in the public
# "lakewatch" repo where models_ext.py does not exist. main() exports only core
# tables today; any future ext export must be wrapped in `if HAS_CITY_EXTENSIONS:`.
from pipeline.db.models import (
    HAS_CITY_EXTENSIONS,
    Lake,
    LakeStats,
    Observation,
    TimelapseAsset,
    TimelapseFrame,
)

if HAS_CITY_EXTENSIONS:
    from pipeline.db.models import (
        EMPRIRecord,
        KSPCBMeasurement,
        Stream,
        StreamLakeConnection,
    )
else:
    EMPRIRecord = None
    KSPCBMeasurement = None
    Stream = None
    StreamLakeConnection = None

EXPORT_DIR = Path("data/export")


def json_serial(obj):
    """JSON serializer for dates and other non-standard types."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def export_lakes(session, lake_filter=None):
    """Export lakes as GeoJSON FeatureCollection."""
    query = select(Lake)
    if lake_filter:
        query = query.where(Lake.id == lake_filter)

    lakes = session.execute(query).scalars().all()
    features = []
    for lake in lakes:
        geom = json.loads(lake.boundary_geojson)
        if geom.get("type") == "Feature":
            geom = geom["geometry"]
        features.append({
            "type": "Feature",
            "properties": {
                "id": lake.id,
                "name": lake.name,
                "name_local": lake.name_local,
                "latitude": lake.latitude,
                "longitude": lake.longitude,
                "ward": lake.ward,
                "custodian": lake.custodian,
                "citizen_group": lake.citizen_group,
                "area_hectares": lake.area_hectares,
                "created_at": lake.created_at,
            },
            "geometry": geom,
        })

    collection = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "count": len(features),
        },
    }

    path = EXPORT_DIR / "lakes.json"
    path.write_text(json.dumps(collection, default=json_serial, indent=2))
    print(f"  lakes.json — {len(features)} lakes")
    return len(features)


def export_observations(session, lake_filter=None):
    """Export all observations as JSON array."""
    query = select(Observation).order_by(Observation.lake_id, Observation.observation_date)
    if lake_filter:
        query = query.where(Observation.lake_id == lake_filter)

    observations = session.execute(query).scalars().all()
    records = [
        {
            "id": obs.id,
            "lake_id": obs.lake_id,
            "observation_date": obs.observation_date,
            "water_area_m2": obs.water_area_m2,
            "mean_ndwi": obs.mean_ndwi,
            "algae_fraction": obs.algae_fraction,
            "cloud_pct": obs.cloud_pct,
            "health_score": obs.health_score,
        }
        for obs in observations
    ]

    path = EXPORT_DIR / "observations.json"
    path.write_text(json.dumps(records, default=json_serial, indent=2))
    print(f"  observations.json — {len(records)} records")
    return len(records)


def export_lake_stats(session, lake_filter=None):
    """Export lake_stats as JSON array."""
    query = select(LakeStats)
    if lake_filter:
        query = query.where(LakeStats.lake_id == lake_filter)

    stats = session.execute(query).scalars().all()
    records = [
        {
            "lake_id": s.lake_id,
            "health_score": s.health_score,
            "latest_water_area_m2": s.latest_water_area_m2,
            "area_change_1yr_pct": s.area_change_1yr_pct,
            "area_change_5yr_pct": s.area_change_5yr_pct,
            "seasonal_amplitude": s.seasonal_amplitude,
            "peak_algae_month": s.peak_algae_month,
            "mean_algae_fraction": s.mean_algae_fraction,
            "observation_count": s.observation_count,
            "latest_observation_date": s.latest_observation_date,
        }
        for s in stats
    ]

    path = EXPORT_DIR / "lake_stats.json"
    path.write_text(json.dumps(records, default=json_serial, indent=2))
    print(f"  lake_stats.json — {len(records)} records")
    return len(records)


def export_timelapse_assets(session, lake_filter=None):
    """Export timelapse_assets as JSON array."""
    query = select(TimelapseAsset)
    if lake_filter:
        query = query.where(TimelapseAsset.lake_id == lake_filter)

    assets = session.execute(query).scalars().all()
    records = [
        {
            "id": a.id,
            "lake_id": a.lake_id,
            "asset_type": a.asset_type,
            "r2_url": a.r2_url,
            "file_size_bytes": a.file_size_bytes,
        }
        for a in assets
    ]

    path = EXPORT_DIR / "timelapse_assets.json"
    path.write_text(json.dumps(records, default=json_serial, indent=2))
    print(f"  timelapse_assets.json — {len(records)} records")
    return len(records)


def export_timelapse_frames(session, lake_filter=None):
    """Export timelapse_frames as JSON array."""
    query = select(TimelapseFrame).order_by(TimelapseFrame.lake_id, TimelapseFrame.frame_order)
    if lake_filter:
        query = query.where(TimelapseFrame.lake_id == lake_filter)

    frames = session.execute(query).scalars().all()
    records = [
        {
            "id": f.id,
            "lake_id": f.lake_id,
            "observation_date": f.observation_date,
            "frame_url": f.frame_url,
            "thumbnail_url": f.thumbnail_url,
            "frame_order": f.frame_order,
        }
        for f in frames
    ]

    path = EXPORT_DIR / "timelapse_frames.json"
    path.write_text(json.dumps(records, default=json_serial, indent=2))
    print(f"  timelapse_frames.json — {len(records)} records")
    return len(records)


def export_sql_dump():
    """Export full database as pg_dump SQL file."""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("  SKIP sql dump — DATABASE_URL not set")
        return

    # Parse DATABASE_URL for pg_dump
    # postgresql://user:pass@host:port/dbname
    from urllib.parse import urlparse

    parsed = urlparse(db_url)
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""

    dump_path = EXPORT_DIR / "lakewatch_dump.sql"
    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "lakewatch",
        "-d", parsed.path.lstrip("/"),
        "--no-owner",
        "--no-privileges",
        "--if-exists",
        "--clean",
        "-f", str(dump_path),
    ]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            size_mb = dump_path.stat().st_size / (1024 * 1024)
            print(f"  lakewatch_dump.sql — {size_mb:.1f} MB")
        else:
            print(f"  WARN: pg_dump failed: {result.stderr[:200]}")
    except FileNotFoundError:
        print("  SKIP sql dump — pg_dump not found (install postgresql client)")
    except subprocess.TimeoutExpired:
        print("  SKIP sql dump — timed out after 120s")


def upload_to_r2():
    """Upload all export files to Cloudflare R2 under data-export/ prefix."""
    import boto3

    endpoint = os.getenv("R2_ENDPOINT") or f"https://{os.getenv('R2_ACCOUNT_ID', '')}.r2.cloudflarestorage.com"
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket = os.getenv("R2_BUCKET_NAME")

    if not all([access_key, secret_key, bucket]):
        print("  SKIP R2 upload — missing R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, or R2_BUCKET_NAME in .env")
        return

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    uploaded = 0
    for path in sorted(EXPORT_DIR.iterdir()):
        if not path.is_file():
            continue
        key = f"data-export/{path.name}"
        content_type = "application/json" if path.suffix == ".json" else "application/sql"
        client.upload_file(
            str(path), bucket, key,
            ExtraArgs={"ContentType": content_type},
        )
        size_kb = path.stat().st_size / 1024
        print(f"  {key} ({size_kb:.0f} KB)")
        uploaded += 1

    print(f"\n  Uploaded {uploaded} files to r2://{bucket}/data-export/")


def main():
    parser = argparse.ArgumentParser(description="Export Lake Watch data for production migration")
    parser.add_argument("--format", choices=["json", "sql", "all"], default="all",
                        help="Export format (default: all)")
    parser.add_argument("--lake", type=str, default=None,
                        help="Export data for a single lake ID only")
    parser.add_argument("--r2", action="store_true",
                        help="Upload exports to Cloudflare R2 after writing locally")
    args = parser.parse_args()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting Lake Watch data to {EXPORT_DIR}/")
    if args.lake:
        print(f"  Filter: {args.lake}")
    print()

    if args.format in ("json", "all"):
        print("JSON exports:")
        session = get_session()
        try:
            lake_count = export_lakes(session, args.lake)
            obs_count = export_observations(session, args.lake)
            stats_count = export_lake_stats(session, args.lake)
            assets_count = export_timelapse_assets(session, args.lake)
            frames_count = export_timelapse_frames(session, args.lake)
        finally:
            session.close()
        print()

    if args.format in ("sql", "all"):
        print("SQL export:")
        export_sql_dump()
        print()

    # Summary
    total_size = sum(f.stat().st_size for f in EXPORT_DIR.iterdir() if f.is_file())
    print(f"Done. Total export size: {total_size / (1024 * 1024):.1f} MB")
    print(f"Files in: {EXPORT_DIR.resolve()}")

    if args.r2:
        print("\nR2 upload:")
        upload_to_r2()

    print()
    print("To restore on production:")
    print("  # Option 1: SQL dump (fastest, needs pg_dump-compatible PostgreSQL)")
    print(f"  psql $DATABASE_URL < {EXPORT_DIR}/lakewatch_dump.sql")
    print()
    print("  # Option 2: JSON import (portable, works with any PostgreSQL)")
    print("  python -m pipeline.scripts.import_data")
    if args.r2:
        print()
        print("  # Option 3: Download from R2 first, then import")
        print("  # Files at: r2://lake-watch-assets/data-export/")


if __name__ == "__main__":
    main()
