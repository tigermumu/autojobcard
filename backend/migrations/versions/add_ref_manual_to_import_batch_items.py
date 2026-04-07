"""Add ref_manual column to import_batch_items

Revision ID: add_ref_manual_001
Revises: 
Create Date: 2026-01-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ref_manual_001'
down_revision = '4abf884358eb'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 ref_manual 字段到 import_batch_items 表
    with op.batch_alter_table('import_batch_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ref_manual', sa.String(length=200), nullable=True, comment='参考手册 (CMM_REFER)，来自Excel的 参考手册 列'))


def downgrade():
    # 删除 ref_manual 字段
    with op.batch_alter_table('import_batch_items', schema=None) as batch_op:
        batch_op.drop_column('ref_manual')
