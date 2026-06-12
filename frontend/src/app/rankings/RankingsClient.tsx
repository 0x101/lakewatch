"use client";

import { useState } from "react";
import Link from "next/link";
import { useLeaderboard } from "@/hooks/useLeaderboard";
import { useDashboardRankings } from "@/hooks/useDashboard";
import { useMovers } from "@/hooks/useInsights";
import HealthBadge from "@/components/leaderboard/HealthBadge";
import TierBadge from "@/components/ui/TierBadge";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { getDisplayName, getLakeTier } from "@/lib/lake-enrichment";

const TABS = [
  { key: "best", label: "Best" },
  { key: "worst", label: "Worst" },
  { key: "most_improved", label: "Most Improved" },
  { key: "most_declined", label: "Most Declined" },
  { key: "most_polluted", label: "Most Polluted" },
  { key: "cleanest", label: "Cleanest" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`bg-white/5 rounded-xl animate-pulse ${className}`} />;
}

/* ── Leaderboard-based tab (best/worst/most_polluted/cleanest) ── */

function LeaderboardTab({ category }: { category: string }) {
  // Map our tab keys to leaderboard API categories
  const apiCategory =
    category === "best"
      ? "recovering"
      : category === "worst"
        ? "shrinking"
        : category === "most_polluted"
          ? "polluted"
          : "volatile"; // cleanest -> volatile (closest match)

  const { data: leaderboardData, isLoading: lbLoading } = useLeaderboard(apiCategory);

  // Also pull dashboard rankings for richer data
  const dashCategory =
    category === "best"
      ? "healthiest"
      : category === "worst"
        ? "most_declined"
        : category === "most_polluted"
          ? "most_polluted"
          : "cleanest";

  const { data: rankingsData, isLoading: rkLoading } = useDashboardRankings(dashCategory);

  const isLoading = lbLoading && rkLoading;

  // Prefer dashboard rankings if available (has custodian), fall back to leaderboard
  const entries = rankingsData?.entries ?? [];
  const lbEntries = leaderboardData?.entries ?? [];

  // Use dashboard rankings for best/worst/most_polluted/cleanest
  if (isLoading) return <Skeleton className="h-64" />;

  if (entries.length === 0 && lbEntries.length === 0) {
    return (
      <p className="text-sm text-foreground/40 py-8 text-center">
        No ranking data available.
      </p>
    );
  }

  // Use dashboard entries if we have them, otherwise leaderboard
  if (entries.length > 0) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-foreground/50 text-xs uppercase tracking-wider">
              <th className="text-left pb-2 w-12">#</th>
              <th className="text-left pb-2">Lake</th>
              <th className="text-right pb-2">Value</th>
              <th className="text-center pb-2">Health</th>
              <th className="text-left pb-2 pl-4">Custodian</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr
                key={entry.lake_id}
                className="border-t border-white/5 text-foreground/70 hover:bg-white/5 cursor-pointer"
              >
                <td className="py-2 font-mono text-foreground/30">
                  {entry.rank}
                </td>
                <td className="py-2">
                  <Link
                    href={`/lakes/${entry.lake_id}`}
                    className="text-blue-400 hover:underline inline-flex items-center gap-1.5"
                  >
                    {getDisplayName(entry.lake_id, entry.lake_name)}
                    <TierBadge tier={getLakeTier(entry.lake_id)} />
                  </Link>
                </td>
                <td className="text-right py-2 font-mono">
                  {entry.metric_value !== null
                    ? entry.metric_value.toFixed(1)
                    : "--"}
                </td>
                <td className="py-2 text-center">
                  <HealthBadge score={entry.health_score} />
                </td>
                <td className="py-2 pl-4">
                  {entry.custodian ? (
                    <span className="text-xs px-2 py-0.5 bg-white/5 text-foreground/50 rounded-full">
                      {entry.custodian}
                    </span>
                  ) : (
                    <span className="text-xs text-foreground/20">--</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Fallback to leaderboard entries
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-foreground/50 text-xs uppercase tracking-wider">
            <th className="text-left pb-2 w-12">#</th>
            <th className="text-left pb-2">Lake</th>
            <th className="text-right pb-2">Metric</th>
            <th className="text-center pb-2">Health</th>
          </tr>
        </thead>
        <tbody>
          {lbEntries.map((entry) => (
            <tr
              key={entry.lake_id}
              className="border-t border-white/5 text-foreground/70 hover:bg-white/5 cursor-pointer"
            >
              <td className="py-2 font-mono text-foreground/30">
                {entry.rank}
              </td>
              <td className="py-2">
                <Link
                  href={`/lakes/${entry.lake_id}`}
                  className="text-blue-400 hover:underline inline-flex items-center gap-1.5"
                >
                  {getDisplayName(entry.lake_id, entry.lake_name)}
                  <TierBadge tier={getLakeTier(entry.lake_id)} />
                </Link>
              </td>
              <td className="text-right py-2 font-mono">
                {entry.metric_value !== null
                  ? entry.metric_value.toFixed(1)
                  : "--"}
              </td>
              <td className="py-2 text-center">
                <HealthBadge score={entry.health_score} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Movers-based tab (most_improved / most_declined) ── */

function MoversTab({ direction }: { direction: "up" | "down" }) {
  const [year, setYear] = useState(2024);
  const { data, isLoading } = useMovers(year);
  const years = Array.from({ length: 8 }, (_, i) => 2025 - i);

  const entries =
    direction === "up" ? data?.improvers ?? [] : data?.decliners ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-foreground/40">
          Year-over-year change in average water area.
        </p>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {years.map((y) => (
            <option key={y} value={y}>
              {y} vs {y - 1}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : entries.length === 0 ? (
        <p className="text-sm text-foreground/40 py-8 text-center">
          No data for {year}.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-foreground/50 text-xs uppercase tracking-wider">
                <th className="text-left pb-2 w-12">#</th>
                <th className="text-left pb-2">Lake</th>
                <th className="text-right pb-2">Change</th>
                <th className="text-center pb-2">Health</th>
                <th className="text-left pb-2 pl-4">Custodian</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, i) => {
                const changePct =
                  entry.change_pct !== null
                    ? entry.change_pct.toFixed(1)
                    : "--";
                const changeColor =
                  direction === "up" ? "text-green-400" : "text-red-400";
                return (
                  <tr
                    key={entry.lake_id}
                    className="border-t border-white/5 text-foreground/70 hover:bg-white/5 cursor-pointer"
                  >
                    <td className="py-2 font-mono text-foreground/30">
                      {i + 1}
                    </td>
                    <td className="py-2">
                      <Link
                        href={`/lakes/${entry.lake_id}`}
                        className="text-blue-400 hover:underline inline-flex items-center gap-1.5"
                      >
                        {getDisplayName(entry.lake_id, entry.lake_name)}
                        <TierBadge tier={getLakeTier(entry.lake_id)} />
                      </Link>
                    </td>
                    <td className={`text-right py-2 font-mono font-bold ${changeColor}`}>
                      {direction === "up" ? "+" : "-"}
                      {entry.change_pct !== null ? Math.abs(entry.change_pct).toFixed(1) : "--"}%
                    </td>
                    <td className="py-2 text-center">
                      <HealthBadge score={entry.health_score} />
                    </td>
                    <td className="py-2 pl-4">
                      {entry.custodian ? (
                        <span className="text-xs px-2 py-0.5 bg-white/5 text-foreground/50 rounded-full">
                          {entry.custodian}
                        </span>
                      ) : (
                        <span className="text-xs text-foreground/20">--</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ── Main Rankings ─────────────────────────────────────── */

export default function RankingsClient() {
  const [activeTab, setActiveTab] = useState<TabKey>("best");

  return (
    <div className="max-w-5xl mx-auto p-4 md:p-8 space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/"
          className="text-sm text-foreground/50 hover:text-foreground/80 mb-2 inline-block"
        >
          &larr; Back to map
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-white">Rankings</h1>
          <ThemeToggle />
        </div>
        <p className="text-foreground/50 mt-1">
          Lakes ranked by satellite-derived health metrics.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === tab.key
                ? "bg-white/10 text-white"
                : "text-foreground/50 hover:text-foreground/80 hover:bg-white/5"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        {activeTab === "most_improved" && <MoversTab direction="up" />}
        {activeTab === "most_declined" && <MoversTab direction="down" />}
        {(activeTab === "best" ||
          activeTab === "worst" ||
          activeTab === "most_polluted" ||
          activeTab === "cleanest") && (
          <LeaderboardTab category={activeTab} />
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-white/10 pt-4 text-xs text-foreground/30">
        <p>
          All metrics derived from Copernicus Sentinel-2 satellite imagery.
          Rankings update with each satellite pass (~5 days).
        </p>
      </div>
    </div>
  );
}
