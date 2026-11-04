"""Data quality and insights endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.queries.insights import (
    get_all_lake_stats_with_names,
    get_city_summary,
    get_movers,
    get_outliers,
    get_pulse,
    get_rankings,
    get_raw_observations,
    get_seasonal_aggregates,
    get_stats_by_custodian,
    get_yearly_trends,
)
from app.schemas.insights import (
    CitySummary,
    CustodianStatsEntry,
    CustodianStatsResponse,
    LakeStatsRow,
    LakeStatsTableResponse,
    MonthlyAggregate,
    MoverEntry,
    MoversResponse,
    OutlierEntry,
    OutliersResponse,
    PulseCitySummary,
    PulseLakeEntry,
    PulseObservationWindow,
    PulseResponse,
    RankingEntry,
    RankingsResponse,
    RawObservationRow,
    RawObservationsResponse,
    SeasonalResponse,
    TrendsResponse,
    YearlyTrend,
)

router = APIRouter(prefix="/api")

RANKING_CATEGORIES = {
    "health",
    "improving",
    "declining",
    "most_polluted",
    "cleanest",
    "largest",
    "smallest",
}


@router.get("/insights/observations", response_model=RawObservationsResponse)
def list_raw_observations(
    lake_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """Raw observation data as a sortable table."""
    rows, total = get_raw_observations(db, lake_id, page, page_size)
    return RawObservationsResponse(
        total=total,
        page=page,
        page_size=page_size,
        observations=[
            RawObservationRow(
                lake_id=r.lake_id,
                lake_name=r.lake_name,
                observation_date=str(r.observation_date),
                water_area_m2=r.water_area_m2,
                mean_ndwi=r.mean_ndwi,
                algae_fraction=r.algae_fraction,
                cloud_pct=r.cloud_pct,
            )
            for r in rows
        ],
    )


@router.get("/insights/stats", response_model=LakeStatsTableResponse)
def list_lake_stats(db: Session = Depends(get_db)):
    """All lake stats as a plain table."""
    rows = get_all_lake_stats_with_names(db)
    return LakeStatsTableResponse(
        count=len(rows),
        stats=[
            LakeStatsRow(
                lake_id=r.lake_id,
                lake_name=r.lake_name,
                health_score=r.health_score,
                latest_water_area_m2=r.latest_water_area_m2,
                area_change_1yr_pct=r.area_change_1yr_pct,
                area_change_5yr_pct=r.area_change_5yr_pct,
                seasonal_amplitude=r.seasonal_amplitude,
                peak_algae_month=r.peak_algae_month,
                mean_algae_fraction=r.mean_algae_fraction,
                observation_count=r.observation_count,
                latest_observation_date=(
                    str(r.latest_observation_date) if r.latest_observation_date else None
                ),
            )
            for r in rows
        ],
    )


@router.get("/insights/by-custodian", response_model=CustodianStatsResponse)
def list_stats_by_custodian(db: Session = Depends(get_db)):
    """Lake health stats grouped by custodian agency."""
    rows = get_stats_by_custodian(db)
    return CustodianStatsResponse(
        entries=[
            CustodianStatsEntry(
                custodian=r.custodian,
                lake_count=r.lake_count,
                avg_health=round(r.avg_health, 1) if r.avg_health is not None else None,
                distressed_count=r.distressed_count,
                healthy_count=r.healthy_count,
            )
            for r in rows
        ],
    )


@router.get("/insights/outliers", response_model=OutliersResponse)
def list_outliers(db: Session = Depends(get_db)):
    """Flagged outlier observations with explanations."""
    outliers = get_outliers(db)
    return OutliersResponse(
        count=len(outliers),
        outliers=[OutlierEntry(**o) for o in outliers],
    )


@router.get("/insights/city-summary", response_model=CitySummary)
def city_summary(db: Session = Depends(get_db)):
    """City-wide health snapshot across all lakes."""
    data = get_city_summary(db)
    return CitySummary(**data)


@router.get("/insights/trends", response_model=TrendsResponse)
def yearly_trends(db: Session = Depends(get_db)):
    """Yearly aggregated data for trend charts."""
    years = get_yearly_trends(db)
    return TrendsResponse(
        years=[
            YearlyTrend(
                year=y["year"],
                avg_health=y["avg_health"],
                total_water_area=y["total_water_area"],
                avg_algae=y["avg_algae"],
                observation_count=y["observation_count"],
            )
            for y in years
        ],
    )


@router.get("/insights/seasonal", response_model=SeasonalResponse)
def seasonal_data(db: Session = Depends(get_db)):
    """Monthly aggregated data across all lakes for seasonal patterns."""
    months = get_seasonal_aggregates(db)
    return SeasonalResponse(
        months=[MonthlyAggregate(**m) for m in months],
    )


@router.get("/insights/rankings", response_model=RankingsResponse)
def lake_rankings(
    category: str = Query(
        default="health",
        description="Ranking category: health, improving, declining, "
        "most_polluted, cleanest, largest, smallest",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lake rankings in multiple categories."""
    if category not in RANKING_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {category}. "
            f"Use one of: {', '.join(sorted(RANKING_CATEGORIES))}",
        )
    entries = get_rankings(db, category, limit)
    return RankingsResponse(
        category=category,
        entries=[RankingEntry(**e) for e in entries],
    )


@router.get("/insights/movers", response_model=MoversResponse)
def year_over_year_movers(
    year: int | None = Query(
        default=None,
        ge=2016,
        description="Year to compare against the previous one (default: last full year)",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Year-over-year water area movers: top improvers and decliners."""
    this_year = date.today().year
    if year is None:
        year = this_year - 1
    elif year > this_year:
        raise HTTPException(status_code=400, detail=f"year must be <= {this_year}")
    data = get_movers(db, year, limit)
    return MoversResponse(
        year=data["year"],
        improvers=[MoverEntry(**e) for e in data["improvers"]],
        decliners=[MoverEntry(**e) for e in data["decliners"]],
    )


@router.get("/insights/pulse", response_model=PulseResponse)
def lake_pulse(
    window_days: int = Query(default=120, ge=30, le=365),
    db: Session = Depends(get_db),
):
    """Recent movers (gainers/shrinkers), algae watchlist, and city net change."""
    data = get_pulse(db, window_days)
    return PulseResponse(
        as_of=data["as_of"],
        observation_window=PulseObservationWindow(**data["observation_window"]),
        gainers=[PulseLakeEntry(**e) for e in data["gainers"]],
        shrinkers=[PulseLakeEntry(**e) for e in data["shrinkers"]],
        algae_watch=[PulseLakeEntry(**e) for e in data["algae_watch"]],
        city=PulseCitySummary(**data["city"]),
    )
