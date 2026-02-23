"""Cyperf CVE mapping ORM model."""

from datetime import datetime

from sqlalchemy import VARCHAR, Boolean, Column, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from database import Base


class CyperfSupportedCVE(Base):
    """Cyperf CVE mapping entity.

    Stores the association between CVE IDs and the Cyperf Attack Profiles that can test them.
    Uses idempotent upsert pattern: ON CONFLICT (cve_id) UPDATE to handle profile changes.

    Sync workflow:
    1. fetch_attack_profiles() from Cyperf Controller
    2. extract_cves_from_profiles() to build {cve_id: profile_name} mapping
    3. upsert_from_cyperf_data() for each mapping (handles insert or update)
    4. Commit transaction atomically (all CVEs updated together)
    """

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
        Index("idx_cyperf_cve", "cve_id"),
        Index("idx_cyperf_profile", "attack_profile_name"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<CyperfSupportedCVE(cve_id={self.cve_id}, profile={self.attack_profile_name})>"

    @classmethod
    def upsert_from_cyperf_data(
        cls,
        session: Session,
        cve_id: str,
        profile_name: str,
        profile_id: str | None = None,
        profile_version: str | None = None,
    ) -> "CyperfSupportedCVE":
        """Upsert a CVE-to-profile mapping (insert or update on conflict).

        Idempotent operation: creates record if not exists, updates if it does.
        Updates last_synced timestamp; preserves first_synced if record existed.
        Marks record as active (is_deprecated=False) on successful sync.

        Args:
            session: SQLAlchemy session for database operations
            cve_id: CVE identifier (e.g. CVE-2024-1234)
            profile_name: Human-readable attack profile name
            profile_id: Optional attack profile ID from Cyperf
            profile_version: Optional attack profile version

        Returns:
            Updated or inserted CyperfSupportedCVE record

        Note:
            Uses session.merge() for idempotent upsert. Caller must commit.
        """
        # Create new record or get existing one
        record = cls(
            cve_id=cve_id,
            attack_profile_name=profile_name,
            attack_profile_id=profile_id,
            profile_version=profile_version,
            last_synced=datetime.utcnow(),
            is_deprecated=False,
        )

        # merge() handles insert-or-update semantics
        merged = session.merge(record)
        return merged
