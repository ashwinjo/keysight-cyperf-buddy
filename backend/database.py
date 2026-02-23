"""Database configuration and session management."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_settings

logger = logging.getLogger(__name__)

# Create declarative base for ORM models
Base = declarative_base()

# Get settings to configure database
settings = get_settings()

# Create async SQLAlchemy engine
# For development, uses SQLite with aiosqlite driver
# For production, uses PostgreSQL with psycopg async driver
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    future=True,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session.

    Yields:
        AsyncSession: Database session for request handling.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """Get a new database session for background jobs.

    Unlike get_db() which is a dependency (yields), this returns a session
    directly for use in background jobs like Cyperf sync.

    Returns:
        AsyncSession: New database session (caller must close)

    Note:
        Caller is responsible for closing the session. Typically used in
        try/finally blocks in background job functions.
    """
    return AsyncSessionLocal()
