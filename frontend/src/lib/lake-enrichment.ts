/**
 * Utility functions for lake enrichment data (display names, tiers, zones).
 *
 * All functions accept the lake ID and fall back gracefully when
 * a lake isn't found in the enrichment map.
 */

import { LAKE_ENRICHMENT, ZONES, type LakeEnrichment, type ZoneName } from "@/data/lake-enrichment";

// Re-export for convenience
export type { LakeEnrichment, ZoneName };
export { ZONES };

/** Get the display name for a lake. Falls back to the original API name. */
export function getDisplayName(lakeId: string, originalName: string): string {
  return LAKE_ENRICHMENT[lakeId]?.displayName ?? originalName;
}

/**
 * Get all searchable names for a lake (display name + alt names + original).
 * Used to build the search index.
 */
export function getSearchableNames(lakeId: string, originalName: string): string[] {
  const enrichment = LAKE_ENRICHMENT[lakeId];
  const names = new Set<string>();

  names.add(originalName.toLowerCase());
  if (enrichment) {
    names.add(enrichment.displayName.toLowerCase());
    enrichment.altNames?.forEach((n) => names.add(n.toLowerCase()));
  }

  return Array.from(names);
}

/** Check if a search query matches any name for a lake (case-insensitive substring). */
export function matchesSearch(lakeId: string, originalName: string, query: string): boolean {
  if (!query.trim()) return false;
  const q = query.trim().toLowerCase();
  const names = getSearchableNames(lakeId, originalName);
  return names.some((name) => name.includes(q));
}

/** Get the tier for a lake. Defaults to 3 if not in enrichment data. */
export function getLakeTier(lakeId: string): 1 | 2 | 3 {
  return LAKE_ENRICHMENT[lakeId]?.tier ?? 3;
}

/** Get the zone for a lake. Returns null if not in enrichment data. */
export function getLakeZone(lakeId: string): string | null {
  return LAKE_ENRICHMENT[lakeId]?.zone ?? null;
}

/** Get alternate names for display (e.g. "Also known as" on detail page). */
export function getAltNames(lakeId: string): string[] {
  const enrichment = LAKE_ENRICHMENT[lakeId];
  if (!enrichment?.altNames?.length) return [];

  // Filter out names that match the display name (case-insensitive)
  const display = enrichment.displayName.toLowerCase();
  return enrichment.altNames.filter((n) => n.toLowerCase() !== display);
}

/** Get all unique zone names in display order. */
export function getAllZones(): readonly string[] {
  return ZONES;
}

/** Tier display configuration. */
const TIER_CONFIG = {
  1: { label: "Tier 1", shortLabel: "T1", color: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  2: { label: "Tier 2", shortLabel: "T2", color: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  3: { label: "Tier 3", shortLabel: "T3", color: "bg-white/10 text-white/50 border-white/10" },
} as const;

/** Get tier display config (label, shortLabel, color classes). */
export function getTierConfig(tier: 1 | 2 | 3) {
  return TIER_CONFIG[tier];
}

/**
 * Enrich a GeoJSON FeatureCollection with zone and tier properties.
 * Used to augment API data before passing to Mapbox.
 */
export function enrichGeoJSON(
  geojson: GeoJSON.FeatureCollection
): GeoJSON.FeatureCollection {
  return {
    ...geojson,
    features: geojson.features.map((feature) => {
      const id = (feature.properties?.id ?? feature.id) as string;
      const enrichment = LAKE_ENRICHMENT[id];
      return {
        ...feature,
        properties: {
          ...feature.properties,
          display_name: enrichment?.displayName ?? feature.properties?.name,
          zone: enrichment?.zone ?? null,
          tier: enrichment?.tier ?? 3,
        },
      };
    }),
  };
}
