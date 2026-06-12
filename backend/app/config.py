"""Application configuration."""

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/lakewatch")

# Comma-separated list of allowed CORS origins. Defaults to local dev.
# In production set CORS_ORIGINS to your frontend URL(s), e.g.
#   CORS_ORIGINS=https://yourcity.example.com,http://localhost:3000
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
