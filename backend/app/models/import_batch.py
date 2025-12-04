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
    workcard_number = Column(String(100), nullable=False)
    selected_workcard_id = Column(Integer, nullable=True)
    similarity_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("ImportBatch", back_populates="items")









