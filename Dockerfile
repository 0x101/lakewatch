# LakeWatch API image (FastAPI backend + the shared pipeline.db models).
#
# Build from the repo root:   docker build -t lakewatch-api .
# Run:                        docker run -p 8000:8000 -e DATABASE_URL=... lakewatch-api
#
# Deliberately lean: the API only needs SQLAlchemy + FastAPI. The heavy
# pipeline deps (Earth Engine, rasterio, matplotlib, ffmpeg) are NOT installed;
# run the pipeline with `uv` locally or in GitHub Actions instead.
# Versions are pinned to match backend/uv.lock so builds are reproducible.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# No PostGIS/GDAL needed — boundaries are stored as GeoJSON text.
RUN pip install \
    fastapi==0.135.3 \
    uvicorn==0.44.0 \
    pydantic==2.12.5 \
    sqlalchemy==2.0.49 \
    psycopg2-binary==2.9.11 \
    python-dotenv==1.1.0

# Only the modules the API imports: pipeline/db (models + engine) and the
# package markers. Timelapse frames/assets are served from pipeline/data if
# you mount it (or point the DB at R2 URLs instead).
COPY pipeline/__init__.py /app/pipeline/__init__.py
COPY pipeline/db/ /app/pipeline/db/
COPY backend/app/ /app/backend/app/

# `pipeline.*` resolves via /app, `app.*` via /app/backend.
ENV PYTHONPATH=/app:/app/backend

RUN useradd --system --uid 10001 --no-create-home lakewatch
USER lakewatch

WORKDIR /app/backend
EXPOSE 8000

# sh -c so Railway/Render/Fly's $PORT is honoured; exec keeps uvicorn as PID 1
# so it receives SIGTERM directly and shuts down gracefully.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --proxy-headers --forwarded-allow-ips='*'"]
