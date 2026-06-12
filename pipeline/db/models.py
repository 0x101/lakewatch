"""SQLAlchemy ORM models for Lake Watch database."""

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Lake(Base):
    """Lake boundary and metadata (DB-01)."""

    __tablename__ = "lakes"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # slugified name
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_kannada: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    boundary_geojson: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )  # GeoJSON string (no PostGIS dependency)
    ward: Mapped[str | None] = mapped_column(String, nullable=True)
    custodian: Mapped[str | None] = mapped_column(String, nullable=True)
    citizen_group: Mapped[str | None] = mapped_column(String, nullable=True)
    area_hectares: Mapped[float | None] = mapped_column(Float, nullable=True)
    boundary_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class Observation(Base):
    """Satellite observation record for a lake (DB-02)."""

    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("lake_id", "observation_date"),
        Index("ix_obs_lake_date", "lake_id", "observation_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lake_id: Mapped[str] = mapped_column(
        String, ForeignKey("lakes.id"), nullable=False
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    water_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_ndwi: Mapped[float | None] = mapped_column(Float, nullable=True)
    algae_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class LakeStats(Base):
    """Pre-computed materialized stats per lake (DB-03)."""

    __tablename__ = "lake_stats"

    lake_id: Mapped[str] = mapped_column(
        String, ForeignKey("lakes.id"), primary_key=True
    )
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_water_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_change_1yr_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_change_5yr_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    seasonal_amplitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_algae_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mean_algae_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    latest_observation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class TimelapseAsset(Base):
    """Timelapse asset reference for GIF/video/thumbnail stored in R2."""

    __tablename__ = "timelapse_assets"
    __table_args__ = (
        UniqueConstraint("lake_id", "asset_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lake_id: Mapped[str] = mapped_column(
        String, ForeignKey("lakes.id"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "gif-full", "gif-share", "video-full", "video-share", "thumbnail"
    r2_url: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class TimelapseFrame(Base):
    """Timelapse frame reference linking observation to R2 asset (DB-04)."""

    __tablename__ = "timelapse_frames"
    __table_args__ = (
        UniqueConstraint("lake_id", "observation_date"),
        Index("ix_tlf_lake_order", "lake_id", "frame_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lake_id: Mapped[str] = mapped_column(
        String, ForeignKey("lakes.id"), nullable=False
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    frame_url: Mapped[str] = mapped_column(String, nullable=False)  # R2 URL
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    frame_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# --- Bangalore extensions (re-exported for backward compat + metadata registration) ---
# Imported at the BOTTOM so Base is already defined (models_ext imports Base from here).
# This registers the ext tables on the shared Base.metadata (alembic + tests see them)
# AND keeps `from pipeline.db.models import EMPRIRecord` working for query modules/tests.
#
# Graceful degradation: this SHARED file ships byte-identical to the public "lakewatch"
# repo, where models_ext.py does not exist. The try/except keeps the import safe and
# exposes HAS_CITY_EXTENSIONS so shared modules can branch on extension availability.
try:
    from pipeline.db.models_ext import (  # noqa: E402,F401
        EMPRIRecord,
        KSPCBMeasurement,
        Stream,
        StreamLakeConnection,
    )

    HAS_CITY_EXTENSIONS = True
except ImportError:
    EMPRIRecord = None  # type: ignore[assignment,misc]
    KSPCBMeasurement = None  # type: ignore[assignment,misc]
    Stream = None  # type: ignore[assignment,misc]
    StreamLakeConnection = None  # type: ignore[assignment,misc]
    HAS_CITY_EXTENSIONS = False
