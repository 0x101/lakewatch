"use client";

import { useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { useTimeseries } from "@/hooks/useTimeseries";

interface TimeseriesChartProps {
  lakeId: string;
}

const INTERVALS = [
  { key: "monthly", label: "Monthly" },
  { key: "yearly", label: "Yearly" },
  { key: "raw", label: "Raw" },
] as const;

interface ChartDatum {
  date: string;
  water_area_ha: number | null;
  algae_fraction: number | null;
}

function formatXTick(dateStr: string): string {
  const d = new Date(dateStr);
  const month = d.toLocaleDateString("en-US", { month: "short" });
  const year = String(d.getFullYear()).slice(2);
  return `${month} '${year}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;

  const areaEntry = payload.find(
    (p: { dataKey?: string }) => p.dataKey === "water_area_ha"
  );
  const algaeEntry = payload.find(
    (p: { dataKey?: string }) => p.dataKey === "algae_fraction"
  );

  return (
    <div className="bg-gray-900 border border-white/10 rounded-lg px-3 py-2 text-sm shadow-lg">
      <p className="text-foreground/70 mb-1">{label}</p>
      {areaEntry?.value != null && (
        <p className="text-blue-400">
          Water Area: {Number(areaEntry.value).toFixed(1)} ha
        </p>
      )}
      {algaeEntry?.value != null && (
        <p className="text-red-400">
          Algae: {(Number(algaeEntry.value) * 100).toFixed(1)}%
        </p>
      )}
    </div>
  );
}

export default function TimeseriesChart({ lakeId }: TimeseriesChartProps) {
  const [interval, setInterval] = useState("monthly");
  const { data, isLoading } = useTimeseries(lakeId, interval);

  const chartData: ChartDatum[] =
    data?.observations.map((obs) => ({
      date: obs.date,
      water_area_ha:
        obs.water_area_m2 !== null ? obs.water_area_m2 / 10000 : null,
      algae_fraction: obs.algae_fraction,
    })) ?? [];

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-white">
          Surface Area &amp; Algae Over Time
        </h3>
        <div className="flex gap-1 bg-white/5 rounded-lg p-0.5">
          {INTERVALS.map((iv) => (
            <button
              key={iv.key}
              onClick={() => setInterval(iv.key)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                interval === iv.key
                  ? "bg-white/15 text-white font-medium"
                  : "text-foreground/50 hover:text-foreground/80"
              }`}
            >
              {iv.label}
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-foreground/40 mb-4">
        <span className="text-blue-400">Blue</span> = satellite-measured surface area (ha).{" "}
        <span className="text-red-400">Red</span> = algae coverage fraction (0-1).{" "}
        Gaps = cloud cover.
      </p>

      {isLoading ? (
        <div className="h-[350px] bg-white/5 rounded-lg animate-pulse" />
      ) : chartData.length === 0 ? (
        <div className="h-[350px] flex items-center justify-center text-foreground/50">
          No observations available for this interval.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={350}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis
              dataKey="date"
              tickFormatter={formatXTick}
              tick={{ fill: "#999", fontSize: 11 }}
              tickLine={false}
            />
            <YAxis
              yAxisId="area"
              tick={{ fill: "#3b82f6", fontSize: 11 }}
              tickLine={false}
              label={{
                value: "Water Area (ha)",
                angle: -90,
                position: "insideLeft",
                style: { fill: "#3b82f6", fontSize: 11 },
              }}
            />
            <YAxis
              yAxisId="algae"
              orientation="right"
              domain={[0, 1]}
              tick={{ fill: "#ef4444", fontSize: 11 }}
              tickLine={false}
              label={{
                value: "Algae Fraction",
                angle: 90,
                position: "insideRight",
                style: { fill: "#ef4444", fontSize: 11 },
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              yAxisId="area"
              type="monotone"
              dataKey="water_area_ha"
              stroke="#3b82f6"
              fill="#3b82f680"
              connectNulls={true}
            />
            <Area
              yAxisId="algae"
              type="monotone"
              dataKey="algae_fraction"
              stroke="#ef4444"
              fill="#ef444440"
              connectNulls={true}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
