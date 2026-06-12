"""Tests for backfill checkpoint logic and year-by-year processing."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pipeline.satellite.backfill import (
    CHECKPOINT_FILE,
    backfill_lake,
    load_checkpoint,
    save_checkpoint,
)


class TestCheckpointPersistence:
    """Tests for checkpoint load/save operations."""

    def test_load_checkpoint_empty(self, tmp_path):
        """When checkpoint file doesn't exist, returns empty set."""
        fake_checkpoint = tmp_path / "checkpoint.json"
        with patch("pipeline.satellite.backfill.CHECKPOINT_FILE", fake_checkpoint):
            result = load_checkpoint("bellandur-lake")
        assert result == set()

    def test_save_and_load_checkpoint(self, tmp_path):
        """Saving multiple years and loading returns them all."""
        fake_checkpoint = tmp_path / "checkpoint.json"
        with patch("pipeline.satellite.backfill.CHECKPOINT_FILE", fake_checkpoint):
            save_checkpoint("bellandur-lake", 2020)
            save_checkpoint("bellandur-lake", 2021)
            result = load_checkpoint("bellandur-lake")

        assert result == {2020, 2021}

    def test_save_checkpoint_idempotent(self, tmp_path):
        """Saving the same year twice doesn't duplicate it."""
        fake_checkpoint = tmp_path / "checkpoint.json"
        with patch("pipeline.satellite.backfill.CHECKPOINT_FILE", fake_checkpoint):
            save_checkpoint("bellandur-lake", 2020)
            save_checkpoint("bellandur-lake", 2020)
            data = json.loads(fake_checkpoint.read_text())

        assert data["bellandur-lake"].count(2020) == 1

    def test_save_checkpoint_multiple_lakes(self, tmp_path):
        """Checkpoints for different lakes are independent."""
        fake_checkpoint = tmp_path / "checkpoint.json"
        with patch("pipeline.satellite.backfill.CHECKPOINT_FILE", fake_checkpoint):
            save_checkpoint("bellandur-lake", 2020)
            save_checkpoint("ulsoor-lake", 2021)
            bellandur = load_checkpoint("bellandur-lake")
            ulsoor = load_checkpoint("ulsoor-lake")

        assert bellandur == {2020}
        assert ulsoor == {2021}


class TestBackfillLake:
    """Tests for the year-by-year backfill orchestration."""

    @patch("pipeline.satellite.backfill.upsert_observations")
    @patch("pipeline.satellite.backfill.filter_cloudy")
    @patch("pipeline.satellite.backfill.extract_observations_for_year")
    def test_backfill_skips_completed_years(
        self, mock_extract, mock_filter, mock_upsert, tmp_path
    ):
        """Years already in checkpoint are skipped entirely."""
        fake_checkpoint = tmp_path / "checkpoint.json"

        # Pre-save checkpoints for 2015 and 2016
        fake_checkpoint.write_text(
            json.dumps({"bellandur-lake": [2015, 2016]})
        )

        mock_extract.return_value = [{"date": "2017-01-05", "cloud_pct": 0.1}]
        mock_filter.return_value = [{"date": "2017-01-05", "cloud_pct": 0.1}]
        mock_upsert.return_value = 1

        mock_session = MagicMock()
        mock_geometry = MagicMock()

        with patch("pipeline.satellite.backfill.CHECKPOINT_FILE", fake_checkpoint):
            result = backfill_lake(
                "bellandur-lake", mock_geometry,
                start_year=2015, end_year=2017, session=mock_session
            )

        # extract should only be called for 2017 (2015 and 2016 skipped)
        assert mock_extract.call_count == 1
        mock_extract.assert_called_once_with(mock_geometry, 2017)

        assert 2017 in result["years_completed"]
        assert result["total_observations"] == 1

    @patch("pipeline.satellite.backfill.save_checkpoint")
    @patch("pipeline.satellite.backfill.upsert_observations")
    @patch("pipeline.satellite.backfill.filter_cloudy")
    @patch("pipeline.satellite.backfill.extract_observations_for_year")
    @patch("pipeline.satellite.backfill.load_checkpoint")
    def test_backfill_continues_on_year_failure(
        self, mock_load_cp, mock_extract, mock_filter, mock_upsert, mock_save_cp
    ):
        """A failure in one year doesn't block other years."""
        mock_load_cp.return_value = set()

        def extract_side_effect(geometry, year):
            if year == 2016:
                raise RuntimeError("GEE timeout for 2016")
            return [{"date": f"{year}-01-05", "cloud_pct": 0.1}]

        mock_extract.side_effect = extract_side_effect
        mock_filter.return_value = [{"date": "2015-01-05", "cloud_pct": 0.1}]
        mock_upsert.return_value = 1

        mock_session = MagicMock()
        mock_geometry = MagicMock()

        result = backfill_lake(
            "bellandur-lake", mock_geometry,
            start_year=2015, end_year=2017, session=mock_session
        )

        assert 2016 in result["years_failed"]
        assert 2015 in result["years_completed"]
        assert 2017 in result["years_completed"]
        assert result["total_observations"] == 2
