"""Lake list and detail endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.queries.lakes import get_all_lakes_with_boundaries, get_all_lakes_with_stats, get_lake_by_id
from app.schemas.lake import LakeDetail, LakeListItem, LakesResponse

router = APIRouter(prefix="/api")


@router.get("/lakes", response_model=LakesResponse)
def list_lakes(db: Session = Depends(get_db)):
    """List all lakes with their latest stats."""
    rows = get_all_lakes_with_stats(db)
    lakes = []
    for lake, stats in rows:
        lakes.append(
            LakeListItem(
                id=lake.id,
                name=lake.name,
                latitude=lake.latitude,
                longitude=lake.longitude,
                health_score=stats.health_score if stats else None,
                latest_water_area_m2=stats.latest_water_area_m2 if stats else None,
                area_change_1yr_pct=stats.area_change_1yr_pct if stats else None,
                area_change_5yr_pct=stats.area_change_5yr_pct if stats else None,
                mean_algae_fraction=stats.mean_algae_fraction if stats else None,
                observation_count=stats.observation_count if stats else 0,
            )
        )
    return LakesResponse(lakes=lakes)


@router.get("/lakes/geojson")
def list_lakes_geojson(db: Session = Depends(get_db)):
    """Return all lakes as a GeoJSON FeatureCollection with polygon boundaries."""
    rows = get_all_lakes_with_boundaries(db)
    features = []
    for lake, stats in rows:
        geometry = json.loads(lake.boundary_geojson) if lake.boundary_geojson else {}
        features.append(
            {
                "type": "Feature",
                "id": lake.id,
                "geometry": geometry,
                "properties": {
                    "id": lake.id,
                    "name": lake.name,
                    "health_score": stats.health_score if stats else None,
                    "area_change_5yr_pct": stats.area_change_5yr_pct if stats else None,
                    "latest_water_area_m2": stats.latest_water_area_m2 if stats else None,
                    "observation_count": stats.observation_count if stats else 0,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/lakes/{lake_id}", response_model=LakeDetail)
def get_lake(lake_id: str, db: Session = Depends(get_db)):
    """Get full lake detail including GeoJSON boundary."""
    result = get_lake_by_id(db, lake_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lake not found")

    lake, stats = result
    boundary_geojson = json.loads(lake.boundary_geojson) if lake.boundary_geojson else {}

    return LakeDetail(
        id=lake.id,
        name=lake.name,
        latitude=lake.latitude,
        longitude=lake.longitude,
        health_score=stats.health_score if stats else None,
        latest_water_area_m2=stats.latest_water_area_m2 if stats else None,
        area_change_1yr_pct=stats.area_change_1yr_pct if stats else None,
        area_change_5yr_pct=stats.area_change_5yr_pct if stats else None,
        mean_algae_fraction=stats.mean_algae_fraction if stats else None,
        observation_count=stats.observation_count if stats else 0,
        boundary_geojson=boundary_geojson,
        ward=lake.ward,
        custodian=lake.custodian,
        citizen_group=lake.citizen_group,
        area_hectares=lake.area_hectares,
        boundary_area_m2=lake.boundary_area_m2,
        name_kannada=lake.name_kannada,
        latest_observation_date=(
            str(stats.latest_observation_date) if stats and stats.latest_observation_date else None
        ),
        peak_algae_month=stats.peak_algae_month if stats else None,
        seasonal_amplitude=stats.seasonal_amplitude if stats else None,
        water_coverage_pct=(
            round((stats.latest_water_area_m2 / lake.boundary_area_m2) * 100, 1)
            if stats and stats.latest_water_area_m2 and lake.boundary_area_m2 and lake.boundary_area_m2 > 0
            else None
        ),
    )
