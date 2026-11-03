"""Tests for GeoJSON lake loading (validation + derived fields, no DB)."""

import json

import pytest

from pipeline.scripts.load_lakes import (
    _polygon_area_m2,
    _validate_geometry,
    load_lakes_from_geojson,
    slugify,
)

# ~100 m x ~100 m square near the equator.
SQUARE = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [0.000898, 0], [0.000898, 0.000898], [0, 0.000898], [0, 0]]],
}


def _fc(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def _feature(name, geometry=SQUARE, **props):
    return {"type": "Feature", "properties": {"name": name, **props}, "geometry": geometry}


def test_slugify():
    assert slugify("Ulsoor  Lake") == "ulsoor-lake"
    assert slugify("!!!") == "lake"


def test_polygon_area_square():
    assert _polygon_area_m2(SQUARE, 0.0) == pytest.approx(10_000, rel=0.01)


def test_polygon_area_subtracts_holes():
    hole = [[0.0002, 0.0002], [0.0004, 0.0002], [0.0004, 0.0004], [0.0002, 0.0004], [0.0002, 0.0002]]
    geom = {"type": "Polygon", "coordinates": [SQUARE["coordinates"][0], hole]}
    assert _polygon_area_m2(geom, 0.0) < _polygon_area_m2(SQUARE, 0.0)


@pytest.mark.parametrize(
    "geometry, fragment",
    [
        (None, "missing"),
        ({"type": "Point", "coordinates": [0, 0]}, "unsupported"),
        ({"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]}, "at least 4"),
        (
            {"type": "Polygon", "coordinates": [[[500000, 1400000], [1, 0], [1, 1], [500000, 1400000]]]},
            "EPSG:4326",
        ),
    ],
)
def test_validate_geometry_rejects(geometry, fragment):
    assert fragment in _validate_geometry(geometry)


def test_validate_geometry_accepts_square():
    assert _validate_geometry(SQUARE) is None


def test_duplicate_ids_abort_before_writing(tmp_path, capsys):
    path = tmp_path / "lakes.geojson"
    path.write_text(json.dumps(_fc(_feature("Kere"), _feature("kere"))))
    with pytest.raises(SystemExit):
        load_lakes_from_geojson(str(path), dry_run=True)
    assert "already used" in capsys.readouterr().err


def test_dry_run_reports_valid_lakes(tmp_path):
    path = tmp_path / "lakes.geojson"
    path.write_text(json.dumps(_fc(_feature("A"), _feature("B", id="b-custom"))))
    assert load_lakes_from_geojson(str(path), dry_run=True) == 2
