"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useLakes } from "@/hooks/useLakes";
import { getHealthColor } from "@/lib/constants";
import { getDisplayName, matchesSearch, getLakeZone } from "@/lib/lake-enrichment";
import { useUIStore } from "@/lib/store";

/**
 * Persistent search bar fixed at the top of the map view.
 * Always visible regardless of bottom sheet / sidebar scroll state.
 * On result select: pans/zooms the map and highlights the lake.
 */
export function MapSearchBar() {
  const [query, setQuery] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const { data: lakesData } = useLakes();

  const setHighlightedLakeId = useUIStore((s) => s.setHighlightedLakeId);
  const setMapFlyTo = useUIStore((s) => s.setMapFlyTo);
  const setMobileSidebarOpen = useUIStore((s) => s.setMobileSidebarOpen);

  const allLakes = useMemo(() => lakesData?.lakes ?? [], [lakesData]);

  const searchResults = useMemo(() => {
    if (!query.trim()) return [];
    return allLakes
      .filter((l) => matchesSearch(l.id, l.name, query))
      .slice(0, 8);
  }, [query, allLakes]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function selectLake(lake: (typeof allLakes)[0]) {
    setQuery("");
    setShowDropdown(false);
    setMobileSidebarOpen(false);
    setHighlightedLakeId(lake.id);
    setMapFlyTo({ lng: lake.longitude, lat: lake.latitude, zoom: 14 });
  }

  return (
    <div
      ref={searchRef}
      className="fixed top-0 left-0 right-12 z-30 md:left-80"
      style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}
    >
      <div className="px-3 pt-3 pb-1">
        <div className="relative">
          <div className="relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setShowDropdown(true);
              }}
              onFocus={() => query.trim() && setShowDropdown(true)}
              placeholder="Search lakes..."
              className="w-full bg-gray-900/80 backdrop-blur-md border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 outline-none focus:border-white/20 shadow-lg"
            />
            {query && (
              <button
                onClick={() => {
                  setQuery("");
                  setShowDropdown(false);
                  setHighlightedLakeId(null);
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Results dropdown */}
          {showDropdown && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900/95 backdrop-blur-md border border-white/10 rounded-xl overflow-hidden z-50 shadow-xl">
              {searchResults.map((lake) => {
                const displayName = getDisplayName(lake.id, lake.name);
                const zone = getLakeZone(lake.id);
                return (
                  <button
                    key={lake.id}
                    onClick={() => selectLake(lake)}
                    className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-white/10 transition-colors"
                  >
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{
                        backgroundColor: getHealthColor(lake.health_score),
                      }}
                    />
                    <span className="text-sm text-white/80 truncate flex-1">
                      {displayName}
                    </span>
                    {zone && (
                      <span className="text-[10px] text-white/25 hidden sm:inline">
                        {zone}
                      </span>
                    )}
                    {lake.health_score !== null && (
                      <span className="text-[10px] text-white/40 font-mono w-5 text-right">
                        {Math.round(lake.health_score)}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* No results */}
          {showDropdown && query.trim() && searchResults.length === 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900/95 backdrop-blur-md border border-white/10 rounded-xl p-3 z-50 shadow-xl">
              <p className="text-xs text-white/30 text-center">No lakes found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
