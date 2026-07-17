/**
 * City identity config — single source of truth for the frontend.
 *
 * Imports `frontend/city.config.json`, a synced copy of the repo-root
 * `city.config.json` (the actual source of truth). Turbopack can't import
 * files outside the frontend root, so `scripts/sync-city-config.mjs`
 * (wired as `predev`/`prebuild`) refreshes the copy. This is the ONLY
 * module that touches the JSON, so the blast radius stays one file.
 */
import cityConfig from "../../city.config.json";

export const CITY: string = cityConfig.city;
export const BRAND: string = cityConfig.brand;
export const DOMAIN: string = cityConfig.domain;
export const ATTRIBUTION: string[] = cityConfig.attribution;
// `local_language` is being renamed from the old `language_label_field` key;
// read it tolerantly so both shapes type-check during the transition.
export const LOCAL_LANGUAGE: string | undefined = (
  cityConfig as { local_language?: string }
).local_language;

export default cityConfig;
