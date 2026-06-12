/**
 * Typed API client for the LakeWatch backend.
 *
 * All requests go to the same origin and are proxied to the backend
 * via Next.js rewrites configured in next.config.ts.
 */

import type {
  CitySummary,
  CustodianStatsResponse,
  DashboardRankingsResponse,
  LakeDetail,
  LakeStatsTableResponse,
  LakesResponse,
  LeaderboardResponse,
  MoversResponse,
  OutliersResponse,
  PulseResponse,
  RawObservationsResponse,
  SeasonalResponse,
  TimelapseResponse,
  TimeseriesResponse,
  TrendsResponse,
} from "./types";

// Exported so the private-only api-ext.ts reuses a single fetch implementation.
export async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export function fetchLakes(): Promise<LakesResponse> {
  return apiFetch<LakesResponse>("/api/lakes");
}

export function fetchLakesGeoJSON(): Promise<GeoJSON.FeatureCollection> {
  return apiFetch<GeoJSON.FeatureCollection>("/api/lakes/geojson");
}

export function fetchLeaderboard(
  category: string
): Promise<LeaderboardResponse> {
  return apiFetch<LeaderboardResponse>(
    `/api/leaderboard?category=${encodeURIComponent(category)}`
  );
}

export function fetchTimeseries(
  lakeId: string,
  interval: string = "raw"
): Promise<TimeseriesResponse> {
  return apiFetch<TimeseriesResponse>(
    `/api/lakes/${encodeURIComponent(lakeId)}/timeseries?interval=${encodeURIComponent(interval)}`
  );
}

export function fetchLakeDetail(lakeId: string): Promise<LakeDetail> {
  return apiFetch<LakeDetail>(
    `/api/lakes/${encodeURIComponent(lakeId)}`
  );
}

export function fetchTimelapse(lakeId: string): Promise<TimelapseResponse> {
  return apiFetch<TimelapseResponse>(
    `/api/lakes/${encodeURIComponent(lakeId)}/timelapse`
  );
}

export function fetchRawObservations(
  page: number = 1,
  pageSize: number = 100,
  lakeId?: string
): Promise<RawObservationsResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (lakeId) params.set("lake_id", lakeId);
  return apiFetch<RawObservationsResponse>(
    `/api/insights/observations?${params}`
  );
}

export function fetchLakeStatsTable(): Promise<LakeStatsTableResponse> {
  return apiFetch<LakeStatsTableResponse>("/api/insights/stats");
}

export function fetchOutliers(): Promise<OutliersResponse> {
  return apiFetch<OutliersResponse>("/api/insights/outliers");
}

export function fetchCustodianStats(): Promise<CustodianStatsResponse> {
  return apiFetch<CustodianStatsResponse>("/api/insights/by-custodian");
}

export function fetchCitySummary(): Promise<CitySummary> {
  return apiFetch<CitySummary>("/api/insights/city-summary");
}

export function fetchTrends(): Promise<TrendsResponse> {
  return apiFetch<TrendsResponse>("/api/insights/trends");
}

export function fetchSeasonal(): Promise<SeasonalResponse> {
  return apiFetch<SeasonalResponse>("/api/insights/seasonal");
}

export function fetchDashboardRankings(
  category: string,
  limit: number = 20
): Promise<DashboardRankingsResponse> {
  return apiFetch<DashboardRankingsResponse>(
    `/api/insights/rankings?category=${encodeURIComponent(category)}&limit=${limit}`
  );
}

export function fetchMovers(
  year: number,
  limit: number = 20
): Promise<MoversResponse> {
  return apiFetch<MoversResponse>(
    `/api/insights/movers?year=${year}&limit=${limit}`
  );
}

export function fetchPulse(windowDays?: number): Promise<PulseResponse> {
  const query =
    windowDays !== undefined ? `?window_days=${windowDays}` : "";
  return apiFetch<PulseResponse>(`/api/insights/pulse${query}`);
}
