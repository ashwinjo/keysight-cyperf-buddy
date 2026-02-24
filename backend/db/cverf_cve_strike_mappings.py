"""CvrfCveStrikeMappings ORM model.

Stores CVE-to-Strike-name mappings sourced from Cyperf's
ApplicationResourcesApi.get_resources_strikes() endpoint.

Design decisions:
- Composite primary key (cve_id, strike_name) enforces uniqueness per mapping;
  no separate auto-increment id column needed.
- No foreign key to cves.id — Cyperf data is ingested independently of NVD.
  A CVE may be testable in Cyperf before it appears in the NVD feed.
- Full refresh strategy: sync service truncates all rows, then re-inserts fresh
  data from Cyperf. No delta tracking needed at this layer.
- created_at / updated_at are server-side timestamps; updated_at refreshes on
  every upsert via onupdate=func.now().
"""

from sqlalchemy import VARCHAR, Column, DateTime, Index
from sqlalchemy.sql import func

from database import Base


class CvrfCveStrikeMappings(Base):
    """CVE to Cyperf Strike name mapping entity.

    Each row represents a single (CVE ID, Strike name) association discovered
    during a Cyperf sync. One CVE may have multiple rows if Cyperf maps it to
    multiple Strikes.

    Table: cverf_cve_strike_mappings
    PK:    (cve_id, strike_name) — composite, enforces uniqueness
    """

    __tablename__ = "cverf_cve_strike_mappings"

    # Composite primary key — no surrogate id column
    cve_id = Column(
        VARCHAR(20),
        primary_key=True,
        nullable=False,
        comment="CVE identifier, e.g. CVE-2024-1234",
    )
    strike_name = Column(
        VARCHAR(255),
        primary_key=True,
        nullable=False,
        comment="Cyperf Strike name that covers this CVE",
    )

    # Audit timestamps — server-side defaults; no application-layer management needed
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when this mapping was first inserted",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when this mapping was last updated",
    )

    __table_args__ = (
        Index("idx_cverf_strike_cve", "cve_id"),
        Index("idx_cverf_strike_name", "strike_name"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<CvrfCveStrikeMappings(cve_id={self.cve_id!r}, strike={self.strike_name!r})>"
