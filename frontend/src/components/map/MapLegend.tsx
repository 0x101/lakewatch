"use client";

import { HEALTH_SCALE } from "@/lib/constants";

export function MapLegend() {
  return (
    <div className="absolute bottom-6 right-3 z-10 bg-gray-900/80 backdrop-blur-sm rounded-lg px-3 py-2.5 text-white border border-white/10 md:bottom-6 md:right-14">
      <p className="text-[9px] text-white/40 uppercase tracking-wider mb-1.5">
        Lake Health
      </p>
      <div className="flex items-center gap-0.5 mb-1.5">
        {HEALTH_SCALE.map((s, i) => (
          <div
            key={s.stop}
            className={`h-2 flex-1 ${i === 0 ? "rounded-l" : ""} ${i === HEALTH_SCALE.length - 1 ? "rounded-r" : ""}`}
            style={{ backgroundColor: s.color }}
          />
        ))}
      </div>
      <div className="flex justify-between">
        <span className="text-[8px] text-white/50">0</span>
        <span className="text-[8px] text-white/50">100</span>
      </div>
      <div className="flex gap-2 mt-1.5">
        {HEALTH_SCALE.map((s) => (
          <div key={s.stop} className="flex items-center gap-1">
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-[8px] text-white/50">{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
