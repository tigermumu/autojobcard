from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# --- Material Schemas ---
class DefectMaterialBase(BaseModel):
    material_seq: Optional[int] = None
    part_number: str
    amount: Optional[float] = None
    unit: Optional[str] = None
    remark: Optional[str] = None

class DefectMaterialCreate(DefectMaterialBase):
    pass

class DefectMaterial(DefectMaterialBase):
    id: int
    step_id: int

    class Config:
        from_attributes = True

# --- Step Schemas ---
class DefectStepBase(BaseModel):
    step_number: int
    step_desc_cn: Optional[str] = None
    step_desc_en: Optional[str] = None
    manhour: Optional[float] = None
    trade: Optional[str] = None
    manpower: Optional[str] = None
    refer_manual: Optional[str] = None

class DefectStepCreate(DefectStepBase):
    materials: List[DefectMaterialCreate] = []

class DefectStep(DefectStepBase):
    id: int
    scheme_id: int
    materials: List[DefectMaterial] = []

    class Config:
        from_attributes = True

# --- Scheme Schemas ---
class DefectSchemeBase(BaseModel):
    comp_pn: str
    defect_catalog: Optional[int] = 0
    jc_desc_cn: Optional[str] = None
    jc_desc_en: Optional[str] = None
    type: Optional[str] = None
    cust: Optional[str] = None
    comp_name: Optional[str] = None
    key_words_1: Optional[str] = None
    key_words_2: Optional[str] = None
    trade: Optional[str] = None
    zone: Optional[str] = None
    loc: Optional[str] = None
    qty: Optional[int] = None
    jc_type: Optional[str] = None
    labor: Optional[float] = None
    manhour: Optional[float] = None
    candidate_history_wo: Optional[str] = None
    refer_manual: Optional[str] = None

class DefectSchemeCreate(DefectSchemeBase):
    steps: List[DefectStepCreate] = []

class DefectSchemeUpdate(BaseModel):
    comp_pn: Optional[str] = None
    defect_catalog: Optional[int] = None
    jc_desc_cn: Optional[str] = None
    jc_desc_en: Optional[str] = None
    type: Optional[str] = None
    cust: Optional[str] = None
    comp_name: Optional[str] = None
    key_words_1: Optional[str] = None
    key_words_2: Optional[str] = None
    trade: Optional[str] = None
    zone: Optional[str] = None
    loc: Optional[str] = None
    qty: Optional[int] = None
    jc_type: Optional[str] = None
    labor: Optional[float] = None
    manhour: Optional[float] = None
    candidate_history_wo: Optional[str] = None
    refer_manual: Optional[str] = None
    steps: Optional[List[DefectStepCreate]] = None

class DefectScheme(DefectSchemeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    steps: List[DefectStep] = []

    class Config:
        from_attributes = True
