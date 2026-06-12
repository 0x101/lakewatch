"use client";

import { getTierConfig } from "@/lib/lake-enrichment";

interface TierBadgeProps {
  tier: 1 | 2 | 3;
}

export default function TierBadge({ tier }: TierBadgeProps) {
  const config = getTierConfig(tier);
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold border ${config.color}`}
    >
      {config.shortLabel}
    </span>
  );
}
