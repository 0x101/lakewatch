"""Lake endpoint response schemas (Pydantic v2)."""

from pydantic import BaseModel


class LakeListItem(BaseModel):
    """Lake summary for list endpoint."""

    id: str
    name: str
    latitude: float
    longitude: float
    health_score: float | None = None
    latest_water_area_m2: float | None = None
    area_change_1yr_pct: float | None = None
    area_change_5yr_pct: float | None = None
    mean_algae_fraction: float | None = None
    observation_count: int = 0


class LakesResponse(BaseModel):
    """Response wrapper for lake list endpoint."""

    lakes: list[LakeListItem]


class LakeGeoJSONProperties(BaseModel):
    """Properties for a lake GeoJSON feature (flat — no nested objects)."""

    id: str
    name: str
    health_score: float | None = None
    area_change_5yr_pct: float | None = None
    latest_water_area_m2: float | None = None
    observation_count: int = 0


class LakeDetail(BaseModel):
    """Full lake detail for single-lake endpoint."""

    id: str
    name: str
    latitude: float
    longitude: float
    health_score: float | None = None
    latest_water_area_m2: float | None = None
    area_change_1yr_pct: float | None = None
    area_change_5yr_pct: float | None = None
    mean_algae_fraction: float | None = None
    observation_count: int = 0
    boundary_geojson: dict
    ward: str | None = None
    custodian: str | None = None
    citizen_group: str | None = None
    area_hectares: float | None = None
    boundary_area_m2: float | None = None
    name_local: str | None = None
    latest_observation_date: str | None = None
    peak_algae_month: int | None = None
    seasonal_amplitude: float | None = None
    water_coverage_pct: float | None = None
