"""Leaderboard endpoint — ranked lakes by category."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.queries.leaderboard import VALID_CATEGORIES, get_leaderboard
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse

router = APIRouter(prefix="/api")


@router.get("/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard_endpoint(
    category: str = "shrinking",
    db: Session = Depends(get_db),
):
    """Return ranked lakes for a leaderboard category.

    Categories: shrinking, recovering, polluted, volatile.
    """
    if category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {category}. Use one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )

    rows = get_leaderboard(db, category)

    # Determine metric name from category config
    from app.queries.leaderboard import CATEGORY_CONFIG

    metric_name = CATEGORY_CONFIG[category]["metric_name"]

    entries = [
        LeaderboardEntry(
            rank=idx + 1,
            lake_id=row.id,
            lake_name=row.name,
            metric_value=row.metric_value,
            metric_name=metric_name,
            health_score=row.health_score,
            area_change_5yr_pct=row.area_change_5yr_pct,
            observation_count=row.observation_count,
            pollution_level=row.pollution_level,
        )
        for idx, row in enumerate(rows)
    ]

    return LeaderboardResponse(category=category, entries=entries)
