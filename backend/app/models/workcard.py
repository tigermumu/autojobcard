from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class WorkCardType(Base):
    """工卡类型表"""
    __tablename__ = "workcard_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    workcards = relationship("WorkCard", back_populates="workcard_type")

class WorkCard(Base):
    """工卡基础数据表"""
    __tablename__ = "workcards"
    
    id = Column(Integer, primary_key=True, index=True)
    workcard_number = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    system = Column(String(100), nullable=False, index=True)
    component = Column(String(100), nullable=False, index=True)
    location = Column(String(200))
    action = Column(Text)
    configuration_id = Column(Integer, ForeignKey("configurations.id"))
    workcard_type_id = Column(Integer, ForeignKey("workcard_types.id"))
    
    # 单机构型识别字段
    aircraft_number = Column(String(50), nullable=True, index=True, comment="飞机号，例如B-XXXX")
    aircraft_type = Column(String(50), nullable=True, index=True, comment="机型，冗余存储以便快速查询")
    msn = Column(String(50), nullable=True, index=True, comment="MSN，冗余存储以便快速查询")
    amm_ipc_eff = Column(String(100), nullable=True, index=True, comment="AMM/IPC EFF，冗余存储以便快速查询")
    
    # 清洗后的索引字段（9个字段）
    main_area = Column(String(200), nullable=True, index=True, comment="主区域")
    main_component = Column(String(200), nullable=True, index=True, comment="主部件")
    first_level_subcomponent = Column(String(200), nullable=True, index=True, comment="一级子部件")
    second_level_subcomponent = Column(String(200), nullable=True, index=True, comment="二级子部件")
    orientation = Column(String(100), nullable=True, comment="方位")
    defect_subject = Column(String(200), nullable=True, comment="缺陷主体")
    defect_description = Column(Text, nullable=True, comment="缺陷描述")
    location_index = Column(String(200), nullable=True, comment="位置索引")
    quantity = Column(String(50), nullable=True, comment="数量")
    
    # 原始数据备份（JSON格式保存完整原始数据）
    raw_data = Column(Text, nullable=True, comment="原始数据JSON备份")
    
    # 清洗状态
    is_cleaned = Column(Boolean, default=False)
    cleaning_confidence = Column(Float, default=0.0)
    cleaning_notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 复合索引：用于快速查询单机构型工卡数据
    __table_args__ = (
        Index('idx_aircraft_config', 'aircraft_number', 'aircraft_type', 'msn', 'amm_ipc_eff'),
        Index('idx_config_cleaned', 'configuration_id', 'is_cleaned'),
    )
    
    # 关系
    configuration = relationship("Configuration", back_populates="workcards")
    workcard_type = relationship("WorkCardType", back_populates="workcards")
    matching_results = relationship("MatchingResult", back_populates="workcard")
