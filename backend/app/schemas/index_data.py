from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class IndexDataBase(BaseModel):
    main_area: str
    main_component: str
    first_level_subcomponent: str
    second_level_subcomponent: str
    orientation: Optional[str] = None
    defect_subject: Optional[str] = None
    defect_description: Optional[str] = None
    location: Optional[str] = None
    quantity: Optional[str] = None

class IndexDataCreate(IndexDataBase):
    configuration_id: int

class IndexDataUpdate(BaseModel):
    main_area: Optional[str] = None
    main_component: Optional[str] = None
    first_level_subcomponent: Optional[str] = None
    second_level_subcomponent: Optional[str] = None
    orientation: Optional[str] = None
    defect_subject: Optional[str] = None
    defect_description: Optional[str] = None
    location: Optional[str] = None
    quantity: Optional[str] = None

class IndexDataResponse(IndexDataBase):
    id: int
    configuration_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IndexDataHierarchy(BaseModel):
    """层级结构数据"""
    main_area: str
    main_components: List[Dict[str, Any]]

class IndexDataImport(BaseModel):
    """批量导入数据"""
    configuration_id: int
    data: List[IndexDataBase]



