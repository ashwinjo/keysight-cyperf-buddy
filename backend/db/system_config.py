"""SystemConfig ORM model for key-value system configuration storage."""

import logging

from sqlalchemy import TEXT, VARCHAR, Column, DateTime, Index, Integer, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from database import Base

logger = logging.getLogger(__name__)


class SystemConfig(Base):
    """Key-value store for system-wide configuration.

    Stores configuration values such as the Keysight CyPerf Controller endpoint,
    feature flags, and other admin-managed settings. Each record is identified by
    a unique config_key (e.g., "cyperf_endpoint"). Values are stored as TEXT and
    are expected to be JSON-serializable strings.

    Schema:
        config_key — unique, not-null VARCHAR(100) identifier
        config_value — TEXT value (treat as opaque string; serialize as needed)
        created_at — server-side UTC timestamp on insert
        updated_at — server-side UTC timestamp on insert; updated on row mutation

    Usage::

        # Read
        endpoint = await SystemConfig.get_value(session, "cyperf_endpoint")

        # Upsert
        await SystemConfig.set_value(session, "cyperf_endpoint", "cyperf.example.com")
    """

    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Auto-incremented PK")
    config_key = Column(
        VARCHAR(100),
        nullable=False,
        unique=True,
        comment="Configuration key (e.g., 'cyperf_endpoint')",
    )
    config_value = Column(TEXT, nullable=False, comment="Configuration value (JSON-serializable)")
    created_at = Column(
        DateTime,
        server_default=func.now(),
        comment="Timestamp when this config entry was first created",
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when this config entry was last updated",
    )

    __table_args__ = (
        UniqueConstraint("config_key", name="uq_system_config_key"),
        Index("idx_system_config_key", "config_key"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<SystemConfig(key={self.config_key!r})>"

    @classmethod
    async def get_value(
        cls, session: AsyncSession, key: str, default: str | None = None
    ) -> str | None:
        """Retrieve a configuration value by key.

        Args:
            session: AsyncSession for database operations.
            key: The config_key to look up.
            default: Value to return if key does not exist. Default: None.

        Returns:
            The stored config_value string, or `default` if not found.

        Raises:
            Any SQLAlchemy exception propagates to the caller — no silent failures.
        """
        stmt = select(cls).where(cls.config_key == key)
        result = await session.execute(stmt)
        record = result.scalars().first()
        if record is None:
            return default
        return record.config_value

    @classmethod
    async def set_value(cls, session: AsyncSession, key: str, value: str) -> "SystemConfig":
        """Atomically upsert a configuration value.

        If `key` already exists, updates config_value (and triggers updated_at).
        If `key` does not exist, creates a new row.

        Args:
            session: AsyncSession for database operations.
            key: The config_key to set.
            value: The new config_value (must not be None).

        Returns:
            The SystemConfig ORM record after upsert.

        Raises:
            Any SQLAlchemy exception propagates to the caller — no silent failures.
        """
        stmt = select(cls).where(cls.config_key == key)
        result = await session.execute(stmt)
        record = result.scalars().first()

        if record is None:
            record = cls(config_key=key, config_value=value)
            session.add(record)
            logger.info("SystemConfig: created key=%r", key)
        else:
            record.config_value = value
            logger.info("SystemConfig: updated key=%r", key)

        await session.flush()
        return record
