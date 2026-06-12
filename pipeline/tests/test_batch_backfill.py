"""Tests for batch backfill orchestrator script."""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from pipeline.scripts.batch_backfill import batch_backfill, get_top_lakes


def _make_mock_lake(lake_id, area):
    """Create a mock Lake object."""
    lake = SimpleNamespace(
        id=lake_id,
        name=lake_id.replace("-", " ").title(),
        area_hectares=area,
        boundary=MagicMock(),
    )
    return lake


class TestGetTopLakes:
    """Tests for get_top_lakes query."""

    def test_returns_lakes_ordered_by_area(self):
        """Should query lakes ordered by area_hectares descending."""
        mock_session = MagicMock()
        lakes = [_make_mock_lake(f"lake-{i}", 100 - i) for i in range(5)]
        mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = lakes

        result = get_top_lakes(mock_session, limit=5)
        assert len(result) == 5
        mock_session.query.return_value.order_by.return_value.limit.assert_called_with(5)


class TestBatchBackfill:
    """Tests for the batch_backfill orchestrator."""

    @patch("pipeline.scripts.batch_backfill.refresh_lake_stats")
    @patch("pipeline.scripts.batch_backfill.backfill_lake")
    @patch("pipeline.scripts.batch_backfill.lake_to_ee_geometry")
    @patch("pipeline.scripts.batch_backfill.get_top_lakes")
    @patch("pipeline.scripts.batch_backfill.get_session")
    @patch("pipeline.scripts.batch_backfill.initialize_gee")
    def test_batch_processes_in_chunks(
        self, mock_gee, mock_get_session, mock_get_lakes,
        mock_geometry, mock_backfill, mock_refresh,
    ):
        """15 lakes with batch_size=5 should process in 3 batches with 2 sleeps."""
        lakes = [_make_mock_lake(f"lake-{i}", 100 - i) for i in range(15)]
        mock_get_lakes.return_value = lakes
        mock_get_session.return_value = MagicMock()
        mock_geometry.return_value = MagicMock()
        mock_backfill.return_value = {"lake_id": "", "total_observations": 10, "years_completed": [], "years_failed": []}

        with patch("pipeline.scripts.batch_backfill.time.sleep") as mock_sleep:
            result = batch_backfill(batch_size=5, pause_seconds=30, lake_limit=15)

        assert mock_backfill.call_count == 15
        assert mock_sleep.call_count == 2  # Between 3 batches
        mock_sleep.assert_called_with(30)

    @patch("pipeline.scripts.batch_backfill.refresh_lake_stats")
    @patch("pipeline.scripts.batch_backfill.backfill_lake")
    @patch("pipeline.scripts.batch_backfill.lake_to_ee_geometry")
    @patch("pipeline.scripts.batch_backfill.get_top_lakes")
    @patch("pipeline.scripts.batch_backfill.get_session")
    @patch("pipeline.scripts.batch_backfill.initialize_gee")
    def test_batch_respects_lake_limit(
        self, mock_gee, mock_get_session, mock_get_lakes,
        mock_geometry, mock_backfill, mock_refresh,
    ):
        """lake_limit should be passed through to get_top_lakes."""
        mock_get_lakes.return_value = []
        mock_get_session.return_value = MagicMock()

        batch_backfill(batch_size=10, pause_seconds=0, lake_limit=25)
        mock_get_lakes.assert_called_once_with(mock_get_session.return_value, limit=25)

    @patch("pipeline.scripts.batch_backfill.refresh_lake_stats")
    @patch("pipeline.scripts.batch_backfill.backfill_lake")
    @patch("pipeline.scripts.batch_backfill.lake_to_ee_geometry")
    @patch("pipeline.scripts.batch_backfill.get_top_lakes")
    @patch("pipeline.scripts.batch_backfill.get_session")
    @patch("pipeline.scripts.batch_backfill.initialize_gee")
    def test_batch_calls_refresh_after_each_lake(
        self, mock_gee, mock_get_session, mock_get_lakes,
        mock_geometry, mock_backfill, mock_refresh,
    ):
        """refresh_lake_stats should be called once per lake with correct lake_id."""
        lakes = [_make_mock_lake(f"lake-{i}", 100 - i) for i in range(3)]
        mock_get_lakes.return_value = lakes
        session = MagicMock()
        mock_get_session.return_value = session
        mock_geometry.return_value = MagicMock()
        mock_backfill.return_value = {"lake_id": "", "total_observations": 5, "years_completed": [], "years_failed": []}

        with patch("pipeline.scripts.batch_backfill.time.sleep"):
            batch_backfill(batch_size=10, pause_seconds=0, lake_limit=3)

        assert mock_refresh.call_count == 3
        for i, lake in enumerate(lakes):
            mock_refresh.assert_any_call(lake.id, session=session)

    @patch("pipeline.scripts.batch_backfill.refresh_lake_stats")
    @patch("pipeline.scripts.batch_backfill.backfill_lake")
    @patch("pipeline.scripts.batch_backfill.lake_to_ee_geometry")
    @patch("pipeline.scripts.batch_backfill.get_top_lakes")
    @patch("pipeline.scripts.batch_backfill.get_session")
    @patch("pipeline.scripts.batch_backfill.initialize_gee")
    def test_batch_handles_failure_gracefully(
        self, mock_gee, mock_get_session, mock_get_lakes,
        mock_geometry, mock_backfill, mock_refresh,
    ):
        """If one lake fails, others should still be processed."""
        lakes = [_make_mock_lake(f"lake-{i}", 100 - i) for i in range(3)]
        mock_get_lakes.return_value = lakes
        mock_get_session.return_value = MagicMock()
        mock_geometry.return_value = MagicMock()

        def backfill_side_effect(lake_id, geometry, session=None):
            if lake_id == "lake-1":
                raise RuntimeError("GEE timeout")
            return {"lake_id": lake_id, "total_observations": 5, "years_completed": [2020], "years_failed": []}

        mock_backfill.side_effect = backfill_side_effect

        with patch("pipeline.scripts.batch_backfill.time.sleep"):
            result = batch_backfill(batch_size=10, pause_seconds=0, lake_limit=3)

        assert "lake-1" in result["failed"]
        assert result["lakes_processed"] == 2
