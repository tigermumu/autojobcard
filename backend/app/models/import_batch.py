from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    defect_list_id = Column(Integer, ForeignKey("defect_lists.id"), nullable=True)
    aircraft_number = Column(String(50), nullable=False)
    workcard_number = Column(String(100), nullable=False)
    maintenance_level = Column(String(100), nullable=False)
    aircraft_type = Column(String(100), nullable=False)
    customer = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship(
        "ImportBatchItem",
        back_populates="batch",
        cascade="all, delete-orphan"
    )


class ImportBatchItem(Base):
    __tablename__ = "import_batch_items"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    defect_record_id = Column(Integer, ForeignKey("defect_records.id"), nullable=True)
    defect_number = Column(String(100), nullable=False)
    description_cn = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    workcard_number = Column(String(100), nullable=True)  # 候选工卡，Excel中没有数据时可以留空
    issued_workcard_number = Column(String(100), nullable=True)  # Store relative/already issued workcard number
    selected_workcard_id = Column(Integer, nullable=True)
    similarity_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("ImportBatch", back_populates="items")

    # 新增字段 - 用于保存 Excel 导入的扩展信息
    reference_workcard_number = Column(String(100), nullable=True, comment="相关工卡号 (txtCRN)")
    reference_workcard_item = Column(String(100), nullable=True, comment="相关工卡序号 (refNo)")
    area = Column(String(100), nullable=True, comment="区域 (txtZoneName)")
    zone_number = Column(String(100), nullable=True, comment="区域号 (txtZoneTen)")
    loc = Column(String(100), nullable=True, comment="位置 (Location)")
    qty = Column(Integer, nullable=True, comment="数量 (Qty)")
    comp_pn = Column(String(100), nullable=True, comment="部件件号 (P/N)")
    keywords_1 = Column(String(100), nullable=True, comment="关键词1")
    keywords_2 = Column(String(100), nullable=True, comment="关键词2")
    candidate_description_en = Column(Text, nullable=True, comment="历史工卡描述（英文），来自Excel的 Candidate Workcard Description (English) 列")
    candidate_description_cn = Column(Text, nullable=True, comment="历史工卡描述（中文），来自Excel的 Candidate Workcard Description (Chinese) 列")
    ref_manual = Column(String(200), nullable=True, comment="参考手册 (CMM_REFER)，来自Excel的 参考手册 列")








