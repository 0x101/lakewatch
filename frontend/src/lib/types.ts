/** TypeScript types mirroring backend Pydantic schemas. */

export interface LakeListItem {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  health_score: number | null;
  latest_water_area_m2: number | null;
  area_change_1yr_pct: number | null;
  area_change_5yr_pct: number | null;
  mean_algae_fraction: number | null;
  observation_count: number;
}

export interface LakesResponse {
  lakes: LakeListItem[];
}

export interface LakeGeoJSONProperties {
  id: string;
  name: string;
  health_score: number | null;
  area_change_5yr_pct: number | null;
  latest_water_area_m2: number | null;
  observation_count: number;
}

export interface LeaderboardEntry {
  rank: number;
  lake_id: string;
  lake_name: string;
  metric_value: number | null;
  metric_name: string;
  health_score: number | null;
  area_change_5yr_pct: number | null;
  observation_count: number;
  pollution_level: string | null;
}

export interface LeaderboardResponse {
  category: string;
  entries: LeaderboardEntry[];
}

export interface ObservationPoint {
  date: string;
  water_area_m2: number | null;
  mean_ndwi: number | null;
  algae_fraction: number | null;
  cloud_pct: number | null;
}

export interface TimeseriesResponse {
  lake_id: string;
  interval: string;
  count: number;
  observations: ObservationPoint[];
}

export interface LakeDetail {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  health_score: number | null;
  latest_water_area_m2: number | null;
  area_change_1yr_pct: number | null;
  area_change_5yr_pct: number | null;
  mean_algae_fraction: number | null;
  observation_count: number;
  boundary_geojson: GeoJSON.Geometry;
  ward: string | null;
  custodian: string | null;
  citizen_group: string | null;
  area_hectares: number | null;
  name_local: string | null;
  latest_observation_date: string | null;
  peak_algae_month: number | null;
  seasonal_amplitude: number | null;
  boundary_area_m2: number | null;
  water_coverage_pct: number | null;
}

export interface FrameItem {
  observation_date: string;
  frame_url: string;
  thumbnail_url: string | null;
  frame_order: number;
}

export interface AssetItem {
  asset_type: string;
  url: string;
  file_size_bytes: number | null;
}

export interface TimelapseResponse {
  lake_id: string;
  frames: FrameItem[];
  assets: AssetItem[];
}

/** EMPRI ground-truth data for a lake. */
export interface EMPRIRecord {
  lake_id: string;
  survey_year: number;
  pollution_level: string | null;
  pollution_sources: string | null;
  biota_type: string | null;
  custodian_agency: string | null;
  encroachment_status: string | null;
  sewage_inflow: string | null;
  water_spread_area_ha: number | null;
  catchment_area_ha: number | null;
  rejuvenation_status: string | null;
}

/** Stream network connection. */
export interface ConnectedLake {
  lake_id: string;
  lake_name: string;
  relationship: string;
  stream_name: string | null;
}

export interface StreamConnectionsResponse {
  lake_id: string;
  feeds_into: ConnectedLake[];
  fed_by: ConnectedLake[];
}

/** Insights page types. */
export interface RawObservationRow {
  lake_id: string;
  lake_name: string;
  observation_date: string;
  water_area_m2: number | null;
  mean_ndwi: number | null;
  algae_fraction: number | null;
  cloud_pct: number | null;
}

export interface RawObservationsResponse {
  total: number;
  page: number;
  page_size: number;
  observations: RawObservationRow[];
}

export interface LakeStatsRow {
  lake_id: string;
  lake_name: string;
  health_score: number | null;
  latest_water_area_m2: number | null;
  area_change_1yr_pct: number | null;
  area_change_5yr_pct: number | null;
  seasonal_amplitude: number | null;
  peak_algae_month: number | null;
  mean_algae_fraction: number | null;
  observation_count: number;
  latest_observation_date: string | null;
}

export interface LakeStatsTableResponse {
  count: number;
  stats: LakeStatsRow[];
}

export interface CrossReferenceEntry {
  month: string;
  satellite_algae_fraction: number | null;
  agreement: string | null;
}

export interface CrossReferenceResponse {
  lake_id: string;
  entries: CrossReferenceEntry[];
}

export interface OutlierEntry {
  lake_id: string;
  lake_name: string;
  observation_date: string;
  outlier_type: string;
  value: number | null;
  explanation: string;
}

export interface OutliersResponse {
  count: number;
  outliers: OutlierEntry[];
}

export interface CustodianStatsEntry {
  custodian: string;
  lake_count: number;
  avg_health: number | null;
  distressed_count: number;
  healthy_count: number;
}

export interface CustodianStatsResponse {
  entries: CustodianStatsEntry[];
}

/** City-wide dashboard types. */
export interface CitySummary {
  total_lakes: number;
  total_observations: number;
  avg_health_score: number;
  median_health_score: number;
  total_water_area_ha: number;
  distressed_count: number;
  struggling_count: number;
  healthy_count: number;
  avg_algae_fraction: number;
  lakes_improving: number;
  lakes_declining: number;
}

export interface YearlyTrendPoint {
  year: number;
  avg_health: number | null;
  total_water_area: number | null;
  avg_algae: number | null;
  observation_count: number;
}

export interface TrendsResponse {
  years: YearlyTrendPoint[];
}

export interface SeasonalPoint {
  month: number;
  avg_water_area: number | null;
  avg_algae: number | null;
  observation_count: number;
}

export interface SeasonalResponse {
  months: SeasonalPoint[];
}

export interface DashboardRankingEntry {
  rank: number;
  lake_id: string;
  lake_name: string;
  metric_value: number | null;
  health_score: number | null;
  custodian: string | null;
}

export interface DashboardRankingsResponse {
  category: string;
  entries: DashboardRankingEntry[];
}

/** Year-over-year movers. */
export interface MoverEntry {
  lake_id: string;
  lake_name: string;
  current_year_avg_area: number | null;
  previous_year_avg_area: number | null;
  change_pct: number | null;
  health_score: number | null;
  custodian: string | null;
}

export interface MoversResponse {
  year: number;
  improvers: MoverEntry[];
  decliners: MoverEntry[];
}

/** Pulse: recent movers + algae watch + city net change. */
export interface PulseLakeEntry {
  lake_id: string;
  lake_name: string;
  water_area_m2: number | null;
  area_change_m2: number | null;
  area_change_pct: number | null;
  algae_fraction: number | null;
  algae_trend: number | null;
}

export interface PulseCitySummary {
  total_water_area_now_m2: number | null;
  total_water_area_1yr_ago_m2: number | null;
  net_change_m2: number | null;
}

export interface PulseObservationWindow {
  start: string | null;
  end: string | null;
}

export interface PulseResponse {
  as_of: string | null;
  observation_window: PulseObservationWindow;
  gainers: PulseLakeEntry[];
  shrinkers: PulseLakeEntry[];
  algae_watch: PulseLakeEntry[];
  city: PulseCitySummary;
}
