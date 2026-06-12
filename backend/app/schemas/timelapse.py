"""Timelapse response schemas (Pydantic v2)."""

from pydantic import BaseModel


class FrameItem(BaseModel):
    """Single timelapse frame."""

    observation_date: str
    frame_url: str
    thumbnail_url: str | None = None
    frame_order: int


class AssetItem(BaseModel):
    """Timelapse asset (GIF, video, thumbnail)."""

    asset_type: str
    url: str
    file_size_bytes: int | None = None


class TimelapseResponse(BaseModel):
    """Response wrapper for timelapse endpoint."""

    lake_id: str
    frames: list[FrameItem]
    assets: list[AssetItem]
