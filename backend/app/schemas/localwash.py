from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


KeywordDimension = Literal["main", "sub", "location", "orientation", "status", "action", "global"]


class KeywordDictItemBase(BaseModel):
    dimension: KeywordDimension
    main_component: Optional[str] = None
    keyword: str
    enabled: bool = True


class KeywordDictItemCreate(KeywordDictItemBase):
    pass


class KeywordDictItemUpdate(BaseModel):
    keyword: Optional[str] = None
    main_component: Optional[str] = None
    enabled: Optional[bool] = None


class GlobalKeywordCreate(BaseModel):
    keyword: str
    enabled: bool = True


class GlobalKeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    enabled: Optional[bool] = None


class GlobalKeywordOut(BaseModel):
    id: int
    keyword: str
    enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KeywordDictItemOut(KeywordDictItemBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KeywordDictBase(BaseModel):
    configuration_id: int
    version: str = Field(..., max_length=50)
    remark: Optional[str] = None


class KeywordDictCreate(KeywordDictBase):
    items: List[KeywordDictItemCreate] = Field(default_factory=list)


class KeywordDictOut(KeywordDictBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KeywordDictDetail(KeywordDictOut):
    items: List[KeywordDictItemOut] = Field(default_factory=list)


class KeywordDictOptionOut(BaseModel):
    """用于前端下拉选择“本地清洗引擎/词典版本”的简要信息。"""

    dict_id: int
    configuration_id: int
    configuration_name: str
    version: str
    remark: Optional[str] = None
    created_at: Optional[datetime] = None


class LocalCleanRequestBase(BaseModel):
    configuration_id: int
    dict_id: Optional[int] = None  # 不传则默认取该构型最新版本
    cabin_layout: Optional[str] = None  # 客舱布局标识


class LocalCleanWorkcardsResponse(BaseModel):
    success: bool
    configuration_id: int
    dict_id: int
    dict_version: str
    total: int
    cleaned: int
    skipped: int
    message: str


class LocalWorkcardUploadRow(BaseModel):
    workcard_number: str = ""
    description_cn: str = ""
    description_en: str = ""


class LocalCleanWorkcardsUploadRequest(BaseModel):
    dict_id: int
    rows: List[LocalWorkcardUploadRow] = Field(default_factory=list)
    cabin_layout: Optional[str] = None  # 客舱布局标识


class LocalCleanedWorkcardOut(BaseModel):
    workcard_number: str = ""
    description_cn: str = ""
    description_en: str = ""
    main_component: Optional[str] = None
    sub_component: Optional[str] = None
    location: Optional[str] = None
    orientation: Optional[str] = None
    status: Optional[str] = None
    action: Optional[str] = None
    error: Optional[str] = None


class LocalCleanWorkcardsUploadResponse(BaseModel):
    success: bool
    configuration_id: int
    dict_id: int
    dict_version: str
    total: int
    cleaned: int
    skipped: int
    cleaned_data: List[LocalCleanedWorkcardOut] = Field(default_factory=list)
    message: str


class LocalCleanDefectsRequest(LocalCleanRequestBase):
    defect_list_id: int


class LocalCleanedDefectOut(BaseModel):
    defect_record_id: int
    defect_number: str
    description_cn: str = ""
    description_en: str = ""
    main_component: Optional[str] = None
    sub_component: Optional[str] = None
    location: Optional[str] = None
    orientation: Optional[str] = None
    status: Optional[str] = None
    action: Optional[str] = None


class LocalCleanDefectsResponse(BaseModel):
    success: bool
    defect_list_id: int
    configuration_id: int
    dict_id: int
    dict_version: str
    total: int
    cleaned: int
    skipped: int
    cleaned_data: List[LocalCleanedDefectOut] = Field(default_factory=list)
    message: str


class LocalCleanedDefectListOut(BaseModel):
    id: int
    title: str


class LocalAvailableCleanedDefectsResponse(BaseModel):
    success: bool
    cabin_layouts: Optional[List[str]] = None  # Existing field for workcards
    defect_lists: Optional[List[LocalCleanedDefectListOut]] = None


class LocalMatchDefectsRequest(LocalCleanDefectsRequest):
    source: str = "upload"  # "upload" or "history"


class LocalCandidateWorkcard(BaseModel):
    id: int  # workcards.id（与现有 CandidateWorkCard.id 对齐）
    workcard_number: str
    description: Optional[str] = None
    description_en: Optional[str] = None
    similarity_score: float  # 使用 score_total（0~100）


class LocalMatchStatsResponse(BaseModel):
    total_defects: int
    matched_defects: int
    unmatched_defects: int
    match_rate: float


class LocalMatchResult(BaseModel):
    defect_record_id: int
    defect_number: str
    description_cn: str = ""
    description_en: str = ""
    main_component: Optional[str] = None
    sub_component: Optional[str] = None
    location: Optional[str] = None
    orientation: Optional[str] = None
    status: Optional[str] = None
    action: Optional[str] = None
    candidates: List[LocalCandidateWorkcard] = Field(default_factory=list)


class LocalMatchDefectsResponse(BaseModel):
    success: bool
    defect_list_id: int
    configuration_id: int
    dict_id: int
    dict_version: str
    results: List[LocalMatchResult] = Field(default_factory=list)
    message: str

