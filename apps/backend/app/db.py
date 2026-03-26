import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
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

# Supabase uses PgBouncer in transaction mode which does NOT support
# prepared statements — statement_cache_size=0 disables them.
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


async def init_db():
    """Create all tables on startup if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
