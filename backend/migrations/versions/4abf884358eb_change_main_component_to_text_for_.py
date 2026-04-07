"""change_main_component_to_text_for_multiple_keywords

Revision ID: 4abf884358eb
Revises: 8dfc709c65d2
Create Date: 2025-12-29 17:35:48.227376

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4abf884358eb'
down_revision = '8dfc709c65d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 修改 workcard_clean_local 表的 main_component 字段
    with op.batch_alter_table('workcard_clean_local', schema=None) as batch_op:
        # 删除索引
        batch_op.drop_index('ix_workcard_clean_local_main_component')
        # 修改字段类型为 Text
        batch_op.alter_column('main_component',
                            existing_type=sa.String(length=200),
                            type_=sa.Text(),
                            existing_nullable=True)
    
    # 修改 workcard_clean_local_upload 表的 main_component 字段
    with op.batch_alter_table('workcard_clean_local_upload', schema=None) as batch_op:
        # 删除索引（如果存在）
        try:
            batch_op.drop_index('ix_workcard_clean_local_upload_main_component')
        except Exception:
            pass  # 索引可能不存在
        # 修改字段类型为 Text
        batch_op.alter_column('main_component',
                            existing_type=sa.String(length=200),
                            type_=sa.Text(),
                            existing_nullable=True)
    
    # 修改 defect_clean_local 表的 main_component 字段
    with op.batch_alter_table('defect_clean_local', schema=None) as batch_op:
        # 删除索引
        batch_op.drop_index('ix_defect_clean_local_main_component')
        # 修改字段类型为 Text
        batch_op.alter_column('main_component',
                            existing_type=sa.String(length=200),
                            type_=sa.Text(),
                            existing_nullable=True)


def downgrade() -> None:
    # 恢复 workcard_clean_local 表的 main_component 字段
    with op.batch_alter_table('workcard_clean_local', schema=None) as batch_op:
        batch_op.alter_column('main_component',
                            existing_type=sa.Text(),
                            type_=sa.String(length=200),
                            existing_nullable=True)
        # 重新创建索引
        batch_op.create_index('ix_workcard_clean_local_main_component', ['main_component'], unique=False)
    
    # 恢复 workcard_clean_local_upload 表的 main_component 字段
    with op.batch_alter_table('workcard_clean_local_upload', schema=None) as batch_op:
        batch_op.alter_column('main_component',
                            existing_type=sa.Text(),
                            type_=sa.String(length=200),
                            existing_nullable=True)
        # 重新创建索引（如果之前存在）
        try:
            batch_op.create_index('ix_workcard_clean_local_upload_main_component', ['main_component'], unique=False)
        except Exception:
            pass
    
    # 恢复 defect_clean_local 表的 main_component 字段
    with op.batch_alter_table('defect_clean_local', schema=None) as batch_op:
        batch_op.alter_column('main_component',
                            existing_type=sa.Text(),
                            type_=sa.String(length=200),
                            existing_nullable=True)
        # 重新创建索引
        batch_op.create_index('ix_defect_clean_local_main_component', ['main_component'], unique=False)