"""Data quality and insights response schemas (Pydantic v2)."""

from pydantic import BaseModel


class RawObservationRow(BaseModel):
    """Single observation row for the raw data table."""

    lake_id: str
    lake_name: str
    observation_date: str
    water_area_m2: float | None = None
    mean_ndwi: float | None = None
    algae_fraction: float | None = None
    cloud_pct: float | None = None


class RawObservationsResponse(BaseModel):
    """Paginated raw observations table."""

    total: int
    page: int
    page_size: int
    observations: list[RawObservationRow]


class LakeStatsRow(BaseModel):
    """Lake stats for the stats table."""

    lake_id: str
    lake_name: str
    health_score: float | None = None
    latest_water_area_m2: float | None = None
    area_change_1yr_pct: float | None = None
    area_change_5yr_pct: float | None = None
    seasonal_amplitude: float | None = None
    peak_algae_month: int | None = None
    mean_algae_fraction: float | None = None
    observation_count: int = 0
    latest_observation_date: str | None = None


class LakeStatsTableResponse(BaseModel):
    """All lake stats as a table."""

    count: int
    stats: list[LakeStatsRow]


class CrossReferenceEntry(BaseModel):
    """Cross-reference between satellite and ground-truth data for a month."""

    month: str
    satellite_algae_fraction: float | None = None
    kspcb_bod: float | None = None
    kspcb_cod: float | None = None
    kspcb_do: float | None = None
    kspcb_classification: str | None = None
    agreement: str | None = None  # "consistent", "contradictory", "partial"


class CrossReferenceResponse(BaseModel):
    """Cross-reference data for a lake."""

    lake_id: str
    entries: list[CrossReferenceEntry]


class OutlierEntry(BaseModel):
    """Flagged outlier observation."""

    lake_id: str
    lake_name: str
    observation_date: str
    outlier_type: str  # "zero_area", "algae_spike", "area_spike"
    value: float | None = None
    explanation: str


class OutliersResponse(BaseModel):
    """Flagged outlier observations."""

    count: int
    outliers: list[OutlierEntry]


class CustodianStatsEntry(BaseModel):
    """Health stats aggregated for a single custodian agency."""

    custodian: str
    lake_count: int
    avg_health: float | None = None
    distressed_count: int = 0
    healthy_count: int = 0


class CustodianStatsResponse(BaseModel):
    """Lake health stats grouped by custodian agency."""

    entries: list[CustodianStatsEntry]


# --- City-wide aggregate metrics ---


class CitySummary(BaseModel):
    """City-wide health snapshot."""

    total_lakes: int
    total_observations: int
    avg_health_score: float | None = None
    median_health_score: float | None = None
    total_water_area_ha: float | None = None
    distressed_count: int = 0
    struggling_count: int = 0
    healthy_count: int = 0
    avg_algae_fraction: float | None = None
    most_common_kspcb_class: str | None = None
    lakes_improving: int = 0
    lakes_declining: int = 0


class YearlyKSPCBDistribution(BaseModel):
    """KSPCB classification counts for a single year."""

    A: int = 0
    B: int = 0
    C: int = 0
    D: int = 0
    E: int = 0


class YearlyTrend(BaseModel):
    """Aggregated metrics for a single year."""

    year: int
    avg_health: float | None = None
    total_water_area: float | None = None
    avg_algae: float | None = None
    observation_count: int = 0
    kspcb_class_distribution: YearlyKSPCBDistribution = YearlyKSPCBDistribution()


class TrendsResponse(BaseModel):
    """Yearly trend data for charts."""

    years: list[YearlyTrend]


class MonthlyAggregate(BaseModel):
    """Aggregated metrics for a single month (1-12) across all years."""

    month: int
    avg_water_area: float | None = None
    avg_algae: float | None = None
    observation_count: int = 0


class SeasonalResponse(BaseModel):
    """Monthly aggregated data across all lakes."""

    months: list[MonthlyAggregate]


class RankingEntry(BaseModel):
    """Single entry in a lake ranking."""

    rank: int
    lake_id: str
    lake_name: str
    metric_value: float | None = None
    health_score: float | None = None
    custodian: str | None = None


class RankingsResponse(BaseModel):
    """Lake rankings in a given category."""

    category: str
    entries: list[RankingEntry]


class CorrelationEntry(BaseModel):
    """Satellite vs KSPCB correlation for a single lake."""

    lake_id: str
    lake_name: str
    health_score: float | None = None
    latest_kspcb_class: str | None = None
    latest_bod: float | None = None
    latest_algae_fraction: float | None = None


class CorrelationResponse(BaseModel):
    """Satellite health score vs KSPCB classification correlation."""

    entries: list[CorrelationEntry]


class MoverEntry(BaseModel):
    """Single lake in the year-over-year movers list."""

    lake_id: str
    lake_name: str
    current_year_avg_area: float | None = None
    previous_year_avg_area: float | None = None
    change_pct: float | None = None
    health_score: float | None = None
    custodian: str | None = None


class MoversResponse(BaseModel):
    """Year-over-year movers: improvers and decliners."""

    year: int
    improvers: list[MoverEntry]
    decliners: list[MoverEntry]


# --- Pulse: recent movers + algae watch + city net change ---


class PulseLakeEntry(BaseModel):
    """A single lake in a pulse list (gainer, shrinker, or algae watch)."""

    lake_id: str
    lake_name: str
    water_area_m2: float | None = None
    area_change_m2: float | None = None
    area_change_pct: float | None = None
    algae_fraction: float | None = None
    algae_trend: float | None = None


class PulseCitySummary(BaseModel):
    """City-wide water area now vs ~1 year ago."""

    total_water_area_now_m2: float | None = None
    total_water_area_1yr_ago_m2: float | None = None
    net_change_m2: float | None = None


class PulseObservationWindow(BaseModel):
    """Date window bounding the observations used in the pulse."""

    start: str | None = None
    end: str | None = None


class PulseResponse(BaseModel):
    """Recent movers, algae watchlist, and city net change."""

    as_of: str | None = None
    observation_window: PulseObservationWindow
    gainers: list[PulseLakeEntry]
    shrinkers: list[PulseLakeEntry]
    algae_watch: list[PulseLakeEntry]
    city: PulseCitySummary
