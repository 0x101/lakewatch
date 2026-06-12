"use client";

import { useState } from "react";
import Link from "next/link";
import {
  useRawObservations,
  useLakeStatsTable,
  useCrossReference,
  useOutliers,
  useCustodianStats,
  useMovers,
} from "@/hooks/useInsights";
import type { MoverEntry } from "@/lib/types";
import { useLakes } from "@/hooks/useLakes";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

type Tab = "overview" | "observations" | "stats" | "outliers" | "crossref" | "movers";

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active
          ? "bg-white/10 text-white"
          : "text-foreground/50 hover:text-foreground/80 hover:bg-white/5"
      }`}
    >
      {children}
    </button>
  );
}

function OverviewPanel() {
  const { data: statsData } = useLakeStatsTable();
  const { data: lakesData } = useLakes();
  const { data: custodianData } = useCustodianStats();

  if (!statsData || !lakesData) {
    return <div className="h-64 bg-white/5 rounded-xl animate-pulse" />;
  }

  const stats = statsData.stats;
  const totalObs = stats.reduce((sum, s) => sum + s.observation_count, 0);
  const avgHealth =
    stats.filter((s) => s.health_score !== null).reduce((sum, s) => sum + (s.health_score ?? 0), 0) /
    stats.filter((s) => s.health_score !== null).length;
  const shrinkingCount = stats.filter(
    (s) => s.area_change_5yr_pct !== null && s.area_change_5yr_pct < -10
  ).length;
  const healthyCount = stats.filter(
    (s) => s.health_score !== null && s.health_score >= 60
  ).length;
  const distressedCount = stats.filter(
    (s) => s.health_score !== null && s.health_score < 30
  ).length;
  const highAlgaeCount = stats.filter(
    (s) => s.mean_algae_fraction !== null && s.mean_algae_fraction > 0.15
  ).length;

  // Monsoon analysis: peak algae month distribution
  const peakMonths: Record<number, number> = {};
  stats.forEach((s) => {
    if (s.peak_algae_month !== null) {
      peakMonths[s.peak_algae_month] = (peakMonths[s.peak_algae_month] ?? 0) + 1;
    }
  });
  const monthNames = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];

  return (
    <div className="space-y-6">
      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          {
            label: "Lakes Tracked",
            value: stats.length.toString(),
            sub: `${totalObs.toLocaleString()} satellite observations`,
          },
          {
            label: "Average Health",
            value: avgHealth.toFixed(0) + "/100",
            sub: `${healthyCount} healthy, ${distressedCount} distressed`,
            color: avgHealth >= 60 ? "text-green-400" : avgHealth >= 30 ? "text-yellow-400" : "text-red-400",
          },
          {
            label: "Shrinking Lakes",
            value: shrinkingCount.toString(),
            sub: "Lost >10% area in 5 years",
            color: "text-red-400",
          },
          {
            label: "High Algae",
            value: highAlgaeCount.toString(),
            sub: "Mean algae >15% of water surface",
            color: "text-orange-400",
          },
        ].map((m) => (
          <div
            key={m.label}
            className="bg-white/5 border border-white/10 rounded-xl p-4"
          >
            <p className="text-xs text-foreground/40 uppercase tracking-wider">
              {m.label}
            </p>
            <p className={`text-2xl font-bold mt-1 ${m.color ?? "text-white"}`}>
              {m.value}
            </p>
            <p className="text-xs text-foreground/40 mt-1">{m.sub}</p>
          </div>
        ))}
      </div>

      {/* Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Health distribution */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-foreground/60 uppercase tracking-wider mb-3">
            Health Distribution
          </h3>
          <div className="space-y-2">
            {[
              { label: "Healthy (60-100)", count: healthyCount, color: "bg-green-500", total: stats.length },
              { label: "Struggling (30-60)", count: stats.filter(s => s.health_score !== null && s.health_score >= 30 && s.health_score < 60).length, color: "bg-yellow-500", total: stats.length },
              { label: "Distressed (0-30)", count: distressedCount, color: "bg-red-500", total: stats.length },
            ].map((b) => (
              <div key={b.label} className="flex items-center gap-3">
                <div className="w-24 text-xs text-foreground/50">{b.label}</div>
                <div className="flex-1 h-4 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${b.color} rounded-full transition-all`}
                    style={{ width: `${(b.count / b.total) * 100}%` }}
                  />
                </div>
                <div className="w-8 text-right text-xs font-mono text-foreground/50">
                  {b.count}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Peak algae season */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-foreground/60 uppercase tracking-wider mb-3">
            When Algae Peaks
          </h3>
          <p className="text-xs text-foreground/40 mb-3">
            Distribution of peak algae months across all tracked lakes.
          </p>
          <div className="flex items-end gap-1" style={{ height: 96 }}>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
              const count = peakMonths[month] ?? 0;
              const maxCount = Math.max(...Object.values(peakMonths), 1);
              const pct = count / maxCount;
              const barH = Math.max(pct * 72, count > 0 ? 4 : 0);
              return (
                <div
                  key={month}
                  className="flex-1 flex flex-col items-center justify-end"
                  style={{ height: 96 }}
                >
                  {count > 0 && (
                    <span className="text-[9px] text-foreground/50 mb-0.5">{count}</span>
                  )}
                  <div
                    className="w-full bg-green-500/50 rounded-t"
                    style={{ height: barH }}
                    title={`${monthNames[month]}: ${count} lakes`}
                  />
                  <span className="text-[10px] text-foreground/30 mt-1">
                    {monthNames[month]}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* By Managing Agency */}
      {custodianData && custodianData.entries.length > 0 && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-foreground/60 uppercase tracking-wider mb-3">
            By Managing Agency
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-foreground/50 text-xs uppercase tracking-wider">
                  <th className="text-left pb-2">Agency</th>
                  <th className="text-right pb-2">Lakes</th>
                  <th className="text-right pb-2 hidden sm:table-cell">Avg Health</th>
                  <th className="text-left pb-2 pl-4 w-32 hidden sm:table-cell"></th>
                  <th className="text-right pb-2">Distressed</th>
                  <th className="text-right pb-2">Healthy</th>
                </tr>
              </thead>
              <tbody>
                {custodianData.entries.map((entry) => {
                  const healthPct = entry.avg_health ?? 0;
                  const barColor =
                    healthPct >= 60
                      ? "bg-green-500"
                      : healthPct >= 30
                        ? "bg-yellow-500"
                        : "bg-red-500";
                  return (
                    <tr
                      key={entry.custodian}
                      className="border-t border-white/5 text-foreground/70"
                    >
                      <td className="py-2 font-medium text-white">
                        {entry.custodian}
                      </td>
                      <td className="text-right py-2 font-mono">
                        {entry.lake_count}
                      </td>
                      <td className="text-right py-2 font-mono hidden sm:table-cell">
                        <span className={healthPct >= 60 ? "text-green-400" : healthPct >= 30 ? "text-yellow-400" : "text-red-400"}>
                          {entry.avg_health !== null ? entry.avg_health.toFixed(0) : "--"}
                        </span>
                      </td>
                      <td className="py-2 pl-4 hidden sm:table-cell">
                        <div className="h-2 bg-white/5 rounded-full overflow-hidden w-full">
                          <div
                            className={`h-full ${barColor} rounded-full transition-all`}
                            style={{ width: `${healthPct}%` }}
                          />
                        </div>
                      </td>
                      <td className="text-right py-2 font-mono">
                        {entry.distressed_count > 0 ? (
                          <span className="text-red-400">{entry.distressed_count}</span>
                        ) : (
                          <span className="text-foreground/30">0</span>
                        )}
                      </td>
                      <td className="text-right py-2 font-mono">
                        {entry.healthy_count > 0 ? (
                          <span className="text-green-400">{entry.healthy_count}</span>
                        ) : (
                          <span className="text-foreground/30">0</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Key findings */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-foreground/60 uppercase tracking-wider mb-3">
          Key Findings
        </h3>
        <ul className="space-y-2 text-sm text-foreground/70 list-disc list-inside">
          <li>
            <strong className="text-white">Bellandur and Varthur</strong> are
            connected via rajakaluve. Both score below 25/100. Overflow from
            Bellandur feeds directly into Varthur.
          </li>
          <li>
            <strong className="text-white">Actively managed lakes score higher.</strong>{" "}
            Lakes with dedicated custodians (Sankey, Lalbagh, Ulsoor) consistently
            score 65+ on the health index.
          </li>
          <li>
            <strong className="text-white">Algae peaks lag behind monsoon.</strong>{" "}
            Water area peaks Oct-Feb (post-monsoon fill), but algae peaks Aug-Sep
            when nutrient-rich runoff enters the lake.
          </li>
          <li>
            <strong className="text-white">Lake size does not correlate with health.</strong>{" "}
            Some of the largest lakes are the most distressed. Smaller lakes with
            active management outperform on every metric.
          </li>
        </ul>
      </div>
    </div>
  );
}

function ObservationsTable() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useRawObservations(page, 50);

  if (isLoading) {
    return <div className="h-96 bg-white/5 rounded-xl animate-pulse" />;
  }

  if (!data) return null;

  const totalPages = Math.ceil(data.total / data.page_size);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-foreground/50">
          {data.total.toLocaleString()} observations across all lakes
        </p>
        <p className="text-xs text-foreground/30">
          Source: Sentinel-2 via Google Earth Engine
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-white/5 text-foreground/50 text-xs uppercase tracking-wider">
              <th className="text-left p-3">Lake</th>
              <th className="text-left p-3">Date</th>
              <th className="text-right p-3">Water Area (m²)</th>
              <th className="text-right p-3">NDWI</th>
              <th className="text-right p-3">Algae %</th>
              <th className="text-right p-3">Cloud %</th>
            </tr>
          </thead>
          <tbody>
            {data.observations.map((obs, i) => (
              <tr
                key={`${obs.lake_id}-${obs.observation_date}-${i}`}
                className="border-t border-white/5 text-foreground/70 hover:bg-white/5"
              >
                <td className="p-3">
                  <Link
                    href={`/lakes/${obs.lake_id}`}
                    className="text-blue-400 hover:underline"
                  >
                    {obs.lake_name}
                  </Link>
                </td>
                <td className="p-3">{obs.observation_date}</td>
                <td className="text-right p-3 font-mono">
                  {obs.water_area_m2 !== null
                    ? obs.water_area_m2.toLocaleString(undefined, {
                        maximumFractionDigits: 0,
                      })
                    : "—"}
                </td>
                <td className="text-right p-3 font-mono">
                  {obs.mean_ndwi?.toFixed(3) ?? "—"}
                </td>
                <td className="text-right p-3 font-mono">
                  {obs.algae_fraction !== null
                    ? (obs.algae_fraction * 100).toFixed(1) + "%"
                    : "—"}
                </td>
                <td className="text-right p-3 font-mono">
                  {obs.cloud_pct !== null
                    ? (obs.cloud_pct * 100).toFixed(1) + "%"
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-3">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="px-3 py-1 text-sm bg-white/5 hover:bg-white/10 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Previous
        </button>
        <span className="text-sm text-foreground/50">
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
          className="px-3 py-1 text-sm bg-white/5 hover:bg-white/10 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function StatsTable() {
  const { data, isLoading } = useLakeStatsTable();

  if (isLoading) {
    return <div className="h-96 bg-white/5 rounded-xl animate-pulse" />;
  }

  if (!data) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-foreground/50">
          {data.count} lakes with computed metrics
        </p>
        <p className="text-xs text-foreground/30">
          Derived from satellite observations
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-white/5 text-foreground/50 text-xs uppercase tracking-wider">
              <th className="text-left p-3">Lake</th>
              <th className="text-right p-3">Health</th>
              <th className="text-right p-3">Water Area</th>
              <th className="text-right p-3">1yr Change</th>
              <th className="text-right p-3">5yr Change</th>
              <th className="text-right p-3">Algae (avg)</th>
              <th className="text-right p-3">Obs</th>
              <th className="text-left p-3">Latest</th>
            </tr>
          </thead>
          <tbody>
            {data.stats.map((s) => (
              <tr
                key={s.lake_id}
                className="border-t border-white/5 text-foreground/70 hover:bg-white/5"
              >
                <td className="p-3">
                  <Link
                    href={`/lakes/${s.lake_id}`}
                    className="text-blue-400 hover:underline"
                  >
                    {s.lake_name}
                  </Link>
                </td>
                <td className="text-right p-3">
                  <span
                    className={`font-bold ${
                      (s.health_score ?? 0) >= 60
                        ? "text-green-400"
                        : (s.health_score ?? 0) >= 30
                          ? "text-yellow-400"
                          : "text-red-400"
                    }`}
                  >
                    {s.health_score?.toFixed(0) ?? "—"}
                  </span>
                </td>
                <td className="text-right p-3 font-mono">
                  {s.latest_water_area_m2 !== null
                    ? (s.latest_water_area_m2 / 10000).toFixed(1) + " ha"
                    : "—"}
                </td>
                <td className="text-right p-3 font-mono">
                  {s.area_change_1yr_pct !== null ? (
                    <span
                      className={
                        s.area_change_1yr_pct >= 0
                          ? "text-green-400"
                          : "text-red-400"
                      }
                    >
                      {s.area_change_1yr_pct >= 0 ? "+" : ""}
                      {s.area_change_1yr_pct.toFixed(1)}%
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="text-right p-3 font-mono">
                  {s.area_change_5yr_pct !== null ? (
                    <span
                      className={
                        s.area_change_5yr_pct >= 0
                          ? "text-green-400"
                          : "text-red-400"
                      }
                    >
                      {s.area_change_5yr_pct >= 0 ? "+" : ""}
                      {s.area_change_5yr_pct.toFixed(1)}%
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="text-right p-3 font-mono">
                  {s.mean_algae_fraction !== null
                    ? (s.mean_algae_fraction * 100).toFixed(1) + "%"
                    : "—"}
                </td>
                <td className="text-right p-3">{s.observation_count}</td>
                <td className="p-3 text-xs text-foreground/40">
                  {s.latest_observation_date ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OutliersTable() {
  const { data, isLoading } = useOutliers();

  if (isLoading) {
    return <div className="h-96 bg-white/5 rounded-xl animate-pulse" />;
  }

  if (!data || data.count === 0) {
    return (
      <p className="text-foreground/50 text-sm">
        No outliers detected in the current dataset.
      </p>
    );
  }

  const typeIcons: Record<string, string> = {
    zero_area: "0",
    algae_spike: "!",
    area_spike: "^",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-foreground/50">
          {data.count} observations flagged as unusual
        </p>
        <p className="text-xs text-foreground/30">
          Flagged for review, not necessarily erroneous
        </p>
      </div>

      <div className="space-y-3">
        {data.outliers.map((o, i) => (
          <div
            key={`${o.lake_id}-${o.observation_date}-${i}`}
            className="bg-white/5 border border-white/10 rounded-xl p-4"
          >
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-400 font-bold text-sm">
                {typeIcons[o.outlier_type] ?? "?"}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Link
                    href={`/lakes/${o.lake_id}`}
                    className="text-sm font-medium text-blue-400 hover:underline"
                  >
                    {o.lake_name}
                  </Link>
                  <span className="text-xs text-foreground/40">
                    {o.observation_date}
                  </span>
                  <span className="text-xs px-2 py-0.5 bg-yellow-500/10 text-yellow-400 rounded">
                    {o.outlier_type.replace("_", " ")}
                  </span>
                </div>
                <p className="text-xs text-foreground/60">{o.explanation}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AgreementBadge({ agreement }: { agreement: string | null }) {
  if (!agreement) return <span className="text-foreground/30">--</span>;

  const styles: Record<string, string> = {
    consistent: "bg-green-500/20 text-green-400",
    contradictory: "bg-red-500/20 text-red-400",
    partial: "bg-yellow-500/20 text-yellow-400",
  };

  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[agreement] ?? "bg-white/10 text-foreground/50"}`}
    >
      {agreement}
    </span>
  );
}

function CrossReferencePanel() {
  // Extension-backed: cross-reference is a Bangalore city extension sourced via
  // api-ext. Renders empty when no city extensions are present (public build).
  const { data: lakesData } = useLakes();
  const [selectedLake, setSelectedLake] = useState("");
  const { data, isLoading } = useCrossReference(selectedLake);

  const lakes = lakesData?.lakes ?? [];

  return (
    <div className="space-y-4">
      {/* Explainer */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-foreground/60 uppercase tracking-wider mb-2">
          Satellite vs. Lab Data
        </h3>
        <p className="text-sm text-foreground/50">
          Satellite observations (algae fraction from NDVI) compared against KSPCB
          lab measurements (BOD, COD, dissolved oxygen). Agreement means both sources
          point the same direction. Disagreement may indicate timing gaps or cloud
          interference. Select a lake to compare.
        </p>
      </div>

      {/* Lake selector */}
      <div className="flex items-center gap-3">
        <label
          htmlFor="crossref-lake"
          className="text-sm text-foreground/60 whitespace-nowrap"
        >
          Pick a lake:
        </label>
        <select
          id="crossref-lake"
          value={selectedLake}
          onChange={(e) => setSelectedLake(e.target.value)}
          className="flex-1 max-w-xs bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">Select a lake...</option>
          {lakes.map((lake) => (
            <option key={lake.id} value={lake.id}>
              {lake.name}
            </option>
          ))}
        </select>
      </div>

      {/* Results */}
      {!selectedLake && (
        <p className="text-sm text-foreground/40 italic">
          Select a lake above to compare satellite and lab data.
        </p>
      )}

      {selectedLake && isLoading && (
        <div className="h-64 bg-white/5 rounded-xl animate-pulse" />
      )}

      {selectedLake && data && data.entries.length === 0 && (
        <p className="text-sm text-foreground/50">
          No cross-reference data available for this lake. Either KSPCB hasn't
          sampled it, or there's no overlapping satellite coverage.
        </p>
      )}

      {selectedLake && data && data.entries.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-foreground/50">
              {data.entries.length} months with data from both sources
            </p>
            <div className="flex gap-3 text-xs text-foreground/40">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                consistent
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-yellow-500 inline-block" />
                partial
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                contradictory
              </span>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/10">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-white/5 text-foreground/50 text-xs uppercase tracking-wider">
                  <th className="text-left p-3">Month</th>
                  <th className="text-right p-3">Satellite Algae %</th>
                  <th className="text-right p-3">KSPCB BOD</th>
                  <th className="text-right p-3">KSPCB COD</th>
                  <th className="text-right p-3">KSPCB DO</th>
                  <th className="text-left p-3">Classification</th>
                  <th className="text-center p-3">Agreement</th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((entry) => (
                  <tr
                    key={entry.month}
                    className="border-t border-white/5 text-foreground/70 hover:bg-white/5"
                  >
                    <td className="p-3 font-medium">{entry.month}</td>
                    <td className="text-right p-3 font-mono">
                      {entry.satellite_algae_fraction !== null
                        ? (entry.satellite_algae_fraction * 100).toFixed(1) + "%"
                        : "--"}
                    </td>
                    <td className="text-right p-3 font-mono">
                      {entry.kspcb_bod?.toFixed(1) ?? "--"}
                    </td>
                    <td className="text-right p-3 font-mono">
                      {entry.kspcb_cod?.toFixed(1) ?? "--"}
                    </td>
                    <td className="text-right p-3 font-mono">
                      {entry.kspcb_do?.toFixed(1) ?? "--"}
                    </td>
                    <td className="p-3 text-xs">
                      {entry.kspcb_classification ?? "--"}
                    </td>
                    <td className="p-3 text-center">
                      <AgreementBadge agreement={entry.agreement} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function HealthBadgeInline({ score }: { score: number | null }) {
  if (score === null) return null;
  const color =
    score >= 60
      ? "bg-green-500/20 text-green-400"
      : score >= 30
        ? "bg-yellow-500/20 text-yellow-400"
        : "bg-red-500/20 text-red-400";
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${color}`}>
      {Math.round(score)}
    </span>
  );
}

function MoverRow({
  entry,
  rank,
  direction,
}: {
  entry: MoverEntry;
  rank: number;
  direction: "up" | "down";
}) {
  const arrow = direction === "up" ? "\u2191" : "\u2193";
  const arrowColor = direction === "up" ? "text-green-400" : "text-red-400";
  const changePct = entry.change_pct !== null ? Math.abs(entry.change_pct).toFixed(1) : "--";

  return (
    <div className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
      <span className="w-5 text-xs font-mono text-foreground/30 text-right">
        {rank}
      </span>
      <span className={`text-sm font-bold ${arrowColor}`}>{arrow}</span>
      <div className="flex-1 min-w-0">
        <Link
          href={`/lakes/${entry.lake_id}`}
          className="text-sm text-blue-400 hover:underline truncate block"
        >
          {entry.lake_name}
        </Link>
      </div>
      <span className={`text-sm font-mono font-bold ${arrowColor}`}>
        {direction === "up" ? "+" : "-"}{changePct}%
      </span>
      <HealthBadgeInline score={entry.health_score} />
      {entry.custodian && (
        <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/10 text-blue-300 border border-blue-500/15 truncate max-w-[100px]">
          {entry.custodian}
        </span>
      )}
    </div>
  );
}

function MoversPanel() {
  const [year, setYear] = useState(2024);
  const { data, isLoading } = useMovers(year);

  const years = Array.from({ length: 8 }, (_, i) => 2025 - i);

  return (
    <div className="space-y-4">
      {/* Explainer + year selector */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground/60 uppercase tracking-wider">
            Year-over-Year Movers
          </h3>
          <p className="text-xs text-foreground/40 mt-1">
            Lakes ranked by change in average water area compared to the previous year.
          </p>
        </div>
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

      {isLoading && (
        <div className="h-64 bg-white/5 rounded-xl animate-pulse" />
      )}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Improvers */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h4 className="text-xs uppercase tracking-wider text-green-400 font-semibold mb-3">
              Top Improvers
            </h4>
            {data.improvers.length === 0 ? (
              <p className="text-sm text-foreground/40 italic">
                No lakes showed improvement in {year}.
              </p>
            ) : (
              data.improvers.map((entry, i) => (
                <MoverRow
                  key={entry.lake_id}
                  entry={entry}
                  rank={i + 1}
                  direction="up"
                />
              ))
            )}
          </div>

          {/* Decliners */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h4 className="text-xs uppercase tracking-wider text-red-400 font-semibold mb-3">
              Top Decliners
            </h4>
            {data.decliners.length === 0 ? (
              <p className="text-sm text-foreground/40 italic">
                No lakes showed decline in {year}.
              </p>
            ) : (
              data.decliners.map((entry, i) => (
                <MoverRow
                  key={entry.lake_id}
                  entry={entry}
                  rank={i + 1}
                  direction="down"
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function InsightsClient() {
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-6">
      <div>
        <Link
          href="/"
          className="text-sm text-foreground/50 hover:text-foreground/80 mb-2 inline-block"
        >
          &larr; Back to map
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-white">Data Insights</h1>
          <ThemeToggle />
        </div>
        <p className="text-foreground/50 mt-1">
          Satellite-derived metrics, raw observations, and data quality checks for every tracked lake.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        <TabButton
          active={tab === "overview"}
          onClick={() => setTab("overview")}
        >
          Overview
        </TabButton>
        <TabButton active={tab === "stats"} onClick={() => setTab("stats")}>
          Lake Stats
        </TabButton>
        <TabButton
          active={tab === "observations"}
          onClick={() => setTab("observations")}
        >
          Raw Observations
        </TabButton>
        <TabButton
          active={tab === "outliers"}
          onClick={() => setTab("outliers")}
        >
          Outliers
        </TabButton>
        <TabButton
          active={tab === "crossref"}
          onClick={() => setTab("crossref")}
        >
          Cross-Reference
        </TabButton>
        <TabButton
          active={tab === "movers"}
          onClick={() => setTab("movers")}
        >
          Movers
        </TabButton>
      </div>

      {/* Content */}
      {tab === "overview" && <OverviewPanel />}
      {tab === "stats" && <StatsTable />}
      {tab === "observations" && <ObservationsTable />}
      {tab === "outliers" && <OutliersTable />}
      {tab === "crossref" && <CrossReferencePanel />}
      {tab === "movers" && <MoversPanel />}

      {/* Data provenance footer */}
      <div className="border-t border-white/10 pt-4 text-xs text-foreground/30 space-y-1">
        <p>
          <strong>Satellite data:</strong> Copernicus Sentinel-2 L2A via Google
          Earth Engine. 10m resolution, ~5-day revisit. Cloud-masked using SCL
          band (&gt;30% rejected).
        </p>
        <p>
          <strong>EMPRI data:</strong> Environmental Management &amp; Policy
          Research Institute, 2018 field survey. One-time snapshot.
        </p>
        <p>
          <strong>KSPCB data:</strong> Karnataka State Pollution Control Board
          lab measurements. Frequency varies by lake.
        </p>
        <p>
          <strong>Lake boundaries:</strong> CSEI-ATREE, Centre for Social and
          Environmental Innovation. CC BY-SA 4.0.
        </p>
      </div>
    </div>
  );
}
