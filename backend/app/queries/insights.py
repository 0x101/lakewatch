"""Data quality and insights query functions."""

from datetime import timedelta

from sqlalchemy import Float as SAFloat
from sqlalchemy import and_, extract, func, select
from sqlalchemy.orm import Session

from pipeline.db.models import (
    HAS_CITY_EXTENSIONS,
    Lake,
    LakeStats,
    Observation,
)

# Bangalore city extensions (KSPCB lab data, EMPRI ground truth). These tables only
# exist in the private repo; in the public "lakewatch" build HAS_CITY_EXTENSIONS is
# False and these names are None. Every query that touches them gates on the flag and
# returns the SAME response shape with empty/null KSPCB values when they are absent.
if HAS_CITY_EXTENSIONS:
    from pipeline.db.models import EMPRIRecord, KSPCBMeasurement
else:
    EMPRIRecord = None  # type: ignore[assignment,misc]
    KSPCBMeasurement = None  # type: ignore[assignment,misc]


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


def get_cross_reference(db: Session, lake_id: str) -> list[dict]:
    """Cross-reference satellite algae with KSPCB data by month."""
    # Get monthly average satellite algae
    sat_stmt = (
        select(
            func.to_char(Observation.observation_date, "YYYY-MM").label("month"),
            func.avg(Observation.algae_fraction).label("avg_algae"),
        )
        .where(Observation.lake_id == lake_id)
        .group_by(func.to_char(Observation.observation_date, "YYYY-MM"))
        .order_by(func.to_char(Observation.observation_date, "YYYY-MM"))
    )
    sat_data = {r.month: r.avg_algae for r in db.execute(sat_stmt).all()}

    # Get KSPCB measurements (city extension only — empty when ext tables absent).
    kspcb_data = {}
    if HAS_CITY_EXTENSIONS:
        kspcb_stmt = (
            select(KSPCBMeasurement)
            .where(KSPCBMeasurement.lake_id == lake_id)
            .order_by(KSPCBMeasurement.measurement_date)
        )
        for m in db.execute(kspcb_stmt).scalars().all():
            month_key = m.measurement_date.strftime("%Y-%m")
            kspcb_data[month_key] = m

    # Merge
    all_months = sorted(set(list(sat_data.keys()) + list(kspcb_data.keys())))
    entries = []
    for month in all_months:
        sat_algae = sat_data.get(month)
        kspcb = kspcb_data.get(month)

        agreement = None
        if sat_algae is not None and kspcb is not None:
            # High algae + high BOD = consistent
            high_algae = sat_algae > 0.1
            high_bod = kspcb.bod_mg_l is not None and kspcb.bod_mg_l > 30
            if high_algae == high_bod:
                agreement = "consistent"
            else:
                agreement = "contradictory"

        entries.append({
            "month": month,
            "satellite_algae_fraction": round(sat_algae, 4) if sat_algae else None,
            "kspcb_bod": kspcb.bod_mg_l if kspcb else None,
            "kspcb_cod": kspcb.cod_mg_l if kspcb else None,
            "kspcb_do": kspcb.dissolved_oxygen_mg_l if kspcb else None,
            "kspcb_classification": kspcb.classification if kspcb else None,
            "agreement": agreement,
        })

    return entries


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

    # Most common KSPCB class: mode of latest classification per lake.
    # City extension only — None when ext tables absent (shape unchanged).
    most_common = None
    if HAS_CITY_EXTENSIONS:
        latest_kspcb = (
            select(
                KSPCBMeasurement.lake_id,
                KSPCBMeasurement.classification,
                func.row_number()
                .over(
                    partition_by=KSPCBMeasurement.lake_id,
                    order_by=KSPCBMeasurement.measurement_date.desc(),
                )
                .label("rn"),
            )
            .where(KSPCBMeasurement.classification.isnot(None))
            .subquery()
        )
        mode_stmt = (
            select(latest_kspcb.c.classification)
            .where(latest_kspcb.c.rn == 1)
            .group_by(latest_kspcb.c.classification)
            .order_by(func.count().desc())
            .limit(1)
        )
        most_common = db.execute(mode_stmt).scalar_one_or_none()

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
        "most_common_kspcb_class": most_common,
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

    # KSPCB classification distribution by year (city extension only).
    # Empty when ext tables absent — each year still emits an all-zeros distribution.
    kspcb_by_year: dict[int, dict[str, int]] = {}
    if HAS_CITY_EXTENSIONS:
        kspcb_stmt = (
            select(
                extract("year", KSPCBMeasurement.measurement_date)
                .cast(SAFloat)
                .label("year"),
                KSPCBMeasurement.classification,
                func.count().label("cnt"),
            )
            .where(KSPCBMeasurement.classification.isnot(None))
            .group_by(
                extract("year", KSPCBMeasurement.measurement_date),
                KSPCBMeasurement.classification,
            )
            .order_by(extract("year", KSPCBMeasurement.measurement_date))
        )
        kspcb_rows = db.execute(kspcb_stmt).all()
        for r in kspcb_rows:
            yr = int(r.year)
            kspcb_by_year.setdefault(yr, {})
            kspcb_by_year[yr][r.classification] = r.cnt

    all_years = sorted(set(list(obs_rows.keys()) + list(kspcb_by_year.keys())))

    results = []
    for yr in all_years:
        obs = obs_rows.get(yr)
        kspcb_dist = kspcb_by_year.get(yr, {})
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
            "kspcb_class_distribution": {
                "A": kspcb_dist.get("A", 0),
                "B": kspcb_dist.get("B", 0),
                "C": kspcb_dist.get("C", 0),
                "D": kspcb_dist.get("D", 0),
                "E": kspcb_dist.get("E", 0),
            },
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


def get_correlation(db: Session) -> list[dict]:
    """Satellite health score vs KSPCB classification correlation."""
    # Correlation is inherently KSPCB-vs-satellite; with no KSPCB extension there is
    # nothing to correlate, so return an empty list (endpoint returns empty entries).
    if not HAS_CITY_EXTENSIONS:
        return []

    # Get latest KSPCB measurement per lake
    latest_kspcb = (
        select(
            KSPCBMeasurement.lake_id,
            KSPCBMeasurement.classification,
            KSPCBMeasurement.bod_mg_l,
            func.row_number()
            .over(
                partition_by=KSPCBMeasurement.lake_id,
                order_by=KSPCBMeasurement.measurement_date.desc(),
            )
            .label("rn"),
        )
        .subquery()
    )

    stmt = (
        select(
            LakeStats.lake_id,
            Lake.name.label("lake_name"),
            LakeStats.health_score,
            latest_kspcb.c.classification.label("latest_kspcb_class"),
            latest_kspcb.c.bod_mg_l.label("latest_bod"),
            LakeStats.mean_algae_fraction.label("latest_algae_fraction"),
        )
        .join(Lake, LakeStats.lake_id == Lake.id)
        .join(
            latest_kspcb,
            (LakeStats.lake_id == latest_kspcb.c.lake_id)
            & (latest_kspcb.c.rn == 1),
        )
        .order_by(LakeStats.health_score.asc().nullslast())
    )

    rows = db.execute(stmt).all()
    return [
        {
            "lake_id": r.lake_id,
            "lake_name": r.lake_name,
            "health_score": round(r.health_score, 1) if r.health_score else None,
            "latest_kspcb_class": r.latest_kspcb_class,
            "latest_bod": round(r.latest_bod, 2) if r.latest_bod else None,
            "latest_algae_fraction": (
                round(r.latest_algae_fraction, 4)
                if r.latest_algae_fraction
                else None
            ),
        }
        for r in rows
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
