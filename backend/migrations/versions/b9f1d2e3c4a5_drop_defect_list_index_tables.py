"""drop defect list index tables

Revision ID: b9f1d2e3c4a5
Revises: a6e4d0c1b9f3
Create Date: 2026-04-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b9f1d2e3c4a5"
down_revision = "a6e4d0c1b9f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("defect_list_index_item")
    op.drop_table("defect_list_index")


def downgrade() -> None:
    op.create_table(
        "defect_list_index",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("sale_wo", sa.String(length=50), nullable=False),
        sa.Column("ac_no", sa.String(length=50), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_defect_list_index_id", "defect_list_index", ["id"])
    op.create_index("ix_defect_list_index_sale_wo", "defect_list_index", ["sale_wo"])
    op.create_index("ix_defect_list_index_ac_no", "defect_list_index", ["ac_no"])
    op.create_table(
        "defect_list_index_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("index_id", sa.Integer(), nullable=False),
        sa.Column("area", sa.String(length=100), nullable=True),
        sa.Column("component", sa.String(length=200), nullable=True),
        sa.Column("pn", sa.String(length=100), nullable=True),
        sa.Column("cmm", sa.String(length=200), nullable=True),
        sa.Column("relate_jc_seq", sa.String(length=20), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["index_id"], ["defect_list_index.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_defect_list_index_item_id", "defect_list_index_item", ["id"])
    op.create_index("ix_defect_list_index_item_area", "defect_list_index_item", ["area"])
    op.create_index("ix_defect_list_index_item_component", "defect_list_index_item", ["component"])
