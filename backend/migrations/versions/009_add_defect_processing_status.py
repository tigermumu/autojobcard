"""add_defect_processing_status

Revision ID: 009
Revises: 008
Create Date: 2025-12-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 为 defect_lists 表添加处理状态和进度字段
    with op.batch_alter_table('defect_lists', schema=None) as batch_op:
        # 检查字段是否存在，如果不存在才添加
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        existing_columns = [col['name'] for col in inspector.get_columns('defect_lists')]
        
        if 'cleaning_status' not in existing_columns:
            batch_op.add_column(sa.Column('cleaning_status', sa.String(length=20), server_default='pending', nullable=True))
        if 'cleaning_progress' not in existing_columns:
            batch_op.add_column(sa.Column('cleaning_progress', sa.Float(), server_default='0.0', nullable=True))
        if 'matching_status' not in existing_columns:
            batch_op.add_column(sa.Column('matching_status', sa.String(length=20), server_default='pending', nullable=True))
        if 'matching_progress' not in existing_columns:
            batch_op.add_column(sa.Column('matching_progress', sa.Float(), server_default='0.0', nullable=True))
        if 'processing_stage' not in existing_columns:
            batch_op.add_column(sa.Column('processing_stage', sa.String(length=20), server_default='upload', nullable=True))
        if 'last_processed_at' not in existing_columns:
            batch_op.add_column(sa.Column('last_processed_at', sa.DateTime(timezone=True), nullable=True))
    
    # 为 defect_records 表添加处理状态字段
    with op.batch_alter_table('defect_records', schema=None) as batch_op:
        # 检查字段是否存在，如果不存在才添加
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        existing_columns = [col['name'] for col in inspector.get_columns('defect_records')]
        
        if 'is_cleaned' not in existing_columns:
            batch_op.add_column(sa.Column('is_cleaned', sa.Boolean(), server_default='0', nullable=True))
        if 'cleaned_at' not in existing_columns:
            batch_op.add_column(sa.Column('cleaned_at', sa.DateTime(timezone=True), nullable=True))
        if 'is_matched' not in existing_columns:
            batch_op.add_column(sa.Column('is_matched', sa.Boolean(), server_default='0', nullable=True))
        if 'matched_at' not in existing_columns:
            batch_op.add_column(sa.Column('matched_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # 移除 defect_lists 表的字段
    with op.batch_alter_table('defect_lists', schema=None) as batch_op:
        batch_op.drop_column('last_processed_at')
        batch_op.drop_column('processing_stage')
        batch_op.drop_column('matching_progress')
        batch_op.drop_column('matching_status')
        batch_op.drop_column('cleaning_progress')
        batch_op.drop_column('cleaning_status')
    
    # 移除 defect_records 表的字段（注意：is_matched 可能已存在，需要检查）
    with op.batch_alter_table('defect_records', schema=None) as batch_op:
        try:
            batch_op.drop_column('matched_at')
        except:
            pass
        try:
            batch_op.drop_column('is_matched')
        except:
            pass  # 如果字段已存在，保留它
        try:
            batch_op.drop_column('cleaned_at')
        except:
            pass
        try:
            batch_op.drop_column('is_cleaned')
        except:
            pass














