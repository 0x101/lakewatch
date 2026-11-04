"""Tests for lake_stats refresh module."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch



def _make_obs(obs_date, water_area_m2=150000.0, algae_fraction=0.05):
    return SimpleNamespace(
        observation_date=obs_date,
        water_area_m2=water_area_m2,
        mean_ndwi=0.45,
        algae_fraction=algae_fraction,
        cloud_pct=0.05,
    )


class TestRefreshLakeStats:
    @patch("pipeline.metrics.refresh.compute_derived_stats")
    @patch("pipeline.metrics.refresh.compute_health_score")
    def test_queries_observations_and_commits(
        self, mock_health, mock_derived
    ):
        """Refresh queries observations, computes metrics, and commits."""
        mock_health.return_value = 75.0
        mock_derived.return_value = {
            "area_change_1yr_pct": -5.0,
            "area_change_5yr_pct": -10.0,
            "seasonal_amplitude": 30000.0,
            "peak_algae_month": 8,
        }

        obs = [
            _make_obs(date(2024, 1, 5)),
            _make_obs(date(2024, 1, 15)),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = obs

        from pipeline.metrics.refresh import refresh_lake_stats

        result = refresh_lake_stats("bellandur-lake", session=mock_session)

        # Verify query was made for the right lake
        mock_query.filter_by.assert_called_once_with(lake_id="bellandur-lake")
        # Verify metrics were computed
        mock_health.assert_called_once_with(obs)
        mock_derived.assert_called_once_with(obs)
        # Verify session was committed
        mock_session.commit.assert_called_once()
        # Verify execute was called (upsert statement)
        mock_session.execute.assert_called_once()
        # Verify result structure
        assert result["lake_id"] == "bellandur-lake"
        assert result["health_score"] == 75.0
        assert result["observation_count"] == 2

    @patch("pipeline.metrics.refresh.compute_derived_stats")
    @patch("pipeline.metrics.refresh.compute_health_score")
    def test_handles_no_observations(self, mock_health, mock_derived):
        """Empty observation list produces None metrics."""
        mock_health.return_value = None
        mock_derived.return_value = {
            "area_change_1yr_pct": None,
            "area_change_5yr_pct": None,
            "seasonal_amplitude": None,
            "peak_algae_month": None,
        }

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        from pipeline.metrics.refresh import refresh_lake_stats

        result = refresh_lake_stats("empty-lake", session=mock_session)

        assert result["health_score"] is None
        assert result["observation_count"] == 0
        mock_session.commit.assert_called_once()

    @patch("pipeline.metrics.refresh.compute_derived_stats")
    @patch("pipeline.metrics.refresh.compute_health_score")
    def test_uses_upsert_with_on_conflict(self, mock_health, mock_derived):
        """Verify the SQL uses ON CONFLICT DO UPDATE on lake_id."""
        mock_health.return_value = 80.0
        mock_derived.return_value = {
            "area_change_1yr_pct": None,
            "area_change_5yr_pct": None,
            "seasonal_amplitude": None,
            "peak_algae_month": None,
        }

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [_make_obs(date(2024, 1, 5))]

        from pipeline.metrics.refresh import refresh_lake_stats

        refresh_lake_stats("test-lake", session=mock_session)

        # Get the executed statement
        call_args = mock_session.execute.call_args
        stmt = call_args[0][0]
        # The compiled statement should reference ON CONFLICT
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "ON CONFLICT" in compiled or "on_conflict" in str(type(stmt).__mro__)
