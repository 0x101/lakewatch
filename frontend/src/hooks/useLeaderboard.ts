/** react-query hook for leaderboard data. */

import { useQuery } from "@tanstack/react-query";
import { fetchLeaderboard } from "@/lib/api";

export function useLeaderboard(category: string) {
  return useQuery({
    queryKey: ["leaderboard", category],
    queryFn: () => fetchLeaderboard(category),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(category),
  });
}
