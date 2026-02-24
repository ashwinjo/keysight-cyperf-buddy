"""Sync metadata ORM model."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import VARCHAR, Column, DateTime, Index, Integer, Text, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from database import Base


class SyncMetadata(Base):
    """Metadata about sync job execution.

    Tracks when each sync job runs, whether it succeeded or failed, and when the next
    sync is scheduled. Supports multiple sync jobs (identified by job_name).

    Sync workflow:
    1. record_sync_start() — marks job as running
    2. (Job performs work: fetch profiles, extract CVEs, upsert to database)
    3. record_sync_complete() — marks job as success/failed with results
    4. Circuit breaker: get_consecutive_failures() — alert on 3+ failures
    """

    __tablename__ = "sync_metadata"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Auto-incremented ID")

    # Job identification
    job_name = Column(
        VARCHAR(50),
        nullable=False,
        unique=True,
        comment="Name of sync job (e.g. 'cyperf_profiles')",
    )

    # Execution tracking
    last_run_at = Column(DateTime, comment="When job last ran")
    last_completed_at = Column(DateTime, comment="When job last completed successfully")

    # Status
    status = Column(VARCHAR(20), comment="Status of last run (success, failure, running)")
    error_message = Column(Text, comment="Error message if last run failed")

    # Results
    profiles_synced = Column(Integer, comment="Number of profiles synced in last run")

    # Scheduling
    next_scheduled_run = Column(DateTime, comment="When next sync is scheduled")

    # Metadata
    created_at = Column(
        DateTime, server_default=func.now(), comment="When sync tracking was created"
    )

    # Indexes
    __table_args__ = (UniqueConstraint("job_name"), Index("idx_sync_job", "job_name"))

    def __repr__(self) -> str:
        """String representation."""
        return f"<SyncMetadata(job={self.job_name}, status={self.status})>"

    @classmethod
    async def record_sync_start(
        cls, session: AsyncSession, job_name: str = "cyperf_profiles"
    ) -> "SyncMetadata":
        """Record the start of a sync job.

        Creates a new SyncMetadata record or updates existing one to mark job as running.

        Args:
            session: AsyncSession for database operations
            job_name: Name of sync job (default: 'cyperf_profiles')

        Returns:
            SyncMetadata record with status='running'

        Raises:
            Any SQLAlchemy exceptions during insert/update
        """
        # Fetch existing record if it exists
        stmt = select(cls).where(cls.job_name == job_name)
        result = await session.execute(stmt)
        record = result.scalars().first()

        if not record:
            # Create new record
            record = cls(
                job_name=job_name,
                last_run_at=datetime.utcnow(),
                status="running",
            )
            session.add(record)
        else:
            # Update existing record
            record.last_run_at = datetime.utcnow()
            record.status = "running"

        return record

    @classmethod
    async def record_sync_complete(
        cls,
        session: AsyncSession,
        job_name: str,
        success: bool,
        profiles_count: int,
        cves_count: int,
        error_msg: str | None = None,
        next_sync_hours: int = 24,
    ) -> "SyncMetadata":
        """Record completion of a sync job.

        Updates SyncMetadata record with success/failure status and results.

        Args:
            session: AsyncSession for database operations
            job_name: Name of sync job
            success: Whether sync succeeded
            profiles_count: Number of profiles synced (0 if failed)
            cves_count: Number of CVEs extracted (0 if failed)
            error_msg: Error message if sync failed (None if success)
            next_sync_hours: Hours until next sync attempt (default: 24)

        Returns:
            Updated SyncMetadata record

        Note:
            On success: sets last_completed_at to current time
            On failure: keeps previous last_completed_at (data is stale but last-known-good)
        """
        # Get existing record
        stmt = select(cls).where(cls.job_name == job_name)
        result = await session.execute(stmt)
        record = result.scalars().first()

        if not record:
            # Create new record if doesn't exist
            record = cls(job_name=job_name)

        # Update status fields
        record.status = "success" if success else "failed"
        record.error_message = error_msg if not success else None
        record.profiles_synced = profiles_count if success else record.profiles_synced

        if success:
            record.last_completed_at = datetime.utcnow()

        record.next_scheduled_run = datetime.utcnow() + timedelta(hours=next_sync_hours)

        merged = await session.merge(record)
        return merged

    @classmethod
    async def get_last_sync_status(
        cls, session: AsyncSession, job_name: str = "cyperf_profiles"
    ) -> Optional["SyncMetadata"]:
        """Retrieve the last sync status for a job.

        Args:
            session: AsyncSession for database operations
            job_name: Name of sync job

        Returns:
            SyncMetadata record or None if job has never run
        """
        stmt = select(cls).where(cls.job_name == job_name)
        result = await session.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def get_consecutive_failures(
        cls, session: AsyncSession, job_name: str = "cyperf_profiles", lookback_count: int = 3
    ) -> int:
        """Count consecutive failures from most recent sync backwards.

        Inspects the last N sync attempts and counts how many consecutive failures
        exist starting from the most recent.

        Args:
            session: AsyncSession for database operations
            job_name: Name of sync job
            lookback_count: Number of recent syncs to inspect (default: 3)

        Returns:
            Number of consecutive failures (0 if last sync succeeded)

        Note:
            This is a simplified implementation. A full implementation would track
            sync history (all attempts). For now, we rely on single SyncMetadata record
            and check if last attempt failed.
        """
        stmt = select(cls).where(cls.job_name == job_name)
        result = await session.execute(stmt)
        record = result.scalars().first()

        if not record:
            # Never synced
            return 0

        if record.status == "success":
            # Last sync succeeded
            return 0

        # Last sync failed; since we only track last sync, return 1
        # (A more sophisticated implementation would track sync history)
        return 1
