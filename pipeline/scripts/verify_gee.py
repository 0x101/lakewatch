"""Verify Google Earth Engine authentication and data access.

Usage:
    python -m pipeline.scripts.verify_gee
"""

import sys


def main() -> None:
    try:
        from pipeline.gee.auth import verify_gee_connection

        result = verify_gee_connection()

        print("GEE Authentication: OK")
        print(f"Image ID: {result['id']}")
        print(f"Bands: {result['bands']}")
        print(f"Date: {result['date']}")

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print(
            "\nCheck that GEE_SERVICE_ACCOUNT_KEY path exists",
            file=sys.stderr,
        )
        sys.exit(1)

    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print(
            "\nTroubleshooting:",
            file=sys.stderr,
        )
        print(
            "  - Check that GEE_SERVICE_ACCOUNT_KEY path exists",
            file=sys.stderr,
        )
        print(
            "  - Check that Earth Engine API is enabled for your GEE project "
            "(GEE_PROJECT_ID)",
            file=sys.stderr,
        )
        print(
            "  - Visit https://code.earthengine.google.com/ to register the Cloud project",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
