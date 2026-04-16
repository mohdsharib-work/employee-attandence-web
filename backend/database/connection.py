# ─────────────────────────────────────────────
#  backend/database/connection.py
#  Async SQLAlchemy engine configured for:
#    - Turso (libSQL) in production
#    - Local SQLite file in development
# ─────────────────────────────────────────────

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from config.settings import settings


def _build_engine():
    url = settings.DATABASE_URL
    token = settings.DATABASE_AUTH_TOKEN

    # ── Turso (libSQL) in production ───────────────────────────────────────
    # Turso URLs look like: libsql://your-db.turso.io
    if url.startswith("libsql://") or url.startswith("https://"):
        from libsql_client import create_client  # noqa: F401
        # SQLAlchemy does not natively support libsql; use the libsql driver URL format
        connect_url = url.replace("libsql://", "sqlite+libsql://", 1)
        return create_async_engine(
            connect_url,
            connect_args={"auth_token": token},
            echo=settings.DEBUG,
        )

    # ── Local SQLite file (development) ────────────────────────────────────
    # DATABASE_URL examples:
    #   file:./attendance.db   →  relative path
    #   file:/abs/path/db      →  absolute path
    if url.startswith("file:"):
        path = url[5:]          # strip the "file:" prefix
        sqlite_url = f"sqlite+aiosqlite:///{path}"
        return create_async_engine(
            sqlite_url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False},
        )

    # ── Fallback: pass the URL through as-is ───────────────────────────────
    return create_async_engine(url, echo=settings.DEBUG)


engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def create_tables():
    """Create all tables on startup. Use Alembic migrations for schema changes."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
