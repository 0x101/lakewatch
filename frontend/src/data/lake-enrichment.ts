/**
 * Static enrichment data for your city's lakes.
 *
 * Maps lake IDs (the slug derived from each lake's name when loaded) to a
 * friendlier display name, alternate/search names, a size tier, and a
 * geographic zone. This is OPTIONAL polish — every lookup falls back
 * gracefully, so the dashboard works with an empty map:
 *
 *   - displayName  -> falls back to the lake's API name
 *   - altNames     -> only used to widen search; safe to omit
 *   - tier         -> defaults to 3 (smallest) when absent
 *   - zone         -> defaults to null (no zone filter) when absent
 *
 * To enrich your city, add entries keyed by lake ID, e.g.:
 *
 *   export const LAKE_ENRICHMENT: Record<string, LakeEnrichment> = {
 *     "ulsoor-lake": {
 *       displayName: "Ulsoor Lake",
 *       altNames: ["Halasuru Lake"],
 *       tier: 1,
 *       zone: "Central",
 *     },
 *   };
 *
 * And edit ZONES below to your city's regions (used by the map zone filter).
 *
 * Reference implementation: Bangalore Lake Watch (nammalakes.com) ships a
 * full enrichment map of ~170 lakes with local names, tiers, and zones.
 */

export interface LakeEnrichment {
  displayName: string;
  altNames?: string[];
  tier: 1 | 2 | 3;
  zone: string;
}

/**
 * Zone names in display order — used by the map's zone filter.
 * Generic compass regions by default; rename to your city's nomenclature.
 */
export const ZONES = [
  "Central",
  "North",
  "East",
  "South",
  "West",
] as const;

export type ZoneName = (typeof ZONES)[number];

/**
 * Enrichment data keyed by lake ID (the slug of the lake name).
 *
 * Empty by default. If a lake ID from the API is not found here, the utility
 * functions fall back to the original API name, tier 3, and no zone.
 */
export const LAKE_ENRICHMENT: Record<string, LakeEnrichment> = {};
