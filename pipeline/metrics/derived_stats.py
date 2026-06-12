"""Derived statistics computation: area change, seasonal amplitude, peak algae.

Transforms raw observation time series into summary metrics for the
lake_stats materialized table.
"""

from collections import defaultdict
from datetime import timedelta

import numpy as np


def compute_derived_stats(observations: list) -> dict:
    """Compute derived statistics from observation history.

    Args:
        observations: List of objects with .observation_date,
            .water_area_m2, .algae_fraction attributes.

    Returns:
        Dict with keys: area_change_1yr_pct, area_change_5yr_pct,
        seasonal_amplitude, peak_algae_month. Values are None when
        insufficient data.
    """
    result = {
        "area_change_1yr_pct": None,
        "area_change_5yr_pct": None,
        "seasonal_amplitude": None,
        "peak_algae_month": None,
    }

    if not observations:
        return result

    obs = sorted(observations, key=lambda o: o.observation_date)

    # --- Area change percentages ---
    result["area_change_1yr_pct"] = _area_change(obs, years_ago=1)
    result["area_change_5yr_pct"] = _area_change(obs, years_ago=5)

    # --- Seasonal amplitude ---
    result["seasonal_amplitude"] = _seasonal_amplitude(obs)

    # --- Peak algae month ---
    result["peak_algae_month"] = _peak_algae_month(obs)

    return result


def _area_change(obs: list, years_ago: int) -> float | None:
    """Compute area change percentage vs N years ago.

    Compares median area of the most recent 60 days to median area
    of the 60-day window centered on N years before the latest date.
    """
    valid = [(o.observation_date, o.water_area_m2) for o in obs if o.water_area_m2 is not None]
    if not valid:
        return None

    latest_date = valid[-1][0]
    target_date = latest_date - timedelta(days=years_ago * 365)

    # Recent window: last 60 days
    recent_start = latest_date - timedelta(days=60)
    recent_areas = [a for d, a in valid if d >= recent_start]

    # Historical window: 30 days before and after target date
    hist_start = target_date - timedelta(days=30)
    hist_end = target_date + timedelta(days=30)
    hist_areas = [a for d, a in valid if hist_start <= d <= hist_end]

    if not recent_areas or not hist_areas:
        return None

    recent_median = float(np.median(recent_areas))
    hist_median = float(np.median(hist_areas))

    if hist_median == 0:
        return None

    return round((recent_median - hist_median) / hist_median * 100.0, 2)


def _seasonal_amplitude(obs: list) -> float | None:
    """Max monthly average area minus min monthly average area."""
    monthly: dict[int, list[float]] = defaultdict(list)
    for o in obs:
        if o.water_area_m2 is not None:
            monthly[o.observation_date.month].append(o.water_area_m2)

    if len(monthly) < 2:
        return None

    monthly_avgs = [float(np.mean(areas)) for areas in monthly.values()]
    return max(monthly_avgs) - min(monthly_avgs)


def _peak_algae_month(obs: list) -> int | None:
    """Month (1-12) with highest mean algae fraction."""
    monthly: dict[int, list[float]] = defaultdict(list)
    for o in obs:
        if o.algae_fraction is not None:
            monthly[o.observation_date.month].append(o.algae_fraction)

    if not monthly:
        return None

    return max(monthly, key=lambda m: float(np.mean(monthly[m])))
