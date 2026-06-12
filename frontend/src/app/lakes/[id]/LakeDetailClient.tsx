"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useLakeDetail } from "@/hooks/useLakeDetail";
import { useLakes } from "@/hooks/useLakes";
import { useTimelapse } from "@/hooks/useTimelapse";
import { useTimeseries } from "@/hooks/useTimeseries";
import HealthBadge from "@/components/leaderboard/HealthBadge";
import TierBadge from "@/components/ui/TierBadge";
import TimeseriesChart from "@/components/lake-detail/TimeseriesChart";
import SeasonalInsight from "@/components/lake-detail/SeasonalInsight";
import { LakeDetailExtensions, LakeDataExtensions } from "@/components/extensions";
import MiniMap from "@/components/lake-detail/MiniMap";
import TimelapsePlayer from "@/components/lake-detail/TimelapsePlayer";
import ThenVsNow from "@/components/lake-detail/ThenVsNow";
import DownloadButtons from "@/components/lake-detail/DownloadButtons";
import ShareButton from "@/components/lake-detail/ShareButton";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { getDisplayName, getAltNames, getLakeTier, getLakeZone } from "@/lib/lake-enrichment";
import { formatRelatableArea } from "@/lib/relatable";
import { perimeterMeters, formatWalkLap } from "@/lib/geo";
import type { LakeDetail } from "@/lib/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

type TabKey = "overview" | "timelapse" | "data";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatHectares(m2: number | null): string {
  if (m2 === null) return "--";
  return (m2 / 10000).toFixed(1);
}

function formatPct(pct: number | null): string {
  if (pct === null) return "";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function formatAlgae(fraction: number | null): string {
  if (fraction === null) return "--";
  return `${(fraction * 100).toFixed(1)}%`;
}

function algaeColor(fraction: number | null): string {
  if (fraction === null) return "text-foreground/60";
  const pct = fraction * 100;
  if (pct < 10) return "text-green-400";
  if (pct <= 30) return "text-yellow-400";
  return "text-red-400";
}

function changeColor(pct: number | null): string {
  if (pct === null) return "text-foreground/60";
  return pct >= 0 ? "text-green-400" : "text-red-400";
}

function healthLabel(score: number | null): string {
  if (score === null) return "N/A";
  if (score >= 60) return "Healthy";
  if (score >= 30) return "Struggling";
  return "Distressed";
}

function healthLabelColor(score: number | null): string {
  if (score === null) return "text-foreground/40";
  if (score >= 60) return "text-green-400";
  if (score >= 30) return "text-yellow-400";
  return "text-red-400";
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PercentileBar({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = ((total - value) / total) * 100;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-foreground/50">{label}</span>
        <span className="text-foreground/70">Top {Math.round(pct)}%</span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full">
        <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

interface QuickStatProps {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
}

function QuickStat({ label, value, sub }: QuickStatProps) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-3 flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-foreground/40 font-medium">
        {label}
      </span>
      <span className="text-lg font-bold text-white leading-tight">{value}</span>
      {sub && <span className="text-xs text-foreground/50">{sub}</span>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

interface LakeDetailClientProps {
  lakeId: string;
}

export default function LakeDetailClient({ lakeId }: LakeDetailClientProps) {
  const { data: lake, isLoading, error, refetch } = useLakeDetail(lakeId);
  const { data: allLakesData } = useLakes();
  const { data: timelapse } = useTimelapse(lakeId);
  const { data: rawTimeseries } = useTimeseries(lakeId, "raw");

  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  // ---- Rankings ----
  const rankings = useMemo(() => {
    const allLakes = allLakesData?.lakes;
    if (!allLakes || !lake) return null;

    const ranked = allLakes.filter((l) => l.health_score !== null);
    const healthSorted = [...ranked].sort((a, b) => (b.health_score ?? 0) - (a.health_score ?? 0));
    const healthIdx = healthSorted.findIndex((l) => l.id === lakeId);
    const healthRank = healthIdx >= 0 ? healthIdx + 1 : null;

    const sizeSorted = [...allLakes]
      .filter((l) => l.latest_water_area_m2 !== null)
      .sort((a, b) => (b.latest_water_area_m2 ?? 0) - (a.latest_water_area_m2 ?? 0));
    const sizeIdx = sizeSorted.findIndex((l) => l.id === lakeId);
    const sizeRank = sizeIdx >= 0 ? sizeIdx + 1 : null;
    const totalSized = sizeSorted.length;

    // Algae: sort ascending (cleanest first)
    const algaeSorted = [...allLakes]
      .filter((l) => l.mean_algae_fraction !== null)
      .sort((a, b) => (a.mean_algae_fraction ?? 0) - (b.mean_algae_fraction ?? 0));
    const algaeIdx = algaeSorted.findIndex((l) => l.id === lakeId);
    const algaeRank = algaeIdx >= 0 ? algaeIdx + 1 : null;
    const totalAlgae = algaeSorted.length;

    return {
      healthRank,
      totalRanked: ranked.length,
      sizeRank,
      totalSized,
      algaeRank,
      totalAlgae,
    };
  }, [allLakesData, lake, lakeId]);

  // ---- First observation year ----
  const firstObsYear = useMemo(() => {
    if (!rawTimeseries?.observations?.length) return null;
    const first = rawTimeseries.observations[0];
    return new Date(first.date).getFullYear();
  }, [rawTimeseries]);

  // ---- Absolute 5yr water-area change (m²) ----
  // Prefer the real timeseries delta; fall back to an exact algebraic delta
  // derived from the reported 5yr percentage when the timeseries is sparse.
  const areaDelta5yrM2 = useMemo<number | null>(() => {
    const obs = rawTimeseries?.observations?.filter((o) => o.water_area_m2 !== null) ?? [];
    if (obs.length >= 2) {
      const latest = obs[obs.length - 1];
      const latestArea = latest.water_area_m2!;
      const targetMs = new Date(latest.date).getTime() - 5 * 365.25 * 24 * 3600 * 1000;
      let closest = obs[0];
      let bestDiff = Infinity;
      for (const o of obs) {
        const diff = Math.abs(new Date(o.date).getTime() - targetMs);
        if (diff < bestDiff) {
          bestDiff = diff;
          closest = o;
        }
      }
      return latestArea - closest.water_area_m2!;
    }
    // Fallback: latest * (pct/100) / (1 + pct/100)
    if (lake?.latest_water_area_m2 != null && lake?.area_change_5yr_pct != null) {
      const pct = lake.area_change_5yr_pct / 100;
      const denom = 1 + pct;
      if (denom !== 0) return (lake.latest_water_area_m2 * pct) / denom;
    }
    return null;
  }, [rawTimeseries, lake]);

  // ---- Shoreline perimeter + walking lap ----
  const walkLap = useMemo<string | null>(() => {
    if (!lake?.boundary_geojson) return null;
    return formatWalkLap(perimeterMeters(lake.boundary_geojson));
  }, [lake]);

  const relatableArea = useMemo<string | null>(() => {
    if (areaDelta5yrM2 == null || !Number.isFinite(areaDelta5yrM2) || areaDelta5yrM2 === 0) return null;
    return formatRelatableArea(areaDelta5yrM2);
  }, [areaDelta5yrM2]);

  // ---- Loading / Error states ----
  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-6">
        <div className="h-8 w-48 bg-white/5 rounded animate-pulse" />
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-white/5 border border-white/10 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-[400px] bg-white/5 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (error || !lake) {
    return (
      <div className="max-w-6xl mx-auto p-4 md:p-8 flex flex-col items-center gap-4">
        <p className="text-lg text-red-400">
          {error instanceof Error ? error.message : "Something went wrong loading this lake."}
        </p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-sm"
        >
          Try again
        </button>
        <Link href="/" className="text-sm text-foreground/50 hover:text-foreground/80">
          Back to map
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-5">
      {/* ================================================================ */}
      {/* HEADER */}
      {/* ================================================================ */}
      <div>
        <Link href="/" className="text-sm text-foreground/50 hover:text-foreground/80 mb-2 inline-block">
          &larr; Back to map
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-white">
            {getDisplayName(lake.id, lake.name)}
            {lake.ward && (
              <span className="text-lg font-normal text-foreground/50 ml-2">({lake.ward})</span>
            )}
          </h1>
          <ThemeToggle />
        </div>
        {/* Also known as */}
        {(() => {
          const altNames = getAltNames(lake.id);
          return altNames.length > 0 ? (
            <p className="text-sm italic text-foreground/40 mt-1">
              Also known as: {altNames.join(", ")}
            </p>
          ) : null;
        })()}
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <TierBadge tier={getLakeTier(lake.id)} />
          {(() => {
            const zone = getLakeZone(lake.id);
            return zone ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-500/15 text-purple-300 border border-purple-500/20">
                {zone}
              </span>
            ) : null;
          })()}
          {lake.custodian && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/15 text-blue-300 border border-blue-500/20">
              {lake.custodian}
            </span>
          )}
          {lake.health_score !== null && <HealthBadge score={lake.health_score} />}
          {lake.name_kannada && (
            <span className="text-xs text-foreground/40">{lake.name_kannada}</span>
          )}
        </div>
      </div>

      {/* ================================================================ */}
      {/* QUICK STATS ROW */}
      {/* ================================================================ */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <QuickStat
          label="Rank"
          value={
            rankings?.healthRank
              ? `#${rankings.healthRank}`
              : "--"
          }
          sub={
            rankings?.totalRanked
              ? `of ${rankings.totalRanked} lakes`
              : null
          }
        />
        <QuickStat
          label="Health"
          value={
            <span className="flex items-center gap-2">
              {lake.health_score !== null ? Math.round(lake.health_score) : "--"}
              <span className={`text-sm font-medium ${healthLabelColor(lake.health_score)}`}>
                {healthLabel(lake.health_score)}
              </span>
            </span>
          }
        />
        <QuickStat
          label="Surface Area"
          value={
            <span>
              {formatHectares(lake.latest_water_area_m2)}{" "}
              <span className="text-sm font-normal text-foreground/50">ha</span>
            </span>
          }
          sub={
            (lake.area_change_5yr_pct !== null || relatableArea) ? (
              <span className="flex flex-col gap-0.5">
                {lake.area_change_5yr_pct !== null && (
                  <span className={changeColor(lake.area_change_5yr_pct)}>
                    {formatPct(lake.area_change_5yr_pct)} over 5yr
                  </span>
                )}
                {relatableArea && (
                  <span className="text-foreground/50">
                    {relatableArea} {(areaDelta5yrM2 ?? 0) >= 0 ? "gained" : "lost"}
                  </span>
                )}
              </span>
            ) : null
          }
        />
        <QuickStat
          label="Algae"
          value={
            <span className={algaeColor(lake.mean_algae_fraction)}>
              {formatAlgae(lake.mean_algae_fraction)}
            </span>
          }
          sub={
            lake.peak_algae_month !== null
              ? `Peaks in ${MONTH_NAMES[lake.peak_algae_month - 1]}`
              : null
          }
        />
        {walkLap && (
          <QuickStat
            label="One lap around"
            value={<span className="text-base">{walkLap}</span>}
            sub="Shoreline perimeter, satellite-derived"
          />
        )}
      </div>

      {/* ================================================================ */}
      {/* TABS */}
      {/* ================================================================ */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-0.5 w-fit">
        {(["overview", "timelapse", "data"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors capitalize ${
              activeTab === tab
                ? "bg-white/15 text-white font-medium"
                : "text-foreground/50 hover:text-foreground/80"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* ================================================================ */}
      {/* OVERVIEW TAB (summary + charts) */}
      {/* ================================================================ */}
      {activeTab === "overview" && (
        <div className="space-y-5">
          {/* Overview: 2-column */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left: MiniMap */}
            <MiniMap
              boundaryGeojson={lake.boundary_geojson}
              center={[lake.longitude, lake.latitude]}
            />

            {/* Right: Key facts */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-semibold text-foreground/40 uppercase tracking-wider">
                Key Facts
              </h3>
              <div className="space-y-2 text-sm">
                {lake.boundary_area_m2 && lake.boundary_area_m2 > 0 && (
                  <FactRow
                    label="BOUNDARY AREA"
                    value={`${(lake.boundary_area_m2 / 10000).toFixed(1)} ha (${Math.round(lake.boundary_area_m2).toLocaleString()} m²)`}
                  />
                )}
                {lake.latest_water_area_m2 !== null && (
                  <FactRow
                    label="WATER SURFACE"
                    value={`${formatHectares(lake.latest_water_area_m2)} ha (${Math.round(lake.latest_water_area_m2).toLocaleString()} m²)`}
                  />
                )}
                {lake.water_coverage_pct !== null && (
                  <div>
                    <FactRow
                      label="WATER COVERAGE"
                      value={`${lake.water_coverage_pct.toFixed(0)}% of boundary is water`}
                    />
                    <div className="mt-1 h-2 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          lake.water_coverage_pct >= 70
                            ? "bg-blue-500"
                            : lake.water_coverage_pct >= 40
                              ? "bg-yellow-500"
                              : "bg-red-500"
                        }`}
                        style={{ width: `${Math.min(lake.water_coverage_pct, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
                {lake.custodian && (
                  <FactRow label="MANAGING AGENCY" value={lake.custodian} />
                )}
                {lake.peak_algae_month !== null && (
                  <FactRow
                    label="PEAK ALGAE MONTH"
                    value={MONTH_NAMES[lake.peak_algae_month - 1]}
                  />
                )}
                {lake.seasonal_amplitude !== null && lake.latest_water_area_m2 !== null && lake.latest_water_area_m2 > 0 && (
                  <FactRow
                    label="SEASONAL SWING"
                    value={`${Math.round((lake.seasonal_amplitude / lake.latest_water_area_m2) * 100)}%`}
                  />
                )}
                <FactRow
                  label="DATA COVERAGE"
                  value={`${lake.observation_count.toLocaleString()} observations${firstObsYear ? ` since ${firstObsYear}` : ""}`}
                />
              </div>
            </div>
          </div>

          {/* Comparative metrics */}
          {rankings && (
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-semibold text-foreground/40 uppercase tracking-wider">
                Comparative Metrics
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {rankings.healthRank !== null && (
                  <PercentileBar
                    label="Healthier than X% of tracked lakes"
                    value={rankings.healthRank}
                    total={rankings.totalRanked}
                  />
                )}
                {rankings.algaeRank !== null && (
                  <PercentileBar
                    label="Less algae than X% of tracked lakes"
                    value={rankings.algaeRank}
                    total={rankings.totalAlgae}
                  />
                )}
                {rankings.sizeRank !== null && (
                  <PercentileBar
                    label="Larger than X% of tracked lakes"
                    value={rankings.sizeRank}
                    total={rankings.totalSized}
                  />
                )}
              </div>
            </div>
          )}

          {/* Charts section */}
          <TimeseriesChart lakeId={lakeId} />
          <SeasonalInsight lake={lake} />
          {/* City-specific extension slot (no-op in the public build). */}
          <LakeDetailExtensions lakeId={lakeId} />

        </div>
      )}

      {/* ================================================================ */}
      {/* DATA TAB */}
      {/* ================================================================ */}
      {activeTab === "data" && (
        <div className="space-y-5">
          {/* Satellite observations table */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h3 className="text-xs font-semibold text-foreground/40 uppercase tracking-wider mb-3">
              Satellite Observations ({rawTimeseries?.count ?? 0})
            </h3>
            {rawTimeseries && rawTimeseries.observations.length > 0 ? (
              <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-gray-900">
                    <tr className="text-foreground/40 border-b border-white/10">
                      <th className="text-left py-1.5 pr-3 font-medium">Date</th>
                      <th className="text-right py-1.5 px-2 font-medium">Water Area (ha)</th>
                      <th className="text-right py-1.5 px-2 font-medium">NDWI</th>
                      <th className="text-right py-1.5 px-2 font-medium">Algae %</th>
                      <th className="text-right py-1.5 px-2 font-medium">Cloud %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rawTimeseries.observations.slice().reverse().map((obs) => (
                      <tr key={obs.date} className="border-b border-white/5 text-foreground/70">
                        <td className="py-1 pr-3">{obs.date}</td>
                        <td className="text-right py-1 px-2">
                          {obs.water_area_m2 !== null ? (obs.water_area_m2 / 10000).toFixed(2) : "--"}
                        </td>
                        <td className="text-right py-1 px-2">
                          {obs.mean_ndwi !== null ? obs.mean_ndwi.toFixed(3) : "--"}
                        </td>
                        <td className="text-right py-1 px-2">
                          {obs.algae_fraction !== null ? (obs.algae_fraction * 100).toFixed(1) : "--"}
                        </td>
                        <td className="text-right py-1 px-2">
                          {obs.cloud_pct !== null ? obs.cloud_pct.toFixed(1) : "--"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-foreground/40">No satellite observations available.</p>
            )}
          </div>

          {/* City-specific data-tab extension slot (no-op in the public build). */}
          <LakeDataExtensions lakeId={lakeId} />

          {/* Data provenance */}
          <div className="border-t border-white/10 pt-4 text-xs text-foreground/30 space-y-1">
            <p>
              <strong>Satellite data:</strong> Copernicus Sentinel-2 L2A via Google Earth Engine. 10m resolution, ~5-day revisit.
            </p>
            <p>
              <strong>Lake boundary:</strong> CSEI-ATREE, Centre for Social and Environmental Innovation. CC BY-SA 4.0.
            </p>
            <p>
              <strong>Ground truth:</strong> EMPRI field survey (2018) + KSPCB lab measurements (2019-2025).
            </p>
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* TIMELAPSE TAB */}
      {/* ================================================================ */}
      {activeTab === "timelapse" && (
        <div className="space-y-5">
          <ThenVsNow lakeId={lakeId} />
          <TimelapsePlayer lakeId={lakeId} />
          <div className="flex flex-wrap items-center gap-3">
            <DownloadButtons assets={timelapse?.assets ?? []} />
            <ShareButton lakeName={lake.name} />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline sub-components
// ---------------------------------------------------------------------------

function FactRow({
  label,
  value,
  sub,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-foreground/30 font-medium">
        {label}
      </span>
      <span className="text-foreground/80">{value}</span>
      {sub && <span className="text-xs text-foreground/40">{sub}</span>}
    </div>
  );
}

