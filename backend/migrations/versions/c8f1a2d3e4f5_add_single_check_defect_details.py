"""add_single_check_defect_details

Revision ID: c8f1a2d3e4f5
Revises: b7c3a9d2e4f1
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f1a2d3e4f5"
down_revision = "b7c3a9d2e4f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("single_defect_checks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("defect_status", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("defect_positions", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("defect_quantity", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("single_defect_checks", schema=None) as batch_op:
        batch_op.drop_column("defect_quantity")
        batch_op.drop_column("defect_positions")
        batch_op.drop_column("defect_status")

