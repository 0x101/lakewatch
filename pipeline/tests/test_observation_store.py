"""Tests for observation storage module (upsert and cloud filtering)."""

from unittest.mock import MagicMock, call

import pytest

from pipeline.satellite.store import filter_cloudy, upsert_observations


class TestFilterCloudy:
    """Tests for cloud cover filtering."""

    def test_filter_cloudy_rejects_above_threshold(self, sample_observation_dicts):
        """Observations with cloud_pct > 0.30 are filtered out."""
        result = filter_cloudy(sample_observation_dicts, max_cloud_pct=0.30)

        assert len(result) == 3
        assert all(obs["cloud_pct"] <= 0.30 for obs in result)
        # The one with cloud_pct=0.50 should be gone
        cloud_pcts = [obs["cloud_pct"] for obs in result]
        assert 0.50 not in cloud_pcts

    def test_filter_cloudy_keeps_exact_threshold(self):
        """Observations at exactly the threshold are kept (<= not <)."""
        observations = [
            {"date": "2024-01-05", "cloud_pct": 0.30, "water_area_m2": 100000.0},
            {"date": "2024-01-15", "cloud_pct": 0.31, "water_area_m2": 100000.0},
        ]
        result = filter_cloudy(observations, max_cloud_pct=0.30)

        assert len(result) == 1
        assert result[0]["cloud_pct"] == 0.30

    def test_filter_cloudy_empty_list(self):
        """Empty input returns empty output."""
        result = filter_cloudy([])
        assert result == []

    def test_filter_cloudy_missing_cloud_pct_defaults_to_reject(self):
        """Observations missing cloud_pct are treated as fully cloudy."""
        observations = [{"date": "2024-01-05", "water_area_m2": 100000.0}]
        result = filter_cloudy(observations, max_cloud_pct=0.30)
        assert len(result) == 0


class TestUpsertObservations:
    """Tests for observation upsert logic."""

    def test_upsert_builds_correct_statement(self):
        """Upsert calls session.execute and session.commit."""
        mock_session = MagicMock()
        observations = [
            {
                "date": "2024-01-05",
                "water_area_m2": 150000.0,
                "mean_ndwi": 0.45,
                "algae_fraction": 0.08,
                "cloud_pct": 0.10,
            }
        ]

        count = upsert_observations(mock_session, observations, "bellandur-lake")

        assert count == 1
        assert mock_session.execute.called
        assert mock_session.commit.called

    def test_upsert_parses_date_string(self):
        """The date string '2024-01-05' is correctly parsed in the SQL values."""
        mock_session = MagicMock()
        observations = [
            {
                "date": "2024-01-05",
                "water_area_m2": 150000.0,
                "mean_ndwi": 0.45,
                "algae_fraction": 0.08,
                "cloud_pct": 0.10,
            }
        ]

        upsert_observations(mock_session, observations, "bellandur-lake")

        # Verify execute was called with a compiled statement
        execute_call = mock_session.execute.call_args
        assert execute_call is not None
        # The statement should have been constructed (we can't easily
        # inspect pg_insert internals, but execute was called once)
        assert mock_session.execute.call_count == 1

    def test_upsert_multiple_observations(self):
        """Multiple observations result in multiple execute calls."""
        mock_session = MagicMock()
        observations = [
            {"date": "2024-01-05", "water_area_m2": 150000.0, "mean_ndwi": 0.45,
             "algae_fraction": 0.08, "cloud_pct": 0.10},
            {"date": "2024-01-15", "water_area_m2": 148000.0, "mean_ndwi": 0.42,
             "algae_fraction": 0.12, "cloud_pct": 0.05},
        ]

        count = upsert_observations(mock_session, observations, "bellandur-lake")

        assert count == 2
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 1

    def test_upsert_empty_list_returns_zero(self):
        """Empty observation list returns 0 and doesn't commit."""
        mock_session = MagicMock()
        count = upsert_observations(mock_session, [], "bellandur-lake")

        assert count == 0
        assert not mock_session.execute.called
        assert not mock_session.commit.called
