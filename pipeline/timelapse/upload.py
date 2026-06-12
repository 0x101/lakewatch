"""R2 upload for timelapse assets via S3-compatible boto3 client.

Uploads GIF, video, and thumbnail artifacts to Cloudflare R2 and
upserts TimelapseAsset records in the database. Handles missing
R2 credentials gracefully (logs warning, skips upload).
"""

import logging
import os
from pathlib import Path

import boto3
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pipeline.db.models import TimelapseAsset

logger = logging.getLogger(__name__)

# Content-type mapping for timelapse assets
CONTENT_TYPES = {
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webm": "video/webm",
}

# Asset filename mapping: asset_type -> filename template ({lake_id} substituted)
ASSET_MAP = {
    "gif-full": "{lake_id}-timelapse-full.gif",
    "gif-share": "{lake_id}-timelapse-share.gif",
    "video-full": "{lake_id}-timelapse-full.mp4",
    "video-share": "{lake_id}-timelapse-share.mp4",
    "thumbnail": "{lake_id}-thumbnail.png",
}


def get_r2_client():
    """Create a boto3 S3 client configured for Cloudflare R2.

    Reads R2_ENDPOINT, R2_ACCESS_KEY, and R2_SECRET_KEY from
    environment variables.

    Returns:
        boto3 S3 client configured for R2.

    Raises:
        KeyError: If required environment variables are missing.
    """
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["R2_SECRET_KEY"],
        region_name="auto",
    )


def upload_asset(
    client,
    local_path: Path,
    lake_id: str,
    asset_type: str,
) -> str:
    """Upload a single asset file to R2 and return its public URL.

    Args:
        client: boto3 S3 client (from get_r2_client).
        local_path: Path to the local file to upload.
        lake_id: Lake identifier for the R2 key prefix.
        asset_type: Asset type name (e.g., "gif-full", "thumbnail").

    Returns:
        Public URL of the uploaded asset.
    """
    local_path = Path(local_path)
    key = f"timelapse/{lake_id}/{asset_type}{local_path.suffix}"
    content_type = CONTENT_TYPES.get(
        local_path.suffix, "application/octet-stream"
    )

    client.upload_file(
        str(local_path),
        os.environ["R2_BUCKET"],
        key,
        ExtraArgs={"ContentType": content_type},
    )

    url = f"{os.environ['R2_PUBLIC_URL']}/{key}"
    logger.info("Uploaded %s -> %s", local_path.name, url)
    return url


def upload_timelapse_assets(
    client,
    output_dir: Path,
    lake_id: str,
    session,
) -> list[str]:
    """Upload all timelapse assets for a lake to R2 and upsert DB records.

    Scans output_dir for expected asset files (GIF full/share, video
    full/share, thumbnail). Uploads each found file and upserts a
    TimelapseAsset record with the R2 URL.

    Handles missing R2 credentials gracefully: if client is None,
    logs a warning and returns an empty list.

    Args:
        client: boto3 S3 client (or None if R2 not configured).
        output_dir: Directory containing the generated assets.
        lake_id: Lake identifier.
        session: SQLAlchemy database session.

    Returns:
        List of R2 public URLs for uploaded assets.
    """
    if client is None:
        logger.warning(
            "R2 credentials not configured, skipping upload for %s",
            lake_id,
        )
        return []

    urls = []
    output_dir = Path(output_dir)

    for asset_type, filename_template in ASSET_MAP.items():
        filename = filename_template.format(lake_id=lake_id)
        local_path = output_dir / filename

        if not local_path.exists():
            logger.debug("Asset not found, skipping: %s", local_path)
            continue

        url = upload_asset(client, local_path, lake_id, asset_type)
        file_size = local_path.stat().st_size

        # Upsert TimelapseAsset record
        stmt = pg_insert(TimelapseAsset).values(
            lake_id=lake_id,
            asset_type=asset_type,
            r2_url=url,
            file_size_bytes=file_size,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["lake_id", "asset_type"],
            set_={
                "r2_url": stmt.excluded.r2_url,
                "file_size_bytes": stmt.excluded.file_size_bytes,
            },
        )
        session.execute(stmt)
        urls.append(url)

    session.commit()
    logger.info(
        "Uploaded %d assets for lake %s to R2", len(urls), lake_id
    )
    return urls
