/** Zustand store for UI-only state. API data lives in react-query. */

import { create } from "zustand";

interface FlyToTarget {
  lng: number;
  lat: number;
  zoom: number;
}

interface UIState {
  selectedLakeId: string | null;
  activeLeaderboardTab: string;
  mobileSidebarOpen: boolean;

  /** Highlighted lake (search result selection). */
  highlightedLakeId: string | null;

  /** One-shot flyTo target consumed by MapView. */
  mapFlyTo: FlyToTarget | null;

  /** Active zone filters (empty = show all). */
  activeZones: string[];

  /** Active tier filters (empty = show all). */
  activeTiers: number[];

  setSelectedLake: (id: string | null) => void;
  setActiveTab: (tab: string) => void;
  setMobileSidebarOpen: (open: boolean) => void;
  setHighlightedLakeId: (id: string | null) => void;
  setMapFlyTo: (target: FlyToTarget | null) => void;
  toggleZone: (zone: string) => void;
  clearZones: () => void;
  toggleTier: (tier: number) => void;
  clearTiers: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  selectedLakeId: null,
  activeLeaderboardTab: "shrinking",
  mobileSidebarOpen: false,
  highlightedLakeId: null,
  mapFlyTo: null,
  activeZones: [],
  activeTiers: [],

  setSelectedLake: (id) => set({ selectedLakeId: id }),
  setActiveTab: (tab) => set({ activeLeaderboardTab: tab }),
  setMobileSidebarOpen: (open) => set({ mobileSidebarOpen: open }),
  setHighlightedLakeId: (id) => set({ highlightedLakeId: id }),
  setMapFlyTo: (target) => set({ mapFlyTo: target }),

  toggleZone: (zone) =>
    set((s) => ({
      activeZones: s.activeZones.includes(zone)
        ? s.activeZones.filter((z) => z !== zone)
        : [...s.activeZones, zone],
    })),
  clearZones: () => set({ activeZones: [] }),

  toggleTier: (tier) =>
    set((s) => ({
      activeTiers: s.activeTiers.includes(tier)
        ? s.activeTiers.filter((t) => t !== tier)
        : [...s.activeTiers, tier],
    })),
  clearTiers: () => set({ activeTiers: [] }),
}));
