"""Timelapse endpoint — frame URLs and asset URLs for a lake."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.queries.lakes import get_lake_by_id
from app.queries.timelapse import get_timelapse_assets, get_timelapse_frames
from app.schemas.timelapse import AssetItem, FrameItem, TimelapseResponse

router = APIRouter(prefix="/api")


@router.get("/lakes/{lake_id}/timelapse", response_model=TimelapseResponse)
def get_timelapse(
    lake_id: str,
    db: Session = Depends(get_db),
):
    """Return timelapse frames and assets for a lake."""
    # Check lake exists
    result = get_lake_by_id(db, lake_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lake not found")

    frames_raw = get_timelapse_frames(db, lake_id)
    assets_raw = get_timelapse_assets(db, lake_id)

    def normalize_frame_url(url: str) -> str:
        """Convert local file paths to serveable URLs."""
        # Strip any leading path components like "pipeline/data/frames/"
        if "pipeline/data/frames/" in url:
            return "/frames/" + url.split("pipeline/data/frames/")[-1]
        if url.startswith("http"):
            return url  # Already an R2 URL
        return url

    def normalize_asset_url(url: str) -> str:
        """Convert local file paths to serveable URLs."""
        if "pipeline/data/assets/" in url:
            return "/assets/" + url.split("pipeline/data/assets/")[-1]
        if url.startswith("http"):
            return url
        return url

    frames = [
        FrameItem(
            observation_date=str(f.observation_date),
            frame_url=normalize_frame_url(f.frame_url),
            thumbnail_url=f.thumbnail_url,
            frame_order=f.frame_order,
        )
        for f in frames_raw
    ]

    assets = [
        AssetItem(
            asset_type=a.asset_type,
            url=normalize_asset_url(a.r2_url),
            file_size_bytes=a.file_size_bytes,
        )
        for a in assets_raw
    ]

    return TimelapseResponse(
        lake_id=lake_id,
        frames=frames,
        assets=assets,
    )
