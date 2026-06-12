/** Map and UI constants. Map center/zoom come from city.config.json. */

import cityConfig from "./city.config";

export const MAP_CENTER = {
  longitude: cityConfig.center.lng,
  latitude: cityConfig.center.lat,
};
export const DEFAULT_ZOOM = cityConfig.zoom;
export const MIN_ZOOM = 9;
export const MAX_ZOOM = 16;

export const MAP_STYLE = "mapbox://styles/mapbox/dark-v11";
export const MAP_STYLE_LIGHT = "mapbox://styles/mapbox/light-v11";

export const LEADERBOARD_CATEGORIES = [
  { key: "shrinking", label: "Most Shrunk", emoji: "📉" },
  { key: "recovering", label: "Most Recovered", emoji: "📈" },
  { key: "polluted", label: "Most Polluted", emoji: "🟢" },
  { key: "volatile", label: "Most Volatile", emoji: "🎢" },
] as const;

/**
 * Colorblind-safe health score palette.
 * Teal replaces green so red/healthy are distinguishable for deuteranopia/protanopia.
 * Each stop has distinct luminance to work in grayscale.
 */
export const HEALTH_SCALE = [
  { stop: 0, color: "#c62828", label: "Critical" },
  { stop: 30, color: "#ef6c00", label: "Poor" },
  { stop: 60, color: "#f9a825", label: "Fair" },
  { stop: 100, color: "#00897b", label: "Healthy" },
] as const;

/** Get the health color for a given score (categorical). */
export function getHealthColor(score: number | null): string {
  if (score === null) return "#6b7280";
  if (score < 30) return HEALTH_SCALE[0].color;
  if (score < 60) return HEALTH_SCALE[1].color;
  if (score < 80) return HEALTH_SCALE[2].color;
  return HEALTH_SCALE[3].color;
}

/** Get the health label for a given score. */
export function getHealthLabel(score: number): string {
  if (score < 30) return "Critical";
  if (score < 60) return "Poor";
  if (score < 80) return "Fair";
  return "Healthy";
}
