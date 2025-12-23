from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class IndexData(Base):
    """索引数据表"""
    __tablename__ = "index_data"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Hierarchy fields (all optional)
    main_area = Column(String(100), nullable=True, index=True)  # Main Area
    main_component = Column(String(100), nullable=True, index=True)  # Main Component
    first_level_subcomponent = Column(String(100), nullable=True, index=True)  # First Level Subcomponent
    second_level_subcomponent = Column(String(100), nullable=True, index=True)  # Second Level Subcomponent
    
    # 独立字段
    orientation = Column(String(50), nullable=True)  # 方位
    defect_subject = Column(String(200), nullable=True)  # 缺陷主体
    defect_description = Column(Text, nullable=True)  # 缺陷描述
    location = Column(String(200), nullable=True)  # 位置
    quantity = Column(String(50), nullable=True)  # 数量
    
    # 关联配置
    configuration_id = Column(Integer, ForeignKey("configurations.id"))
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    configuration = relationship("Configuration")
    
    def __repr__(self):
        return f"<IndexData(id={self.id}, main_area='{self.main_area}', main_component='{self.main_component}')>"



