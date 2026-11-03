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
        area_hectares (optional)  defaults to the polygon's computed area
        boundary_area_m2 (optional) computed from the polygon if absent

Only `name` is required; everything else is optional and degrades to NULL.
A minimal 3-lake example ships in examples/sample-lakes.geojson.

Re-running is safe: lakes are upserted by id (insert-or-update).
"""

import argparse
import json
import math
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


_EARTH_RADIUS_M = 6_371_008.8


def _ring_area_m2(ring, lat0: float) -> float:
    """Planar shoelace area of a lon/lat ring projected to local metres.

    Uses an equirectangular projection centred on ``lat0``. At lake scale
    (< a few km) this is within a fraction of a percent of the geodesic area,
    and it avoids a pyproj/GDAL dependency.
    """
    k = math.cos(math.radians(lat0))
    pts = [
        (math.radians(lon) * _EARTH_RADIUS_M * k, math.radians(lat) * _EARTH_RADIUS_M)
        for lon, lat, *_ in ring
    ]
    area = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _polygon_area_m2(geometry: dict, lat0: float) -> float:
    """Approximate area (m²) of a Polygon/MultiPolygon, holes subtracted."""
    polys = (
        [geometry["coordinates"]]
        if geometry["type"] == "Polygon"
        else geometry["coordinates"]
    )
    total = 0.0
    for poly in polys:
        if not poly:
            continue
        total += _ring_area_m2(poly[0], lat0)
        total -= sum(_ring_area_m2(hole, lat0) for hole in poly[1:])
    return total


def _validate_geometry(geometry) -> str | None:
    """Return an error message if ``geometry`` is unusable, else None."""
    if not isinstance(geometry, dict):
        return "missing geometry"
    gtype = geometry.get("type")
    if gtype not in ("Polygon", "MultiPolygon"):
        return f"unsupported geometry type {gtype!r} (expected Polygon/MultiPolygon)"
    coords = geometry.get("coordinates")
    polys = [coords] if gtype == "Polygon" else coords
    if not polys or not all(poly and len(poly[0]) >= 4 for poly in polys):
        return "polygon has no outer ring with at least 4 positions"
    for poly in polys:
        for lon, lat, *_ in poly[0]:
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                return (
                    f"coordinate ({lon}, {lat}) is outside lon/lat range — is the "
                    "file in EPSG:4326? Reproject with: ogr2ogr -t_srs EPSG:4326"
                )
    return None


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

    # Validate everything up front so a bad feature halfway through the file
    # doesn't leave the database half-loaded, and so two features that slugify
    # to the same id don't silently overwrite each other.
    rows: list[dict] = []
    seen: dict[str, str] = {}
    errors: list[str] = []
    for idx, feat in enumerate(features):
        props = feat.get("properties") or {}
        name = props.get("name")
        if not name:
            print(f"  SKIP feature #{idx}: no 'name' property", file=sys.stderr)
            continue
        geometry = feat.get("geometry")
        problem = _validate_geometry(geometry)
        if problem:
            errors.append(f"feature #{idx} ({name}): {problem}")
            continue
        lake_id = str(props.get("id") or slugify(name))
        if lake_id in seen:
            errors.append(
                f"feature #{idx} ({name}): id {lake_id!r} already used by "
                f"{seen[lake_id]!r} — give one of them an explicit 'id' property"
            )
            continue
        seen[lake_id] = name

        lon, lat = props.get("longitude"), props.get("latitude")
        if lon is None or lat is None:
            lon, lat = _centroid(geometry)

        boundary_area_m2 = props.get("boundary_area_m2")
        if boundary_area_m2 is None:
            boundary_area_m2 = round(_polygon_area_m2(geometry, lat), 1)

        rows.append(
            {
                "id": lake_id,
                "name": name,
                "name_local": props.get("name_local") or props.get("name_kannada"),
                "latitude": lat,
                "longitude": lon,
                "boundary_geojson": json.dumps(geometry),
                "ward": props.get("ward"),
                "custodian": props.get("custodian"),
                "citizen_group": props.get("citizen_group"),
                # Falls back to the polygon area so "largest first" ordering
                # in the backfill/ingest scripts works without this property.
                "area_hectares": (
                    props["area_hectares"]
                    if props.get("area_hectares") is not None
                    else round(boundary_area_m2 / 10_000, 2)
                ),
                "boundary_area_m2": boundary_area_m2,
            }
        )

    if errors:
        print(f"ERROR: {len(errors)} invalid feature(s); nothing was loaded:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        for row in rows[:10]:
            print(f"  {row['id']}: {row['name']} (~{row['boundary_area_m2'] / 10_000:.1f} ha)")
        if len(rows) > 10:
            print(f"  ... and {len(rows) - 10} more")
        return len(rows)

    Base.metadata.create_all(engine)

    session = get_session()
    count = 0
    try:
        for values in rows:
            # Re-running with an edited file updates every field except the id,
            # so fixing a ward/custodian/local name in the GeoJSON takes effect.
            stmt = pg_insert(Lake).values(**values).on_conflict_do_update(
                index_elements=["id"],
                set_={k: v for k, v in values.items() if k != "id"},
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
