"""Database abstraction layer — SQLite (dev) / PostgreSQL (prod) switch.

Usage:
  from agora.storage.db import init_database, close_database

  await init_database(app)  # creates app.state.db + app.state.async_session
  await close_database(app) # cleanup

Backward compatible: app.state.db (aiosqlite) works as before for raw SQL.
New code: use app.state.async_session (SQLAlchemy 2.0 async session) for ORM.
"""

import os
from typing import Optional

import aiosqlite
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from agora.storage.models import Base


def is_postgres(database_url: str) -> bool:
    """Detect if the database URL points to PostgreSQL."""
    return database_url.startswith("postgresql") or database_url.startswith("postgres")


def is_sqlite(database_url: str) -> bool:
    """Detect if the database URL points to SQLite."""
    return "sqlite" in database_url


async def init_database(app, database_url: str = None) -> tuple:
    """Initialize database connections.

    Returns (aiosqlite_conn, async_session_maker) for backward compat.
    Sets app.state.db, app.state.async_session, app.state.engine.
    """
    url = database_url or os.getenv("AGORA_DATABASE_URL", "sqlite+aiosqlite:///./agora.db")

    # Remove prefix for aiosqlite (it doesn't understand sqlite+aiosqlite:///)
    aiosqlite_url = url.replace("sqlite+aiosqlite:///", "").replace("sqlite+aiosqlite://", "")
    if aiosqlite_url == url and "sqlite" in url:
        aiosqlite_url = url.replace("sqlite:///", "")

    # Aiosqlite connection (backward compat for raw SQL queries)
    aiosqlite_conn = None
    if is_sqlite(url):
        db_path = aiosqlite_url
        aiosqlite_conn = await aiosqlite.connect(db_path)
        aiosqlite_conn.row_factory = aiosqlite.Row
        # Enable WAL mode for concurrent reads
        await aiosqlite_conn.execute("PRAGMA journal_mode=WAL")
        await aiosqlite_conn.execute("PRAGMA foreign_keys=ON")
        app.state.db = aiosqlite_conn
        print(f"[DB] SQLite: {db_path}")
    else:
        # For PostgreSQL, we still need an aiosqlite connection for backward compat
        # But we'll use SQLAlchemy for all new code
        # Legacy code paths that use app.state.db directly will need porting
        app.state.db = None
        print(f"[DB] PostgreSQL mode (legacy app.state.db = None)")

    # SQLAlchemy async engine + sessionmaker (for new code + Alembic)
    # Convert aiosqlite URL to sqlalchemy format
    sa_url = url
    if "sqlite+aiosqlite://" in url:
        sa_url = url.replace("sqlite+aiosqlite://", "sqlite+aiosqlite://")

    pool_class = StaticPool if "sqlite" in sa_url else NullPool
    engine = create_async_engine(
        sa_url,
        poolclass=pool_class,
        echo=False,
    )

    # Create all tables if they don't exist (dev mode)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    app.state.engine = engine
    app.state.async_session = session_maker
    print(f"[DB] SQLAlchemy engine ready: {sa_url[:60]}...")

    return aiosqlite_conn, session_maker


async def close_database(app):
    """Close all database connections."""
    if hasattr(app.state, "db") and app.state.db:
        try:
            await app.state.db.close()
        except Exception:
            pass
    if hasattr(app.state, "engine") and app.state.engine:
        await app.state.engine.dispose()


async def get_session(app) -> AsyncSession:
    """Get a new SQLAlchemy async session.

    Usage:
        async with get_session(app) as session:
            result = await session.execute(...)
    """
    maker = app.state.async_session
    async with maker() as session:
        try:
            yield session
        finally:
            await session.close()


# Re-export for convenience
Session = AsyncSession
