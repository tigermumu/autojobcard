from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class ConfigurationBase(BaseModel):
    name: str  # 构型名称（必需）
    aircraft_type: Optional[str] = None  # 机型
    msn: Optional[str] = None  # MSN
    model: Optional[str] = None  # MODEL
    vartab: Optional[str] = None  # VARTAB
    customer: Optional[str] = None  # 客户
    amm_ipc_eff: Optional[str] = None  # AMM/IPC EFF
    version: Optional[str] = None  # 版本（保留）
    description: Optional[str] = None

class ConfigurationCreate(BaseModel):
    name: str  # 构型名称（必需）
    aircraft_type: Optional[str] = None  # 机型
    msn: Optional[str] = None  # MSN
    model: Optional[str] = None  # MODEL
    vartab: Optional[str] = None  # VARTAB
    customer: Optional[str] = None  # 客户
    amm_ipc_eff: Optional[str] = None  # AMM/IPC EFF
    version: Optional[str] = None  # 版本（保留）
    description: Optional[str] = None

class ConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    aircraft_type: Optional[str] = None  # 机型
    msn: Optional[str] = None  # MSN
    model: Optional[str] = None  # MODEL
    vartab: Optional[str] = None  # VARTAB
    customer: Optional[str] = None  # 客户
    amm_ipc_eff: Optional[str] = None  # AMM/IPC EFF
    version: Optional[str] = None  # 版本（保留）
    description: Optional[str] = None
    field_mapping: Optional[Dict[str, Any]] = None

class ConfigurationResponse(ConfigurationBase):
    id: int
    field_mapping: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IndexFileBase(BaseModel):
    filename: str
    file_type: str
    field_mapping: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None

class IndexFileCreate(IndexFileBase):
    file_path: str
    file_size: int
    configuration_id: int

class IndexFileResponse(IndexFileBase):
    id: int
    file_path: str
    file_size: int
    configuration_id: int
    created_at: datetime

    class Config:
        from_attributes = True
