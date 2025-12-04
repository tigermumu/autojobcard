from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class DefectList(Base):
    """缺陷清单表"""
    __tablename__ = "defect_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    aircraft_number = Column(String(20), nullable=False, index=True)  # 飞机号 B-XXXX
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 处理状态
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    processing_progress = Column(Float, default=0.0)
    
    # 配置关联
    configuration_id = Column(Integer, ForeignKey("configurations.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    configuration = relationship("Configuration", back_populates="defect_lists")
    defect_records = relationship("DefectRecord", back_populates="defect_list", cascade="all, delete-orphan")

class DefectRecord(Base):
    """缺陷记录表"""
    __tablename__ = "defect_records"
    
    id = Column(Integer, primary_key=True, index=True)
    defect_number = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    system = Column(String(100), nullable=False, index=True)
    component = Column(String(100), nullable=False, index=True)
    location = Column(String(200))
    severity = Column(String(20))  # critical, major, minor
    
    # 处理状态
    is_matched = Column(Boolean, default=False)
    is_selected = Column(Boolean, default=False)
    selected_workcard_id = Column(Integer, ForeignKey("workcards.id"))
    issued_workcard_number = Column(String(100), nullable=True)  # 已开出的工卡号
    
    # 原始数据
    raw_data = Column(JSON)
    
    defect_list_id = Column(Integer, ForeignKey("defect_lists.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    defect_list = relationship("DefectList", back_populates="defect_records")
    selected_workcard = relationship("WorkCard")
    matching_results = relationship("MatchingResult", back_populates="defect_record")
    cleaned_data = relationship("DefectCleanedData", back_populates="defect_record", uselist=False, cascade="all, delete-orphan")
