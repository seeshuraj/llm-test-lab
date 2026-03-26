import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator
from .models import Base

# Use DATABASE_URL env var (Supabase PostgreSQL connection string)
# Format: postgresql+asyncpg://user:password@host:port/dbname
# For Supabase: use the "Transaction" pooler URL from Settings > Database
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./llm_test_lab.db"  # fallback for local dev
)

# Supabase connection strings may start with 'postgres://' — fix for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# SSL required for Supabase
connect_args = {}
if "asyncpg" in DATABASE_URL:
    connect_args = {"ssl": "require"}

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
