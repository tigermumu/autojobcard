"""add_batch_check_defect_details

Revision ID: d9a0b1c2d3e4
Revises: c8f1a2d3e4f5
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "d9a0b1c2d3e4"
down_revision = "c8f1a2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("batch_defect_checks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("yes_flag", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("no_flag", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("defect_status", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("defect_positions", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("defect_quantity", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("batch_defect_checks", schema=None) as batch_op:
        batch_op.drop_column("defect_quantity")
        batch_op.drop_column("defect_positions")
        batch_op.drop_column("defect_status")
        batch_op.drop_column("no_flag")
        batch_op.drop_column("yes_flag")

