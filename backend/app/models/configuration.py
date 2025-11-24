from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Configuration(Base):
    """飞机构型配置表"""
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    
    # 飞机构型参数
    aircraft_type = Column(String(50), nullable=True)  # 机型
    msn = Column(String(50), nullable=True)  # MSN
    model = Column(String(50), nullable=True)  # MODEL
    vartab = Column(String(50), nullable=True)  # VARTAB
    customer = Column(String(100), nullable=True)  # 客户
    amm_ipc_eff = Column(String(100), nullable=True)  # AMM/IPC EFF
    
    version = Column(String(20), nullable=True)  # 版本（保留用于兼容）
    description = Column(Text)  # 描述
    
    # 索引文件配置
    index_file_path = Column(String(500))
    field_mapping = Column(JSON)  # 字段映射配置
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    workcards = relationship("WorkCard", back_populates="configuration")
    defect_lists = relationship("DefectList", back_populates="configuration")

class IndexFile(Base):
    """索引文件表"""
    __tablename__ = "index_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    
    # 文件内容配置
    field_mapping = Column(JSON)
    validation_rules = Column(JSON)
    
    configuration_id = Column(Integer, ForeignKey("configurations.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    configuration = relationship("Configuration")
