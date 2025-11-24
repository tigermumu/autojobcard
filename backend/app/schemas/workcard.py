from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

class WorkCardBase(BaseModel):
    workcard_number: str
    title: str
    description: Optional[str] = None
    system: str
    component: str
    location: Optional[str] = None
    action: Optional[str] = None
    configuration_id: int
    workcard_type_id: int

class WorkCardCreate(WorkCardBase):
    # 单机构型识别字段
    aircraft_number: Optional[str] = None
    aircraft_type: Optional[str] = None
    msn: Optional[str] = None
    amm_ipc_eff: Optional[str] = None
    
    # 清洗后的索引字段
    main_area: Optional[str] = None
    main_component: Optional[str] = None
    first_level_subcomponent: Optional[str] = None
    second_level_subcomponent: Optional[str] = None
    orientation: Optional[str] = None
    defect_subject: Optional[str] = None
    defect_description: Optional[str] = None
    location_index: Optional[str] = None
    quantity: Optional[str] = None
    
    # 原始数据备份
    raw_data: Optional[Dict[str, Any]] = None

class WorkCardUpdate(BaseModel):
    workcard_number: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    system: Optional[str] = None
    component: Optional[str] = None
    location: Optional[str] = None
    action: Optional[str] = None
    is_cleaned: Optional[bool] = None
    cleaning_confidence: Optional[float] = None
    cleaning_notes: Optional[str] = None
    
    # 单机构型识别字段
    aircraft_number: Optional[str] = None
    aircraft_type: Optional[str] = None
    msn: Optional[str] = None
    amm_ipc_eff: Optional[str] = None
    
    # 清洗后的索引字段
    main_area: Optional[str] = None
    main_component: Optional[str] = None
    first_level_subcomponent: Optional[str] = None
    second_level_subcomponent: Optional[str] = None
    orientation: Optional[str] = None
    defect_subject: Optional[str] = None
    defect_description: Optional[str] = None
    location_index: Optional[str] = None
    quantity: Optional[str] = None

class WorkCardResponse(WorkCardBase):
    id: int
    is_cleaned: bool
    cleaning_confidence: float
    cleaning_notes: Optional[str] = None
    
    # 单机构型识别字段
    aircraft_number: Optional[str] = None
    aircraft_type: Optional[str] = None
    msn: Optional[str] = None
    amm_ipc_eff: Optional[str] = None
    
    # 清洗后的索引字段
    main_area: Optional[str] = None
    main_component: Optional[str] = None
    first_level_subcomponent: Optional[str] = None
    second_level_subcomponent: Optional[str] = None
    orientation: Optional[str] = None
    defect_subject: Optional[str] = None
    defect_description: Optional[str] = None
    location_index: Optional[str] = None
    quantity: Optional[str] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkCardTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class WorkCardTypeCreate(WorkCardTypeBase):
    pass

class WorkCardTypeResponse(WorkCardTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CleanWorkCardRequest(BaseModel):
    """清洗工卡数据请求"""
    raw_data: List[Dict[str, Any]]
    configuration_id: int

class CleanWorkCardResponse(BaseModel):
    """清洗工卡数据响应"""
    success: bool
    cleaned_count: int
    total_count: int
    data: List[Dict[str, Any]]
    error: Optional[str] = None

class SaveCleanedWorkCardRequest(BaseModel):
    """保存清洗后工卡数据请求"""
    cleaned_data: List[Dict[str, Any]]
    configuration_id: int
    aircraft_number: Optional[str] = None  # 飞机号
    aircraft_type: Optional[str] = None  # 机型（如果不提供，将从configuration获取）
    msn: Optional[str] = None  # MSN（如果不提供，将从configuration获取）
    amm_ipc_eff: Optional[str] = None  # AMM/IPC EFF（如果不提供，将从configuration获取）

class SaveCleanedWorkCardResponse(BaseModel):
    """保存清洗后工卡数据响应"""
    success: bool
    saved_count: int
    total_count: int
    skipped_count: int
    errors: List[str]
    message: str

class WorkCardGroup(BaseModel):
    """工卡分组信息"""
    aircraft_number: Optional[str] = ""
    aircraft_type: Optional[str] = ""
    msn: Optional[str] = ""
    amm_ipc_eff: Optional[str] = ""
    configuration_id: int
    count: int
    min_id: int
