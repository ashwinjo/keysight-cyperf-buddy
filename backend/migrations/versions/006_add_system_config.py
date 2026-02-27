"""Add system_config table for key-value system configuration storage.

Revision ID: 006
Revises: 005
Create Date: 2026-02-27 02:53:00.000000

Adds the `system_config` table used to store admin-managed configuration
values (e.g., the Keysight CyPerf Controller endpoint). The table starts
empty; values are populated via the POST /admin/config/cyperf-endpoint API.

Compatible with both SQLite (dev) and PostgreSQL (prod).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create system_config table with unique constraint and index on config_key."""
    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("config_key", sa.VARCHAR(100), nullable=False),
        sa.Column("config_value", sa.TEXT(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_key", name="uq_system_config_key"),
    )
    op.create_index("idx_system_config_key", "system_config", ["config_key"], unique=False)


def downgrade() -> None:
    """Drop system_config table and associated index."""
    op.drop_index("idx_system_config_key", table_name="system_config")
    op.drop_table("system_config")
