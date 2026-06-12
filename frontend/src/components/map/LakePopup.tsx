"use client";

import { Popup } from "react-map-gl/mapbox";
import Link from "next/link";
import { getHealthColor, getHealthLabel } from "@/lib/constants";

interface LakePopupProps {
  longitude: number;
  latitude: number;
  name: string;
  healthScore: number;
  areaChange5yr: number | null;
  latestWaterArea: number | null;
  lakeId: string;
  onClose: () => void;
}

function formatHectares(m2: number): string {
  const ha = m2 / 10000;
  return ha >= 10 ? `${Math.round(ha)} ha` : `${ha.toFixed(1)} ha`;
}

export function LakePopup({
  longitude,
  latitude,
  name,
  healthScore,
  areaChange5yr,
  latestWaterArea,
  lakeId,
  onClose,
}: LakePopupProps) {
  const color = getHealthColor(healthScore);
  const label = getHealthLabel(healthScore);

  const hasAreaChange =
    areaChange5yr !== null && areaChange5yr !== undefined;

  const areaChangeText = hasAreaChange
    ? `Water area ${areaChange5yr >= 0 ? "up" : "down"} ${Math.abs(areaChange5yr).toFixed(0)}% over 5 years`
    : null;

  const areaChangeColor = hasAreaChange
    ? areaChange5yr >= 0
      ? "#22c55e"
      : "#ef4444"
    : "#9ca3af";

  return (
    <Popup
      longitude={longitude}
      latitude={latitude}
      onClose={onClose}
      closeOnClick={false}
      className="lake-popup"
    >
      <Link
        href={`/lakes/${lakeId}`}
        className="block bg-gray-900 text-white rounded-xl p-4 min-w-[220px] -m-[10px] hover:bg-gray-800 transition-colors cursor-pointer no-underline"
      >
        {/* Lake name */}
        <h3 className="font-semibold text-sm text-white mb-2">{name}</h3>

        {/* Health score + label */}
        <div className="flex items-center gap-2 mb-2">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold"
            style={{
              backgroundColor: `${color}20`,
              color,
            }}
          >
            {Math.round(healthScore)}
          </div>
          <span
            className="text-xs font-medium"
            style={{ color }}
          >
            {label}
          </span>
        </div>

        {/* Area change sentence */}
        {areaChangeText && (
          <p className="text-xs mb-1" style={{ color: areaChangeColor }}>
            {areaChangeText}
          </p>
        )}

        {/* Current water area in hectares */}
        {latestWaterArea != null && latestWaterArea > 0 && (
          <p className="text-[11px] text-white/40">
            {formatHectares(latestWaterArea)} water area
          </p>
        )}

        {/* CTA */}
        <p className="text-[10px] text-white/30 mt-2">
          View details &rarr;
        </p>
      </Link>
    </Popup>
  );
}
