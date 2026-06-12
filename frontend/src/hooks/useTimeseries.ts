/** react-query hook for lake timeseries data. */

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchTimeseries } from "@/lib/api";

export function useTimeseries(lakeId: string, interval: string = "monthly") {
  return useQuery({
    queryKey: ["timeseries", lakeId, interval],
    queryFn: () => fetchTimeseries(lakeId, interval),
    staleTime: 10 * 60 * 1000,
    enabled: Boolean(lakeId),
    placeholderData: keepPreviousData,
  });
}
