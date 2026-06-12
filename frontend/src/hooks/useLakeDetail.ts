/** react-query hook for single lake detail data. */

import { useQuery } from "@tanstack/react-query";
import { fetchLakeDetail } from "@/lib/api";

export function useLakeDetail(lakeId: string) {
  return useQuery({
    queryKey: ["lake-detail", lakeId],
    queryFn: () => fetchLakeDetail(lakeId),
    staleTime: 10 * 60 * 1000,
    enabled: Boolean(lakeId),
  });
}
