from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class MatchingResult(Base):
    """匹配结果表"""
    __tablename__ = "matching_results"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 相似度评分
    similarity_score = Column(Float, nullable=False, index=True)
    is_candidate = Column(Boolean, default=False)  # 是否为候选工卡
    
    # 匹配详情
    matching_details = Column(JSON)  # 各字段匹配详情
    algorithm_version = Column(String(20), default="1.0")
    
    # 关联记录
    defect_record_id = Column(Integer, ForeignKey("defect_records.id"))
    workcard_id = Column(Integer, ForeignKey("workcards.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    defect_record = relationship("DefectRecord", back_populates="matching_results")
    workcard = relationship("WorkCard", back_populates="matching_results")

class CandidateWorkCard(Base):
    """候选工卡表（用于快速查询）"""
    __tablename__ = "candidate_workcards"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 候选工卡信息
    defect_record_id = Column(Integer, ForeignKey("defect_records.id"), nullable=False)
    workcard_id = Column(Integer, ForeignKey("workcards.id"), nullable=False)
    similarity_score = Column(Float, nullable=False, index=True)
    
    # 用户选择状态
    is_selected = Column(Boolean, default=False)
    selection_notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    defect_record = relationship("DefectRecord")
    workcard = relationship("WorkCard")
