"""Add workcard aircraft identification fields and cleaned index fields

Revision ID: 003
Revises: 002
Create Date: 2025-01-31 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加单机构型识别字段
    op.add_column('workcards', sa.Column('aircraft_number', sa.String(length=50), nullable=True, comment='飞机号，例如B-XXXX'))
    op.add_column('workcards', sa.Column('aircraft_type', sa.String(length=50), nullable=True, comment='机型，冗余存储以便快速查询'))
    op.add_column('workcards', sa.Column('msn', sa.String(length=50), nullable=True, comment='MSN，冗余存储以便快速查询'))
    op.add_column('workcards', sa.Column('amm_ipc_eff', sa.String(length=100), nullable=True, comment='AMM/IPC EFF，冗余存储以便快速查询'))
    
    # 添加清洗后的索引字段（9个字段）
    op.add_column('workcards', sa.Column('main_area', sa.String(length=200), nullable=True, comment='主区域'))
    op.add_column('workcards', sa.Column('main_component', sa.String(length=200), nullable=True, comment='主部件'))
    op.add_column('workcards', sa.Column('first_level_subcomponent', sa.String(length=200), nullable=True, comment='一级子部件'))
    op.add_column('workcards', sa.Column('second_level_subcomponent', sa.String(length=200), nullable=True, comment='二级子部件'))
    op.add_column('workcards', sa.Column('orientation', sa.String(length=100), nullable=True, comment='方位'))
    op.add_column('workcards', sa.Column('defect_subject', sa.String(length=200), nullable=True, comment='缺陷主体'))
    op.add_column('workcards', sa.Column('defect_description', sa.Text(), nullable=True, comment='缺陷描述'))
    op.add_column('workcards', sa.Column('location_index', sa.String(length=200), nullable=True, comment='位置索引'))
    op.add_column('workcards', sa.Column('quantity', sa.String(length=50), nullable=True, comment='数量'))
    
    # 添加原始数据备份字段
    op.add_column('workcards', sa.Column('raw_data', sa.Text(), nullable=True, comment='原始数据JSON备份'))
    
    # 创建索引
    op.create_index('ix_workcards_aircraft_number', 'workcards', ['aircraft_number'])
    op.create_index('ix_workcards_aircraft_type', 'workcards', ['aircraft_type'])
    op.create_index('ix_workcards_msn', 'workcards', ['msn'])
    op.create_index('ix_workcards_amm_ipc_eff', 'workcards', ['amm_ipc_eff'])
    op.create_index('ix_workcards_main_area', 'workcards', ['main_area'])
    op.create_index('ix_workcards_main_component', 'workcards', ['main_component'])
    op.create_index('ix_workcards_first_level_subcomponent', 'workcards', ['first_level_subcomponent'])
    op.create_index('ix_workcards_second_level_subcomponent', 'workcards', ['second_level_subcomponent'])
    
    # 创建复合索引：用于快速查询单机构型工卡数据
    op.create_index('idx_aircraft_config', 'workcards', 
                    ['aircraft_number', 'aircraft_type', 'msn', 'amm_ipc_eff'])
    op.create_index('idx_config_cleaned', 'workcards', 
                    ['configuration_id', 'is_cleaned'])


def downgrade() -> None:
    # 删除复合索引
    op.drop_index('idx_config_cleaned', table_name='workcards')
    op.drop_index('idx_aircraft_config', table_name='workcards')
    
    # 删除索引字段的索引
    op.drop_index('ix_workcards_second_level_subcomponent', table_name='workcards')
    op.drop_index('ix_workcards_first_level_subcomponent', table_name='workcards')
    op.drop_index('ix_workcards_main_component', table_name='workcards')
    op.drop_index('ix_workcards_main_area', table_name='workcards')
    op.drop_index('ix_workcards_amm_ipc_eff', table_name='workcards')
    op.drop_index('ix_workcards_msn', table_name='workcards')
    op.drop_index('ix_workcards_aircraft_type', table_name='workcards')
    op.drop_index('ix_workcards_aircraft_number', table_name='workcards')
    
    # 删除原始数据备份字段
    op.drop_column('workcards', 'raw_data')
    
    # 删除清洗后的索引字段
    op.drop_column('workcards', 'quantity')
    op.drop_column('workcards', 'location_index')
    op.drop_column('workcards', 'defect_description')
    op.drop_column('workcards', 'defect_subject')
    op.drop_column('workcards', 'orientation')
    op.drop_column('workcards', 'second_level_subcomponent')
    op.drop_column('workcards', 'first_level_subcomponent')
    op.drop_column('workcards', 'main_component')
    op.drop_column('workcards', 'main_area')
    
    # 删除单机构型识别字段
    op.drop_column('workcards', 'amm_ipc_eff')
    op.drop_column('workcards', 'msn')
    op.drop_column('workcards', 'aircraft_type')
    op.drop_column('workcards', 'aircraft_number')



















