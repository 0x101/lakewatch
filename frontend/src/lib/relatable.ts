/**
 * Relatable-units formatter.
 *
 * Turns a raw area in square metres into a human-scale comparison like
 * "≈ 87 ⚽ football fields". The comparison set is config-driven — all
 * city-specific flavor lives in city.config.json, never here.
 */
import cityConfig from "./city.config";

interface RelatableUnit {
  id: string;
  label: string;
  area_m2: number;
  emoji: string;
}

const MAX_QUOTIENT = 500;

/**
 * Format an absolute area as a relatable equivalent, picking the smallest
 * configured unit whose quotient is at most ~500 (falling back to the largest
 * unit if every quotient is bigger). Returns null when no sensible comparison
 * exists — empty config, zero/NaN input, or a rounded count below 1.
 */
export function formatRelatableArea(areaM2: number): string | null {
  if (!Number.isFinite(areaM2) || areaM2 === 0) return null;

  const units = (cityConfig as { relatable_units?: RelatableUnit[] }).relatable_units;
  if (!Array.isArray(units) || units.length === 0) return null;

  const abs = Math.abs(areaM2);
  const sorted = [...units].sort((a, b) => a.area_m2 - b.area_m2);

  let chosen = sorted.find((u) => abs / u.area_m2 <= MAX_QUOTIENT);
  if (!chosen) chosen = sorted[sorted.length - 1];

  const quotient = abs / chosen.area_m2;
  if (Math.round(quotient) < 1) return null;

  return `≈ ${Math.round(quotient).toLocaleString()} ${chosen.emoji} ${chosen.label}`;
}

/**
 * Format an area in square metres as a signed hectare string, e.g.
 * "+4.2 ha" or "-1.1 ha". Non-negative values get a leading "+".
 */
export function formatSignedHa(areaM2: number): string {
  const ha = areaM2 / 10000;
  const sign = ha >= 0 ? "+" : "";
  return `${sign}${ha.toFixed(1)} ha`;
}
