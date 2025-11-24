"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建工卡类型表
    op.create_table('workcard_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workcard_types_id'), 'workcard_types', ['id'], unique=False)
    op.create_index(op.f('ix_workcard_types_name'), 'workcard_types', ['name'], unique=True)

    # 创建构型配置表
    op.create_table('configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('aircraft_type', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('index_file_path', sa.String(length=500), nullable=True),
        sa.Column('field_mapping', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_configurations_id'), 'configurations', ['id'], unique=False)
    op.create_index(op.f('ix_configurations_name'), 'configurations', ['name'], unique=True)

    # 创建索引文件表
    op.create_table('index_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=200), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('field_mapping', sa.JSON(), nullable=True),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('configuration_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['configuration_id'], ['configurations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_index_files_id'), 'index_files', ['id'], unique=False)

    # 创建工卡表
    op.create_table('workcards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workcard_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system', sa.String(length=100), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('action', sa.Text(), nullable=True),
        sa.Column('configuration_id', sa.Integer(), nullable=True),
        sa.Column('workcard_type_id', sa.Integer(), nullable=True),
        sa.Column('is_cleaned', sa.Boolean(), nullable=True),
        sa.Column('cleaning_confidence', sa.Float(), nullable=True),
        sa.Column('cleaning_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['configuration_id'], ['configurations.id'], ),
        sa.ForeignKeyConstraint(['workcard_type_id'], ['workcard_types.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workcards_id'), 'workcards', ['id'], unique=False)
    op.create_index(op.f('ix_workcards_workcard_number'), 'workcards', ['workcard_number'], unique=False)
    op.create_index(op.f('ix_workcards_system'), 'workcards', ['system'], unique=False)
    op.create_index(op.f('ix_workcards_component'), 'workcards', ['component'], unique=False)

    # 创建缺陷清单表
    op.create_table('defect_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aircraft_number', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('processing_progress', sa.Float(), nullable=True),
        sa.Column('configuration_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['configuration_id'], ['configurations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_defect_lists_id'), 'defect_lists', ['id'], unique=False)
    op.create_index(op.f('ix_defect_lists_aircraft_number'), 'defect_lists', ['aircraft_number'], unique=False)

    # 创建缺陷记录表
    op.create_table('defect_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('defect_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system', sa.String(length=100), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('is_matched', sa.Boolean(), nullable=True),
        sa.Column('is_selected', sa.Boolean(), nullable=True),
        sa.Column('selected_workcard_id', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('defect_list_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['defect_list_id'], ['defect_lists.id'], ),
        sa.ForeignKeyConstraint(['selected_workcard_id'], ['workcards.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_defect_records_id'), 'defect_records', ['id'], unique=False)
    op.create_index(op.f('ix_defect_records_system'), 'defect_records', ['system'], unique=False)
    op.create_index(op.f('ix_defect_records_component'), 'defect_records', ['component'], unique=False)

    # 创建匹配结果表
    op.create_table('matching_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('is_candidate', sa.Boolean(), nullable=True),
        sa.Column('matching_details', sa.JSON(), nullable=True),
        sa.Column('algorithm_version', sa.String(length=20), nullable=True),
        sa.Column('defect_record_id', sa.Integer(), nullable=True),
        sa.Column('workcard_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['defect_record_id'], ['defect_records.id'], ),
        sa.ForeignKeyConstraint(['workcard_id'], ['workcards.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matching_results_id'), 'matching_results', ['id'], unique=False)
    op.create_index(op.f('ix_matching_results_similarity_score'), 'matching_results', ['similarity_score'], unique=False)

    # 创建候选工卡表
    op.create_table('candidate_workcards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('defect_record_id', sa.Integer(), nullable=False),
        sa.Column('workcard_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('is_selected', sa.Boolean(), nullable=True),
        sa.Column('selection_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['defect_record_id'], ['defect_records.id'], ),
        sa.ForeignKeyConstraint(['workcard_id'], ['workcards.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_workcards_id'), 'candidate_workcards', ['id'], unique=False)
    op.create_index(op.f('ix_candidate_workcards_similarity_score'), 'candidate_workcards', ['similarity_score'], unique=False)

    # 创建索引数据表
    op.create_table('index_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('main_area', sa.String(length=100), nullable=False),
        sa.Column('main_component', sa.String(length=100), nullable=False),
        sa.Column('first_level_subcomponent', sa.String(length=100), nullable=False),
        sa.Column('second_level_subcomponent', sa.String(length=100), nullable=False),
        sa.Column('orientation', sa.String(length=50), nullable=True),
        sa.Column('defect_subject', sa.String(length=200), nullable=True),
        sa.Column('defect_description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('quantity', sa.String(length=50), nullable=True),
        sa.Column('configuration_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['configuration_id'], ['configurations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_index_data_id'), 'index_data', ['id'], unique=False)
    op.create_index(op.f('ix_index_data_main_area'), 'index_data', ['main_area'], unique=False)
    op.create_index(op.f('ix_index_data_main_component'), 'index_data', ['main_component'], unique=False)
    op.create_index(op.f('ix_index_data_first_level_subcomponent'), 'index_data', ['first_level_subcomponent'], unique=False)
    op.create_index(op.f('ix_index_data_second_level_subcomponent'), 'index_data', ['second_level_subcomponent'], unique=False)

    # 插入默认工卡类型
    op.execute("INSERT INTO workcard_types (name, description) VALUES ('检查工卡', '飞机检查类工卡')")
    op.execute("INSERT INTO workcard_types (name, description) VALUES ('维修工卡', '飞机维修类工卡')")
    op.execute("INSERT INTO workcard_types (name, description) VALUES ('更换工卡', '部件更换类工卡')")


def downgrade() -> None:
    # 删除表（按相反顺序）
    op.drop_table('index_data')
    op.drop_table('candidate_workcards')
    op.drop_table('matching_results')
    op.drop_table('defect_records')
    op.drop_table('defect_lists')
    op.drop_table('workcards')
    op.drop_table('index_files')
    op.drop_table('configurations')
    op.drop_table('workcard_types')
