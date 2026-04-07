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
# Falls back to SQLite for local dev when neither is set.
# ---------------------------------------------------------------------------

_raw_url = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("SUPABASE_DB_URL")
    or "sqlite+aiosqlite:///./llm_test_lab.db"
)

DATABASE_URL: str = _raw_url

# Normalise postgres:// → postgresql+asyncpg://
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
    logger.info("[db] Driver: PostgreSQL/asyncpg")
else:
    logger.info("[db] Driver: SQLite/aiosqlite (local dev fallback)")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def _migrate_add_tables():
    """
    Belt-and-suspenders: explicitly CREATE TABLE IF NOT EXISTS for any table
    that was added after the initial DB deployment.

    SQLAlchemy's create_all is idempotent for *existing* tables but it WON'T
    add a table that was defined in models.py *after* the DB was first
    initialised. This guard ensures those tables always exist.
    """
    async with engine.begin() as conn:
        if is_postgres:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id          VARCHAR PRIMARY KEY,
                    user_id     VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name        VARCHAR NOT NULL,
                    key_hash    VARCHAR NOT NULL UNIQUE,
                    key_prefix  VARCHAR NOT NULL,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_used_at TIMESTAMPTZ,
                    revoked     BOOLEAN NOT NULL DEFAULT FALSE
                )
            """))
        else:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id           TEXT PRIMARY KEY,
                    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name         TEXT NOT NULL,
                    key_hash     TEXT NOT NULL UNIQUE,
                    key_prefix   TEXT NOT NULL,
                    created_at   DATETIME NOT NULL,
                    last_used_at DATETIME,
                    revoked      INTEGER NOT NULL DEFAULT 0
                )
            """))
        logger.info("[db] api_keys table ensured")


async def _migrate_add_columns():
    """Safely add new columns to existing tables without dropping data."""
    json_type = "JSONB" if is_postgres else "TEXT"
    new_columns = [
        ("runs", "scenarios_yaml", "TEXT"),
        ("runs", "rubric", "TEXT"),
        ("runs", "app_endpoint_url", "TEXT"),
        ("runs", "run_label", "VARCHAR"),
        ("run_scenario_results", "rag_scores", json_type),
        # Guard: add key_prefix to api_keys for DBs created before this column
        # existed. The CREATE TABLE IF NOT EXISTS above already includes it,
        # but databases initialised before this migration need it added.
        ("api_keys", "key_prefix", "VARCHAR" if is_postgres else "TEXT"),
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
    """
    Called at FastAPI startup.
    1. create_all  — creates every table in models.py that doesn't exist yet
    2. _migrate_add_tables  — explicit CREATE TABLE IF NOT EXISTS guards for
                              tables added after initial deployment
    3. _migrate_add_columns — ADD COLUMN IF NOT EXISTS for new columns
    """
    # Step 1: create all ORM-defined tables (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[db] create_all complete")

    # Step 2: explicit table guards (catches tables added post-deployment)
    await _migrate_add_tables()

    # Step 3: column migrations
    await _migrate_add_columns()

    logger.info("[db] Schema ready")
