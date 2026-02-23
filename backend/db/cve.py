"""CVE ORM model."""

from sqlalchemy import TEXT, VARCHAR, Column, DateTime, Index, Numeric
from sqlalchemy.sql import func

from database import Base


class CVE(Base):
    """CVE entity in the database."""

    __tablename__ = "cves"

    # Primary key
    id = Column(VARCHAR(20), primary_key=True, comment="CVE identifier (e.g. CVE-2024-1234)")

    # Core CVE data
    description = Column(TEXT, comment="Vulnerability description from NVD")
    published_date = Column(DateTime(timezone=True), comment="Date CVE was published")
    last_modified = Column(DateTime(timezone=True), comment="Last modification date from NVD")

    # CVSS v3.1 metrics
    cvss_v3_vector = Column(VARCHAR(100), comment="CVSS v3.1 vector string")
    cvss_v3_score = Column(Numeric(3, 1), comment="CVSS v3.1 score (0.0-10.0)")
    cvss_v3_severity = Column(
        VARCHAR(20), comment="CVSS v3.1 severity (LOW, MEDIUM, HIGH, CRITICAL)"
    )

    # CVSS v4.0 metrics
    cvss_v4_vector = Column(VARCHAR(100), comment="CVSS v4.0 vector string")
    cvss_v4_score = Column(Numeric(4, 2), comment="CVSS v4.0 score (0.0-10.0)")
    cvss_v4_severity = Column(VARCHAR(20), comment="CVSS v4.0 severity")

    # References
    references = Column(TEXT, comment="JSON array of reference URLs")

    # Tracking
    first_seen = Column(DateTime, server_default=func.now(), comment="When CVE was first imported")
    last_updated = Column(
        DateTime, server_default=func.now(), comment="When CVE data was last updated"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_cve_published", "published_date"),
        Index("idx_cve_severity", "cvss_v3_severity"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<CVE(id={self.id}, severity={self.cvss_v3_severity})>"
