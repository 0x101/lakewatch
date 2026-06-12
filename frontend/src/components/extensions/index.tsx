/**
 * Frontend extension slots — your city's lake-detail UI mounts here.
 *
 * Shared consumers (LakeDetailClient, InsightsClient) render these named
 * slots without importing any city-specific component, hook, or markup
 * directly. That keeps the shared files identical to upstream LakeWatch, so
 * pulling new releases stays conflict-free.
 *
 * In the upstream build every slot renders null. To add your city's data:
 *   1. Build components + hooks for your data (see api-ext.ts for the
 *      fetcher seam, and pipeline/db/models_ext.py for the ORM seam).
 *   2. Render them from the matching slot below, keeping the export name
 *      and props signature unchanged.
 *
 * Reference implementation: Bangalore Lake Watch (nammalakes.com) renders
 * water-quality lab data, field-survey ground truth, and stream-connection
 * cards through these slots.
 */
"use client";

/**
 * Lake-detail overview-tab extensions (e.g. ground-truth / lab-data cards).
 * No-op upstream.
 */
export function LakeDetailExtensions({ lakeId }: { lakeId: string }) {
  void lakeId;
  return null;
}

/** Lake-detail data-tab extensions (e.g. raw measurement tables). No-op upstream. */
export function LakeDataExtensions({ lakeId }: { lakeId: string }) {
  void lakeId;
  return null;
}

/** Insights-page extension seam. No-op upstream. */
export function InsightsExtensions() {
  return null;
}
