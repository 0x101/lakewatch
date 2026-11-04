# LakeWatch

**Track your city's lakes from space.**

LakeWatch turns free Sentinel-2 satellite imagery into a public dashboard of
lake health. For every lake in a city it estimates water surface area and an
algae fraction every few days, scores each lake, and renders a timelapse of how
the lake has changed since 2015. Fork it, drop in your city's lake boundaries
and a `city.config.json`, and run.

It's a kit, not a service: a Python pipeline (Google Earth Engine), a FastAPI
backend, and a Next.js map dashboard you host yourself.

The reference deployment is [Bangalore Lake Watch](https://nammalakes.com),
which tracks ~170 lakes across Bengaluru.

---

## What you get

- **Map dashboard** — every lake as a polygon, colored by health score, on a
  pannable Mapbox map.
- **Health scores & rankings** — per-lake scores plus leaderboards (most
  shrunk, most recovered, most polluted, most volatile).
- **Timelapses** — per-lake GIF/MP4 of the lake's water and algae over the full
  Sentinel-2 archive (2015→now), with optional background music.
- **Pulse page** — recent movers and shareable, social-ready cards.
- **Time-series charts** — water area and algae over time per lake.

---

## How it works

Everything runs server-side on Google Earth Engine, so you never download raw
imagery — only the computed numbers come back.

1. **Imagery.** For each lake boundary, query the Sentinel-2 L2A archive
   (`COPERNICUS/S2_SR_HARMONIZED`) over a date window.
2. **Cloud-aware selection.** Cloudiness is judged *over the lake itself*, not
   over the whole Sentinel-2 tile. A scene with a clear lake but clouds in the
   tile corner is still usable; a scene with clouds parked over the water is
   not. This matters most in the monsoon, when tile-level cloud filtering would
   throw away almost everything.
3. **Water classification.** Compute NDWI (Normalized Difference Water Index)
   per pixel, then pick a water/non-water threshold with Otsu's method rather
   than a fixed cutoff, so the boundary adapts to each scene. Count water
   pixels × pixel area → water surface area.
4. **Algae estimate.** Within the water mask, compute NDVI; the fraction of
   water pixels showing vegetation-like signal is the algae fraction — a proxy
   for blooms and weed cover.
5. **Health score.** Combine water-area trend, algae fraction, and seasonal
   volatility into a 0–100 score.
6. **Timelapse.** Render one frame per usable observation, label it with the
   date, and assemble frames into a GIF/MP4.

### Caveats (read these)

- **10 m resolution.** Sentinel-2 pixels are 10 m. Lakes much below ~0.5 ha
  are unreliable — a handful of pixels can't measure area well.
- **These are estimates.** NDWI and NDVI are proxies, not ground truth. Label
  everything as *satellite-derived estimates*. Pair with local lab/field data
  if you have it (see the extension pattern below).
- **Monsoon gaps.** June–September can be sparse even with lake-level cloud
  filtering. Expect fewer observations in the wet season.

---

## Quickstart

Prereqs: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20.9+, Docker
(or any PostgreSQL 14+), a [Mapbox token](https://account.mapbox.com), and a
Google Earth Engine service account. Optional system tools for timelapses:
`ffmpeg` (MP4) and `gifsicle` (smaller GIFs) — without them the pipeline still
runs and just skips/doesn't optimise those outputs.

All commands below are run **from the repo root** unless a `cd` says otherwise.
Each block is self-contained.

```bash
git clone <your-fork-url> lakewatch && cd lakewatch
cp .env.example .env          # one .env for pipeline, backend AND frontend
```

**1. Google Earth Engine.** Sign up at
[earthengine.google.com](https://earthengine.google.com/), create a Cloud
project, and create a service account with a JSON key. Put the key path in
`GEE_SERVICE_ACCOUNT_KEY` and the project id in `GEE_PROJECT_ID`. Full steps in
[`docs/SETUP.md`](docs/SETUP.md).

```bash
cd pipeline && uv sync && uv run python -m pipeline.scripts.verify_gee
```

**2. Database + schema.** Set
`DATABASE_URL=postgresql://lakewatch:lakewatch@localhost:5433/lakewatch` in
`.env` if you use the bundled Docker database.

```bash
docker compose up -d db
cd pipeline && uv run python -m pipeline.scripts.init_db
```

**3. Load your lakes.** A GeoJSON FeatureCollection of lake boundaries (a 3-lake
Bengaluru sample ships in `examples/`):

```bash
cd pipeline && uv run python -m pipeline.scripts.load_lakes ../examples/sample-lakes.geojson
```

**4. Backfill satellite observations** (2015 → today; resumable):

```bash
cd pipeline && uv run python -m pipeline.scripts.run_pipeline --lake ulsoor-lake   # one lake
cd pipeline && uv run python -m pipeline.scripts.full_backfill                     # every lake
```

**5. Run the API + dashboard** (two terminals):

```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload    # http://localhost:8000/docs
```

```bash
cd frontend && npm ci && npm run dev                              # http://localhost:3000
```

Open http://localhost:3000.

**Running the tests** (no credentials needed — Earth Engine and the DB are
mocked):

```bash
cd pipeline && uv sync --extra dev && uv run pytest
cd backend && uv sync --extra dev && uv run pytest
```

---

## Fork it for your city

1. **`city.config.json`** (repo root) — set `city`, `brand`, `domain`, map
   `center`/`zoom`, `local_language`, attribution, and the "relatable units"
   used to make areas legible (football fields, parks, etc.). All site
   branding and copy reads from this file. Edit the root file only: the
   frontend's copy (`frontend/city.config.json`) is refreshed automatically by
   `npm run dev` / `npm run build` (via `frontend/scripts/sync-city-config.mjs`
   — Turbopack can't import outside the frontend root, so it's a synced copy,
   not a symlink).
2. **Lake boundaries** — replace `examples/sample-lakes.geojson` with your
   city's lakes (a GeoJSON FeatureCollection; only `name` is required per
   feature). See `pipeline/scripts/load_lakes.py` for the exact format.
3. **Optional enrichment** — `frontend/src/data/lake-enrichment.ts` lets you map
   lake ids to nicer display names, alt/search names, size tiers, and map
   zones. Empty by default; everything falls back gracefully.
4. **Secrets** — set `DATABASE_URL`, `GEE_PROJECT_ID`, and
   `GEE_SERVICE_ACCOUNT_KEY_JSON` as GitHub Actions repo secrets. The included
   workflow (`.github/workflows/ingest.yml`) runs a 5-day incremental ingestion
   on cron, so the dashboard stays current automatically. Until those secrets
   exist it skips with a notice instead of failing. (GitHub disables scheduled
   workflows on new forks — enable them under the fork's **Actions** tab.)
5. **CI** — `.github/workflows/ci.yml` lints, tests and builds everything on
   each push/PR and needs no secrets, so it works on a fresh fork.

Detailed deploy steps (Railway for the backend + DB, Vercel for the frontend,
R2 for timelapse assets) are in [`docs/SETUP.md`](docs/SETUP.md).

---

## Extension pattern (your city's own data)

Satellite estimates are only half the story. Most cities also have local
data — water-board lab measurements, field surveys, drainage/stream networks.
LakeWatch lets you mount that data through named seams **without forking the
core**, so you can still pull upstream updates cleanly:

- **`pipeline/db/models_ext.py`** — define extra ORM tables here. The shared
  `models.py` imports it through a `try/except` and exposes
  `HAS_CITY_EXTENSIONS`, so shared queries branch on its presence.
- **`backend/app/extensions.py`** — `register_extensions(app)` mounts your
  city-specific routers. No-op upstream; `main.py` calls it by name and never
  imports your routers directly.
- **`frontend/src/lib/api-ext.ts`** — fetchers for your endpoints. No-op
  upstream (returns empty data), so shared hooks degrade to "no city data".
- **`frontend/src/components/extensions/index.tsx`** — UI slots
  (`LakeDetailExtensions`, `LakeDataExtensions`, `OverviewExtensions`,
  `InsightsExtensions`) rendered by the shared lake-detail and overview
  pages. No-op upstream.

The reference implementation is **Bangalore Lake Watch**
([nammalakes.com](https://nammalakes.com)), which mounts water-quality lab data,
field-survey ground truth, and the storm-drain stream network through these
exact seams.

---

## Data attribution

If you publish a LakeWatch deployment, you **must** attribute the imagery:

> Contains modified Copernicus Sentinel-2 data, processed via Google Earth
> Engine. © European Space Agency (ESA).

And be clear that the numbers are **satellite-derived estimates**, not ground
truth. The default `city.config.json` carries the attribution strings; keep
them (and add any required attribution for your lake-boundary source).

---

## License

MIT — see [`LICENSE`](LICENSE).
