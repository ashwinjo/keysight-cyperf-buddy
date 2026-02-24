"""Add ai_cves table for no-CVE AI-type strikes.

Revision ID: 003
Revises: 002
Create Date: 2026-02-24 00:00:00.000000

Purpose:
    Introduce ai_cves — a table for Cyperf strikes that contain no
    Type='CVE' reference in their Metadata.References array (AI-type,
    fuzzing, protocol-abuse strikes, etc.).

    These strikes were previously silently dropped by the ingestion pipeline
    because fetch_cve_strike_mappings() only processed Type='CVE' references
    with no fallback branch for non-CVE strikes.

Design notes:
    - Surrogate primary key (id, VARCHAR(36)) — no natural composite key.
      New uuid4 assigned per full-replace cycle; cve_id is the stable handle.
    - cve_id uses a synthetic 'NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)>'
      identifier: deterministic across re-syncs; VARCHAR(60) holds the full
      49-char value with margin (existing cverf_cve_strike_mappings.cve_id is
      VARCHAR(20) — too narrow for synthetic IDs; separate table required).
    - VARCHAR(512) for strike_name: AI strike names exceed the VARCHAR(255)
      used in cverf_cve_strike_mappings.
    - metadata is TEXT (JSON blob of raw Metadata.References); nullable.
    - Both tables (cverf_cve_strike_mappings + ai_cves) are updated in a
      single transaction by sync_service.perform_sync().
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_cves table with surrogate PK, unique cve_id, and three indexes."""
    op.create_table(
        "ai_cves",
        sa.Column("id", sa.VARCHAR(36), nullable=False),
        sa.Column("cve_id", sa.VARCHAR(60), nullable=False),
        sa.Column("strike_name", sa.VARCHAR(512), nullable=False),
        sa.Column(
            "strike_type",
            sa.VARCHAR(50),
            nullable=False,
            server_default="ai_attack",
        ),
        sa.Column("metadata", sa.TEXT(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cve_id"),
    )
    op.create_index("idx_ai_cves_cve_id", "ai_cves", ["cve_id"])
    op.create_index("idx_ai_cves_strike_name", "ai_cves", ["strike_name"])
    op.create_index("idx_ai_cves_strike_type", "ai_cves", ["strike_type"])


def downgrade() -> None:
    """Drop ai_cves indexes then the table (reverse of upgrade)."""
    op.drop_index("idx_ai_cves_strike_type", table_name="ai_cves")
    op.drop_index("idx_ai_cves_strike_name", table_name="ai_cves")
    op.drop_index("idx_ai_cves_cve_id", table_name="ai_cves")
    op.drop_table("ai_cves")
