/**
 * Pure geometry helpers for boundary GeoJSON.
 *
 * No React, no city-specific strings — trivially unit-testable.
 */

const EARTH_RADIUS_M = 6371000;
const WALK_PACE_KMH = 5;

function haversine(a: number[], b: number[]): number {
  const [lng1, lat1] = a;
  const [lng2, lat2] = b;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const sinLat = Math.sin(dLat / 2);
  const sinLng = Math.sin(dLng / 2);
  const h =
    sinLat * sinLat +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * sinLng * sinLng;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

function ringPerimeter(ring: number[][]): number {
  let total = 0;
  for (let i = 1; i < ring.length; i++) {
    total += haversine(ring[i - 1], ring[i]);
  }
  return total;
}

/**
 * Shoreline perimeter in metres for a Polygon or MultiPolygon boundary.
 * Uses the exterior ring (index 0) of each polygon. Returns null for any
 * other geometry type or empty coordinates.
 */
export function perimeterMeters(geometry: GeoJSON.Geometry): number | null {
  if (!geometry) return null;

  if (geometry.type === "Polygon") {
    const ring = geometry.coordinates?.[0] as number[][] | undefined;
    if (!ring || ring.length < 2) return null;
    return ringPerimeter(ring);
  }

  if (geometry.type === "MultiPolygon") {
    const polys = geometry.coordinates as number[][][][] | undefined;
    if (!polys || polys.length === 0) return null;
    let total = 0;
    let counted = 0;
    for (const poly of polys) {
      const ring = poly?.[0];
      if (ring && ring.length >= 2) {
        total += ringPerimeter(ring);
        counted++;
      }
    }
    return counted > 0 ? total : null;
  }

  return null;
}

/**
 * Format a perimeter as a walking-lap string at a 5 km/h pace, e.g.
 * "≈ 2.4 km — about a 29 min walk". Returns null for null or non-positive input.
 */
export function formatWalkLap(perimeterM: number | null): string | null {
  if (perimeterM === null || perimeterM <= 0) return null;
  const km = perimeterM / 1000;
  const walkMinutes = Math.round((km / WALK_PACE_KMH) * 60);
  return `≈ ${km.toFixed(1)} km — about a ${walkMinutes} min walk`;
}
