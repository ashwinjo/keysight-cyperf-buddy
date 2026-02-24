"""AICve ORM model.

Stores AI-type (no-CVE) strikes sourced from Cyperf's
ApplicationResourcesApi.get_resources_strikes() endpoint that have no
Type='CVE' reference in their Metadata.References array.

Design decisions:
- Surrogate primary key (id, UUID as VARCHAR(36)) — no natural composite key
  analogous to (cve_id, strike_name) because ai_cves has no real CVE ID.
- cve_id holds a synthetic 'NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)>'
  identifier — deterministic across re-syncs; stable for any downstream
  system that bookmarks the synthetic ID.
- strike_type defaults to 'ai_attack'; extensible for 'fuzzing',
  'protocol_abuse', etc. without schema migrations.
- metadata is TEXT (JSON-encoded Metadata.References blob); application layer
  is responsible for json.loads / json.dumps — avoids JSON column
  type incompatibilities between SQLite (dev) and PostgreSQL (prod).
- Full-replace strategy matches cverf_cve_strike_mappings: sync service
  truncates all rows, then re-inserts fresh data from Cyperf. The surrogate
  id (uuid4) changes each full-replace; cve_id (uuid5) is stable.
- VARCHAR(512) for strike_name: AI strike names are significantly longer
  than typical CVE strike names (existing table uses VARCHAR(255)).
"""

from sqlalchemy import TEXT, VARCHAR, Column, DateTime, Index
from sqlalchemy.sql import func

from database import Base


class AICve(Base):
    """AI-type Cyperf Strike with no associated CVE ID.

    Each row represents a single strike discovered during a Cyperf sync
    that contains no Type='CVE' reference in its Metadata.References array.
    A synthetic NoCVE_cyperf<uuid5> identifier is assigned as cve_id to
    uniquely and stably identify the strike across re-syncs.

    Table: ai_cves
    PK:    id (uuid4 surrogate — new UUID per full-replace cycle)
    UNIQUE: cve_id (uuid5-based — stable per strike name across re-syncs)
    """

    __tablename__ = "ai_cves"

    # Surrogate primary key — UUID as string for portability across SQLite/PostgreSQL.
    # New uuid4 per insert (full-replace strategy resets the PK each sync cycle).
    id = Column(
        VARCHAR(36),
        primary_key=True,
        nullable=False,
        comment="Surrogate UUID primary key (uuid4); new per full-replace cycle",
    )

    # Synthetic CVE identifier: NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)>
    # 'NoCVE_cyperf' (13 chars) + UUID (36 chars) = 49 chars; VARCHAR(60) has margin.
    # Deterministic: same strike_name -> same cve_id across all re-syncs.
    cve_id = Column(
        VARCHAR(60),
        nullable=False,
        unique=True,
        comment="Synthetic CVE ID, e.g. NoCVE_cyperf550e8400-e29b-...; deterministic uuid5",
    )

    # Full strike name from Cyperf API response.
    # AI strike names are significantly longer than CVE strike names;
    # VARCHAR(512) accommodates current AI naming conventions with headroom.
    strike_name = Column(
        VARCHAR(512),
        nullable=False,
        comment="Cyperf Strike name; VARCHAR(512) to handle AI strike name length",
    )

    # Category tag — extensible without schema migrations.
    # Current valid values: 'ai_attack' | 'fuzzing' | 'protocol_abuse'
    strike_type = Column(
        VARCHAR(50),
        nullable=False,
        server_default="ai_attack",
        comment="Strike category: ai_attack | fuzzing | protocol_abuse | ...",
    )

    # JSON blob of raw Metadata.References from Cyperf API response.
    # Stored as TEXT; application layer handles json.loads/dumps.
    # NULL when References list is empty or Metadata key is absent entirely.
    # Python attribute is 'metadata_json' to avoid collision with SQLAlchemy's
    # reserved DeclarativeBase.metadata class attribute (added in 2.0.28+).
    # The actual DB column name remains 'metadata' for schema compatibility.
    metadata_json = Column(
        "metadata",
        TEXT,
        nullable=True,
        comment="JSON-encoded Metadata.References from Cyperf API; null when empty",
    )

    # Audit timestamps — server-side defaults; no application-layer management needed.
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when this record was first inserted",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when this record was last updated",
    )

    __table_args__ = (
        Index("idx_ai_cves_cve_id", "cve_id"),
        Index("idx_ai_cves_strike_name", "strike_name"),
        Index("idx_ai_cves_strike_type", "strike_type"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<AICve(cve_id={self.cve_id!r}, strike={self.strike_name!r})>"
