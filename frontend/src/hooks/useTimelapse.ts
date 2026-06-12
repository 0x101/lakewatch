/** react-query hook for lake timelapse frames and assets. */

import { useQuery } from "@tanstack/react-query";
import { fetchTimelapse } from "@/lib/api";

export function useTimelapse(lakeId: string) {
  return useQuery({
    queryKey: ["timelapse", lakeId],
    queryFn: () => fetchTimelapse(lakeId),
    staleTime: 30 * 60 * 1000,
    enabled: Boolean(lakeId),
  });
}
