/** react-query hooks for insights/data quality page. */

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import {
  fetchRawObservations,
  fetchLakeStatsTable,
  fetchOutliers,
  fetchCustodianStats,
  fetchMovers,
  fetchPulse,
} from "@/lib/api";
// Cross-reference is a Bangalore city extension; sourced from api-ext so this
// shared hook degrades cleanly when the public api-ext stub returns no entries.
import { fetchCrossReference } from "@/lib/api-ext";

export function useRawObservations(
  page: number = 1,
  pageSize: number = 100,
  lakeId?: string
) {
  return useQuery({
    queryKey: ["raw-observations", page, pageSize, lakeId],
    queryFn: () => fetchRawObservations(page, pageSize, lakeId),
    staleTime: 10 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useLakeStatsTable() {
  return useQuery({
    queryKey: ["lake-stats-table"],
    queryFn: fetchLakeStatsTable,
    staleTime: 10 * 60 * 1000,
  });
}

export function useCrossReference(lakeId: string) {
  return useQuery({
    queryKey: ["cross-reference", lakeId],
    queryFn: () => fetchCrossReference(lakeId),
    staleTime: 30 * 60 * 1000,
    enabled: Boolean(lakeId),
  });
}

export function useOutliers() {
  return useQuery({
    queryKey: ["outliers"],
    queryFn: fetchOutliers,
    staleTime: 10 * 60 * 1000,
  });
}

export function useCustodianStats() {
  return useQuery({
    queryKey: ["custodian-stats"],
    queryFn: fetchCustodianStats,
    staleTime: 10 * 60 * 1000,
  });
}

export function useMovers(year: number) {
  return useQuery({
    queryKey: ["movers", year],
    queryFn: () => fetchMovers(year),
    staleTime: 10 * 60 * 1000,
  });
}

export function usePulse() {
  return useQuery({
    queryKey: ["pulse"],
    queryFn: () => fetchPulse(),
    staleTime: 10 * 60 * 1000,
  });
}
