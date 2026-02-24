"""Add cverf_cve_strike_mappings table.

Revision ID: 002
Revises: 001
Create Date: 2026-02-24 01:49:00.000000

Purpose:
    Introduce cverf_cve_strike_mappings — a many-to-many mapping table that stores
    (CVE ID, Strike name) pairs from Cyperf's ApplicationResourcesApi.
    Replaces the 1:1 design of cyperf_supported_cves with a proper multi-row
    structure: one row per (CVE, Strike) combination.

Design notes:
    - Composite primary key (cve_id, strike_name) enforces uniqueness without a
      surrogate id column.
    - No foreign key to cves.id — Cyperf data is populated independently of NVD
      ingestion. A CVE may be testable before it appears in the NVD feed.
    - Two indexes support fast lookups in both directions.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create cverf_cve_strike_mappings table with composite PK and indexes."""
    op.create_table(
        "cverf_cve_strike_mappings",
        sa.Column("cve_id", sa.VARCHAR(20), nullable=False),
        sa.Column("strike_name", sa.VARCHAR(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("cve_id", "strike_name"),
    )
    op.create_index("idx_cverf_strike_cve", "cverf_cve_strike_mappings", ["cve_id"])
    op.create_index("idx_cverf_strike_name", "cverf_cve_strike_mappings", ["strike_name"])


def downgrade() -> None:
    """Drop cverf_cve_strike_mappings table and its indexes."""
    op.drop_index("idx_cverf_strike_name", table_name="cverf_cve_strike_mappings")
    op.drop_index("idx_cverf_strike_cve", table_name="cverf_cve_strike_mappings")
    op.drop_table("cverf_cve_strike_mappings")
