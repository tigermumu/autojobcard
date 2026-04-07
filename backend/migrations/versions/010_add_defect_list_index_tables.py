"""add defect list index tables

Revision ID: 010_defect_list_index
Revises: 
Create Date: 2026-01-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_defect_list_index'
down_revision = 'add_ref_manual_001'
branch_labels = None
depends_on = None


def upgrade():
    # 创建缺陷清单索引表
    op.create_table(
        'defect_list_index',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('sale_wo', sa.String(50), nullable=False),
        sa.Column('ac_no', sa.String(50), nullable=False),
        sa.Column('row_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_defect_list_index_id', 'defect_list_index', ['id'])
    op.create_index('ix_defect_list_index_sale_wo', 'defect_list_index', ['sale_wo'])
    op.create_index('ix_defect_list_index_ac_no', 'defect_list_index', ['ac_no'])
    
    # 创建缺陷清单索引项表
    op.create_table(
        'defect_list_index_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('index_id', sa.Integer(), nullable=False),
        sa.Column('area', sa.String(100), nullable=True),
        sa.Column('component', sa.String(200), nullable=True),
        sa.Column('pn', sa.String(100), nullable=True),
        sa.Column('cmm', sa.String(200), nullable=True),
        sa.Column('relate_jc_seq', sa.String(20), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['index_id'], ['defect_list_index.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_defect_list_index_item_id', 'defect_list_index_item', ['id'])
    op.create_index('ix_defect_list_index_item_area', 'defect_list_index_item', ['area'])
    op.create_index('ix_defect_list_index_item_component', 'defect_list_index_item', ['component'])


def downgrade():
    op.drop_table('defect_list_index_item')
    op.drop_table('defect_list_index')
