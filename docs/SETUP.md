# LakeWatch — Setup & Deploy

This is the long-form guide. For the 5-minute version see the Quickstart in the
[README](../README.md).

Contents:
1. [Prerequisites](#1-prerequisites)
2. [Google Earth Engine service account](#2-google-earth-engine-service-account)
3. [Database & schema](#3-database--schema)
4. [Load your lakes](#4-load-your-lakes)
5. [Backfill satellite observations](#5-backfill-satellite-observations)
6. [Run locally](#6-run-locally)
7. [Configure for your city](#7-configure-for-your-city)
8. [Deploy: backend on Railway](#8-deploy-backend-on-railway)
9. [Deploy: frontend on Vercel](#9-deploy-frontend-on-vercel)
10. [Timelapse assets on Cloudflare R2 (optional)](#10-timelapse-assets-on-cloudflare-r2-optional)
11. [Scheduled ingestion (GitHub Actions)](#11-scheduled-ingestion-github-actions)
12. [Environment variables reference](#12-environment-variables-reference)

---

## 1. Prerequisites

- **Python 3.12+** and [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node 20+** and npm
- **PostgreSQL 14+** (local via Docker, or hosted). No PostGIS required —
  boundaries are stored as GeoJSON text.
- A **Mapbox** account (free tier: 50K map loads/month).
- A **Google Earth Engine** account (free for non-commercial use).
- Optional: **ffmpeg** on your PATH if you want MP4 timelapses with audio.

Copy the env template and fill it in as you go:

```bash
cp .env.example .env
```

---

## 2. Google Earth Engine service account

The pipeline authenticates to Earth Engine headlessly with a service account —
no browser popups, works in CI.

1. **Sign up for Earth Engine**: https://earthengine.google.com/ → "Get
   started". Register a Google Cloud project when prompted (or create one at
   https://console.cloud.google.com/).
2. **Enable the API**: in the Cloud console, enable **Earth Engine API** for
   your project.
3. **Create a service account**: Cloud console → IAM & Admin → Service
   Accounts → Create. Give it the **Earth Engine Resource Viewer** role (and
   Writer if you'll export assets).
4. **Register the service account with Earth Engine**: at
   https://code.earthengine.google.com/ (or via the EE registration page),
   register the service account email so it can call EE.
5. **Create a JSON key**: on the service account → Keys → Add key → JSON.
   Download it and store it **outside the repo** (or at a path that's
   gitignored). Never commit it.
6. **Point the env at it**:

   ```bash
   GEE_PROJECT_ID=your-gee-project
   GEE_SERVICE_ACCOUNT_KEY=/absolute/path/to/your-key.json
   ```

7. **Verify**:

   ```bash
   cd pipeline && uv sync
   uv run python -m pipeline.scripts.verify_gee
   ```

   You should see an image id, a band list, and a date. If it errors, re-check
   that the EE API is enabled and the service account is registered with EE.

---

## 3. Database & schema

**Option A — local Postgres via Docker** (fastest):

```bash
docker compose up -d db
# DATABASE_URL=postgresql://lakewatch:lakewatch@localhost:5433/lakewatch
```

**Option B — any hosted Postgres**: set `DATABASE_URL` to its connection
string.

Create the schema (idempotent — safe to re-run):

```bash
cd pipeline && uv run python -m pipeline.scripts.init_db
```

This runs `Base.metadata.create_all`, creating: `lakes`, `observations`,
`lake_stats`, `timelapse_frames`, `timelapse_assets` (plus any extension tables
you add in `pipeline/db/models_ext.py`). We ship plain `create_all` instead of
migrations on purpose — the schema is small and stable, and a fork's first run
should be one command. If your schema starts evolving, add Alembic at that
point.

---

## 4. Load your lakes

Lake boundaries are a GeoJSON **FeatureCollection**. Each feature needs a
Polygon (or MultiPolygon) geometry in lon/lat and a `name` property; everything
else is optional:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Ulsoor Lake",
        "id": "ulsoor-lake",
        "ward": "...",
        "custodian": "...",
        "area_hectares": 50
      },
      "geometry": { "type": "Polygon", "coordinates": [[[lon, lat], ...]] }
    }
  ]
}
```

If `id` is omitted it's derived from `name` (slugified). If `latitude`/
`longitude` are omitted they're computed from the polygon centroid.

A 3-lake Bengaluru sample ships in `examples/sample-lakes.geojson`:

```bash
cd pipeline
uv run python -m pipeline.scripts.load_lakes ../examples/sample-lakes.geojson
# preview without writing:
uv run python -m pipeline.scripts.load_lakes ../examples/sample-lakes.geojson --dry-run
```

Where to get boundaries for your city: OpenStreetMap (water polygons), your
city's open-data portal, or a government GIS layer. Convert to GeoJSON with
[`ogr2ogr`](https://gdal.org/) or QGIS.

---

## 5. Backfill satellite observations

Single lake (good for a first run):

```bash
cd pipeline
uv run python -m pipeline.scripts.run_pipeline --lake ulsoor-lake \
  --start-year 2015 --end-year 2026
```

All loaded lakes:

```bash
uv run python -m pipeline.scripts.full_backfill
```

The backfill checkpoints its progress, so it's resumable if interrupted. After
a backfill, per-lake stats (health score, trends) are refreshed automatically.

> **Free-tier note.** Earth Engine's free tier is generous but rate-limited.
> Large cities × the full archive can take a while; backfills are chunked by
> year and resumable for this reason.

---

## 6. Run locally

```bash
# backend
cd backend && uv sync
uv run uvicorn app.main:app --reload          # http://localhost:8000  (/docs for API)

# frontend (new terminal)
cd frontend && npm install
npm run dev                                    # http://localhost:3000
```

The frontend proxies `/api/*`, `/frames/*`, and `/assets/*` to `BACKEND_URL`
(default `http://localhost:8000`) via `next.config.ts`, so no CORS setup is
needed in dev.

---

## 7. Configure for your city

Edit **`city.config.json`** at the repo root. It's the single source of truth
for site identity — every brand string, page title, share text, OG image, and
footer attribution in the frontend reads from it. Never edit
`frontend/city.config.json` directly: it's a synced copy (Turbopack can't
import outside the frontend root), refreshed automatically by the `predev`/
`prebuild` hook (`frontend/scripts/sync-city-config.mjs`).

| Field                   | What it does                                                |
| ----------------------- | ----------------------------------------------------------- |
| `city`, `brand`, `domain` | Site title, page metadata, share copy, OG images, sidebar branding |
| `center`, `zoom`        | Initial map view                                            |
| `local_language`        | Label for the optional local-language lake name (set a `name_local` property per feature in your GeoJSON) |
| `attribution`           | Strings shown in footers and the about page (keep the Sentinel-2 attribution) |
| `relatable_units`       | "X football fields" style comparators for areas             |

Optional polish in **`frontend/src/data/lake-enrichment.ts`**: map lake ids to
display names, alternate/search names, size tiers, and map zones. It's empty by
default and every lookup falls back gracefully.

The about page is generic (methodology, attribution, a "run this for your
city" section) and overview-page findings are computed from your data — a
fresh fork shows your city's name everywhere without touching components.

---

## 8. Deploy: backend on Railway

The backend ships with `backend/Dockerfile` and `backend/railway.toml`.

1. Create a Railway project and add a **PostgreSQL** plugin.
2. New service → deploy from your repo. Railway picks up `backend/railway.toml`
   (Dockerfile build, healthcheck at `/health`).
3. Set service variables: `DATABASE_URL` (use Railway's Postgres URL),
   `CORS_ORIGINS` (your frontend URL), and the R2 vars if you use R2.
4. Run `init_db` and a backfill against the Railway database (locally with
   `DATABASE_URL` pointed at Railway, or via a one-off Railway shell).

---

## 9. Deploy: frontend on Vercel

`frontend/vercel.json` sets the framework to Next.js.

1. Import the repo into Vercel; set the **root directory** to `frontend/`.
2. Set environment variables: `NEXT_PUBLIC_MAPBOX_TOKEN` and `BACKEND_URL`
   (your Railway backend URL).
3. Deploy. The Next rewrites proxy API/frame/asset requests to `BACKEND_URL`.

---

## 10. Timelapse assets on Cloudflare R2 (optional)

Timelapse GIFs/MP4s can be large and viral sharing means bandwidth. Cloudflare
R2 is S3-compatible with **zero egress fees**, which is why it's the default.

1. Create an R2 bucket and an API token (access key + secret).
2. Set: `R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`, `R2_BUCKET`,
   `R2_PUBLIC_URL` (the bucket's public base URL).
3. The timelapse upload step (`pipeline/timelapse/upload.py`) pushes rendered
   assets to R2 and records their URLs.

If you skip R2, the backend can serve frames/assets locally from
`pipeline/data/` (mounted at `/frames` and `/assets`) — fine for small
deployments, not for viral traffic.

---

## 11. Scheduled ingestion (GitHub Actions)

`.github/workflows/ingest.yml` runs an incremental ingestion every 5 days (and
on manual dispatch), keeping the dashboard current with new Sentinel-2 passes.

Set these as **repo secrets** (`gh secret set <NAME>` or repo Settings →
Secrets):

- `DATABASE_URL`
- `GEE_PROJECT_ID`
- `GEE_SERVICE_ACCOUNT_KEY_JSON` — the **full JSON contents** of your service
  account key (the workflow writes it to a temp file at runtime).

The workflow validates that the secrets are present and that the key is valid
JSON before running.

---

## 12. Environment variables reference

| Variable                       | Used by            | Notes                                                   |
| ------------------------------ | ------------------ | ------------------------------------------------------- |
| `DATABASE_URL`                 | pipeline, backend  | PostgreSQL connection string                            |
| `GEE_PROJECT_ID`               | pipeline           | Your Earth Engine Cloud project id                      |
| `GEE_SERVICE_ACCOUNT_KEY`      | pipeline (local)   | Path to the service-account JSON key file               |
| `GEE_SERVICE_ACCOUNT_KEY_JSON` | CI (Actions secret)| Full JSON contents of the key (workflow writes to file) |
| `CORS_ORIGINS`                 | backend            | Comma-separated allowed origins                         |
| `R2_ENDPOINT`                  | pipeline           | R2 S3 endpoint URL (optional)                           |
| `R2_ACCESS_KEY`                | pipeline           | R2 access key (optional)                                |
| `R2_SECRET_KEY`                | pipeline           | R2 secret key (optional)                                |
| `R2_BUCKET`                    | pipeline           | R2 bucket name (optional)                               |
| `R2_PUBLIC_URL`                | pipeline           | Public base URL for the bucket (optional)               |
| `GEE_VERIFY_BBOX`            | pipeline           | Optional `min_lng,min_lat,max_lng,max_lat` for the `verify_gee` connectivity check |
| `LAKEWATCH_WATERMARK`          | pipeline           | Timelapse watermark text (defaults to "LakeWatch")      |
| `NEXT_PUBLIC_MAPBOX_TOKEN`     | frontend           | Mapbox access token                                     |
| `BACKEND_URL`                  | frontend           | URL the frontend proxies API/frame requests to          |

Never commit `.env` or your service-account key — both are gitignored.
