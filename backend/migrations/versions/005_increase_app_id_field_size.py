"""Increase cyperf_applications ID field size to 512.

Revision ID: 005
Revises: 004
Create Date: 2026-02-25 16:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase VARCHAR size for cyperf_applications and cyperf_application_types ID fields."""
    # For PostgreSQL
    op.alter_column(
        "cyperf_applications",
        "id",
        existing_type=sa.String(36),
        type_=sa.String(512),
        existing_nullable=False,
    )

    op.alter_column(
        "cyperf_application_types",
        "id",
        existing_type=sa.String(36),
        type_=sa.String(512),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert VARCHAR size for IDs back to 36."""
    op.alter_column(
        "cyperf_applications",
        "id",
        existing_type=sa.String(512),
        type_=sa.String(36),
        existing_nullable=False,
    )

    op.alter_column(
        "cyperf_application_types",
        "id",
        existing_type=sa.String(512),
        type_=sa.String(36),
        existing_nullable=False,
    )
