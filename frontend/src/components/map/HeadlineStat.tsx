"use client";

import { useLakes } from "@/hooks/useLakes";
import { useLeaderboard } from "@/hooks/useLeaderboard";

export function HeadlineStat() {
  const { data: lakesData, isLoading: lakesLoading } = useLakes();
  const { data: shrinkingData, isLoading: shrinkingLoading } =
    useLeaderboard("shrinking");

  if (lakesLoading || shrinkingLoading) {
    return (
      <div className="animate-pulse space-y-2">
        <div className="h-8 bg-white/10 rounded w-3/4" />
        <div className="h-4 bg-white/10 rounded w-1/2" />
      </div>
    );
  }

  const shrinkingCount = shrinkingData?.entries?.length ?? 0;

  const withData = lakesData?.lakes?.filter(l => l.observation_count > 0) ?? [];
  const healthyCount = withData.filter(l => (l.health_score ?? 0) >= 60).length;
  const distressedCount = withData.filter(l => l.health_score !== null && l.health_score < 30).length;
  const totalObs = withData.reduce((sum, l) => sum + l.observation_count, 0);

  return (
    <div className="space-y-3">
      <div>
        <p className="text-2xl font-bold leading-tight">
          <span className="text-white">{withData.length}</span>{" "}
          <span className="text-white/70 text-lg font-normal">lakes with satellite data</span>
        </p>
        <p className="text-sm text-white/40 mt-1">
          {totalObs.toLocaleString()} observations across {withData.length} lakes
        </p>
      </div>
      <div className="flex gap-3">
        <div className="flex-1 bg-white/5 rounded-lg p-2 text-center">
          <p className="text-lg font-bold text-green-400">{healthyCount}</p>
          <p className="text-[10px] text-white/40">healthy</p>
        </div>
        <div className="flex-1 bg-white/5 rounded-lg p-2 text-center">
          <p className="text-lg font-bold text-red-400">{distressedCount}</p>
          <p className="text-[10px] text-white/40">distressed</p>
        </div>
        <div className="flex-1 bg-white/5 rounded-lg p-2 text-center">
          <p className="text-lg font-bold text-orange-400">{shrinkingCount}</p>
          <p className="text-[10px] text-white/40">shrinking</p>
        </div>
      </div>
      <p className="text-xs text-white/30">
        Updated every 5 days from Sentinel-2 imagery.
      </p>
    </div>
  );
}
