"""Timelapse query functions for frames and assets."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from pipeline.db.models import TimelapseAsset, TimelapseFrame


def get_timelapse_frames(db: Session, lake_id: str) -> list:
    """Fetch timelapse frames for a lake, ordered by frame_order."""
    stmt = (
        select(TimelapseFrame)
        .where(TimelapseFrame.lake_id == lake_id)
        .order_by(TimelapseFrame.frame_order.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_timelapse_assets(db: Session, lake_id: str) -> list:
    """Fetch timelapse assets (GIF, video, thumbnail) for a lake."""
    stmt = select(TimelapseAsset).where(TimelapseAsset.lake_id == lake_id)
    return list(db.execute(stmt).scalars().all())
