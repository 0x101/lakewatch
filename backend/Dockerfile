FROM python:3.12-slim

WORKDIR /app

# System dependencies for PostGIS + geospatial
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pipeline (shared models + dependencies)
COPY pipeline/ /app/pipeline/

# Install Python dependencies
COPY pipeline/pyproject.toml /app/pipeline/
RUN cd /app/pipeline && uv pip install --system -r pyproject.toml

# Install backend-specific deps
RUN uv pip install --system fastapi uvicorn python-dotenv

# Copy backend code
COPY backend/ /app/backend/

# Set Python path so backend can import pipeline modules
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
