/** react-query hooks for city-wide dashboard page. */

import { useQuery } from "@tanstack/react-query";
import {
  fetchCitySummary,
  fetchTrends,
  fetchSeasonal,
  fetchDashboardRankings,
} from "@/lib/api";

export function useCitySummary() {
  return useQuery({
    queryKey: ["city-summary"],
    queryFn: fetchCitySummary,
    staleTime: 10 * 60 * 1000,
  });
}

export function useTrends() {
  return useQuery({
    queryKey: ["trends"],
    queryFn: fetchTrends,
    staleTime: 10 * 60 * 1000,
  });
}

export function useSeasonal() {
  return useQuery({
    queryKey: ["seasonal"],
    queryFn: fetchSeasonal,
    staleTime: 10 * 60 * 1000,
  });
}

export function useDashboardRankings(category: string, limit: number = 20) {
  return useQuery({
    queryKey: ["dashboard-rankings", category, limit],
    queryFn: () => fetchDashboardRankings(category, limit),
    staleTime: 10 * 60 * 1000,
  });
}
