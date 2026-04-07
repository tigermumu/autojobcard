from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class KeywordDict(Base):
    """
    本地清洗/匹配：关键词字典头（按构型 configuration_id 多份，支持版本）。
    独立于现有 AI 链路；仅 local 模式使用。
    """

    __tablename__ = "keyword_dict"

    id = Column(Integer, primary_key=True, index=True)
    configuration_id = Column(Integer, ForeignKey("configurations.id"), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    remark = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    configuration = relationship("Configuration")
    items = relationship("KeywordDictItem", back_populates="dict", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("configuration_id", "version", name="uq_keyword_dict_configuration_version"),
    )


class KeywordDictItem(Base):
    """
    本地清洗/匹配：关键词字典明细（条目级启停）。

    dimension: main/sub/location/orientation/status
    - main_component: 用于 sub/location/orientation 绑定到某个主部件语境；status 不绑定（可空）。
    """

    __tablename__ = "keyword_dict_item"

    id = Column(Integer, primary_key=True, index=True)
    dict_id = Column(Integer, ForeignKey("keyword_dict.id"), nullable=False, index=True)
    dimension = Column(String(20), nullable=False, index=True)
    main_component = Column(String(200), nullable=True, index=True)
    keyword = Column(String(200), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dict = relationship("KeywordDict", back_populates="items")

    __table_args__ = (
        Index("idx_keyword_dict_item_dict_dim_main", "dict_id", "dimension", "main_component"),
    )


class GlobalKeyword(Base):
    __tablename__ = "global_keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(200), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkcardCleanLocal(Base):
    """本地清洗后的历史工卡结构化结果（独立于 workcards 原表字段）。"""

    __tablename__ = "workcard_clean_local"

    id = Column(Integer, primary_key=True, index=True)
    workcard_id = Column(Integer, ForeignKey("workcards.id"), nullable=False, index=True)
    aircraft_type = Column(String(50), nullable=True, index=True)

    configuration_id = Column(Integer, ForeignKey("configurations.id"), nullable=False, index=True)
    dict_id = Column(Integer, ForeignKey("keyword_dict.id"), nullable=False, index=True)
    dict_version = Column(String(50), nullable=False)

    description_en = Column(Text, nullable=True)
    description_cn = Column(Text, nullable=True)
    workcard_number = Column(String(50), nullable=True, index=True)

    main_component = Column(Text, nullable=True)  # 多值，逗号分隔
    sub_component = Column(Text, nullable=True)  # 多值，逗号分隔，移除索引
    location = Column(String(200), nullable=True, index=True)
    orientation = Column(String(100), nullable=True, index=True)
    status = Column(String(200), nullable=True, index=True)
    action = Column(String(200), nullable=True, index=True)
    cabin_layout = Column(String(100), nullable=True, index=True)  # 客舱布局标识

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workcard = relationship("WorkCard")
    configuration = relationship("Configuration")
    dict = relationship("KeywordDict")

    __table_args__ = (
        Index("idx_workcard_clean_local_cfg_dict", "configuration_id", "dict_id"),
        Index("idx_workcard_clean_local_cfg_dict_cabin", "configuration_id", "dict_id", "cabin_layout"),
    )


class WorkcardCleanLocalUpload(Base):
    """
    本地清洗后的历史工卡结构化结果（来自 /workcard/add 上传的 Excel，不依赖 workcards 原表）。
    用于实现“本地模式下清洗完成后保存到数据库”的需求。
    """

    __tablename__ = "workcard_clean_local_upload"

    id = Column(Integer, primary_key=True, index=True)

    configuration_id = Column(Integer, ForeignKey("configurations.id"), nullable=False, index=True)
    dict_id = Column(Integer, ForeignKey("keyword_dict.id"), nullable=False, index=True)
    dict_version = Column(String(50), nullable=False)

    description_en = Column(Text, nullable=True)
    description_cn = Column(Text, nullable=True)
    workcard_number = Column(String(50), nullable=True, index=True)

    main_component = Column(String(200), nullable=True, index=True)
    sub_component = Column(Text, nullable=True)  # 多值，逗号分隔
    location = Column(String(200), nullable=True, index=True)
    orientation = Column(String(100), nullable=True, index=True)
    status = Column(String(200), nullable=True, index=True)
    action = Column(String(200), nullable=True, index=True)
    error = Column(String(200), nullable=True)
    cabin_layout = Column(String(100), nullable=True, index=True)  # 客舱布局标识

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    configuration = relationship("Configuration")
    dict = relationship("KeywordDict")

    __table_args__ = (
        Index("idx_workcard_clean_local_upload_cfg_dict", "configuration_id", "dict_id"),
        Index("idx_workcard_clean_local_upload_cfg_dict_cabin", "configuration_id", "dict_id", "cabin_layout"),
    )


class DefectCleanLocal(Base):
    """本地清洗后的缺陷结构化结果（独立于 defect_cleaned_data/AI 链路）。"""

    __tablename__ = "defect_clean_local"

    id = Column(Integer, primary_key=True, index=True)
    defect_record_id = Column(Integer, ForeignKey("defect_records.id"), nullable=False, index=True)
    aircraft_type = Column(String(50), nullable=True, index=True)

    configuration_id = Column(Integer, ForeignKey("configurations.id"), nullable=False, index=True)
    dict_id = Column(Integer, ForeignKey("keyword_dict.id"), nullable=False, index=True)
    dict_version = Column(String(50), nullable=False)

    description_en = Column(Text, nullable=True)
    description_cn = Column(Text, nullable=True)

    main_component = Column(String(200), nullable=True, index=True)
    sub_component = Column(Text, nullable=True)  # 多值，逗号分隔
    location = Column(String(200), nullable=True, index=True)
    orientation = Column(String(100), nullable=True, index=True)
    status = Column(String(200), nullable=True, index=True)
    action = Column(String(200), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    defect_record = relationship("DefectRecord")
    configuration = relationship("Configuration")
    dict = relationship("KeywordDict")

    __table_args__ = (
        Index("idx_defect_clean_local_cfg_dict", "configuration_id", "dict_id"),
    )


class DefectMatchLocal(Base):
    """本地匹配候选结果（只存 score_total>=90 的候选；最终回归到 import_batch_items 字段口径）。"""

    __tablename__ = "defect_match_local"

    id = Column(Integer, primary_key=True, index=True)
    defect_record_id = Column(Integer, ForeignKey("defect_records.id"), nullable=False, index=True)
    workcard_id = Column(Integer, ForeignKey("workcards.id"), nullable=True, index=True)
    aircraft_type = Column(String(50), nullable=True, index=True)

    configuration_id = Column(Integer, ForeignKey("configurations.id"), nullable=False, index=True)
    dict_id = Column(Integer, ForeignKey("keyword_dict.id"), nullable=False, index=True)
    dict_version = Column(String(50), nullable=False)

    description_en = Column(Text, nullable=True)
    description_cn = Column(Text, nullable=True)
    candidate_desc_en = Column(Text, nullable=True)
    candidate_desc_cn = Column(Text, nullable=True)
    workcard_number = Column(String(50), nullable=True, index=True)

    score_total = Column(Float, nullable=False, default=0.0)
    score_main = Column(Float, nullable=False, default=0.0)
    score_sub = Column(Float, nullable=False, default=0.0)
    score_location = Column(Float, nullable=False, default=0.0)
    score_orientation = Column(Float, nullable=False, default=0.0)
    score_status = Column(Float, nullable=False, default=0.0)
    score_action = Column(Float, nullable=False, default=0.0)

    action = Column(String(200), nullable=True, index=True)
    cabin_layout = Column(String(100), nullable=True, index=True)  # 客舱布局标识

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    defect_record = relationship("DefectRecord")
    workcard = relationship("WorkCard")
    configuration = relationship("Configuration")
    dict = relationship("KeywordDict")

    __table_args__ = (
        Index("idx_defect_match_local_defect_cfg", "defect_record_id", "configuration_id"),
        Index("idx_defect_match_local_defect_cfg_cabin", "defect_record_id", "configuration_id", "cabin_layout"),
        Index("idx_defect_match_local_score", "score_total"),
    )

