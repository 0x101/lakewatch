/** react-query hooks for stream network data. */

import { useQuery } from "@tanstack/react-query";
import { fetchStreamConnections, fetchStreamsGeoJSON } from "@/lib/api-ext";

export function useStreamConnections(lakeId: string) {
  return useQuery({
    queryKey: ["stream-connections", lakeId],
    queryFn: () => fetchStreamConnections(lakeId),
    staleTime: 30 * 60 * 1000,
    enabled: Boolean(lakeId),
  });
}

export function useStreamsGeoJSON() {
  return useQuery({
    queryKey: ["streams-geojson"],
    queryFn: fetchStreamsGeoJSON,
    staleTime: 30 * 60 * 1000,
  });
}
