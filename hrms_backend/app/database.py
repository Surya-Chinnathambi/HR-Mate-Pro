import sys
import asyncio
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Ensure psycopg async works on Windows by forcing SelectorEventLoop
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # Debug print can help confirm policy application during startup
        print("[Init] WindowsSelectorEventLoopPolicy set for psycopg async compatibility")
    except Exception as e:
        print(f"[Init] Failed to set WindowsSelectorEventLoopPolicy: {e}")

# Sync engine for migrations (uses psycopg2)
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Async engine for API (uses asyncpg)
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session makers
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

def get_session():
    """Sync session for migrations"""
    with Session(sync_engine) as session:
        yield session

async def get_async_session():
    """Async session for API endpoints"""
    async with AsyncSessionLocal() as session:
        yield session

# Alias for backward compatibility
async def get_db():
    """Alias for get_async_session"""
    async with AsyncSessionLocal() as session:
        yield session

def create_db_and_tables():
    """Create all tables"""
    SQLModel.metadata.create_all(sync_engine)