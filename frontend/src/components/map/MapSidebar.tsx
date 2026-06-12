"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useLakes } from "@/hooks/useLakes";
import { getHealthColor } from "@/lib/constants";
import { useUIStore } from "@/lib/store";
import { ThemeToggle } from "../ui/ThemeToggle";
import TierBadge from "../ui/TierBadge";
import { getDisplayName, getLakeTier, getLakeZone, getAllZones } from "@/lib/lake-enrichment";

// ---------------------------------------------------------------------------
// Zone / Tier filter chips
// ---------------------------------------------------------------------------

function ZoneChips() {
  const activeZones = useUIStore((s) => s.activeZones);
  const toggleZone = useUIStore((s) => s.toggleZone);
  const clearZones = useUIStore((s) => s.clearZones);
  const zones = getAllZones();
  const allSelected = activeZones.length === 0;

  return (
    <div className="flex flex-wrap gap-1.5 mb-3">
      <button
        onClick={clearZones}
        className={`px-2.5 py-1 rounded-full text-[10px] font-medium border transition-colors ${
          allSelected
            ? "bg-white/15 text-white border-white/20"
            : "bg-white/5 text-white/40 border-white/5 hover:bg-white/10"
        }`}
      >
        All
      </button>
      {zones.map((zone) => {
        const active = activeZones.includes(zone);
        return (
          <button
            key={zone}
            onClick={() => toggleZone(zone)}
            className={`px-2.5 py-1 rounded-full text-[10px] font-medium border transition-colors ${
              active
                ? "bg-blue-500/20 text-blue-300 border-blue-500/30"
                : "bg-white/5 text-white/40 border-white/5 hover:bg-white/10"
            }`}
          >
            {zone}
          </button>
        );
      })}
    </div>
  );
}

function TierChips() {
  const activeTiers = useUIStore((s) => s.activeTiers);
  const toggleTier = useUIStore((s) => s.toggleTier);
  const tiers = [1, 2, 3] as const;

  return (
    <div className="flex gap-1.5 mb-3">
      {tiers.map((tier) => {
        const active = activeTiers.includes(tier);
        const colors =
          tier === 1
            ? active
              ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
              : "bg-white/5 text-white/40 border-white/5 hover:bg-white/10"
            : tier === 2
              ? active
                ? "bg-blue-500/20 text-blue-300 border-blue-500/30"
                : "bg-white/5 text-white/40 border-white/5 hover:bg-white/10"
              : active
                ? "bg-white/15 text-white/60 border-white/20"
                : "bg-white/5 text-white/40 border-white/5 hover:bg-white/10";
        return (
          <button
            key={tier}
            onClick={() => toggleTier(tier)}
            className={`px-2.5 py-1 rounded-full text-[10px] font-medium border transition-colors ${colors}`}
          >
            Tier {tier}
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lake list item
// ---------------------------------------------------------------------------

function LakeRow({
  lake,
  index,
  onClick,
}: {
  lake: { id: string; name: string; health_score: number | null };
  index: number;
  onClick?: () => void;
}) {
  const displayName = getDisplayName(lake.id, lake.name);
  const tier = getLakeTier(lake.id);
  return (
    <Link
      href={`/lakes/${lake.id}`}
      onClick={onClick}
      className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors group"
    >
      <span className="text-[10px] font-mono text-white/20 w-4 text-right">
        {index + 1}
      </span>
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ backgroundColor: getHealthColor(lake.health_score) }}
      />
      <span className="text-xs text-white/70 group-hover:text-white truncate flex-1">
        {displayName}
      </span>
      <TierBadge tier={tier} />
      <span
        className="text-[10px] font-mono"
        style={{ color: getHealthColor(lake.health_score) }}
      >
        {lake.health_score !== null ? Math.round(lake.health_score) : "--"}
      </span>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Main Sidebar
// ---------------------------------------------------------------------------

export function MapSidebar() {
  const isOpen = useUIStore((s) => s.mobileSidebarOpen);
  const setIsOpen = useUIStore((s) => s.setMobileSidebarOpen);
  const activeZones = useUIStore((s) => s.activeZones);
  const activeTiers = useUIStore((s) => s.activeTiers);
  const { data: lakesData } = useLakes();

  const allLakes = lakesData?.lakes ?? [];
  const withData = allLakes.filter((l) => l.observation_count > 0);
  const healthyCount = withData.filter(
    (l) => (l.health_score ?? 0) >= 60
  ).length;
  const distressedCount = withData.filter(
    (l) => l.health_score !== null && l.health_score < 30
  ).length;

  // Filter lakes by active zones and tiers
  const filteredLakes = useMemo(() => {
    let lakes = withData.filter((l) => l.health_score !== null);

    if (activeZones.length > 0) {
      lakes = lakes.filter((l) => {
        const zone = getLakeZone(l.id);
        return zone !== null && activeZones.includes(zone);
      });
    }

    if (activeTiers.length > 0) {
      lakes = lakes.filter((l) => activeTiers.includes(getLakeTier(l.id)));
    }

    return lakes.sort((a, b) => (a.health_score ?? 0) - (b.health_score ?? 0));
  }, [withData, activeZones, activeTiers]);

  const listLabel =
    activeZones.length > 0 || activeTiers.length > 0
      ? "Filtered lakes"
      : "Most distressed";

  return (
    <>
      {/* Mobile peek bar — always visible, tap to expand */}
      <div
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-gray-900/95 backdrop-blur-md text-white rounded-t-xl shadow-lg border-t border-white/10"
      >
        {/* Drag handle + summary — always shown */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full px-4 pt-3 pb-2"
        >
          <div className="w-10 h-1 bg-white/20 rounded-full mx-auto mb-3" />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo-icon.svg" alt="" className="w-6 h-6" />
              <span className="text-sm font-semibold">Namma Lakes</span>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="font-bold text-white">{withData.length}</span>
              <span className="font-bold text-green-400">{healthyCount} <span className="text-white/30 font-normal">ok</span></span>
              <span className="font-bold text-red-400">{distressedCount} <span className="text-white/30 font-normal">bad</span></span>
              <svg
                className={`w-4 h-4 text-white/40 transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
              </svg>
            </div>
          </div>
        </button>

        {/* Expandable content */}
        <div
          className={`overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? "max-h-[50vh] opacity-100" : "max-h-0 opacity-0"}`}
        >
          <div className="px-4 pb-4 overflow-y-auto max-h-[50vh]">
            {/* Zone chips */}
            <ZoneChips />

            {/* Tier chips */}
            <TierChips />

            {/* Lake list */}
            <p className="text-[10px] text-white/30 uppercase tracking-wider mb-2 px-1">
              {listLabel}
            </p>
            <div className="space-y-0.5 mb-3">
              {filteredLakes.slice(0, 10).map((lake, i) => (
                <LakeRow
                  key={lake.id}
                  lake={lake}
                  index={i}
                  onClick={() => setIsOpen(false)}
                />
              ))}
              {filteredLakes.length === 0 && (
                <p className="text-xs text-white/20 px-2 py-3 text-center">
                  No lakes match filters
                </p>
              )}
            </div>

            {/* Nav */}
            <div className="border-t border-white/5 pt-2 space-y-0.5">
              <Link href="/pulse" onClick={() => setIsOpen(false)} className="block px-3 py-1.5 text-sm font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                Pulse
              </Link>
              <Link href="/overview" onClick={() => setIsOpen(false)} className="block px-3 py-1.5 text-sm font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                City Overview
              </Link>
              <Link href="/rankings" onClick={() => setIsOpen(false)} className="block px-3 py-1.5 text-sm font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                Rankings
              </Link>
              <Link href="/lakes" onClick={() => setIsOpen(false)} className="block px-3 py-1.5 text-sm font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                All Lakes
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div
        className="hidden md:block fixed z-40 top-0 left-0 w-80 h-full bg-gray-900/95 backdrop-blur-md text-white overflow-y-auto rounded-r-xl"
      >
        <div className="p-4 flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo-icon.svg" alt="" className="w-8 h-8" />
              <div>
                <h1 className="text-base font-bold tracking-tight leading-tight">
                  Namma Lakes
                </h1>
                <p className="text-[9px] text-white/30">
                  Satellite-powered civic data
                </p>
              </div>
            </div>
            <ThemeToggle />
          </div>

          {/* Quick stats */}
          <div className="flex items-center gap-3 mb-4 px-1">
            <div className="text-center">
              <p className="text-2xl font-bold text-white">
                {withData.length}
              </p>
              <p className="text-[9px] text-white/30 uppercase tracking-wider">
                lakes
              </p>
            </div>
            <div className="w-px h-8 bg-white/10" />
            <div className="text-center">
              <p className="text-2xl font-bold text-green-400">
                {healthyCount}
              </p>
              <p className="text-[9px] text-white/30 uppercase tracking-wider">
                healthy
              </p>
            </div>
            <div className="w-px h-8 bg-white/10" />
            <div className="text-center">
              <p className="text-2xl font-bold text-red-400">
                {distressedCount}
              </p>
              <p className="text-[9px] text-white/30 uppercase tracking-wider">
                distressed
              </p>
            </div>
          </div>

          {/* Zone filter chips */}
          <p className="text-[10px] text-white/30 uppercase tracking-wider mb-2 px-1">
            Zones
          </p>
          <ZoneChips />

          {/* Tier filter chips */}
          <p className="text-[10px] text-white/30 uppercase tracking-wider mb-2 px-1">
            Tiers
          </p>
          <TierChips />

          {/* Lake list */}
          <div className="flex-1 overflow-y-auto mb-3">
            <p className="text-[10px] text-white/30 uppercase tracking-wider mb-2 px-1">
              {listLabel}
            </p>
            <div className="space-y-0.5">
              {filteredLakes.slice(0, 20).map((lake, i) => (
                <LakeRow key={lake.id} lake={lake} index={i} />
              ))}
              {filteredLakes.length === 0 && (
                <p className="text-xs text-white/20 px-2 py-3 text-center">
                  No lakes match filters
                </p>
              )}
            </div>
          </div>

          {/* Nav */}
          <div className="border-t border-white/5 pt-3 space-y-1">
            <Link href="/pulse" className="block px-3 py-2 text-sm font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Pulse
            </Link>
            <Link href="/overview" className="block px-3 py-2 text-sm font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              City Overview
            </Link>
            <Link href="/rankings" className="block px-3 py-2 text-sm font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Rankings
            </Link>
            <Link href="/lakes" className="block px-3 py-2 text-sm font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              All Lakes
            </Link>
            <Link href="/about" className="block px-3 py-2 text-xs text-white/40 hover:text-white/60 hover:bg-white/5 rounded-lg transition-colors">
              About
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
