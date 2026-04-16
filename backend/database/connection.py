# ─────────────────────────────────────────────
#  backend/database/connection.py
# ─────────────────────────────────────────────

from typing import AsyncGenerator

from sqlalchemy.orm import DeclarativeBase
from config.settings import settings


# ── Shared ORM Base ───────────────────────────
class Base(DeclarativeBase):
    pass


# ── Detect DB mode ────────────────────────────
_url = settings.DATABASE_URL
_token = getattr(settings, "DATABASE_AUTH_TOKEN", None)

_USE_TURSO = _url.startswith("libsql://") or _url.startswith("https://")


# ─────────────────────────────────────────────
#  TURSO (Production)
# ─────────────────────────────────────────────
if _USE_TURSO:
    import libsql_experimental as libsql
    from sqlalchemy.schema import CreateTable

    def _get_turso_conn():
        return libsql.connect(
            database=_url,
            auth_token=_token,
        )

    class _TursoSession:
        def __init__(self):
            self._conn = None

        async def __aenter__(self):
            self._conn = _get_turso_conn()
            return self

        async def __aexit__(self, exc_type, exc, tb):
            self._conn.close()

        async def execute(self, statement, params=None):
            sql = str(statement)
            return self._conn.execute(sql, params or [])

        async def commit(self):
            self._conn.commit()

        async def rollback(self):
            self._conn.rollback()

    class _TursoSessionFactory:
        def __call__(self):
            return _TursoSession()

    AsyncSessionLocal = _TursoSessionFactory()
    engine = None

    async def create_tables():
        conn = _get_turso_conn()
        try:
            # Load models so metadata is registered
            import models.user
            import models.employee
            import models.attendance

            # Use SQLAlchemy DDL generator (SAFE)
            for table in Base.metadata.sorted_tables:
                ddl = str(
                    CreateTable(table).compile(
                        compile_kwargs={"literal_binds": True}
                    )
                )
                ddl = ddl.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
                conn.execute(ddl)

            conn.commit()

        finally:
            conn.close()

    async def get_db() -> AsyncGenerator[_TursoSession, None]:
        session = _TursoSession()
        async with session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# ─────────────────────────────────────────────
#  LOCAL DEV (SQLite async)
# ─────────────────────────────────────────────
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
        _sqlite_url = _url

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
