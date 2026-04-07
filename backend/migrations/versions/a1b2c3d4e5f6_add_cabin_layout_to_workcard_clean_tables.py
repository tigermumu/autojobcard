"""add cabin_layout to workcard_clean tables

Revision ID: a1b2c3d4e5f6
Revises: 5c2a9e1b7d2f
Create Date: 2025-12-27

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "5c2a9e1b7d2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cabin_layout column to workcard_clean_local
    with op.batch_alter_table("workcard_clean_local", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cabin_layout", sa.String(length=100), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_workcard_clean_local_cabin_layout"),
            ["cabin_layout"],
            unique=False
        )
        batch_op.create_index(
            "idx_workcard_clean_local_cfg_dict_cabin",
            ["configuration_id", "dict_id", "cabin_layout"],
            unique=False
        )

    # Add cabin_layout column to workcard_clean_local_upload
    with op.batch_alter_table("workcard_clean_local_upload", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cabin_layout", sa.String(length=100), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_workcard_clean_local_upload_cabin_layout"),
            ["cabin_layout"],
            unique=False
        )
        batch_op.create_index(
            "idx_workcard_clean_local_upload_cfg_dict_cabin",
            ["configuration_id", "dict_id", "cabin_layout"],
            unique=False
        )


def downgrade() -> None:
    # Drop indexes and column from workcard_clean_local_upload
    with op.batch_alter_table("workcard_clean_local_upload", schema=None) as batch_op:
        batch_op.drop_index("idx_workcard_clean_local_upload_cfg_dict_cabin")
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_cabin_layout"))
        batch_op.drop_column("cabin_layout")

    # Drop indexes and column from workcard_clean_local
    with op.batch_alter_table("workcard_clean_local", schema=None) as batch_op:
        batch_op.drop_index("idx_workcard_clean_local_cfg_dict_cabin")
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_cabin_layout"))
        batch_op.drop_column("cabin_layout")
