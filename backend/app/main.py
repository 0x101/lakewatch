"""FastAPI application for LakeWatch."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import CORS_ORIGINS
from app.extensions import register_extensions
from app.routers.insights import router as insights_router
from app.routers.lakes import router as lakes_router
from app.routers.leaderboard import router as leaderboard_router
from app.routers.timelapse import router as timelapse_router
from app.routers.timeseries import router as timeseries_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    yield


app = FastAPI(
    title="LakeWatch API",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# The API is public and read-only: no cookies/auth, so no credentialed CORS
# and no write methods.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)


app.include_router(lakes_router)
app.include_router(timeseries_router)
app.include_router(timelapse_router)
app.include_router(leaderboard_router)
app.include_router(insights_router)

# City-specific routers (if any) mount through the extension seam.
# No-op in the upstream build; see app/extensions.py.
register_extensions(app)


# Serve timelapse frames and assets as static files
_frames_dir = os.path.join(os.path.dirname(__file__), "..", "..", "pipeline", "data", "frames")
_assets_dir = os.path.join(os.path.dirname(__file__), "..", "..", "pipeline", "data", "assets")
if os.path.isdir(_frames_dir):
    app.mount("/frames", StaticFiles(directory=_frames_dir), name="frames")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


# Registered on Starlette's base class so router-level 404/405s (unknown
# paths) get the same {"error": ...} shape as the HTTPExceptions we raise.
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
