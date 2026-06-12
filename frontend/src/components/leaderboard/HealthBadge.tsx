"use client";

import { getHealthColor } from "@/lib/constants";

interface HealthBadgeProps {
  score: number | null;
}

export default function HealthBadge({ score }: HealthBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-700 text-gray-400">
        N/A
      </span>
    );
  }

  const rounded = Math.round(score);

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold text-white"
      style={{ backgroundColor: getHealthColor(rounded) }}
    >
      {rounded}
    </span>
  );
}
