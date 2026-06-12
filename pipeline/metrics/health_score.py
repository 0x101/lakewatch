"""Health score computation for a lake based on observation history.

Produces a composite 0-100 score from four weighted components:
  - Area stability (40%): How much the lake area has changed over 5 years
  - Algae level (30%): Mean algae fraction in recent observations
  - Water presence (20%): Current area vs. historical maximum
  - Trend (10%): Whether the lake is growing, stable, or shrinking
"""

import numpy as np


def compute_health_score(observations: list) -> float | None:
    """Compute composite health score (0-100) from observation history.

    Args:
        observations: List of objects with .observation_date,
            .water_area_m2, .algae_fraction attributes.

    Returns:
        Float 0-100, or None if fewer than 10 observations with valid data.
    """
    if len(observations) < 10:
        return None

    # Sort by date
    obs = sorted(observations, key=lambda o: o.observation_date)

    # Extract valid areas
    areas = [o.water_area_m2 for o in obs if o.water_area_m2 is not None]
    if len(areas) < 10:
        return None

    # --- Area stability (40%) ---
    area_now = float(np.median(areas[-12:])) if len(areas) >= 12 else float(np.median(areas))
    area_5yr = float(np.median(areas[:12])) if len(areas) > 60 else float(areas[0])
    change_5yr = (area_now - area_5yr) / area_5yr if area_5yr > 0 else 0.0
    # 0% change -> 100, -50% change -> 0, linear
    area_stability = max(0.0, min(100.0, 100.0 + change_5yr * 200.0))

    # --- Algae score (30%) ---
    algae_values = [o.algae_fraction for o in obs[-24:] if o.algae_fraction is not None]
    if algae_values:
        mean_algae = float(np.mean(algae_values))
        # fraction < 0.05 -> 100, > 0.50 -> 0
        algae_score = max(0.0, min(100.0, (0.50 - mean_algae) / 0.45 * 100.0))
    else:
        algae_score = 50.0  # neutral if no data

    # --- Water presence (20%) ---
    max_area = max(areas)
    water_presence = min(100.0, area_now / max_area * 100.0) if max_area > 0 else 0.0

    # --- Trend (10%) ---
    recent = areas[-24:] if len(areas) >= 24 else areas
    if len(recent) >= 2:
        x = np.arange(len(recent), dtype=float)
        slope = float(np.polyfit(x, recent, 1)[0])
        mean_recent = float(np.mean(recent))
        # Normalize: 50 = stable, >50 = improving, <50 = declining
        trend_score = max(0.0, min(100.0, 50.0 + slope / mean_recent * 5000.0))
    else:
        trend_score = 50.0

    return 0.40 * area_stability + 0.30 * algae_score + 0.20 * water_presence + 0.10 * trend_score
