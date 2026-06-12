"use client";

import type { LakeDetail } from "@/lib/types";
import HealthBadge from "@/components/leaderboard/HealthBadge";
import { formatRelatableArea } from "@/lib/relatable";

interface StatsCardsProps {
  lake: LakeDetail;
  kspcbClass?: string | null;
  /** Absolute 5yr water-area change in m². Used for the relatable equivalent. */
  areaDelta5yrM2?: number | null;
}

const KSPCB_CLASS_COLORS: Record<string, string> = {
  A: "bg-green-500/20 text-green-400 border-green-500/30",
  B: "bg-green-500/10 text-green-300 border-green-500/20",
  C: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  D: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  E: "bg-red-500/20 text-red-400 border-red-500/30",
};

function formatHectares(m2: number | null): string {
  if (m2 === null) return "--";
  const ha = m2 / 10000;
  return ha.toFixed(1);
}

function formatHectaresContext(m2: number | null): string | null {
  if (m2 === null) return null;
  const ha = m2 / 10000;
  const fields = Math.round(ha * 1.4);
  if (fields <= 0) return "less than a football field";
  if (fields === 1) return "~1 football field";
  return `~${fields} football fields`;
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function changeColor(pct: number | null): string {
  if (pct === null) return "text-foreground/60";
  return pct >= 0 ? "text-green-400" : "text-red-400";
}

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  help?: string;
}

function StatCard({ label, value, sub, help }: StatCardProps) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-1 group relative">
      <span className="text-xs uppercase tracking-wider text-foreground/50">
        {label}
        {help && (
          <span className="ml-1 inline-block cursor-help text-foreground/30 hover:text-foreground/60" title={help}>
            ℹ
          </span>
        )}
      </span>
      <span className="text-2xl font-bold text-white">{value}</span>
      {sub && (
        <span className="text-sm text-foreground/60">{sub}</span>
      )}
      {help && (
        <span className="hidden group-hover:block absolute -bottom-1 translate-y-full left-0 right-0 z-10 bg-gray-900 border border-white/10 rounded-lg p-3 text-xs text-foreground/70 leading-relaxed shadow-xl">
          {help}
        </span>
      )}
    </div>
  );
}

export default function StatsCards({ lake, kspcbClass, areaDelta5yrM2 }: StatsCardsProps) {
  const relatableDelta =
    typeof areaDelta5yrM2 === "number" && Number.isFinite(areaDelta5yrM2) && areaDelta5yrM2 !== 0
      ? formatRelatableArea(areaDelta5yrM2)
      : null;
  const deltaVerb = (areaDelta5yrM2 ?? 0) >= 0 ? "gained" : "lost";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
      <StatCard
        label="Surface Area"
        help="Surface area covered by water, measured from satellite imagery. Does not indicate depth or volume. 1 hectare = 10,000 m²."
        value={
          <span>
            {formatHectares(lake.latest_water_area_m2)}{" "}
            <span className="text-sm font-normal text-foreground/60">ha</span>
          </span>
        }
        sub={
          <>
            {lake.area_change_5yr_pct !== null && (
              <span className={changeColor(lake.area_change_5yr_pct)}>
                {formatPct(lake.area_change_5yr_pct)} over 5 years
              </span>
            )}
            {relatableDelta && (
              <span className="block text-xs text-foreground/50">
                {relatableDelta} {deltaVerb} over 5 years
              </span>
            )}
          </>
        }
      />

      <StatCard
        label="Health Score"
        help="Composite score: area stability (40%), algae levels (30%), water presence (20%), trend (10%). Derived from satellite observations, not lab samples."
        value={
          <span className="flex items-center gap-2">
            {lake.health_score !== null ? Math.round(lake.health_score) : "--"}
            <HealthBadge score={lake.health_score} />
          </span>
        }
        sub={lake.ward}
      />

      <StatCard
        label="Algae Level"
        help="Fraction of water surface showing algae, detected via NDVI on satellite imagery. Above 15% is elevated. Typically peaks during post-monsoon months."
        value={
          <span className={algaeColor(lake.mean_algae_fraction)}>
            {formatAlgae(lake.mean_algae_fraction)}
          </span>
        }
        sub={
          lake.peak_algae_month !== null
            ? `Peaks in ${new Date(2000, lake.peak_algae_month - 1).toLocaleDateString("en-US", { month: "long" })}`
            : null
        }
      />

      <StatCard
        label="Water Quality"
        help="KSPCB lab classification: Class A (drinking water after disinfection) through Class E (irrigation/industrial). Based on BOD, COD, dissolved oxygen, and coliform levels measured in lab samples."
        value={
          kspcbClass ? (
            <span
              className={`inline-flex px-3 py-0.5 rounded text-lg font-bold border ${
                KSPCB_CLASS_COLORS[kspcbClass] ?? "bg-white/10 text-foreground/60 border-white/10"
              }`}
            >
              Class {kspcbClass}
            </span>
          ) : (
            <span className="text-foreground/30">--</span>
          )
        }
        sub="KSPCB lab classification"
      />

      <StatCard
        label="Observations"
        help="Usable Sentinel-2 satellite passes for this lake. One image per clear day, ~5-day revisit cycle. Monsoon months (Jun-Sep) have fewer due to cloud cover."
        value={lake.observation_count.toLocaleString()}
        sub={
          lake.latest_observation_date
            ? `Latest: ${formatDate(lake.latest_observation_date)}`
            : null
        }
      />
    </div>
  );
}
