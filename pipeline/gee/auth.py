"""Google Earth Engine service account authentication.

Provides headless GEE initialization using a service account JSON key file.
No browser popup -- suitable for CI/CD and server environments.
"""

import os
from pathlib import Path

import ee
from dotenv import load_dotenv


def initialize_gee() -> None:
    """Initialize GEE with service account credentials from .env.

    Reads GEE_PROJECT_ID and GEE_SERVICE_ACCOUNT_KEY from environment.
    Raises FileNotFoundError if the key file doesn't exist.
    Raises ee.EEException if authentication or project registration fails.
    """
    load_dotenv()

    project_id = os.getenv("GEE_PROJECT_ID")
    if not project_id:
        raise ValueError(
            "GEE_PROJECT_ID not set in environment. "
            "Add it to .env (e.g., GEE_PROJECT_ID=your-gee-project)"
        )

    key_path = os.getenv("GEE_SERVICE_ACCOUNT_KEY")
    if not key_path:
        raise ValueError(
            "GEE_SERVICE_ACCOUNT_KEY not set in environment. "
            "Add the path to your service account JSON key file in .env"
        )

    key_file = Path(key_path).expanduser()
    if not key_file.exists():
        raise FileNotFoundError(
            f"GEE service account key not found at: {key_file}\n"
            f"Download it from Google Cloud Console > IAM > Service Accounts > Keys"
        )

    credentials = ee.ServiceAccountCredentials(
        email=None,  # Auto-extracted from key file
        key_file=str(key_file),
    )
    ee.Initialize(credentials=credentials, project=project_id)


def verify_gee_connection() -> dict:
    """Verify GEE works by querying one Sentinel-2 image over a sample bbox.

    Calls initialize_gee() first, then fetches one Sentinel-2 image's metadata
    for a small bounding box, confirming auth and data access end-to-end.

    Returns:
        dict with keys: id (image ID), bands (list of band names),
        date (from GENERATION_TIME property)

    Raises:
        Exception if GEE auth fails or query returns no results.
    """
    initialize_gee()

    # A small sample bounding box (lon/lat) used only to confirm data access.
    # Override with GEE_VERIFY_BBOX=min_lng,min_lat,max_lng,max_lat; the default
    # is just a connectivity-check example — any bbox with Sentinel-2 coverage works.
    bbox_env = os.getenv("GEE_VERIFY_BBOX")
    if bbox_env:
        coords = [float(v) for v in bbox_env.split(",")]
        if len(coords) != 4:
            raise ValueError(
                "GEE_VERIFY_BBOX must be 4 comma-separated numbers: "
                "min_lng,min_lat,max_lng,max_lat"
            )
    else:
        coords = [77.63, 12.92, 77.70, 12.95]
    bbox = ee.Geometry.Rectangle(coords)

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(bbox)
        .filterDate("2024-01-01", "2024-01-31")
        .limit(1)
    )

    image = collection.first()
    info = image.getInfo()

    if info is None:
        raise RuntimeError(
            "No Sentinel-2 images found for the sample bbox in "
            "2024-01-01 to 2024-01-31. "
            "Check that the Earth Engine API is enabled for your project."
        )

    return {
        "id": info["id"],
        "bands": [b["id"] for b in info["bands"]],
        "date": info["properties"].get("GENERATION_TIME"),
    }
