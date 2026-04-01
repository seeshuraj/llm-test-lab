import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from typing import AsyncGenerator
from .models import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URL resolution
#
# The backend runs on Render. Set ONE of these in Render > Environment:
#
#   DATABASE_URL      — full asyncpg URL  (Render auto-injects this if you
#                        attach a Render Postgres; also accepted from any host)
#   SUPABASE_DB_URL   — Supabase connection string, e.g.
#                        postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
#
# NOTE: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are
#       frontend-only variables for the JS Supabase client. The backend uses
#       a direct PostgreSQL connection string — not the anon key.
#
# Falls back to SQLite for local dev when neither is set.
# ---------------------------------------------------------------------------

_raw_url = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("SUPABASE_DB_URL")
    or "sqlite+aiosqlite:///./llm_test_lab.db"
)

DATABASE_URL: str = _raw_url

# Normalise Supabase / Heroku postgres:// → postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

is_postgres = "asyncpg" in DATABASE_URL

connect_args: dict = {}
if is_postgres:
    connect_args = {
        "ssl": "require",
        "statement_cache_size": 0,  # required for Supabase pgBouncer pooler
    }

if is_postgres:
    logger.info("[db] Using PostgreSQL (Supabase)")
else:
    logger.info("[db] Using SQLite (local dev fallback)")

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
    json_type = "JSONB" if is_postgres else "TEXT"
    new_columns = [
        ("runs", "scenarios_yaml", "TEXT"),
        ("runs", "rubric", "TEXT"),
        ("runs", "app_endpoint_url", "TEXT"),
        ("runs", "run_label", "VARCHAR"),
        ("run_scenario_results", "rag_scores", json_type),
    ]
    async with engine.begin() as conn:
        for table, column, col_type in new_columns:
            if is_postgres:
                sql = f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='{table}' AND column_name='{column}'
                    ) THEN
                        ALTER TABLE {table} ADD COLUMN {column} {col_type};
                        RAISE NOTICE 'Added column {column} to {table}';
                    END IF;
                END$$;
                """
            else:
                sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"

            try:
                await conn.execute(text(sql))
                logger.info("Migration OK: %s.%s", table, column)
            except Exception as e:
                logger.warning("Migration skipped %s.%s: %s", table, column, e)


async def init_db():
    """Create all tables on startup, then apply safe column migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_add_columns()
    logger.info("[db] Schema ready")
