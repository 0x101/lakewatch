/** react-query hooks for lake data. */

import { useQuery } from "@tanstack/react-query";
import { fetchLakes, fetchLakesGeoJSON } from "@/lib/api";

export function useLakes() {
  return useQuery({
    queryKey: ["lakes"],
    queryFn: fetchLakes,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLakesGeoJSON() {
  return useQuery({
    queryKey: ["lakes-geojson"],
    queryFn: fetchLakesGeoJSON,
    staleTime: 5 * 60 * 1000,
  });
}
