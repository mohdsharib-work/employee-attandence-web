# ─────────────────────────────────────────────
#  backend/database/connection.py
#
#  Strategy:
#   - Turso (production)  → libsql_experimental native async client
#                           wrapped in a thin SQLAlchemy-compatible session shim
#   - Local SQLite (dev)  → standard SQLAlchemy async engine + aiosqlite
# ─────────────────────────────────────────────

import os
from typing import AsyncGenerator

from sqlalchemy.orm import DeclarativeBase

from config.settings import settings


# ── Shared ORM Base (used by all models) ──────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  Detect which mode we're in
# ─────────────────────────────────────────────────────────────────────────────
_url   = settings.DATABASE_URL   # e.g. "libsql://xxx.turso.io" or "file:./attendance.db"
_token = getattr(settings, "DATABASE_AUTH_TOKEN", None)

_USE_TURSO = _url.startswith("libsql://") or _url.startswith("https://")


# ─────────────────────────────────────────────────────────────────────────────
#  TURSO PATH — libsql_experimental native client
# ─────────────────────────────────────────────────────────────────────────────
if _USE_TURSO:
    import libsql_experimental as libsql  # pip install libsql-experimental

    def _get_turso_conn():
        """Return a connected libsql async connection."""
        return libsql.connect(
            database=_url,
            auth_token=_token,
        )

    # Thin shim so existing code can do `async with AsyncSessionLocal() as session:`
    class _TursoSession:
        """Minimal async session shim wrapping a libsql connection."""

        def __init__(self):
            self._conn = None

        async def __aenter__(self):
            self._conn = _get_turso_conn()
            await self._conn.__aenter__()
            return self

        async def __aexit__(self, exc_type, exc, tb):
            await self._conn.__aexit__(exc_type, exc, tb)

        async def execute(self, statement, params=None):
            # Accept SQLAlchemy text() or raw string
            sql = str(statement)
            return await self._conn.execute(sql, params or [])

        async def commit(self):
            await self._conn.commit()

        async def rollback(self):
            await self._conn.rollback()

        async def close(self):
            pass  # handled by __aexit__

    class _TursoSessionFactory:
        def __call__(self):
            return _TursoSession()

    AsyncSessionLocal = _TursoSessionFactory()

    # Stub engine (needed for create_tables to work via libsql directly)
    engine = None

    async def create_tables():
        """Create all tables using raw DDL via libsql."""
        conn = _get_turso_conn()
        async with conn:
            # Import all models so Base.metadata is populated
            from database import models  # noqa: F401  adjust if your models live elsewhere
            for table in Base.metadata.sorted_tables:
                ddl = str(
                    table.compile(dialect=None)  # generates CREATE TABLE IF NOT EXISTS SQL
                )
                # Use libsql's executescript for DDL
                await conn.executescript(
                    f"CREATE TABLE IF NOT EXISTS {table.name} "
                    f"({', '.join(str(c.compile()) for c in table.columns)});"
                )

    async def get_db() -> AsyncGenerator[_TursoSession, None]:
        session = _TursoSession()
        async with session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# ─────────────────────────────────────────────────────────────────────────────
#  LOCAL DEV PATH — standard SQLAlchemy async + aiosqlite
# ─────────────────────────────────────────────────────────────────────────────
else:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    if _url.startswith("file:"):
        _path = _url[5:]
        _sqlite_url = f"sqlite+aiosqlite:///{_path}"
    else:
        _sqlite_url = _url  # pass through as-is

    engine = create_async_engine(
        _sqlite_url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async def create_tables():
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
