FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies (no PostGIS/GDAL needed — boundaries stored as GeoJSON text)
RUN pip install --no-cache-dir \
    sqlalchemy==2.0.49 \
    psycopg2-binary==2.9.11 \
    python-dotenv==1.1.0 \
    "fastapi>=0.135" \
    "uvicorn>=0.44"

# Copy source code
COPY pipeline/ /app/pipeline/
COPY backend/ /app/backend/

ENV PYTHONPATH=/app:/app/backend

WORKDIR /app/backend

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
