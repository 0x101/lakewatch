"use client";

import { LineChart, Line } from "recharts";
import { useTimeseries } from "@/hooks/useTimeseries";
import type { ObservationPoint } from "@/lib/types";

interface SparklineProps {
  lakeId: string;
  metricKey: "water_area_m2" | "algae_fraction" | "mean_ndwi";
}

export default function Sparkline({ lakeId, metricKey }: SparklineProps) {
  const { data, isLoading } = useTimeseries(lakeId, "monthly");

  if (isLoading) {
    return <div className="w-20 h-6 bg-gray-800 rounded animate-pulse" />;
  }

  if (!data || !data.observations || data.observations.length === 0) {
    return <span className="text-gray-600 text-xs">&mdash;</span>;
  }

  const observations = data.observations.slice(-12);
  const chartData = observations
    .map((obs: ObservationPoint, i: number) => ({
      index: i,
      value: obs[metricKey],
    }))
    .filter(
      (d: { index: number; value: number | null }) => d.value !== null
    );

  if (chartData.length < 2) {
    return <span className="text-gray-600 text-xs">&mdash;</span>;
  }

  return (
    <LineChart width={80} height={24} data={chartData}>
      <Line
        type="monotone"
        dataKey="value"
        stroke="#3b82f6"
        strokeWidth={1.5}
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  );
}
