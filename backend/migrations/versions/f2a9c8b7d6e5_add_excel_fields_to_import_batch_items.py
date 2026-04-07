"""add_excel_fields_to_import_batch_items

Revision ID: f2a9c8b7d6e5
Revises: db574b6a01b8
Create Date: 2026-03-07 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a9c8b7d6e5'
down_revision = 'db574b6a01b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('import_batch_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('loc', sa.String(length=100), nullable=True, comment='位置 (Location)'))
        batch_op.add_column(sa.Column('qty', sa.Integer(), nullable=True, comment='数量 (Qty)'))
        batch_op.add_column(sa.Column('comp_pn', sa.String(length=100), nullable=True, comment='部件件号 (P/N)'))
        batch_op.add_column(sa.Column('keywords_1', sa.String(length=100), nullable=True, comment='关键词1'))
        batch_op.add_column(sa.Column('keywords_2', sa.String(length=100), nullable=True, comment='关键词2'))
        batch_op.add_column(sa.Column('candidate_description_cn', sa.Text(), nullable=True, comment='历史工卡描述（中文），来自Excel的 Candidate Workcard Description (Chinese) 列'))


def downgrade() -> None:
    with op.batch_alter_table('import_batch_items', schema=None) as batch_op:
        batch_op.drop_column('candidate_description_cn')
        batch_op.drop_column('keywords_2')
        batch_op.drop_column('keywords_1')
        batch_op.drop_column('comp_pn')
        batch_op.drop_column('qty')
        batch_op.drop_column('loc')
