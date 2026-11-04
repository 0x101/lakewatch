"""Unit tests for derived stats computation."""

from datetime import date, timedelta
from types import SimpleNamespace


from pipeline.metrics.derived_stats import compute_derived_stats


def _make_obs(obs_date, water_area_m2=150000.0, algae_fraction=0.05):
    """Helper to create observation-like objects."""
    return SimpleNamespace(
        observation_date=obs_date,
        water_area_m2=water_area_m2,
        algae_fraction=algae_fraction,
        mean_ndwi=0.45,
        cloud_pct=0.05,
    )


class TestAreaChange1yr:
    def test_area_change_1yr(self):
        """1yr area change should reflect median area difference."""
        obs = []
        # 2023 observations: median area = 100000
        for i in range(10):
            obs.append(_make_obs(date(2023, 3, 1) + timedelta(days=i * 5), water_area_m2=100000.0))
        # 2024 observations: median area = 90000
        for i in range(10):
            obs.append(_make_obs(date(2024, 3, 1) + timedelta(days=i * 5), water_area_m2=90000.0))
        result = compute_derived_stats(obs)
        assert result["area_change_1yr_pct"] is not None
        assert abs(result["area_change_1yr_pct"] - (-10.0)) < 2.0


class TestAreaChange5yr:
    def test_area_change_5yr(self):
        """5yr area change should reflect median area difference."""
        obs = []
        # 2019 observations: median area = 120000
        for i in range(10):
            obs.append(_make_obs(date(2019, 3, 1) + timedelta(days=i * 5), water_area_m2=120000.0))
        # 2024 observations: median area = 90000
        for i in range(10):
            obs.append(_make_obs(date(2024, 3, 1) + timedelta(days=i * 5), water_area_m2=90000.0))
        result = compute_derived_stats(obs)
        assert result["area_change_5yr_pct"] is not None
        assert abs(result["area_change_5yr_pct"] - (-25.0)) < 2.0


class TestSeasonalAmplitude:
    def test_seasonal_amplitude(self):
        """Max monthly avg minus min monthly avg."""
        obs = []
        # January observations: area 100000
        for i in range(5):
            obs.append(_make_obs(date(2024, 1, 1 + i), water_area_m2=100000.0))
        # July observations: area 150000
        for i in range(5):
            obs.append(_make_obs(date(2024, 7, 1 + i), water_area_m2=150000.0))
        result = compute_derived_stats(obs)
        assert result["seasonal_amplitude"] is not None
        assert abs(result["seasonal_amplitude"] - 50000.0) < 1.0


class TestPeakAlgaeMonth:
    def test_peak_algae_month(self):
        """Month with highest mean algae_fraction."""
        obs = []
        # March: high algae (0.40)
        for i in range(5):
            obs.append(_make_obs(date(2024, 3, 1 + i), algae_fraction=0.40))
        # Other months: low algae (0.10)
        for month in [1, 2, 4, 5, 6]:
            for i in range(3):
                obs.append(_make_obs(date(2024, month, 1 + i), algae_fraction=0.10))
        result = compute_derived_stats(obs)
        assert result["peak_algae_month"] == 3


class TestDerivedStatsEdgeCases:
    def test_handles_empty_list(self):
        """Empty list returns all None."""
        result = compute_derived_stats([])
        assert result["area_change_1yr_pct"] is None
        assert result["area_change_5yr_pct"] is None
        assert result["seasonal_amplitude"] is None
        assert result["peak_algae_month"] is None

    def test_handles_no_5yr_data(self):
        """Only 2 years of data: 5yr is None, 1yr is computed."""
        obs = []
        for i in range(10):
            obs.append(_make_obs(date(2023, 6, 1) + timedelta(days=i * 5), water_area_m2=100000.0))
        for i in range(10):
            obs.append(_make_obs(date(2024, 6, 1) + timedelta(days=i * 5), water_area_m2=95000.0))
        result = compute_derived_stats(obs)
        assert result["area_change_5yr_pct"] is None
        assert result["area_change_1yr_pct"] is not None
