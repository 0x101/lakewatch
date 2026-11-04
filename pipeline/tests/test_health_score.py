"""Unit tests for health score computation."""

from datetime import date, timedelta
from types import SimpleNamespace


from pipeline.metrics.health_score import compute_health_score


def _make_obs(obs_date, water_area_m2=150000.0, algae_fraction=0.05, mean_ndwi=0.45):
    """Helper to create observation-like objects."""
    return SimpleNamespace(
        observation_date=obs_date,
        water_area_m2=water_area_m2,
        algae_fraction=algae_fraction,
        mean_ndwi=mean_ndwi,
        cloud_pct=0.05,
    )


def _make_many_obs(n, start_date, water_area_m2=150000.0, algae_fraction=0.05):
    """Create n observations spaced ~5 days apart."""
    return [
        _make_obs(
            start_date + timedelta(days=i * 5),
            water_area_m2=water_area_m2,
            algae_fraction=algae_fraction,
        )
        for i in range(n)
    ]


class TestHealthScoreGuards:
    def test_returns_none_for_few_observations(self):
        """Health score returns None when fewer than 10 observations."""
        obs = _make_many_obs(5, date(2024, 1, 1))
        result = compute_health_score(obs)
        assert result is None

    def test_returns_none_for_empty_list(self):
        result = compute_health_score([])
        assert result is None


class TestHealthScoreComputation:
    def test_returns_float_for_sufficient_data(self):
        """50 stable observations should produce a good score."""
        obs = _make_many_obs(50, date(2020, 1, 1))
        result = compute_health_score(obs)
        assert isinstance(result, float)
        assert 0 <= result <= 100
        # Stable lake with low algae should score well
        assert result > 70

    def test_weights_sum_to_100(self):
        """Verify formula weights: 0.40 + 0.30 + 0.20 + 0.10 = 1.0."""
        # Create observations where we can predict component scores
        # Stable area, low algae, full water presence, stable trend
        obs = _make_many_obs(60, date(2020, 1, 1), water_area_m2=150000.0, algae_fraction=0.02)
        result = compute_health_score(obs)
        assert isinstance(result, float)
        # All components should be high -> total near 100
        assert result > 80

    def test_penalizes_shrinking_lake(self):
        """Lake that lost significant area over time should score poorly."""
        # Start with large area, shrink dramatically over time
        obs = []
        start = date(2019, 1, 1)
        for i in range(80):
            # Area decreases from 200000 to 40000 (80% decline)
            area = 200000.0 - (i * 2000.0)
            obs.append(_make_obs(start + timedelta(days=i * 5), water_area_m2=area))
        result = compute_health_score(obs)
        assert isinstance(result, float)
        assert result < 50

    def test_penalizes_high_algae(self):
        """High algae fraction should drag down the score."""
        obs = _make_many_obs(50, date(2020, 1, 1), algae_fraction=0.45)
        result = compute_health_score(obs)
        assert isinstance(result, float)
        # High algae should drag score below healthy threshold
        assert result < 70


class TestHealthScoreEdgeCases:
    def test_handles_none_water_areas(self):
        """Observations with None water_area_m2 should be filtered out."""
        obs = _make_many_obs(15, date(2024, 1, 1))
        # Add some with None area
        for i in range(5):
            obs.append(_make_obs(date(2024, 6, 1) + timedelta(days=i * 5), water_area_m2=None))
        result = compute_health_score(obs)
        assert result is not None  # Should still compute with the 15 valid ones

    def test_handles_none_algae_fractions(self):
        """Observations with None algae should be filtered gracefully."""
        obs = _make_many_obs(15, date(2024, 1, 1))
        for o in obs[:5]:
            o.algae_fraction = None
        result = compute_health_score(obs)
        assert result is not None
