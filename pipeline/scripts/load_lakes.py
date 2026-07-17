"""Load your city's lake boundaries from a GeoJSON file into the database.

This is the first step after setting up the database: it reads a GeoJSON
FeatureCollection of lake boundaries and upserts one row per lake into the
`lakes` table. After this, run the satellite backfill to populate
observations (see pipeline/scripts/run_pipeline.py and full_backfill.py).

Usage:
    python -m pipeline.scripts.load_lakes examples/sample-lakes.geojson
    python -m pipeline.scripts.load_lakes path/to/your-city-lakes.geojson

Input format — a GeoJSON FeatureCollection where each Feature has:

    geometry:   a Polygon (or MultiPolygon) in lon/lat (EPSG:4326)
    properties:
        name       (required)  human-readable lake name
        id         (optional)  stable slug; auto-derived from name if absent
        name_local (optional)  name in a local language/script
        ward       (optional)
        custodian  (optional)
        citizen_group (optional)
        area_hectares (optional)

Only `name` is required; everything else is optional and degrades to NULL.
A minimal 3-lake example ships in examples/sample-lakes.geojson.

Re-running is safe: lakes are upserted by id (insert-or-update).
"""

import argparse
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert as pg_insert

load_dotenv()

from pipeline.db.database import engine, get_session  # noqa: E402
from pipeline.db.models import Base, Lake  # noqa: E402


def slugify(name: str) -> str:
    """Turn a lake name into a stable, URL-safe id (e.g. 'Ulsoor Lake' -> 'ulsoor-lake')."""
    slug = name.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "lake"


def _ring_centroid(coords) -> tuple[float, float]:
    """Approximate centroid (lon, lat) of a polygon's outer ring via vertex mean."""
    # coords for a Polygon is [outer_ring, hole1, ...]; use the outer ring.
    ring = coords[0]
    # Drop the closing vertex if it repeats the first.
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return lon, lat


def _centroid(geometry: dict) -> tuple[float, float]:
    """Compute an approximate centroid (lon, lat) for a Polygon or MultiPolygon."""
    gtype = geometry.get("type")
    coords = geometry["coordinates"]
    if gtype == "Polygon":
        return _ring_centroid(coords)
    if gtype == "MultiPolygon":
        # Average the per-polygon centroids.
        cs = [_ring_centroid(poly) for poly in coords]
        lon = sum(c[0] for c in cs) / len(cs)
        lat = sum(c[1] for c in cs) / len(cs)
        return lon, lat
    raise ValueError(f"Unsupported geometry type: {gtype!r} (expected Polygon/MultiPolygon)")


def load_lakes_from_geojson(geojson_path: str, dry_run: bool = False) -> int:
    """Parse a GeoJSON FeatureCollection and upsert all lakes. Returns the count."""
    path = Path(geojson_path)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(path.read_text())
    if data.get("type") != "FeatureCollection":
        print("ERROR: input must be a GeoJSON FeatureCollection", file=sys.stderr)
        sys.exit(1)

    features = data.get("features", [])
    print(f"Found {len(features)} features in {path}")

    if dry_run:
        for feat in features[:10]:
            name = feat.get("properties", {}).get("name", "<unnamed>")
            lake_id = feat.get("properties", {}).get("id") or slugify(name)
            print(f"  {lake_id}: {name}")
        if len(features) > 10:
            print(f"  ... and {len(features) - 10} more")
        return len(features)

    Base.metadata.create_all(engine)

    session = get_session()
    count = 0
    try:
        for feat in features:
            props = feat.get("properties", {})
            geometry = feat["geometry"]
            name = props.get("name")
            if not name:
                print("  SKIP feature with no 'name' property", file=sys.stderr)
                continue

            lake_id = props.get("id") or slugify(name)
            lon, lat = props.get("longitude"), props.get("latitude")
            if lon is None or lat is None:
                lon, lat = _centroid(geometry)

            geojson_str = json.dumps(geometry)
            values = {
                "id": lake_id,
                "name": name,
                "name_local": props.get("name_local") or props.get("name_kannada"),
                "latitude": lat,
                "longitude": lon,
                "boundary_geojson": geojson_str,
                "ward": props.get("ward"),
                "custodian": props.get("custodian"),
                "citizen_group": props.get("citizen_group"),
                "area_hectares": props.get("area_hectares"),
                "boundary_area_m2": props.get("boundary_area_m2"),
            }
            stmt = pg_insert(Lake).values(**values).on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "boundary_geojson": geojson_str,
                    "area_hectares": props.get("area_hectares"),
                    "boundary_area_m2": props.get("boundary_area_m2"),
                },
            )
            session.execute(stmt)
            count += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Loaded {count} lakes into the database.")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Load lake boundaries from a GeoJSON FeatureCollection"
    )
    parser.add_argument(
        "geojson",
        help="Path to a GeoJSON FeatureCollection of lake boundaries",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List lakes without writing to the database",
    )
    args = parser.parse_args()

    count = load_lakes_from_geojson(args.geojson, dry_run=args.dry_run)

    if not args.dry_run:
        print()
        print(f"Done — {count} lakes loaded. Next, run the satellite backfill:")
        print("  python -m pipeline.scripts.full_backfill")
        print("Or a single lake:")
        print("  python -m pipeline.scripts.run_pipeline --lake <lake-id>")


if __name__ == "__main__":
    main()
