"""Tests for R2 timelapse asset upload module."""

from unittest.mock import MagicMock, patch

import pytest


@patch.dict("os.environ", {}, clear=True)
def test_get_r2_client_requires_env_vars():
    """get_r2_client raises KeyError when R2_ENDPOINT is missing."""
    from pipeline.timelapse.upload import get_r2_client

    with pytest.raises(KeyError):
        get_r2_client()


@patch.dict(
    "os.environ",
    {
        "R2_ENDPOINT": "https://r2.example.com",
        "R2_ACCESS_KEY": "test-key",
        "R2_SECRET_KEY": "test-secret",
        "R2_BUCKET": "test-bucket",
        "R2_PUBLIC_URL": "https://pub.r2.example.com",
    },
)
@patch("pipeline.timelapse.upload.boto3")
def test_upload_asset_calls_boto3(mock_boto3, tmp_path):
    """upload_asset calls boto3 upload_file with correct params."""
    from pipeline.timelapse.upload import upload_asset

    mock_client = MagicMock()
    test_file = tmp_path / "test.gif"
    test_file.write_bytes(b"GIF89a" + b"\x00" * 100)

    upload_asset(mock_client, test_file, "bellandur-lake", "gif-full")

    mock_client.upload_file.assert_called_once_with(
        str(test_file),
        "test-bucket",
        "timelapse/bellandur-lake/gif-full.gif",
        ExtraArgs={"ContentType": "image/gif"},
    )


@patch.dict(
    "os.environ",
    {
        "R2_ENDPOINT": "https://r2.example.com",
        "R2_ACCESS_KEY": "test-key",
        "R2_SECRET_KEY": "test-secret",
        "R2_BUCKET": "test-bucket",
        "R2_PUBLIC_URL": "https://pub.r2.example.com",
    },
)
def test_upload_asset_constructs_url(tmp_path):
    """upload_asset returns correctly formatted R2 public URL."""
    from pipeline.timelapse.upload import upload_asset

    mock_client = MagicMock()
    test_file = tmp_path / "test.gif"
    test_file.write_bytes(b"GIF89a" + b"\x00" * 100)

    url = upload_asset(mock_client, test_file, "bellandur-lake", "gif-full")

    assert url == "https://pub.r2.example.com/timelapse/bellandur-lake/gif-full.gif"


@patch.dict(
    "os.environ",
    {
        "R2_ENDPOINT": "https://r2.example.com",
        "R2_ACCESS_KEY": "test-key",
        "R2_SECRET_KEY": "test-secret",
        "R2_BUCKET": "test-bucket",
        "R2_PUBLIC_URL": "https://pub.r2.example.com",
    },
)
def test_upload_timelapse_assets_skips_missing_files(tmp_path):
    """upload_timelapse_assets only uploads files that exist."""
    from pipeline.timelapse.upload import upload_timelapse_assets

    mock_client = MagicMock()
    mock_session = MagicMock()

    # Only create the gif-full file
    gif_file = tmp_path / "bellandur-lake-timelapse-full.gif"
    gif_file.write_bytes(b"GIF89a" + b"\x00" * 100)

    urls = upload_timelapse_assets(
        mock_client, tmp_path, "bellandur-lake", mock_session
    )

    # Only 1 file existed, so only 1 upload
    assert len(urls) == 1
    assert mock_client.upload_file.call_count == 1
    mock_session.commit.assert_called_once()


def test_upload_graceful_without_credentials(tmp_path):
    """upload_timelapse_assets returns empty list when client is None."""
    from pipeline.timelapse.upload import upload_timelapse_assets

    mock_session = MagicMock()

    urls = upload_timelapse_assets(
        None, tmp_path, "bellandur-lake", mock_session
    )

    assert urls == []
    mock_session.commit.assert_not_called()


@patch.dict(
    "os.environ",
    {
        "R2_ENDPOINT": "https://r2.example.com",
        "R2_ACCESS_KEY": "test-key",
        "R2_SECRET_KEY": "test-secret",
        "R2_BUCKET": "test-bucket",
        "R2_PUBLIC_URL": "https://pub.r2.example.com",
    },
)
def test_upload_asset_mp4_content_type(tmp_path):
    """upload_asset uses video/mp4 content-type for .mp4 files."""
    from pipeline.timelapse.upload import upload_asset

    mock_client = MagicMock()
    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(b"\x00" * 100)

    upload_asset(mock_client, test_file, "bellandur-lake", "video-full")

    mock_client.upload_file.assert_called_once_with(
        str(test_file),
        "test-bucket",
        "timelapse/bellandur-lake/video-full.mp4",
        ExtraArgs={"ContentType": "video/mp4"},
    )
