"""Extension registry — your city's extra data sources mount here.

LakeWatch ships with a generic satellite pipeline: water area + algae
estimates for every lake. Most cities also have their *own* local data —
water-board lab measurements, field surveys, drainage/stream networks,
custodian records. Rather than fork the core, you mount that data through
this seam.

`main.py` calls `register_extensions(app)` by name and never references any
city-specific router directly. That keeps the shared files identical to
upstream, so pulling new LakeWatch releases stays conflict-free.

To add your city's data:

1. Add ORM models in `pipeline/db/models_ext.py` (the shared `models.py`
   imports it through a try/except and exposes `HAS_CITY_EXTENSIONS`).
2. Write routers under `backend/app/routers/` for your endpoints.
3. Mount them here:

       from app.routers.my_city import router as my_city_router

       def register_extensions(app: FastAPI) -> None:
           app.include_router(my_city_router)

The reference implementation is Bangalore Lake Watch (nammalakes.com),
which mounts water-quality lab data, field-survey ground truth, and the
storm-drain stream network through this exact seam.
"""

from fastapi import FastAPI


def register_extensions(app: FastAPI) -> None:
    """Mount city-specific routers onto the FastAPI app.

    No-op in the upstream LakeWatch build. Override per the module docstring
    to wire in your city's own data sources.
    """
    return None
