"""Initial schema: CVEs, Cyperf mappings, sync metadata.

Revision ID: 001
Revises:
Create Date: 2026-02-23 06:11:08.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema tables."""
    # CVEs table
    op.create_table(
        "cves",
        sa.Column("id", sa.VARCHAR(20), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cvss_v3_vector", sa.VARCHAR(100), nullable=True),
        sa.Column("cvss_v3_score", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("cvss_v3_severity", sa.VARCHAR(20), nullable=True),
        sa.Column("cvss_v4_vector", sa.VARCHAR(100), nullable=True),
        sa.Column("cvss_v4_score", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("cvss_v4_severity", sa.VARCHAR(20), nullable=True),
        sa.Column("references", sa.TEXT(), nullable=True),
        sa.Column("first_seen", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("last_updated", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cve_published", "cves", ["published_date"], unique=False)
    op.create_index("idx_cve_severity", "cves", ["cvss_v3_severity"], unique=False)

    # Cyperf supported CVEs table
    op.create_table(
        "cyperf_supported_cves",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("cve_id", sa.VARCHAR(20), nullable=False),
        sa.Column("attack_profile_name", sa.VARCHAR(255), nullable=False),
        sa.Column("attack_profile_id", sa.VARCHAR(100), nullable=True),
        sa.Column("profile_version", sa.VARCHAR(50), nullable=True),
        sa.Column("first_synced", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.Column("is_deprecated", sa.Boolean(), nullable=True, server_default=sa.literal(False)),
        sa.ForeignKeyConstraint(["cve_id"], ["cves.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cve_id"),
    )
    op.create_index("idx_cyperf_cve", "cyperf_supported_cves", ["cve_id"], unique=False)
    op.create_index(
        "idx_cyperf_profile", "cyperf_supported_cves", ["attack_profile_name"], unique=False
    )

    # Sync metadata table
    op.create_table(
        "sync_metadata",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("job_name", sa.VARCHAR(50), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.VARCHAR(20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("profiles_synced", sa.Integer(), nullable=True),
        sa.Column("next_scheduled_run", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_name"),
    )
    op.create_index("idx_sync_job", "sync_metadata", ["job_name"], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index("idx_sync_job", table_name="sync_metadata")
    op.drop_table("sync_metadata")
    op.drop_index("idx_cyperf_profile", table_name="cyperf_supported_cves")
    op.drop_index("idx_cyperf_cve", table_name="cyperf_supported_cves")
    op.drop_table("cyperf_supported_cves")
    op.drop_index("idx_cve_severity", table_name="cves")
    op.drop_index("idx_cve_published", table_name="cves")
    op.drop_table("cves")
