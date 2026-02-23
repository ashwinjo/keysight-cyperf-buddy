"""Cyperf CVE mapping ORM model."""

from sqlalchemy import VARCHAR, Boolean, Column, DateTime, ForeignKey, Index, Integer
from sqlalchemy.sql import func

from database import Base


class CyperfSupportedCVE(Base):
    """Cyperf CVE mapping entity."""

    __tablename__ = "cyperf_supported_cves"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Auto-incremented ID")

    # Foreign key to CVEs
    cve_id = Column(
        VARCHAR(20),
        ForeignKey("cves.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Reference to CVE in cves table",
    )

    # Attack profile details
    attack_profile_name = Column(VARCHAR(255), nullable=False, comment="Name of attack profile")
    attack_profile_id = Column(VARCHAR(100), comment="ID of attack profile in Cyperf")
    profile_version = Column(VARCHAR(50), comment="Version of attack profile")

    # Sync tracking
    first_synced = Column(
        DateTime, server_default=func.now(), comment="When this mapping was first discovered"
    )
    last_synced = Column(DateTime, comment="When mapping was last updated from Cyperf")
    is_deprecated = Column(Boolean, default=False, comment="Whether profile is no longer available")

    # Indexes
    __table_args__ = (
        Index("idx_cyperf_cve", "cve_id", comment="Index for CVE lookups"),
        Index("idx_cyperf_profile", "attack_profile_name", comment="Index for profile lookups"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<CyperfSupportedCVE(cve_id={self.cve_id}, profile={self.attack_profile_name})>"
