from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class DefectScheme(Base):
    """
    缺陷处理方案主表
    对应 CSV 中的 defect_catalog 维度
    """
    __tablename__ = "defect_schemes"

    id = Column(Integer, primary_key=True, index=True)
    comp_pn = Column(String(50), nullable=False, index=True, comment="部件件号")
    defect_catalog = Column(Integer, nullable=False, comment="缺陷分类号")
    
    jc_desc_cn = Column(Text, nullable=True, comment="标准缺陷描述(中文)")
    jc_desc_en = Column(Text, nullable=True, comment="标准缺陷描述(英文)")
    
    key_words_1 = Column(String(100), nullable=True, index=True, comment="关键词1")
    key_words_2 = Column(String(100), nullable=True, index=True, comment="关键词2")
    
    trade = Column(String(50), nullable=True, comment="工种")
    zone = Column(String(50), nullable=True, comment="区域")
    loc = Column(String(100), nullable=True, comment="位置")
    qty = Column(Integer, nullable=True, comment="数量")
    jc_type = Column(String(50), nullable=True, comment="工卡类型")
    labor = Column(Float, nullable=True, comment="人工")
    manhour = Column(Float, nullable=True, comment="总工时")
    
    candidate_history_wo = Column(String(100), nullable=True, comment="候选历史工卡指令号")
    refer_manual = Column(String(100), nullable=True, comment="参考手册")
    type = Column(String(50), nullable=True, comment="机型")
    cust = Column(String(50), nullable=True, comment="客户")
    comp_name = Column(String(100), nullable=True, comment="部件名称")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    steps = relationship("DefectStep", back_populates="scheme", cascade="all, delete-orphan", order_by="DefectStep.step_number")

    # 约束与索引
    __table_args__ = (
        UniqueConstraint('comp_pn', 'defect_catalog', name='uix_comp_pn_catalog'),
        Index('idx_scheme_search', 'comp_pn', 'key_words_1', 'key_words_2'),
    )

class DefectStep(Base):
    """
    工序步骤表
    对应 CSV 中的 steps_item 维度
    """
    __tablename__ = "defect_steps"

    id = Column(Integer, primary_key=True, index=True)
    scheme_id = Column(Integer, ForeignKey("defect_schemes.id"), nullable=False, index=True)
    
    step_number = Column(Integer, nullable=False, comment="步骤号")
    step_desc_cn = Column(Text, nullable=True, comment="工序指导(中文)")
    step_desc_en = Column(Text, nullable=True, comment="工序指导(英文)")
    manhour = Column(Float, nullable=True, comment="步骤工时")
    trade = Column(String(50), nullable=True, comment="工种")
    manpower = Column(String(50), nullable=True, comment="人力")
    refer_manual = Column(String(100), nullable=True, comment="参考手册")
    
    # 关系
    scheme = relationship("DefectScheme", back_populates="steps")
    materials = relationship("DefectMaterial", back_populates="step", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_scheme_step', 'scheme_id', 'step_number'),
    )

class DefectMaterial(Base):
    """
    航材物料表
    将 CSV 中的 PN_REQUESTED 字符串解析后存储
    """
    __tablename__ = "defect_materials"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("defect_steps.id"), nullable=False, index=True)
    material_seq = Column(Integer, nullable=True, comment="航材序号")
    
    part_number = Column(String(50), nullable=False, index=True, comment="航材件号")
    amount = Column(Float, nullable=True, comment="数量")
    unit = Column(String(20), nullable=True, comment="单位")
    remark = Column(String(200), nullable=True, comment="备注")
    
    # 关系
    step = relationship("DefectStep", back_populates="materials")
