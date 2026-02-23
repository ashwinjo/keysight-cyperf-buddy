"""Sync metadata ORM model."""

from sqlalchemy import VARCHAR, Column, DateTime, Index, Integer, Text, UniqueConstraint
from sqlalchemy.sql import func

from database import Base


class SyncMetadata(Base):
    """Metadata about sync job execution."""

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
