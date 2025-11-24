"""Add configuration fields

Revision ID: 002
Revises: 001
Create Date: 2025-10-31 08:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加新的飞机构型参数字段
    op.add_column('configurations', sa.Column('msn', sa.String(length=50), nullable=True))
    op.add_column('configurations', sa.Column('model', sa.String(length=50), nullable=True))
    op.add_column('configurations', sa.Column('vartab', sa.String(length=50), nullable=True))
    op.add_column('configurations', sa.Column('customer', sa.String(length=100), nullable=True))
    op.add_column('configurations', sa.Column('amm_ipc_eff', sa.String(length=100), nullable=True))
    
    # 修改现有字段为可空
    op.alter_column('configurations', 'aircraft_type', nullable=True)
    op.alter_column('configurations', 'version', nullable=True)


def downgrade() -> None:
    # 删除新添加的字段
    op.drop_column('configurations', 'amm_ipc_eff')
    op.drop_column('configurations', 'customer')
    op.drop_column('configurations', 'vartab')
    op.drop_column('configurations', 'model')
    op.drop_column('configurations', 'msn')
    
    # 恢复字段非空约束
    op.alter_column('configurations', 'aircraft_type', nullable=False)
    op.alter_column('configurations', 'version', nullable=False)






















