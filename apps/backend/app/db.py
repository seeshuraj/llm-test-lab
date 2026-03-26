import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from typing import AsyncGenerator
from .models import Base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./llm_test_lab.db"
)

# Normalise Supabase/Heroku postgres:// URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

is_postgres = "asyncpg" in DATABASE_URL

connect_args = {}
if is_postgres:
    connect_args = {
        "ssl": "require",
        "statement_cache_size": 0,
    }

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def _migrate_add_columns():
    """Safely add new columns to existing tables without dropping data."""
    new_columns = [
        ("runs", "scenarios_yaml", "TEXT"),
        ("runs", "rubric", "TEXT"),
        ("runs", "app_endpoint_url", "TEXT"),
    ]
    async with engine.begin() as conn:
        for table, column, col_type in new_columns:
            try:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                )
            except Exception:
                # Column already exists — safe to ignore
                pass


async def init_db():
    """Create all tables on startup, then apply safe column migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_add_columns()
