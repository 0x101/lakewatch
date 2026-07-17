/**
 * Syncs the repo-root `city.config.json` (source of truth) over the
 * frontend-local copy at `frontend/city.config.json`.
 *
 * Turbopack can't import files outside the frontend root, so the frontend
 * keeps its own copy; this script (wired as `predev`/`prebuild`) refreshes it.
 */
import { copyFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "..", "..", "city.config.json");
const target = join(here, "..", "city.config.json");

copyFileSync(source, target);
console.log(`[sync-city-config] copied ${source} -> ${target}`);
