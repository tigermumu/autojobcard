from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class DefectListBase(BaseModel):
    aircraft_number: str
    title: str
    description: Optional[str] = None
    configuration_id: int

class DefectListCreate(DefectListBase):
    pass

class DefectListUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    processing_progress: Optional[float] = None

class DefectListResponse(DefectListBase):
    id: int
    status: str
    processing_progress: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DefectRecordBase(BaseModel):
    defect_number: str
    title: str
    description: Optional[str] = None
    system: str
    component: str
    location: Optional[str] = None
    severity: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

class DefectRecordCreate(DefectRecordBase):
    defect_list_id: int

class DefectRecordUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    system: Optional[str] = None
    component: Optional[str] = None
    location: Optional[str] = None
    severity: Optional[str] = None
    is_matched: Optional[bool] = None
    is_selected: Optional[bool] = None
    selected_workcard_id: Optional[int] = None

class DefectRecordResponse(DefectRecordBase):
    id: int
    is_matched: bool
    is_selected: bool
    selected_workcard_id: Optional[int] = None
    defect_list_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

