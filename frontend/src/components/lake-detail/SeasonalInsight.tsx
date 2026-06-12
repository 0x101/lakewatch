"use client";

import { useTimeseries } from "@/hooks/useTimeseries";
import type { LakeDetail } from "@/lib/types";

interface SeasonalInsightProps {
  lake: LakeDetail;
}

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export default function SeasonalInsight({ lake }: SeasonalInsightProps) {
  const { data: timeseries } = useTimeseries(lake.id, "raw");

  if (!timeseries || timeseries.count < 6) return null;

  // Compute monthly averages
  const monthlyArea: Record<number, number[]> = {};
  const monthlyAlgae: Record<number, number[]> = {};

  for (const obs of timeseries.observations) {
    const month = new Date(obs.date).getMonth();
    if (obs.water_area_m2 !== null) {
      if (!monthlyArea[month]) monthlyArea[month] = [];
      monthlyArea[month].push(obs.water_area_m2);
    }
    if (obs.algae_fraction !== null) {
      if (!monthlyAlgae[month]) monthlyAlgae[month] = [];
      monthlyAlgae[month].push(obs.algae_fraction);
    }
  }

  const avgArea = Object.entries(monthlyArea).map(([m, vals]) => ({
    month: parseInt(m),
    avg: vals.reduce((a, b) => a + b, 0) / vals.length,
  }));

  const avgAlgae = Object.entries(monthlyAlgae).map(([m, vals]) => ({
    month: parseInt(m),
    avg: vals.reduce((a, b) => a + b, 0) / vals.length,
  }));

  if (avgArea.length < 6) return null;

  const maxArea = Math.max(...avgArea.map((a) => a.avg));
  const minArea = Math.min(...avgArea.map((a) => a.avg));
  const maxAreaMonth = avgArea.find((a) => a.avg === maxArea)?.month ?? 0;
  const minAreaMonth = avgArea.find((a) => a.avg === minArea)?.month ?? 0;

  const seasonalChange = maxArea > 0 ? ((maxArea - minArea) / maxArea) * 100 : 0;

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-foreground/60 uppercase tracking-wider mb-3">
        Seasonal Pattern
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Water area by month */}
        <div>
          <p className="text-xs text-foreground/40 mb-2">
            Average water area by month
          </p>
          <div className="flex items-end gap-1" style={{ height: 64 }}>
            {Array.from({ length: 12 }, (_, i) => {
              const entry = avgArea.find((a) => a.month === i);
              const val = entry?.avg ?? 0;
              const pct = maxArea > 0 ? val / maxArea : 0;
              const barH = Math.max(pct * 52, val > 0 ? 3 : 0);
              const isMax = i === maxAreaMonth;
              const isMin = i === minAreaMonth;
              return (
                <div
                  key={i}
                  className="flex-1 flex flex-col items-center justify-end"
                  style={{ height: 64 }}
                >
                  <div
                    className={`w-full rounded-t ${
                      isMax
                        ? "bg-blue-400"
                        : isMin
                          ? "bg-red-400/60"
                          : "bg-blue-500/40"
                    }`}
                    style={{ height: barH }}
                    title={`${MONTH_NAMES[i]}: ${(val / 10000).toFixed(1)} ha`}
                  />
                  <span className="text-[8px] text-foreground/30 mt-1">
                    {MONTH_NAMES[i][0]}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Algae by month */}
        <div>
          <p className="text-xs text-foreground/40 mb-2">
            Average algae fraction by month
          </p>
          <div className="flex items-end gap-1" style={{ height: 64 }}>
            {Array.from({ length: 12 }, (_, i) => {
              const entry = avgAlgae.find((a) => a.month === i);
              const val = entry?.avg ?? 0;
              const maxAlgaeVal = Math.max(
                ...avgAlgae.map((a) => a.avg),
                0.01
              );
              const pct = val / maxAlgaeVal;
              const barH = Math.max(pct * 52, val > 0 ? 3 : 0);
              return (
                <div
                  key={i}
                  className="flex-1 flex flex-col items-center justify-end"
                  style={{ height: 64 }}
                >
                  <div
                    className={`w-full rounded-t ${
                      val > 0.15
                        ? "bg-green-400"
                        : val > 0.05
                          ? "bg-green-500/50"
                          : "bg-green-500/25"
                    }`}
                    style={{ height: barH }}
                    title={`${MONTH_NAMES[i]}: ${(val * 100).toFixed(1)}%`}
                  />
                  <span className="text-[8px] text-foreground/30 mt-1">
                    {MONTH_NAMES[i][0]}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Insight text */}
      <div className="mt-3 text-xs text-foreground/50 space-y-1">
        <p>
          Water area peaks in{" "}
          <strong className="text-foreground/70">
            {MONTH_NAMES[maxAreaMonth]}
          </strong>{" "}
          and hits its lowest in{" "}
          <strong className="text-foreground/70">
            {MONTH_NAMES[minAreaMonth]}
          </strong>
          . Seasonal swing: {seasonalChange.toFixed(0)}%.
        </p>
        {lake.peak_algae_month !== null && (
          <p>
            Algae tends to peak in{" "}
            <strong className="text-foreground/70">
              {MONTH_NAMES[lake.peak_algae_month - 1]}
            </strong>
            , typically when monsoon runoff brings in nutrients.
          </p>
        )}
      </div>
    </div>
  );
}
