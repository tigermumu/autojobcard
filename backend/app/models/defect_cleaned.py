from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class DefectCleanedData(Base):
    """缺陷记录清洗后的数据表 - 存储清洗后的9个索引字段"""
    __tablename__ = "defect_cleaned_data"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 关联缺陷记录（一对一关系）
    defect_record_id = Column(Integer, ForeignKey("defect_records.id"), unique=True, nullable=False, index=True)
    
    # 清洗后的层级字段（有依赖关系）
    main_area = Column(String(200), nullable=True, index=True, comment="主区域")
    main_component = Column(String(200), nullable=True, index=True, comment="主部件")
    first_level_subcomponent = Column(String(200), nullable=True, index=True, comment="一级子部件")
    second_level_subcomponent = Column(String(200), nullable=True, index=True, comment="二级子部件")
    
    # 清洗后的独立字段
    orientation = Column(String(100), nullable=True, comment="方位")
    defect_subject = Column(String(200), nullable=True, comment="缺陷主体")
    defect_description = Column(Text, nullable=True, comment="缺陷描述")
    location = Column(String(200), nullable=True, comment="位置")
    quantity = Column(String(50), nullable=True, comment="数量")
    
    # 工卡描述（中文）- 原始描述文本
    description_cn = Column(Text, nullable=True, comment="工卡描述（中文）- 原始缺陷描述")
    
    # 清洗元数据
    is_cleaned = Column(Boolean, default=True, comment="是否已清洗")
    cleaned_at = Column(DateTime(timezone=True), server_default=func.now(), comment="清洗时间")
    cleaning_confidence = Column(String(50), nullable=True, comment="清洗置信度")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 复合索引：用于快速查询和筛选
    __table_args__ = (
        Index('idx_defect_cleaned_main', 'main_area', 'main_component'),
        Index('idx_defect_cleaned_sub', 'main_area', 'main_component', 'first_level_subcomponent'),
    )
    
    # 关系
    defect_record = relationship("DefectRecord", back_populates="cleaned_data", uselist=False)
    
    def __repr__(self):
        return f"<DefectCleanedData(id={self.id}, defect_record_id={self.defect_record_id}, main_area='{self.main_area}')>"


