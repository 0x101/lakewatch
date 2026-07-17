"""Data quality and insights query functions."""

from datetime import timedelta

from sqlalchemy import Float as SAFloat
from sqlalchemy import and_, extract, func, select
from sqlalchemy.orm import Session

from pipeline.db.models import (
    Lake,
    LakeStats,
    Observation,
)


def get_raw_observations(
    db: Session,
    lake_id: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list, int]:
    """Fetch raw observations with lake names, paginated."""
    base = (
        select(
            Observation.lake_id,
            Lake.name.label("lake_name"),
            Observation.observation_date,
            Observation.water_area_m2,
            Observation.mean_ndwi,
            Observation.algae_fraction,
            Observation.cloud_pct,
        )
        .join(Lake, Observation.lake_id == Lake.id)
        .order_by(Observation.observation_date.desc())
    )

    if lake_id:
        base = base.where(Observation.lake_id == lake_id)

    # Count total
    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.execute(count_stmt).scalar_one()

    # Paginate
    stmt = base.offset((page - 1) * page_size).limit(page_size)
    rows = list(db.execute(stmt).all())

    return rows, total


def get_all_lake_stats_with_names(db: Session) -> list:
    """Fetch all lake stats joined with lake names."""
    stmt = (
        select(
            LakeStats.lake_id,
            Lake.name.label("lake_name"),
            LakeStats.health_score,
            LakeStats.latest_water_area_m2,
            LakeStats.area_change_1yr_pct,
            LakeStats.area_change_5yr_pct,
            LakeStats.seasonal_amplitude,
            LakeStats.peak_algae_month,
            LakeStats.mean_algae_fraction,
            LakeStats.observation_count,
            LakeStats.latest_observation_date,
        )
        .join(Lake, LakeStats.lake_id == Lake.id)
        .order_by(LakeStats.health_score.asc().nullslast())
    )
    return list(db.execute(stmt).all())


def get_outliers(db: Session, limit: int = 50) -> list[dict]:
    """Detect and return outlier observations."""
    outliers = []

    # 1. Zero-area observations for lakes that normally have water
    zero_stmt = (
        select(Observation, Lake.name)
        .join(Lake, Observation.lake_id == Lake.id)
        .join(LakeStats, Observation.lake_id == LakeStats.lake_id)
        .where(
            Observation.water_area_m2 == 0,
            LakeStats.observation_count > 10,
        )
        .order_by(Observation.observation_date.desc())
        .limit(limit)
    )
    for obs, lake_name in db.execute(zero_stmt).all():
        outliers.append({
            "lake_id": obs.lake_id,
            "lake_name": lake_name,
            "observation_date": str(obs.observation_date),
            "outlier_type": "zero_area",
            "value": 0.0,
            "explanation": (
                "Water area reads as 0 m² despite this lake normally having water. "
                "Likely cause: cloud shadow misclassified as land, or dry-season exposure "
                "of lake bed. Check cloud_pct and surrounding observations."
            ),
        })

    # 2. Algae spikes (>0.3 when mean is <0.1)
    spike_stmt = (
        select(Observation, Lake.name, LakeStats.mean_algae_fraction)
        .join(Lake, Observation.lake_id == Lake.id)
        .join(LakeStats, Observation.lake_id == LakeStats.lake_id)
        .where(
            Observation.algae_fraction > 0.3,
            LakeStats.mean_algae_fraction < 0.1,
        )
        .order_by(Observation.algae_fraction.desc())
        .limit(limit)
    )
    for obs, lake_name, mean_algae in db.execute(spike_stmt).all():
        outliers.append({
            "lake_id": obs.lake_id,
            "lake_name": lake_name,
            "observation_date": str(obs.observation_date),
            "outlier_type": "algae_spike",
            "value": obs.algae_fraction,
            "explanation": (
                f"Algae fraction of {obs.algae_fraction:.1%} is unusually high "
                f"for this lake (mean: {mean_algae:.1%}). May indicate a genuine "
                "bloom event, or could be misclassification of floating vegetation."
            ),
        })

    return outliers[:limit]


def get_stats_by_custodian(db: Session) -> list:
    """Aggregate lake health stats grouped by custodian agency."""
    stmt = (
        select(
            func.coalesce(Lake.custodian, "Unknown").label("custodian"),
            func.count(Lake.id).label("lake_count"),
            func.avg(LakeStats.health_score).label("avg_health"),
            func.count()
            .filter(LakeStats.health_score < 30)
            .label("distressed_count"),
            func.count()
            .filter(LakeStats.health_score >= 60)
            .label("healthy_count"),
        )
        .join(LakeStats, Lake.id == LakeStats.lake_id)
        .group_by(func.coalesce(Lake.custodian, "Unknown"))
        .order_by(func.count(Lake.id).desc())
    )
    return list(db.execute(stmt).all())


def get_city_summary(db: Session) -> dict:
    """Compute city-wide health snapshot from lake_stats."""
    # Core aggregates from lake_stats
    stmt = select(
        func.count(LakeStats.lake_id).label("total_lakes"),
        func.sum(LakeStats.observation_count).label("total_observations"),
        func.avg(LakeStats.health_score).label("avg_health_score"),
        func.percentile_cont(0.5)
        .within_group(LakeStats.health_score)
        .label("median_health_score"),
        func.sum(LakeStats.latest_water_area_m2 / 10000.0).label(
            "total_water_area_ha"
        ),
        func.count()
        .filter(LakeStats.health_score < 30)
        .label("distressed_count"),
        func.count()
        .filter(LakeStats.health_score.between(30, 59.999))
        .label("struggling_count"),
        func.count()
        .filter(LakeStats.health_score >= 60)
        .label("healthy_count"),
        func.avg(LakeStats.mean_algae_fraction).label("avg_algae_fraction"),
        func.count()
        .filter(LakeStats.area_change_1yr_pct > 0)
        .label("lakes_improving"),
        func.count()
        .filter(LakeStats.area_change_1yr_pct < 0)
        .label("lakes_declining"),
    )
    row = db.execute(stmt).one()

    return {
        "total_lakes": row.total_lakes or 0,
        "total_observations": row.total_observations or 0,
        "avg_health_score": (
            round(row.avg_health_score, 1) if row.avg_health_score else None
        ),
        "median_health_score": (
            round(row.median_health_score, 1) if row.median_health_score else None
        ),
        "total_water_area_ha": (
            round(row.total_water_area_ha, 2) if row.total_water_area_ha else None
        ),
        "distressed_count": row.distressed_count,
        "struggling_count": row.struggling_count,
        "healthy_count": row.healthy_count,
        "avg_algae_fraction": (
            round(row.avg_algae_fraction, 4) if row.avg_algae_fraction else None
        ),
        "lakes_improving": row.lakes_improving,
        "lakes_declining": row.lakes_declining,
    }


def get_yearly_trends(db: Session) -> list[dict]:
    """Yearly aggregated observation data for trend charts."""
    obs_stmt = (
        select(
            extract("year", Observation.observation_date)
            .cast(SAFloat)
            .label("year"),
            func.avg(Observation.health_score).label("avg_health"),
            func.sum(Observation.water_area_m2).label("total_water_area"),
            func.avg(Observation.algae_fraction).label("avg_algae"),
            func.count().label("observation_count"),
        )
        .group_by(extract("year", Observation.observation_date))
        .order_by(extract("year", Observation.observation_date))
    )
    obs_rows = {int(r.year): r for r in db.execute(obs_stmt).all()}

    results = []
    for yr in sorted(obs_rows.keys()):
        obs = obs_rows[yr]
        results.append({
            "year": yr,
            "avg_health": round(obs.avg_health, 1) if obs and obs.avg_health else None,
            "total_water_area": (
                round(obs.total_water_area, 0)
                if obs and obs.total_water_area
                else None
            ),
            "avg_algae": (
                round(obs.avg_algae, 4) if obs and obs.avg_algae else None
            ),
            "observation_count": obs.observation_count if obs else 0,
        })

    return results


def get_seasonal_aggregates(db: Session) -> list[dict]:
    """Monthly aggregated data across all lakes and years."""
    stmt = (
        select(
            extract("month", Observation.observation_date)
            .cast(SAFloat)
            .label("month"),
            func.avg(Observation.water_area_m2).label("avg_water_area"),
            func.avg(Observation.algae_fraction).label("avg_algae"),
            func.count().label("observation_count"),
        )
        .group_by(extract("month", Observation.observation_date))
        .order_by(extract("month", Observation.observation_date))
    )
    rows = db.execute(stmt).all()

    return [
        {
            "month": int(r.month),
            "avg_water_area": round(r.avg_water_area, 2) if r.avg_water_area else None,
            "avg_algae": round(r.avg_algae, 4) if r.avg_algae else None,
            "observation_count": r.observation_count,
        }
        for r in rows
    ]


def get_rankings(db: Session, category: str, limit: int = 20) -> list[dict]:
    """Lake rankings in a given category."""
    base_cols = [
        LakeStats.lake_id,
        Lake.name.label("lake_name"),
        LakeStats.health_score,
        Lake.custodian,
    ]

    if category == "health":
        stmt = (
            select(*base_cols, LakeStats.health_score.label("metric_value"))
            .join(Lake, LakeStats.lake_id == Lake.id)
            .where(LakeStats.health_score.isnot(None))
            .order_by(LakeStats.health_score.desc())
            .limit(limit)
        )
    elif category == "improving":
        stmt = (
            select(*base_cols, LakeStats.area_change_1yr_pct.label("metric_value"))
            .join(Lake, LakeStats.lake_id == Lake.id)
            .where(LakeStats.area_change_1yr_pct > 0)
            .order_by(LakeStats.area_change_1yr_pct.desc())
            .limit(limit)
        )
    elif category == "declining":
        stmt = (
            select(*base_cols, LakeStats.area_change_1yr_pct.label("metric_value"))
            .join(Lake, LakeStats.lake_id == Lake.id)
            .where(LakeStats.area_change_1yr_pct < 0)
            .order_by(LakeStats.area_change_1yr_pct.asc())
            .limit(limit)
        )
    elif category == "most_polluted":
        stmt = (
            select(*base_cols, LakeStats.mean_algae_fraction.label("metric_value"))
            .join(Lake, LakeStats.lake_id == Lake.id)
            .where(LakeStats.mean_algae_fraction.isnot(None))
            .order_by(LakeStats.mean_algae_fraction.desc())
            .limit(limit)
        )
    elif category == "cleanest":
        stmt = (
            select(*base_cols, LakeStats.mean_algae_fraction.label("metric_value"))
            .join(Lake, LakeStats.lake_id == Lake.id)
            .where(LakeStats.mean_algae_fraction.isnot(None))
            .order_by(LakeStats.mean_algae_fraction.asc())
            .limit(limit)
        )
    elif category == "largest":
        stmt = (
            select(*base_cols, LakeStats.latest_water_area_m2.label("metric_value"))
            .join(Lake, LakeStats.lake_id == Lake.id)
            .where(LakeStats.latest_water_area_m2.isnot(None))
            .order_by(LakeStats.latest_water_area_m2.desc())
            .limit(limit)
        )
    elif category == "smallest":
        stmt = (
            select(*base_cols, LakeStats.latest_water_area_m2.label("metric_value"))
            .join(Lake, LakeStats.lake_id == Lake.id)
            .where(LakeStats.latest_water_area_m2 > 0)
            .order_by(LakeStats.latest_water_area_m2.asc())
            .limit(limit)
        )
    else:
        return []

    rows = db.execute(stmt).all()
    return [
        {
            "rank": i + 1,
            "lake_id": r.lake_id,
            "lake_name": r.lake_name,
            "metric_value": round(r.metric_value, 4) if r.metric_value else None,
            "health_score": round(r.health_score, 1) if r.health_score else None,
            "custodian": r.custodian,
        }
        for i, r in enumerate(rows)
    ]


def get_movers(db: Session, year: int, limit: int = 20) -> dict:
    """Compute year-over-year water area change for each lake.

    Returns dict with 'improvers' and 'decliners' lists.
    """
    prev_year = year - 1

    # Avg water area per lake for the given year
    curr_sub = (
        select(
            Observation.lake_id,
            func.avg(Observation.water_area_m2).label("avg_area"),
        )
        .where(
            extract("year", Observation.observation_date) == year,
            Observation.water_area_m2.isnot(None),
            Observation.water_area_m2 > 0,
        )
        .group_by(Observation.lake_id)
        .subquery("curr")
    )

    prev_sub = (
        select(
            Observation.lake_id,
            func.avg(Observation.water_area_m2).label("avg_area"),
        )
        .where(
            extract("year", Observation.observation_date) == prev_year,
            Observation.water_area_m2.isnot(None),
            Observation.water_area_m2 > 0,
        )
        .group_by(Observation.lake_id)
        .subquery("prev")
    )

    stmt = (
        select(
            Lake.id.label("lake_id"),
            Lake.name.label("lake_name"),
            curr_sub.c.avg_area.label("current_year_avg_area"),
            prev_sub.c.avg_area.label("previous_year_avg_area"),
            (
                (curr_sub.c.avg_area - prev_sub.c.avg_area)
                / prev_sub.c.avg_area
                * 100
            ).label("change_pct"),
            LakeStats.health_score,
            Lake.custodian,
        )
        .join(curr_sub, Lake.id == curr_sub.c.lake_id)
        .join(prev_sub, Lake.id == prev_sub.c.lake_id)
        .outerjoin(LakeStats, Lake.id == LakeStats.lake_id)
        .where(prev_sub.c.avg_area > 0)
    )

    rows = db.execute(stmt).all()

    entries = []
    for r in rows:
        entries.append({
            "lake_id": r.lake_id,
            "lake_name": r.lake_name,
            "current_year_avg_area": round(r.current_year_avg_area, 2) if r.current_year_avg_area else None,
            "previous_year_avg_area": round(r.previous_year_avg_area, 2) if r.previous_year_avg_area else None,
            "change_pct": round(r.change_pct, 2) if r.change_pct is not None else None,
            "health_score": round(r.health_score, 1) if r.health_score else None,
            "custodian": r.custodian,
        })

    # Sort: improvers desc by change_pct, decliners asc by change_pct
    improvers = sorted(
        [e for e in entries if e["change_pct"] is not None and e["change_pct"] > 0],
        key=lambda x: x["change_pct"],
        reverse=True,
    )[:limit]

    decliners = sorted(
        [e for e in entries if e["change_pct"] is not None and e["change_pct"] < 0],
        key=lambda x: x["change_pct"],
    )[:limit]

    return {"year": year, "improvers": improvers, "decliners": decliners}


def get_pulse(db: Session, window_days: int = 120, top_n: int = 5) -> dict:
    """Compute the recent 'pulse' across lakes: movers, algae watch, city deltas.

    For each lake with >=2 valid water-area observations in the last
    ``window_days``, compares the latest observation to the immediately
    previous one. Returns gainers, shrinkers, an algae watchlist, and a
    city-wide net change vs ~1 year ago. Generic and city-agnostic.
    """
    # Window upper bound = newest observation overall (data may lag "today").
    max_date = db.execute(
        select(func.max(Observation.observation_date))
    ).scalar_one_or_none()
    if max_date is None:
        return {
            "as_of": None,
            "observation_window": {"start": None, "end": None},
            "gainers": [],
            "shrinkers": [],
            "algae_watch": [],
            "city": {
                "total_water_area_now_m2": None,
                "total_water_area_1yr_ago_m2": None,
                "net_change_m2": None,
            },
        }

    window_start = max_date - timedelta(days=window_days)

    # Rank observations per lake (newest first) within the window.
    ranked = (
        select(
            Observation.lake_id,
            Observation.observation_date,
            Observation.water_area_m2,
            Observation.algae_fraction,
            func.row_number()
            .over(
                partition_by=Observation.lake_id,
                order_by=Observation.observation_date.desc(),
            )
            .label("rn"),
        )
        .where(
            Observation.observation_date >= window_start,
            Observation.observation_date <= max_date,
            Observation.water_area_m2.isnot(None),
        )
        .subquery()
    )

    latest = (
        select(
            ranked.c.lake_id,
            ranked.c.observation_date.label("latest_date"),
            ranked.c.water_area_m2.label("latest_area"),
            ranked.c.algae_fraction.label("latest_algae"),
        )
        .where(ranked.c.rn == 1)
        .subquery()
    )
    previous = (
        select(
            ranked.c.lake_id,
            ranked.c.observation_date.label("prev_date"),
            ranked.c.water_area_m2.label("prev_area"),
            ranked.c.algae_fraction.label("prev_algae"),
        )
        .where(ranked.c.rn == 2)
        .subquery()
    )

    stmt = (
        select(
            latest.c.lake_id,
            Lake.name.label("lake_name"),
            latest.c.latest_date,
            latest.c.latest_area,
            latest.c.latest_algae,
            previous.c.prev_area,
            previous.c.prev_algae,
        )
        .join(previous, latest.c.lake_id == previous.c.lake_id)
        .join(Lake, latest.c.lake_id == Lake.id)
    )
    rows = db.execute(stmt).all()

    entries: list[dict] = []
    latest_dates: list = []
    for r in rows:
        latest_area = r.latest_area
        prev_area = r.prev_area
        change_m2 = None
        change_pct = None
        if latest_area is not None and prev_area is not None:
            change_m2 = round(latest_area - prev_area)
            if prev_area:
                change_pct = round((latest_area - prev_area) / prev_area * 100, 2)

        algae_trend = None
        if r.latest_algae is not None and r.prev_algae is not None:
            algae_trend = round(r.latest_algae - r.prev_algae, 4)

        entries.append({
            "lake_id": r.lake_id,
            "lake_name": r.lake_name,
            "water_area_m2": round(latest_area) if latest_area is not None else None,
            "area_change_m2": change_m2,
            "area_change_pct": change_pct,
            "algae_fraction": (
                round(r.latest_algae, 4) if r.latest_algae is not None else None
            ),
            "algae_trend": algae_trend,
        })
        if r.latest_date is not None:
            latest_dates.append(r.latest_date)

    with_change = [e for e in entries if e["area_change_m2"] is not None]
    gainers = sorted(
        [e for e in with_change if e["area_change_m2"] > 0],
        key=lambda x: x["area_change_m2"],
        reverse=True,
    )[:top_n]
    shrinkers = sorted(
        [e for e in with_change if e["area_change_m2"] < 0],
        key=lambda x: x["area_change_m2"],
    )[:top_n]
    algae_watch = sorted(
        [e for e in entries if e["algae_fraction"] is not None],
        key=lambda x: x["algae_fraction"],
        reverse=True,
    )[:top_n]

    as_of = max(latest_dates) if latest_dates else None

    # City totals: sum of latest areas now, and nearest-to-(latest-365d) per lake.
    total_now = sum(
        e["water_area_m2"] for e in entries if e["water_area_m2"] is not None
    )

    # ~1-year-ago comparison: for each lake in `entries`, find the observation
    # nearest to (its latest_date - 365 days) within +/-45 days.
    latest_by_lake = {r.lake_id: r.latest_date for r in rows}
    total_1yr_ago = 0.0
    counted_any = False
    for lake_id, latest_date in latest_by_lake.items():
        target = latest_date - timedelta(days=365)
        lo = target - timedelta(days=45)
        hi = target + timedelta(days=45)
        # Fetch candidate rows in the window and pick the nearest by date in
        # Python (dialect-agnostic: avoids julianday/date-arithmetic differences
        # between SQLite tests and Postgres production).
        candidates = db.execute(
            select(
                Observation.observation_date,
                Observation.water_area_m2,
            ).where(
                Observation.lake_id == lake_id,
                Observation.water_area_m2.isnot(None),
                Observation.observation_date >= lo,
                Observation.observation_date <= hi,
            )
        ).all()
        if candidates:
            nearest = min(
                candidates, key=lambda c: abs((c.observation_date - target).days)
            )
            total_1yr_ago += nearest.water_area_m2
            counted_any = True

    total_1yr_ago_val = round(total_1yr_ago) if counted_any else None
    net_change = (
        round(total_now - total_1yr_ago_val)
        if (counted_any and total_now is not None)
        else None
    )

    return {
        "as_of": str(as_of) if as_of is not None else None,
        "observation_window": {
            "start": str(window_start),
            "end": str(max_date),
        },
        "gainers": gainers,
        "shrinkers": shrinkers,
        "algae_watch": algae_watch,
        "city": {
            "total_water_area_now_m2": round(total_now) if entries else None,
            "total_water_area_1yr_ago_m2": total_1yr_ago_val,
            "net_change_m2": net_change,
        },
    }
