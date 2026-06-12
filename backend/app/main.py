"""FastAPI application for LakeWatch."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
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
import os

_frames_dir = os.path.join(os.path.dirname(__file__), "..", "..", "pipeline", "data", "frames")
_assets_dir = os.path.join(os.path.dirname(__file__), "..", "..", "pipeline", "data", "assets")
if os.path.isdir(_frames_dir):
    app.mount("/frames", StaticFiles(directory=_frames_dir), name="frames")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
