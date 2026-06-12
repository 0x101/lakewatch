"use client";

import { useState } from "react";
import Link from "next/link";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  useCitySummary,
  useTrends,
  useSeasonal,
  useDashboardRankings,
} from "@/hooks/useDashboard";
import HealthBadge from "@/components/leaderboard/HealthBadge";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

const MONTH_NAMES = [
  "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const KSPCB_COLORS: Record<string, string> = {
  A: "#22c55e",
  B: "#84cc16",
  C: "#eab308",
  D: "#f97316",
  E: "#ef4444",
};

const RANKING_TABS = [
  { key: "healthiest", label: "Healthiest" },
  { key: "most_improved", label: "Most Improved" },
  { key: "most_declined", label: "Most Declined" },
  { key: "most_polluted", label: "Most Polluted" },
  { key: "cleanest", label: "Cleanest" },
] as const;

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`bg-white/5 rounded-xl animate-pulse ${className}`} />;
}

function healthColor(score: number): string {
  if (score >= 60) return "text-green-400";
  if (score >= 30) return "text-yellow-400";
  return "text-red-400";
}

/* ── Row 1: City Health Score ────────────────────────────── */

function CityHealthScore() {
  const { data, isLoading } = useCitySummary();

  if (isLoading || !data) return <Skeleton className="h-40" />;

  const score = Math.round(data.avg_health_score);

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-6 text-center">
      <p className="text-xs uppercase tracking-wider text-foreground/40 mb-2">
        City Health Score
      </p>
      <p className={`text-6xl font-bold ${healthColor(score)}`}>
        {score}
        <span className="text-2xl font-normal text-foreground/40">/100</span>
      </p>
      <p className="text-sm text-foreground/50 mt-3">
        {data.healthy_count} of {data.total_lakes} lakes healthy, {data.distressed_count} distressed
      </p>
    </div>
  );
}

/* ── Row 2: Key Metric Cards ────────────────────────────── */

function MetricCards() {
  const { data, isLoading } = useCitySummary();

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Total Water Area",
      value: `${data.total_water_area_ha.toFixed(0)}`,
      unit: "ha",
      sub: `Across ${data.total_lakes} lakes`,
    },
    {
      label: "Improving vs Declining",
      value: `${data.lakes_improving}`,
      unit: `/ ${data.lakes_declining}`,
      sub: "Improving / declining lakes",
      color:
        data.lakes_improving >= data.lakes_declining
          ? "text-green-400"
          : "text-red-400",
    },
    {
      label: "Average Algae Level",
      value: `${(data.avg_algae_fraction * 100).toFixed(1)}`,
      unit: "%",
      sub: "Mean across all lakes",
      color:
        data.avg_algae_fraction < 0.1
          ? "text-green-400"
          : data.avg_algae_fraction < 0.2
            ? "text-yellow-400"
            : "text-red-400",
    },
    {
      label: "Common KSPCB Class",
      value: data.most_common_kspcb_class ?? "--",
      unit: "",
      sub: `${data.total_observations.toLocaleString()} observations`,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className="bg-white/5 border border-white/10 rounded-xl p-4"
        >
          <p className="text-xs text-foreground/40 uppercase tracking-wider">
            {c.label}
          </p>
          <p className={`text-2xl font-bold mt-1 ${c.color ?? "text-white"}`}>
            {c.value}
            {c.unit && (
              <span className="text-sm font-normal text-foreground/40 ml-1">
                {c.unit}
              </span>
            )}
          </p>
          <p className="text-xs text-foreground/40 mt-1">{c.sub}</p>
        </div>
      ))}
    </div>
  );
}

/* ── Row 3: Trends Over Time ────────────────────────────── */

function TrendsCharts() {
  const { data, isLoading } = useTrends();

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </div>
    );
  }

  const years = data.years;

  // Build stacked bar data for KSPCB classes
  const allClasses = Array.from(
    new Set(years.flatMap((y) => Object.keys(y.kspcb_class_distribution ?? {})))
  ).sort();

  const kspcbData = years.map((y) => ({
    year: y.year,
    ...(y.kspcb_class_distribution ?? {}),
  }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Health trend line */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-4">
          Average Health Score by Year
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={years}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="year"
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17,24,39,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#fff",
              }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(value: any) => [Number(value)?.toFixed(1), "Health"]}
            />
            <Line
              type="monotone"
              dataKey="avg_health"
              stroke="#22c55e"
              strokeWidth={2}
              dot={{ r: 3, fill: "#22c55e" }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* KSPCB class distribution stacked bar */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-4">
          KSPCB Classification by Year
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={kspcbData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="year"
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <YAxis
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17,24,39,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#fff",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }}
            />
            {allClasses.map((cls) => (
              <Bar
                key={cls}
                dataKey={cls}
                stackId="kspcb"
                fill={KSPCB_COLORS[cls] ?? "#6b7280"}
                name={`Class ${cls}`}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ── Row 4: Seasonal Patterns ───────────────────────────── */

function SeasonalCharts() {
  const { data, isLoading } = useSeasonal();

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  const months = data.months.map((m) => ({
    ...m,
    monthLabel: MONTH_NAMES[m.month] || String(m.month),
    algae_pct: m.avg_algae !== null ? m.avg_algae * 100 : null,
  }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Water area by month */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-4">
          Avg Water Area by Month (ha)
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={months}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="monthLabel"
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <YAxis
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17,24,39,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#fff",
              }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(value: any) => [
                Number(value)?.toFixed(1) + " ha",
                "Water Area",
              ]}
            />
            <Bar dataKey="avg_water_area" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Algae by month */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-4">
          Avg Algae Level by Month (%)
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={months}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="monthLabel"
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <YAxis
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17,24,39,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#fff",
              }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(value: any) => [
                Number(value)?.toFixed(1) + "%",
                "Algae",
              ]}
            />
            <Bar dataKey="algae_pct" fill="#f97316" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ── Row 5: Rankings ────────────────────────────────────── */

function Rankings() {
  const [activeTab, setActiveTab] = useState<string>("healthiest");
  const { data, isLoading } = useDashboardRankings(activeTab);

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-4">
        Lake Rankings
      </h3>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap mb-4">
        {RANKING_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeTab === tab.key
                ? "bg-white/10 text-white"
                : "text-foreground/50 hover:text-foreground/80 hover:bg-white/5"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <Skeleton className="h-64" />
      ) : !data || data.entries.length === 0 ? (
        <p className="text-sm text-foreground/40 py-8 text-center">
          No ranking data available.
        </p>
      ) : (
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
              {data.entries.map((entry) => (
                <tr
                  key={entry.lake_id}
                  className="border-t border-white/5 text-foreground/70 hover:bg-white/5"
                >
                  <td className="py-2 font-mono text-foreground/30">
                    {entry.rank}
                  </td>
                  <td className="py-2">
                    <Link
                      href={`/lakes/${entry.lake_id}`}
                      className="text-blue-400 hover:underline"
                    >
                      {entry.lake_name}
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
      )}
    </div>
  );
}

/* ── Main Dashboard ─────────────────────────────────────── */

export default function DashboardClient() {
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
          <h1 className="text-3xl font-bold text-white">City Dashboard</h1>
          <ThemeToggle />
        </div>
        <p className="text-foreground/50 mt-1">
          Aggregate metrics across all tracked lakes in Bangalore.
        </p>
      </div>

      {/* Row 1: City Health Score */}
      <CityHealthScore />

      {/* Row 2: Key Metric Cards */}
      <MetricCards />

      {/* Row 3: Trends Over Time */}
      <TrendsCharts />

      {/* Row 4: Seasonal Patterns */}
      <SeasonalCharts />

      {/* Row 5: Rankings */}
      <Rankings />

      {/* Footer: Data provenance */}
      <div className="border-t border-white/10 pt-4 text-xs text-foreground/30 space-y-1">
        <p>
          <strong>Satellite data:</strong> Copernicus Sentinel-2 L2A via Google
          Earth Engine. 10m resolution, ~5-day revisit. Cloud-masked using SCL
          band (&gt;30% rejected).
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
