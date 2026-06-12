"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLakeStatsTable } from "@/hooks/useInsights";
import HealthBadge from "@/components/leaderboard/HealthBadge";
import TierBadge from "@/components/ui/TierBadge";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { getDisplayName, matchesSearch, getLakeTier, getLakeZone, getAllZones } from "@/lib/lake-enrichment";
import type { LakeStatsRow } from "@/lib/types";

type SortColumn =
  | "lake_name"
  | "health_score"
  | "latest_water_area_m2"
  | "area_change_1yr_pct"
  | "area_change_5yr_pct"
  | "mean_algae_fraction"
  | "observation_count";

type SortDir = "asc" | "desc";
type HealthFilter = "all" | "healthy" | "struggling" | "distressed";

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`bg-white/5 rounded-xl animate-pulse ${className}`} />;
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-foreground/20 ml-1">&#8597;</span>;
  return (
    <span className="text-white ml-1">
      {dir === "asc" ? "\u2191" : "\u2193"}
    </span>
  );
}

function getHealthStatus(score: number | null): HealthFilter {
  if (score === null) return "all";
  if (score >= 60) return "healthy";
  if (score >= 30) return "struggling";
  return "distressed";
}

function sortRows(
  rows: LakeStatsRow[],
  col: SortColumn,
  dir: SortDir
): LakeStatsRow[] {
  return [...rows].sort((a, b) => {
    const aVal = a[col];
    const bVal = b[col];

    // Nulls always go to bottom
    if (aVal === null && bVal === null) return 0;
    if (aVal === null) return 1;
    if (bVal === null) return -1;

    if (typeof aVal === "string" && typeof bVal === "string") {
      return dir === "asc"
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    const numA = Number(aVal);
    const numB = Number(bVal);
    return dir === "asc" ? numA - numB : numB - numA;
  });
}

export default function LakesClient() {
  const { data, isLoading } = useLakeStatsTable();
  const router = useRouter();

  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<SortColumn>("health_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [healthFilter, setHealthFilter] = useState<HealthFilter>("all");
  const [zoneFilter, setZoneFilter] = useState<string>("all");
  const [tierFilter, setTierFilter] = useState<string>("all");

  const handleSort = (col: SortColumn) => {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
  };

  const filteredRows = useMemo(() => {
    if (!data) return [];
    let rows = data.stats;

    // Text search (enriched — searches display name + alt names)
    if (search.trim()) {
      rows = rows.filter((r) => matchesSearch(r.lake_id, r.lake_name, search));
    }

    // Health filter
    if (healthFilter !== "all") {
      rows = rows.filter((r) => getHealthStatus(r.health_score) === healthFilter);
    }

    // Zone filter
    if (zoneFilter !== "all") {
      rows = rows.filter((r) => getLakeZone(r.lake_id) === zoneFilter);
    }

    // Tier filter
    if (tierFilter !== "all") {
      rows = rows.filter((r) => getLakeTier(r.lake_id) === Number(tierFilter));
    }

    // Sort
    return sortRows(rows, sortCol, sortDir);
  }, [data, search, healthFilter, zoneFilter, tierFilter, sortCol, sortDir]);

  const columns: { key: SortColumn; label: string; align: string }[] = [
    { key: "lake_name", label: "Name", align: "text-left" },
    { key: "health_score", label: "Health", align: "text-right" },
    { key: "latest_water_area_m2", label: "Area (ha)", align: "text-right" },
    { key: "area_change_1yr_pct", label: "1yr", align: "text-right" },
    { key: "area_change_5yr_pct", label: "5yr", align: "text-right" },
    { key: "mean_algae_fraction", label: "Algae", align: "text-right" },
    { key: "observation_count", label: "Obs", align: "text-right" },
  ];

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/"
          className="text-sm text-foreground/50 hover:text-foreground/80 mb-2 inline-block"
        >
          &larr; Back to map
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-white">All Lakes</h1>
          <ThemeToggle />
        </div>
        <p className="text-foreground/50 mt-1">
          {data ? `${data.count} lakes tracked` : "Loading..."} with satellite-derived metrics.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search lakes (any name)..."
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 outline-none focus:border-white/20 w-64"
        />
        <select
          value={healthFilter}
          onChange={(e) => setHealthFilter(e.target.value as HealthFilter)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All health</option>
          <option value="healthy">Healthy (60+)</option>
          <option value="struggling">Struggling (30-60)</option>
          <option value="distressed">Distressed (&lt;30)</option>
        </select>
        <select
          value={zoneFilter}
          onChange={(e) => setZoneFilter(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All zones</option>
          {getAllZones().map((z) => (
            <option key={z} value={z}>{z}</option>
          ))}
        </select>
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All tiers</option>
          <option value="1">Tier 1</option>
          <option value="2">Tier 2</option>
          <option value="3">Tier 3</option>
        </select>
        <span className="text-xs text-foreground/30 ml-auto">
          {filteredRows.length} lakes shown
        </span>
      </div>

      {/* Table */}
      {isLoading ? (
        <Skeleton className="h-96" />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-white/5">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`${col.align} p-3 text-foreground/50 text-xs uppercase tracking-wider cursor-pointer hover:text-foreground/80 select-none whitespace-nowrap`}
                  >
                    {col.label}
                    <SortIcon active={sortCol === col.key} dir={sortDir} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="text-center py-12 text-foreground/40"
                  >
                    No lakes match your filters.
                  </td>
                </tr>
              ) : (
                filteredRows.map((lake) => (
                  <tr
                    key={lake.lake_id}
                    onClick={() => router.push(`/lakes/${lake.lake_id}`)}
                    className="border-t border-white/5 text-foreground/70 hover:bg-white/5 cursor-pointer transition-colors"
                  >
                    <td className="p-3 font-medium text-white whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5">
                        {getDisplayName(lake.lake_id, lake.lake_name)}
                        <TierBadge tier={getLakeTier(lake.lake_id)} />
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <HealthBadge score={lake.health_score} />
                    </td>
                    <td className="p-3 text-right font-mono">
                      {lake.latest_water_area_m2 !== null
                        ? (lake.latest_water_area_m2 / 10000).toFixed(1)
                        : "--"}
                    </td>
                    <td className="p-3 text-right font-mono">
                      {lake.area_change_1yr_pct !== null ? (
                        <span
                          className={
                            lake.area_change_1yr_pct >= 0
                              ? "text-green-400"
                              : "text-red-400"
                          }
                        >
                          {lake.area_change_1yr_pct >= 0 ? "+" : ""}
                          {lake.area_change_1yr_pct.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-foreground/30">--</span>
                      )}
                    </td>
                    <td className="p-3 text-right font-mono">
                      {lake.area_change_5yr_pct !== null ? (
                        <span
                          className={
                            lake.area_change_5yr_pct >= 0
                              ? "text-green-400"
                              : "text-red-400"
                          }
                        >
                          {lake.area_change_5yr_pct >= 0 ? "+" : ""}
                          {lake.area_change_5yr_pct.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-foreground/30">--</span>
                      )}
                    </td>
                    <td className="p-3 text-right font-mono">
                      {lake.mean_algae_fraction !== null
                        ? (lake.mean_algae_fraction * 100).toFixed(1) + "%"
                        : "--"}
                    </td>
                    <td className="p-3 text-right font-mono">
                      {lake.observation_count}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer */}
      <p className="text-xs text-foreground/30">
        Lab data available on individual lake pages.
      </p>
    </div>
  );
}
