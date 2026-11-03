"""Database engine and session factory.

`engine` is created lazily-by-URL: SQLAlchemy does not open a connection until
a session actually runs a query, so importing this module never requires a
live database. If `DATABASE_URL` is unset we fall back to a localhost
placeholder so imports (and unit tests that mock the DB) work; any real query
will still need a valid `DATABASE_URL`.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://localhost:5432/lakewatch"

# Hosted Postgres (Railway, Neon, ...) drops idle connections; pre-ping
# transparently replaces dead ones instead of failing the next request.
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_session():
    """Create and return a new database session."""
    return SessionLocal()
