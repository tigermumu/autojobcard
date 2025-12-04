"""add defect cleaned data table

Revision ID: 004
Revises: 003
Create Date: 2025-11-07 12:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建缺陷清洗数据表
    op.create_table(
        'defect_cleaned_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('defect_record_id', sa.Integer(), nullable=False),
        sa.Column('main_area', sa.String(length=200), nullable=True),
        sa.Column('main_component', sa.String(length=200), nullable=True),
        sa.Column('first_level_subcomponent', sa.String(length=200), nullable=True),
        sa.Column('second_level_subcomponent', sa.String(length=200), nullable=True),
        sa.Column('orientation', sa.String(length=100), nullable=True),
        sa.Column('defect_subject', sa.String(length=200), nullable=True),
        sa.Column('defect_description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('quantity', sa.String(length=50), nullable=True),
        sa.Column('description_cn', sa.Text(), nullable=True),
        sa.Column('is_cleaned', sa.Boolean(), nullable=True),
        sa.Column('cleaned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('cleaning_confidence', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['defect_record_id'], ['defect_records.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('defect_record_id')
    )
    
    # 创建索引
    op.create_index(op.f('ix_defect_cleaned_data_id'), 'defect_cleaned_data', ['id'], unique=False)
    op.create_index(op.f('ix_defect_cleaned_data_defect_record_id'), 'defect_cleaned_data', ['defect_record_id'], unique=True)
    op.create_index(op.f('ix_defect_cleaned_data_main_area'), 'defect_cleaned_data', ['main_area'], unique=False)
    op.create_index(op.f('ix_defect_cleaned_data_main_component'), 'defect_cleaned_data', ['main_component'], unique=False)
    op.create_index(op.f('ix_defect_cleaned_data_first_level_subcomponent'), 'defect_cleaned_data', ['first_level_subcomponent'], unique=False)
    
    # 创建复合索引
    op.create_index('idx_defect_cleaned_main', 'defect_cleaned_data', ['main_area', 'main_component'], unique=False)
    op.create_index('idx_defect_cleaned_sub', 'defect_cleaned_data', ['main_area', 'main_component', 'first_level_subcomponent'], unique=False)


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_defect_cleaned_sub', table_name='defect_cleaned_data')
    op.drop_index('idx_defect_cleaned_main', table_name='defect_cleaned_data')
    op.drop_index(op.f('ix_defect_cleaned_data_first_level_subcomponent'), table_name='defect_cleaned_data')
    op.drop_index(op.f('ix_defect_cleaned_data_main_component'), table_name='defect_cleaned_data')
    op.drop_index(op.f('ix_defect_cleaned_data_main_area'), table_name='defect_cleaned_data')
    op.drop_index(op.f('ix_defect_cleaned_data_defect_record_id'), table_name='defect_cleaned_data')
    op.drop_index(op.f('ix_defect_cleaned_data_id'), table_name='defect_cleaned_data')
    
    # 删除表
    op.drop_table('defect_cleaned_data')





