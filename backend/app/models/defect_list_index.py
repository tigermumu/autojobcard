"""
缺陷清单索引表模型
用于存储索引表配置和数据
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DefectListIndex(Base):
    """缺陷清单索引表配置"""
    __tablename__ = "defect_list_index"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 配置信息
    name = Column(String(200), nullable=True)  # 索引表名称（可选）
    sale_wo = Column(String(50), nullable=False, index=True)  # 销售指令号
    ac_no = Column(String(50), nullable=False, index=True)  # 飞机号
    
    # 元数据
    row_count = Column(Integer, default=0)  # 数据行数
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联的索引项
    items = relationship("DefectListIndexItem", back_populates="index", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DefectListIndex(id={self.id}, sale_wo='{self.sale_wo}', ac_no='{self.ac_no}')>"


class DefectListIndexItem(Base):
    """缺陷清单索引表数据项"""
    __tablename__ = "defect_list_index_item"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 关联索引表
    index_id = Column(Integer, ForeignKey("defect_list_index.id", ondelete="CASCADE"), nullable=False)
    
    # 索引数据字段
    comp_pn = Column(String(100), nullable=True, index=True)  # Component P/N
    comp_desc = Column(String(200), nullable=True, index=True)  # Component Description
    comp_cmm = Column(String(200), nullable=True)  # Component Manual (CMM)
    comp_cmm_rev = Column(String(50), nullable=True)  # Component Manual Revision
    remark = Column(Text, nullable=True)  # Remark
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    index = relationship("DefectListIndex", back_populates="items")
    
    def __repr__(self):
        return f"<DefectListIndexItem(id={self.id}, comp_pn='{self.comp_pn}', comp_desc='{self.comp_desc}')>"
