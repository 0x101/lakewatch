"""Leaderboard response schemas (Pydantic v2)."""

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    """Single entry in a leaderboard ranking."""

    rank: int
    lake_id: str
    lake_name: str
    metric_value: float | None = None
    metric_name: str
    health_score: float | None = None
    area_change_5yr_pct: float | None = None
    observation_count: int = 0
    pollution_level: str | None = None


class LeaderboardResponse(BaseModel):
    """Response wrapper for leaderboard endpoint."""

    category: str
    entries: list[LeaderboardEntry]
