"use client";

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
} from "@/hooks/useDashboard";
import { useLakeStatsTable, useCustodianStats } from "@/hooks/useInsights";
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

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`bg-white/5 rounded-xl animate-pulse ${className}`} />;
}

function healthColor(score: number): string {
  if (score >= 60) return "text-green-400";
  if (score >= 30) return "text-yellow-400";
  return "text-red-400";
}

/* ── City Health Score ─────────────────────────────────── */

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

/* ── Key Metric Cards ──────────────────────────────────── */

function MetricCards() {
  const { data, isLoading } = useCitySummary();
  const { data: statsData } = useLakeStatsTable();

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );
  }

  const shrinkingCount = statsData
    ? statsData.stats.filter(
        (s) => s.area_change_5yr_pct !== null && s.area_change_5yr_pct < -10
      ).length
    : 0;

  const highAlgaeCount = statsData
    ? statsData.stats.filter(
        (s) => s.mean_algae_fraction !== null && s.mean_algae_fraction > 0.15
      ).length
    : 0;

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
      label: "Shrinking Lakes",
      value: `${shrinkingCount}`,
      unit: "",
      sub: "Lost >10% area in 5 years",
      color: "text-red-400",
    },
    {
      label: "High Algae",
      value: `${highAlgaeCount}`,
      unit: "",
      sub: "Mean algae >15% of surface",
      color: "text-orange-400",
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

/* ── Trends + KSPCB Charts ─────────────────────────────── */

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

/* ── Seasonal + Algae Peaks ────────────────────────────── */

function SeasonalCharts() {
  const { data, isLoading } = useSeasonal();
  const { data: statsData } = useLakeStatsTable();

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

  // Peak algae month distribution from stats
  const peakMonths: Record<number, number> = {};
  if (statsData) {
    statsData.stats.forEach((s) => {
      if (s.peak_algae_month !== null) {
        peakMonths[s.peak_algae_month] = (peakMonths[s.peak_algae_month] ?? 0) + 1;
      }
    });
  }

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

      {/* Algae peaks distribution */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-3">
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
                  title={`${MONTH_NAMES[month]}: ${count} lakes`}
                />
                <span className="text-[10px] text-foreground/30 mt-1">
                  {MONTH_NAMES[month]}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ── Custodian Table ───────────────────────────────────── */

function CustodianTable() {
  const { data: custodianData, isLoading } = useCustodianStats();

  if (isLoading) return <Skeleton className="h-48" />;
  if (!custodianData || custodianData.entries.length === 0) return null;

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-3">
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
  );
}

/* ── Health Distribution ───────────────────────────────── */

function HealthDistribution() {
  const { data: statsData, isLoading } = useLakeStatsTable();

  if (isLoading || !statsData) return <Skeleton className="h-40" />;

  const stats = statsData.stats;
  const healthyCount = stats.filter(
    (s) => s.health_score !== null && s.health_score >= 60
  ).length;
  const strugglingCount = stats.filter(
    (s) => s.health_score !== null && s.health_score >= 30 && s.health_score < 60
  ).length;
  const distressedCount = stats.filter(
    (s) => s.health_score !== null && s.health_score < 30
  ).length;

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-3">
        Health Distribution
      </h3>
      <div className="space-y-2">
        {[
          { label: "Healthy (60-100)", count: healthyCount, color: "bg-green-500", total: stats.length },
          { label: "Struggling (30-60)", count: strugglingCount, color: "bg-yellow-500", total: stats.length },
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
  );
}

/* ── Key Findings ──────────────────────────────────────── */

function KeyFindings() {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <h3 className="text-xs font-semibold text-foreground/50 uppercase tracking-wider mb-3">
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
  );
}

/* ── Main Overview ─────────────────────────────────────── */

export default function OverviewClient() {
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
          <h1 className="text-3xl font-bold text-white">City Overview</h1>
          <ThemeToggle />
        </div>
        <p className="text-foreground/50 mt-1">
          Aggregate metrics across all tracked lakes in Bangalore.
        </p>
      </div>

      {/* City Health Score */}
      <CityHealthScore />

      {/* Key Metric Cards */}
      <MetricCards />

      {/* Health Distribution */}
      <HealthDistribution />

      {/* Trends + KSPCB */}
      <TrendsCharts />

      {/* Seasonal + Algae Peaks */}
      <SeasonalCharts />

      {/* Custodian Table */}
      <CustodianTable />

      {/* Key Findings */}
      <KeyFindings />

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
