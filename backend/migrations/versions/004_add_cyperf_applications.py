"""Add cyperf_applications and cyperf_application_types tables.

Revision ID: 004
Revises: 003
Create Date: 2026-02-25 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create cyperf_application_types and cyperf_applications tables."""
    # Create cyperf_application_types table
    op.create_table(
        "cyperf_application_types",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("description", sa.String(2048), nullable=True),
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
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cyperf_application_types_id",
        "cyperf_application_types",
        ["id"],
        unique=True,
    )
    op.create_index("ix_cyperf_application_types_name", "cyperf_application_types", ["name"])
    op.create_index(
        "ix_cyperf_application_types_created_at",
        "cyperf_application_types",
        ["created_at"],
    )

    # Create cyperf_applications table
    op.create_table(
        "cyperf_applications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("description", sa.String(2048), nullable=True),
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
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cyperf_applications_id", "cyperf_applications", ["id"], unique=True)
    op.create_index("ix_cyperf_applications_name", "cyperf_applications", ["name"])
    op.create_index("ix_cyperf_applications_created_at", "cyperf_applications", ["created_at"])


def downgrade() -> None:
    """Drop cyperf_applications and cyperf_application_types tables."""
    op.drop_index("ix_cyperf_applications_created_at", table_name="cyperf_applications")
    op.drop_index("ix_cyperf_applications_name", table_name="cyperf_applications")
    op.drop_index("ix_cyperf_applications_id", table_name="cyperf_applications")
    op.drop_table("cyperf_applications")

    op.drop_index("ix_cyperf_application_types_created_at", table_name="cyperf_application_types")
    op.drop_index("ix_cyperf_application_types_name", table_name="cyperf_application_types")
    op.drop_index("ix_cyperf_application_types_id", table_name="cyperf_application_types")
    op.drop_table("cyperf_application_types")
