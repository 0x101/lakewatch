"""End-to-end timelapse generation CLI.

Single command that orchestrates: frame selection -> GEE export ->
frame rendering -> TimelapseFrame upsert -> GIF/video assembly ->
R2 upload. Produces a lake's complete timelapse from database
observations to shareable artifacts.

Usage:
    python -m pipeline.timelapse.cli my-lake-id
    python -m pipeline.timelapse.cli my-lake-id --skip-upload
    python -m pipeline.timelapse.cli my-lake-id --skip-export --skip-upload
"""

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from pipeline.db.database import get_session
from pipeline.db.models import Lake, TimelapseFrame
from pipeline.gee.auth import initialize_gee
from pipeline.satellite.extract import lake_to_ee_geometry
from pipeline.timelapse.assemble import (
    generate_gif_versions,
    generate_thumbnail,
    generate_video_versions,
)
from pipeline.timelapse.export import (
    export_observation_geotiff,
    get_image_for_date,
)
from pipeline.timelapse.render import render_frame
from pipeline.timelapse.select import select_best_per_month
from pipeline.timelapse.upload import get_r2_client, upload_timelapse_assets

logger = logging.getLogger(__name__)


def generate_timelapse(
    lake_id: str,
    output_dir: Path | None = None,
    music_path: Path | None = None,
    skip_upload: bool = False,
    skip_export: bool = False,
) -> dict:
    """Generate a complete timelapse for a lake.

    Orchestrates the full pipeline from database observations to
    uploaded GIF/video artifacts. Supports --skip-export for iteration
    (reuses existing frames) and --skip-upload for local-only runs.

    Args:
        lake_id: Lake identifier (slug, e.g., "my-lake-id").
        output_dir: Base output directory. Defaults to pipeline/data.
        music_path: Optional path to background music MP3 for video.
        skip_upload: If True, skip R2 upload step.
        skip_export: If True, skip GEE export (use existing frames).

    Returns:
        Summary dict with keys: lake_id, lake_name, frame_count,
        gif_full_path, gif_share_path, video_full_path, video_share_path,
        thumbnail_path, r2_urls.
    """
    # Step 0: Initialize GEE (only needed for export)
    if not skip_export:
        initialize_gee()

    # Step 1: Query database for lake record
    session = get_session()
    lake = session.query(Lake).filter_by(id=lake_id).first()
    if lake is None:
        raise ValueError(f"Lake not found: {lake_id}")

    lake_name = lake.name
    logger.info("Generating timelapse for %s (%s)", lake_name, lake_id)

    # Step 2: Select best observation per month
    observations = select_best_per_month(session, lake_id)
    logger.info("Selected %d observations for timelapse", len(observations))

    # Step 3: Create output directories
    if output_dir is None:
        output_dir = Path("pipeline/data")
    output_dir = Path(output_dir)
    frames_dir = output_dir / "frames" / lake_id
    assets_dir = output_dir / "assets" / lake_id
    frames_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Step 4: Export and render frames
    if not skip_export:
        geometry = lake_to_ee_geometry(lake)
        geotiff_dir = frames_dir / "geotiff"
        geotiff_dir.mkdir(parents=True, exist_ok=True)

        skipped = 0
        for i, obs in enumerate(observations, 1):
            obs_date = obs["observation_date"]
            date_str = (
                obs_date.strftime("%Y-%m-%d")
                if isinstance(obs_date, datetime)
                or hasattr(obs_date, "strftime")
                else str(obs_date)
            )
            logger.info(
                "Exporting frame %d/%d: %s", i, len(observations), date_str
            )

            try:
                image = get_image_for_date(geometry, date_str)
                geotiff_path = export_observation_geotiff(
                    image, geometry, date_str, geotiff_dir
                )
                render_frame(
                    geotiff_path,
                    frames_dir / f"{date_str}.png",
                    lake_name,
                    date_str,
                )
            except Exception as e:
                logger.warning("Skipping frame %s: %s", date_str, e)
                skipped += 1
                continue

            if i < len(observations):
                time.sleep(1.5)

        if skipped:
            logger.info(
                "Skipped %d/%d frames due to missing imagery",
                skipped, len(observations),
            )

    # Step 5: Collect all rendered PNG paths (sorted = chronological)
    frame_paths = sorted(frames_dir.glob("*.png"))
    if not frame_paths:
        raise RuntimeError(
            f"No rendered frames found in {frames_dir}. "
            "Run without --skip-export first."
        )
    logger.info("Found %d rendered frames", len(frame_paths))

    # Step 4b: Upsert TimelapseFrame records for each rendered frame
    for idx, frame_path in enumerate(frame_paths):
        # Extract date from filename (YYYY-MM-DD.png)
        date_str = frame_path.stem
        try:
            obs_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning("Skipping non-date filename: %s", frame_path.name)
            continue

        stmt = pg_insert(TimelapseFrame).values(
            lake_id=lake_id,
            observation_date=obs_date,
            frame_url=str(frame_path),
            frame_order=idx,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["lake_id", "observation_date"],
            set_={
                "frame_url": stmt.excluded.frame_url,
                "frame_order": stmt.excluded.frame_order,
            },
        )
        session.execute(stmt)

    session.commit()
    logger.info(
        "Upserted %d TimelapseFrame records for lake %s",
        len(frame_paths),
        lake_id,
    )

    # Step 6: Generate GIF versions
    gif_full_path, gif_share_path = generate_gif_versions(
        frame_paths, assets_dir, lake_id
    )

    # Step 7: Generate thumbnail
    thumbnail_path = generate_thumbnail(
        frame_paths, assets_dir / f"{lake_id}-thumbnail.png"
    )

    # Step 8: Generate video versions
    video_full_path, video_share_path = generate_video_versions(
        frames_dir, assets_dir, lake_id, music_path=music_path
    )

    # Step 9: Upload to R2
    r2_urls = []
    if not skip_upload:
        try:
            client = get_r2_client()
        except KeyError:
            logger.warning(
                "R2 credentials not configured, skipping upload"
            )
            client = None
        r2_urls = upload_timelapse_assets(
            client, assets_dir, lake_id, session
        )

    # Step 10: Log summary
    gif_full_size = gif_full_path.stat().st_size / (1024 * 1024)
    gif_share_size = gif_share_path.stat().st_size / (1024 * 1024)
    logger.info(
        "Timelapse complete for %s: %d frames, GIF full=%.1fMB, share=%.1fMB",
        lake_name,
        len(frame_paths),
        gif_full_size,
        gif_share_size,
    )

    session.close()

    return {
        "lake_id": lake_id,
        "lake_name": lake_name,
        "frame_count": len(frame_paths),
        "gif_full_path": gif_full_path,
        "gif_share_path": gif_share_path,
        "video_full_path": video_full_path,
        "video_share_path": video_share_path,
        "thumbnail_path": thumbnail_path,
        "r2_urls": r2_urls,
    }


def main():
    """CLI entry point for timelapse generation."""
    parser = argparse.ArgumentParser(
        description="Generate a complete timelapse for a lake."
    )
    parser.add_argument(
        "lake_id",
        help="Lake identifier (slug, e.g., my-lake-id)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Base output directory (default: pipeline/data)",
    )
    parser.add_argument(
        "--music",
        type=Path,
        default=None,
        help="Path to background music MP3 for video",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip R2 upload step",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip GEE export (use existing frames)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    result = generate_timelapse(
        lake_id=args.lake_id,
        output_dir=args.output_dir,
        music_path=args.music,
        skip_upload=args.skip_upload,
        skip_export=args.skip_export,
    )

    print(f"\nTimelapse complete for {result['lake_name']}:")
    print(f"  Frames:     {result['frame_count']}")
    print(f"  GIF (full): {result['gif_full_path']}")
    print(f"  GIF (share):{result['gif_share_path']}")
    print(f"  Video (full):{result['video_full_path']}")
    print(f"  Video (share):{result['video_share_path']}")
    print(f"  Thumbnail:  {result['thumbnail_path']}")
    if result["r2_urls"]:
        print(f"  R2 URLs:    {len(result['r2_urls'])} uploaded")
        for url in result["r2_urls"]:
            print(f"    - {url}")


if __name__ == "__main__":
    main()
