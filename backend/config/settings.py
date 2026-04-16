# ─────────────────────────────────────────────
#  backend/config/settings.py
#  All configuration driven by environment variables.
#  For local dev, create a backend/.env file.
# ─────────────────────────────────────────────

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME:    str  = "Face Attendance API"
    APP_VERSION: str  = "1.0.0"
    DEBUG:       bool = False

    # ── Database (Turso / libSQL) ─────────────────────────────────────────────
    # Set these in Render's environment variables dashboard.
    # For local dev, use: DATABASE_URL=file:./attendance.db  (no auth token needed)
    DATABASE_URL:        str = "file:./attendance.db"
    DATABASE_AUTH_TOKEN: str = ""          # leave empty for local SQLite file

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    SECRET_KEY:                  str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM:                   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS:   int = 7

    # ── Desktop App API Key ───────────────────────────────────────────────────
    DESKTOP_API_KEY: str = "dev-api-key-change-me"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In production, set ALLOWED_ORIGINS to your Vercel frontend URL, e.g.:
    # ALLOWED_ORIGINS=https://your-app.vercel.app
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:3000",
    ]

    class Config:
        env_file = ".env"
        extra    = "ignore"


settings = Settings()
