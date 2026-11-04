"""Tests for incremental ingestion script."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


from pipeline.scripts.incremental_ingest import (
    incremental_ingest_all,
    incremental_ingest_lake,
)


def _make_mock_lake(lake_id, area=50.0):
    """Create a mock Lake object."""
    return SimpleNamespace(
        id=lake_id,
        name=lake_id.replace("-", " ").title(),
        area_hectares=area,
        boundary=MagicMock(),
    )


class TestIncrementalIngestLake:
    """Tests for incremental_ingest_lake."""

    @patch("pipeline.scripts.incremental_ingest.lake_to_ee_geometry")
    def test_skips_no_prior_observations(self, mock_geometry):
        """Lakes with no prior observations should be skipped."""
        lake = _make_mock_lake("new-lake")
        session = MagicMock()
        session.query.return_value.filter_by.return_value.scalar.return_value = None

        result = incremental_ingest_lake(lake, session)

        assert result == 0
        mock_geometry.assert_not_called()

    @patch("pipeline.scripts.incremental_ingest.date")
    @patch("pipeline.scripts.incremental_ingest.upsert_observations")
    @patch("pipeline.scripts.incremental_ingest.filter_cloudy")
    @patch("pipeline.scripts.incremental_ingest.extract_observations_for_year")
    @patch("pipeline.scripts.incremental_ingest.lake_to_ee_geometry")
    def test_processes_since_last_date(
        self, mock_geometry, mock_extract, mock_filter, mock_upsert, mock_date,
    ):
        """Should only process observations after latest_observation_date."""
        # Pin "today" to 2025-08-01 so only year 2025 is extracted
        mock_date.today.return_value = date(2025, 8, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        lake = _make_mock_lake("bellandur-lake")
        session = MagicMock()
        session.query.return_value.filter_by.return_value.scalar.return_value = date(2025, 6, 15)

        mock_geometry.return_value = MagicMock()
        mock_extract.return_value = [
            {"date": "2025-06-10", "cloud_pct": 0.05},  # Before cutoff - should be filtered
            {"date": "2025-06-20", "cloud_pct": 0.05},  # After cutoff - should be kept
            {"date": "2025-07-01", "cloud_pct": 0.05},  # After cutoff - should be kept
        ]
        mock_filter.return_value = [
            {"date": "2025-06-20", "cloud_pct": 0.05},
            {"date": "2025-07-01", "cloud_pct": 0.05},
        ]
        mock_upsert.return_value = 2

        result = incremental_ingest_lake(lake, session)

        assert result == 2
        # filter_cloudy should receive only observations after the cutoff
        filter_call_args = mock_filter.call_args[0][0]
        for obs in filter_call_args:
            assert obs["date"] >= "2025-06-16"

    @patch("pipeline.scripts.incremental_ingest.lake_to_ee_geometry")
    def test_no_new_dates(self, mock_geometry):
        """If latest_observation_date is today, return 0 early."""
        lake = _make_mock_lake("bellandur-lake")
        session = MagicMock()
        session.query.return_value.filter_by.return_value.scalar.return_value = date.today()

        result = incremental_ingest_lake(lake, session)

        assert result == 0
        mock_geometry.assert_not_called()

    @patch("pipeline.scripts.incremental_ingest.upsert_observations")
    @patch("pipeline.scripts.incremental_ingest.filter_cloudy")
    @patch("pipeline.scripts.incremental_ingest.extract_observations_for_year")
    @patch("pipeline.scripts.incremental_ingest.lake_to_ee_geometry")
    def test_spans_multiple_years(
        self, mock_geometry, mock_extract, mock_filter, mock_upsert,
    ):
        """If last observation was in a previous year, extract for both years."""
        lake = _make_mock_lake("bellandur-lake")
        session = MagicMock()
        session.query.return_value.filter_by.return_value.scalar.return_value = date(2024, 11, 1)

        mock_geometry.return_value = MagicMock()
        mock_extract.return_value = [{"date": "2025-01-05", "cloud_pct": 0.1}]
        mock_filter.return_value = [{"date": "2025-01-05", "cloud_pct": 0.1}]
        mock_upsert.return_value = 1

        with patch("pipeline.scripts.incremental_ingest.date") as mock_date:
            mock_date.today.return_value = date(2025, 3, 1)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            result = incremental_ingest_lake(lake, session)

        # Should have called extract for both 2024 and 2025
        assert mock_extract.call_count == 2


class TestIncrementalIngestAll:
    """Tests for incremental_ingest_all."""

    @patch("pipeline.scripts.incremental_ingest.refresh_lake_stats")
    @patch("pipeline.scripts.incremental_ingest.incremental_ingest_lake")
    @patch("pipeline.scripts.incremental_ingest.get_session")
    @patch("pipeline.scripts.incremental_ingest.initialize_gee")
    def test_calls_refresh_after_each_lake(
        self, mock_gee, mock_get_session, mock_ingest, mock_refresh,
    ):
        """refresh_lake_stats should be called for each lake after ingestion."""
        session = MagicMock()
        mock_get_session.return_value = session
        lakes = [_make_mock_lake(f"lake-{i}") for i in range(3)]
        session.query.return_value.order_by.return_value.limit.return_value.all.return_value = lakes
        mock_ingest.return_value = 5

        result = incremental_ingest_all(lake_limit=3)

        assert mock_refresh.call_count == 3
        for lake in lakes:
            mock_refresh.assert_any_call(lake.id, session=session)


class TestIncrementalMonthWindow:
    """Only months that can hold new imagery are queried from GEE."""

    @patch("pipeline.scripts.incremental_ingest.date")
    @patch("pipeline.scripts.incremental_ingest.upsert_observations", return_value=0)
    @patch("pipeline.scripts.incremental_ingest.filter_cloudy", side_effect=lambda o: o)
    @patch("pipeline.scripts.incremental_ingest.extract_observations_for_year", return_value=[])
    @patch("pipeline.scripts.incremental_ingest.lake_to_ee_geometry")
    def test_months_span_year_boundary(self, _geom, mock_extract, _f, _u, mock_date):
        mock_date.today.return_value = date(2026, 2, 10)
        lake = _make_mock_lake("x")
        session = MagicMock()
        session.query.return_value.filter_by.return_value.scalar.return_value = date(2025, 11, 20)

        incremental_ingest_lake(lake, session)

        calls = [(c.args[1], list(c.kwargs["months"])) for c in mock_extract.call_args_list]
        assert calls == [(2025, [11, 12]), (2026, [1, 2])]


@patch("pipeline.scripts.incremental_ingest.refresh_lake_stats")
@patch("pipeline.scripts.incremental_ingest.incremental_ingest_lake")
@patch("pipeline.scripts.incremental_ingest.get_session")
@patch("pipeline.scripts.incremental_ingest.initialize_gee")
def test_failed_lake_rolls_back_and_others_continue(_gee, mock_get_session, mock_lake, _refresh):
    session = MagicMock()
    mock_get_session.return_value = session
    lakes = [_make_mock_lake("a"), _make_mock_lake("b")]
    session.query.return_value.order_by.return_value.all.return_value = lakes
    mock_lake.side_effect = [RuntimeError("boom"), 3]

    summary = incremental_ingest_all()

    session.rollback.assert_called_once()
    assert summary["results"]["a"]["status"] == "error"
    assert summary["results"]["b"] == {"observations": 3, "status": "ok"}
