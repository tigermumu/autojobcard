from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ImportBatchMetadata(BaseModel):
    aircraft_number: str = Field(..., max_length=50)
    workcard_number: str = Field(..., max_length=100)
    maintenance_level: str = Field(..., max_length=100)
    aircraft_type: str = Field(..., max_length=100)
    customer: str = Field(..., max_length=100)
    defect_list_id: Optional[int] = None


class ImportBatchItemCreate(BaseModel):
    defect_record_id: Optional[int] = None
    defect_number: str
    description_cn: Optional[str] = ""
    description_en: Optional[str] = ""
    workcard_number: Optional[str] = None  # 候选工卡，Excel中没有数据时可以留空
    issued_workcard_number: Optional[str] = None
    selected_workcard_id: Optional[int] = None
    similarity_score: Optional[float] = None
    reference_workcard_number: Optional[str] = None
    reference_workcard_item: Optional[str] = None
    area: Optional[str] = None
    zone_number: Optional[str] = None
    loc: Optional[str] = None
    qty: Optional[int] = None
    comp_pn: Optional[str] = None
    keywords_1: Optional[str] = None
    keywords_2: Optional[str] = None
    candidate_description_en: Optional[str] = None  # 历史工卡描述（英文），来自Excel的 Candidate Workcard Description (English) 列
    candidate_description_cn: Optional[str] = None  # 历史工卡描述（中文），来自Excel的 Candidate Workcard Description (Chinese) 列
    ref_manual: Optional[str] = None  # 参考手册 (CMM_REFER)，来自Excel的 参考手册 列


class ImportBatchCreate(BaseModel):
    metadata: ImportBatchMetadata
    items: List[ImportBatchItemCreate]


class ImportBatchSummary(BaseModel):
    id: int
    aircraft_number: str
    workcard_number: str
    maintenance_level: str
    aircraft_type: str
    customer: str
    defect_list_id: Optional[int] = None
    created_at: datetime
    item_count: int

    class Config:
        from_attributes = True


class ImportBatchItem(BaseModel):
    id: int
    defect_record_id: Optional[int] = None
    defect_number: str
    description_cn: Optional[str] = ""
    description_en: Optional[str] = ""
    workcard_number: Optional[str] = None  # 候选工卡，Excel中没有数据时可以留空
    selected_workcard_id: Optional[int] = None
    similarity_score: Optional[float] = None
    issued_workcard_number: Optional[str] = None  # 已开出的工卡号
    # Add new fields for API response
    reference_workcard_number: Optional[str] = None
    reference_workcard_item: Optional[str] = None
    area: Optional[str] = None
    zone_number: Optional[str] = None
    loc: Optional[str] = None
    qty: Optional[int] = None
    comp_pn: Optional[str] = None
    keywords_1: Optional[str] = None
    keywords_2: Optional[str] = None
    candidate_description_en: Optional[str] = None  # 历史工卡描述（英文），来自Excel的 Candidate Workcard Description (English) 列
    candidate_description_cn: Optional[str] = None  # 历史工卡描述（中文），来自Excel的 Candidate Workcard Description (Chinese) 列
    ref_manual: Optional[str] = None  # 参考手册 (CMM_REFER)，来自Excel的 参考手册 列

    class Config:
        from_attributes = True


class ImportBatchDetail(BaseModel):
    id: int
    aircraft_number: str
    workcard_number: str
    maintenance_level: str
    aircraft_type: str
    customer: str
    defect_list_id: Optional[int] = None
    created_at: datetime
    items: List[ImportBatchItem]

    class Config:
        from_attributes = True

