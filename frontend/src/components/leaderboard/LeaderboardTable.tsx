"use client";

import Link from "next/link";
import type { LeaderboardEntry } from "@/lib/types";
import HealthBadge from "./HealthBadge";
import Sparkline from "./Sparkline";
import TierBadge from "../ui/TierBadge";
import { getDisplayName, getLakeTier } from "@/lib/lake-enrichment";

interface LeaderboardTableProps {
  entries: LeaderboardEntry[];
  isLoading: boolean;
  category: string;
}

function formatMetric(value: number | null, metricName: string): string {
  if (value === null || value === undefined) return "—";
  const isPct =
    metricName.includes("pct") || metricName.includes("percent");
  if (isPct) {
    const sign = value > 0 ? "+" : "";
    return `${sign}${value.toFixed(1)}%`;
  }
  return value.toFixed(1);
}

type SparklineMetric = "water_area_m2" | "algae_fraction" | "mean_ndwi";

function sparklineMetricForCategory(category: string): SparklineMetric {
  if (category === "polluted") return "algae_fraction";
  return "water_area_m2";
}

const POLLUTION_COLORS: Record<string, string> = {
  Severe: "bg-red-500/20 text-red-400 border-red-500/30",
  High: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  Moderate: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  Low: "bg-green-500/20 text-green-400 border-green-500/30",
};

function PollutionPill({ level }: { level: string | null }) {
  if (!level) return null;
  const colors = POLLUTION_COLORS[level] ?? "bg-gray-500/20 text-gray-400 border-gray-500/30";
  return (
    <span
      className={`inline-flex ml-2 px-1.5 py-0.5 text-[10px] font-medium rounded border ${colors}`}
      title={`EMPRI pollution: ${level}`}
    >
      {level}
    </span>
  );
}

function rankStyle(rank: number): string {
  if (rank === 1) return "text-yellow-400 font-bold";
  if (rank === 2) return "text-gray-300 font-bold";
  if (rank === 3) return "text-amber-600 font-bold";
  return "text-gray-400";
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 10 }).map((_, i) => (
        <tr key={i} className="border-b border-gray-800">
          <td className="px-3 py-3">
            <div className="h-4 w-6 bg-gray-800 rounded animate-pulse" />
          </td>
          <td className="px-3 py-3">
            <div className="h-4 w-32 bg-gray-800 rounded animate-pulse" />
          </td>
          <td className="px-3 py-3">
            <div className="h-4 w-16 bg-gray-800 rounded animate-pulse" />
          </td>
          <td className="px-3 py-3 hidden md:table-cell">
            <div className="h-6 w-20 bg-gray-800 rounded animate-pulse" />
          </td>
          <td className="px-3 py-3">
            <div className="h-5 w-10 bg-gray-800 rounded-full animate-pulse" />
          </td>
        </tr>
      ))}
    </>
  );
}

export default function LeaderboardTable({
  entries,
  isLoading,
  category,
}: LeaderboardTableProps) {
  if (!isLoading && entries.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p className="text-lg">
          No lakes in this category yet.
        </p>
        <p className="text-sm mt-2">
          Data may still be processing. Check back after the next satellite pass.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
            <th className="px-3 py-3 w-12">#</th>
            <th className="px-3 py-3">Lake</th>
            <th className="px-3 py-3">Metric</th>
            <th className="px-3 py-3 hidden md:table-cell">Trend</th>
            <th className="px-3 py-3">Health</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <SkeletonRows />
          ) : (
            entries.map((entry) => (
              <Link
                key={entry.lake_id}
                href={`/lakes/${entry.lake_id}`}
                className="contents"
              >
                <tr className="border-b border-gray-800/50 hover:bg-gray-800/60 cursor-pointer transition-colors">
                  <td className={`px-3 py-3 ${rankStyle(entry.rank)}`}>
                    {entry.rank}
                  </td>
                  <td className="px-3 py-3 font-semibold text-white max-w-[260px]">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="truncate max-w-[180px]">{getDisplayName(entry.lake_id, entry.lake_name)}</span>
                      <TierBadge tier={getLakeTier(entry.lake_id)} />
                      <PollutionPill level={entry.pollution_level} />
                    </span>
                  </td>
                  <td className="px-3 py-3 text-gray-300 font-mono text-sm">
                    {formatMetric(entry.metric_value, entry.metric_name)}
                  </td>
                  <td className="px-3 py-3 hidden md:table-cell">
                    <Sparkline
                      lakeId={entry.lake_id}
                      metricKey={sparklineMetricForCategory(category)}
                    />
                  </td>
                  <td className="px-3 py-3">
                    <HealthBadge score={entry.health_score} />
                  </td>
                </tr>
              </Link>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
