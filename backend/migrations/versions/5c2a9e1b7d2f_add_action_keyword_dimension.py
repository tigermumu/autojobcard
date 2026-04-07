"""add action keyword dimension fields

Revision ID: 5c2a9e1b7d2f
Revises: ef12b7a6c0a1
Create Date: 2025-12-26

"""

from alembic import op
import sqlalchemy as sa


revision = "5c2a9e1b7d2f"
down_revision = "ef12b7a6c0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workcard_clean_local", schema=None) as batch_op:
        batch_op.add_column(sa.Column("action", sa.String(length=200), nullable=True))
        batch_op.create_index(batch_op.f("ix_workcard_clean_local_action"), ["action"], unique=False)

    with op.batch_alter_table("defect_clean_local", schema=None) as batch_op:
        batch_op.add_column(sa.Column("action", sa.String(length=200), nullable=True))
        batch_op.create_index(batch_op.f("ix_defect_clean_local_action"), ["action"], unique=False)

    with op.batch_alter_table("defect_match_local", schema=None) as batch_op:
        batch_op.add_column(sa.Column("score_action", sa.Float(), nullable=False, server_default="0.0"))

    with op.batch_alter_table("workcard_clean_local_upload", schema=None) as batch_op:
        batch_op.add_column(sa.Column("action", sa.String(length=200), nullable=True))
        batch_op.create_index(batch_op.f("ix_workcard_clean_local_upload_action"), ["action"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("workcard_clean_local_upload", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_action"))
        batch_op.drop_column("action")

    with op.batch_alter_table("defect_match_local", schema=None) as batch_op:
        batch_op.drop_column("score_action")

    with op.batch_alter_table("defect_clean_local", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_defect_clean_local_action"))
        batch_op.drop_column("action")

    with op.batch_alter_table("workcard_clean_local", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_action"))
        batch_op.drop_column("action")








