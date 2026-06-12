/**
 * City-extension API client — no-op upstream stub.
 *
 * Shared hooks (useStreams, useInsights, and any city-data hooks you add)
 * import their fetchers from here instead of calling city-specific endpoints
 * directly. In the upstream LakeWatch build these all resolve to empty/null
 * responses, so the shared hooks and components degrade cleanly to "no city
 * data" with zero code changes.
 *
 * When you add your city's data, replace this file with real fetchers that
 * hit your extension endpoints (mounted via backend/app/extensions.py). Reuse
 * the single `apiFetch` implementation exported from api.ts. Keep the export
 * names and return types identical so the shared hooks keep working.
 *
 * Reference implementation: Bangalore Lake Watch (nammalakes.com).
 */

import type {
  CrossReferenceResponse,
  EMPRIRecord,
  KSPCBCityAveragesResponse,
  KSPCBTimeseriesResponse,
  StreamConnectionsResponse,
} from "./types";

export function fetchEMPRI(lakeId: string): Promise<EMPRIRecord | null> {
  void lakeId;
  return Promise.resolve(null);
}

export function fetchKSPCB(lakeId: string): Promise<KSPCBTimeseriesResponse> {
  return Promise.resolve({ lake_id: lakeId, count: 0, measurements: [] });
}

export function fetchKSPCBCityAverages(): Promise<KSPCBCityAveragesResponse> {
  return Promise.resolve({ count: 0, averages: [] });
}

export function fetchStreamConnections(
  lakeId: string
): Promise<StreamConnectionsResponse> {
  return Promise.resolve({ lake_id: lakeId, feeds_into: [], fed_by: [] });
}

export function fetchStreamsGeoJSON(): Promise<GeoJSON.FeatureCollection> {
  return Promise.resolve({ type: "FeatureCollection", features: [] });
}

export function fetchCrossReference(
  lakeId: string
): Promise<CrossReferenceResponse> {
  return Promise.resolve({ lake_id: lakeId, entries: [] });
}
