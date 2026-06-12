"""Lake query functions — single-query joins to avoid N+1."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from pipeline.db.models import Lake, LakeStats


def get_all_lakes_with_stats(db: Session) -> list[tuple[Lake, LakeStats | None]]:
    """Fetch all lakes with their stats in a single outerjoin query."""
    stmt = (
        select(Lake, LakeStats)
        .outerjoin(LakeStats, Lake.id == LakeStats.lake_id)
        .order_by(Lake.name)
    )
    return list(db.execute(stmt).all())


def get_all_lakes_with_boundaries(db: Session) -> list[tuple[Lake, LakeStats | None]]:
    """Fetch all lakes (including boundary geometry) with their stats."""
    stmt = (
        select(Lake, LakeStats)
        .outerjoin(LakeStats, Lake.id == LakeStats.lake_id)
        .order_by(Lake.name)
    )
    return list(db.execute(stmt).all())


def get_lake_by_id(db: Session, lake_id: str) -> tuple[Lake, LakeStats | None] | None:
    """Fetch a single lake with stats by ID. Returns None if not found."""
    stmt = (
        select(Lake, LakeStats)
        .outerjoin(LakeStats, Lake.id == LakeStats.lake_id)
        .where(Lake.id == lake_id)
    )
    result = db.execute(stmt).first()
    return result if result else None
