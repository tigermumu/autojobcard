from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class MatchingResultBase(BaseModel):
    similarity_score: float
    is_candidate: bool
    matching_details: Optional[Dict[str, Any]] = None
    algorithm_version: str = "1.0"

class MatchingResultCreate(MatchingResultBase):
    defect_record_id: int
    workcard_id: int

class MatchingResultResponse(MatchingResultBase):
    id: int
    defect_record_id: int
    workcard_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CandidateWorkCardBase(BaseModel):
    defect_record_id: int
    workcard_id: int
    similarity_score: float
    is_selected: bool = False
    selection_notes: Optional[str] = None

class CandidateWorkCardCreate(CandidateWorkCardBase):
    pass

class CandidateWorkCardResponse(CandidateWorkCardBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MatchingConfig(BaseModel):
    """匹配算法配置"""
    similarity_threshold: float = 75.0
    field_weights: Dict[str, float] = {
        "main_area": 0.05,
        "main_component": 0.20,
        "first_level_subcomponent": 0.35,  # 一级子部件权重最高
        "second_level_subcomponent": 0.20,
        "orientation": 0.05,
        "defect_subject": 0.10,
        "defect_description": 0.05
    }
    algorithm_version: str = "1.0"
    max_candidates: int = 10

class MatchingRequest(BaseModel):
    """匹配请求"""
    defect_record_id: int
    config: MatchingConfig

