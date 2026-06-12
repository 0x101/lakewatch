"""Timeseries observation response schemas (Pydantic v2)."""

from pydantic import BaseModel


class ObservationPoint(BaseModel):
    """Single data point in a timeseries."""

    date: str
    water_area_m2: float | None = None
    mean_ndwi: float | None = None
    algae_fraction: float | None = None
    cloud_pct: float | None = None


class TimeseriesResponse(BaseModel):
    """Response wrapper for timeseries endpoint."""

    lake_id: str
    interval: str
    count: int
    observations: list[ObservationPoint]
