/**
 * Syncs the repo-root `city.config.json` (source of truth) over the
 * frontend-local copy at `frontend/city.config.json`.
 *
 * Turbopack can't import files outside the frontend root, so the frontend
 * keeps its own copy; this script (wired as `predev`/`prebuild`) refreshes it.
 */
import { copyFileSync, existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "..", "..", "city.config.json");
const target = join(here, "..", "city.config.json");

if (!existsSync(source)) {
  // e.g. a deploy that only uploads frontend/: keep the committed copy.
  if (!existsSync(target)) {
    console.error(`[sync-city-config] neither ${source} nor ${target} exists`);
    process.exit(1);
  }
  console.warn(`[sync-city-config] ${source} not found; using existing ${target}`);
  process.exit(0);
}

// Fail fast with a readable message instead of a cryptic Turbopack JSON error.
try {
  JSON.parse(readFileSync(source, "utf8"));
} catch (err) {
  console.error(`[sync-city-config] ${source} is not valid JSON: ${err.message}`);
  process.exit(1);
}

copyFileSync(source, target);
console.log(`[sync-city-config] copied ${source} -> ${target}`);
