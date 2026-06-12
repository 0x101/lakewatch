"use client";

import { LEADERBOARD_CATEGORIES } from "@/lib/constants";

interface LeaderboardTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function LeaderboardTabs({
  activeTab,
  onTabChange,
}: LeaderboardTabsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {LEADERBOARD_CATEGORIES.map((cat) => {
        const isActive = activeTab === cat.key;
        return (
          <button
            key={cat.key}
            onClick={() => onTabChange(cat.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
            }`}
          >
            {cat.emoji} {cat.label}
          </button>
        );
      })}
    </div>
  );
}
