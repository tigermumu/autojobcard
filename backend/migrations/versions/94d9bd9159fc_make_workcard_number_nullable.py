"""make workcard_number nullable in import_batch_items

Revision ID: 94d9bd9159fc
Revises: 156d20ab3d58
Create Date: 2025-12-16 18:30:37

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '94d9bd9159fc'
down_revision = '156d20ab3d58'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 将 import_batch_items 表的 workcard_number 字段改为可空
    # 候选工卡，Excel中没有数据时可以留空
    with op.batch_alter_table('import_batch_items', schema=None) as batch_op:
        batch_op.alter_column('workcard_number',
                              existing_type=sa.String(length=100),
                              nullable=True)


def downgrade() -> None:
    # 恢复 workcard_number 字段为必填
    # 注意：如果数据库中有 NULL 值，此操作可能会失败
    with op.batch_alter_table('import_batch_items', schema=None) as batch_op:
        batch_op.alter_column('workcard_number',
                              existing_type=sa.String(length=100),
                              nullable=False)










