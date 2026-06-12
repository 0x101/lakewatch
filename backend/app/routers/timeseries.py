"""Timeseries endpoint — observation history with interval aggregation."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.queries.lakes import get_lake_by_id
from app.queries.observations import get_aggregated_observations, get_raw_observations
from app.schemas.observation import ObservationPoint, TimeseriesResponse

router = APIRouter(prefix="/api")

INTERVAL_MAP = {"monthly": "month", "yearly": "year"}


@router.get("/lakes/{lake_id}/timeseries", response_model=TimeseriesResponse)
def get_timeseries(
    lake_id: str,
    interval: str = "raw",
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    """Return observation timeseries for a lake.

    Supports raw (all observations), monthly, and yearly aggregation intervals.
    """
    # Check lake exists
    result = get_lake_by_id(db, lake_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lake not found")

    if interval == "raw":
        rows = get_raw_observations(db, lake_id, from_date, to_date)
        points = [
            ObservationPoint(
                date=str(obs.observation_date),
                water_area_m2=obs.water_area_m2,
                mean_ndwi=obs.mean_ndwi,
                algae_fraction=obs.algae_fraction,
                cloud_pct=obs.cloud_pct,
            )
            for obs in rows
        ]
    elif interval in INTERVAL_MAP:
        sql_interval = INTERVAL_MAP[interval]
        rows = get_aggregated_observations(
            db, lake_id, sql_interval, from_date, to_date
        )
        points = [
            ObservationPoint(
                date=str(row.period.date()) if hasattr(row.period, "date") else str(row.period),
                water_area_m2=row.water_area_m2,
                mean_ndwi=row.mean_ndwi,
                algae_fraction=row.algae_fraction,
                cloud_pct=row.cloud_pct,
            )
            for row in rows
        ]
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval: {interval}. Use raw, monthly, or yearly.",
        )

    return TimeseriesResponse(
        lake_id=lake_id,
        interval=interval,
        count=len(points),
        observations=points,
    )
