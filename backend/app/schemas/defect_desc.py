from typing import Optional, List
from pydantic import BaseModel

class StandardDefectDescBase(BaseModel):
    seq: Optional[int] = None
    comp_pn: Optional[str] = None
    standardized_desc: Optional[str] = None
    type: Optional[str] = None
    cust: Optional[str] = None
    comp_name: Optional[str] = None

class StandardDefectDescCreate(StandardDefectDescBase):
    pass

class StandardDefectDescUpdate(StandardDefectDescBase):
    pass

class StandardDefectDesc(StandardDefectDescBase):
    id: int

    class Config:
        from_attributes = True

class CustomDefectDescBase(BaseModel):
    seq: Optional[int] = None
    comp_pn: Optional[str] = None
    standardized_desc: Optional[str] = None
    type: Optional[str] = None
    cust: Optional[str] = None
    comp_name: Optional[str] = None

class CustomDefectDescCreate(CustomDefectDescBase):
    pass

class CustomDefectDescUpdate(CustomDefectDescBase):
    pass

class CustomDefectDesc(CustomDefectDescBase):
    id: int

    class Config:
        from_attributes = True

class SingleDefectCheckBase(BaseModel):
    seq: Optional[int] = None
    comp_pn: Optional[str] = None
    standardized_desc: Optional[str] = None
    type: Optional[str] = None
    cust: Optional[str] = None
    comp_name: Optional[str] = None
    loc: Optional[str] = None
    inspector: Optional[str] = None
    yes_flag: Optional[int] = None
    no_flag: Optional[int] = None
    defect_status: Optional[str] = None
    defect_positions: Optional[str] = None
    defect_quantity: Optional[int] = None
    aircraft_no: Optional[str] = None
    sale_wo: Optional[str] = None
    plan_year_month: Optional[str] = None
    local_photo_url: Optional[str] = None
    global_photo_url: Optional[str] = None
    defect_desc_preview: Optional[str] = None
    desc_text: Optional[str] = None
    loc_text: Optional[str] = None
    qty_text: Optional[str] = None

class SingleDefectCheckCreate(SingleDefectCheckBase):
    pass

class SingleDefectCheckUpdate(SingleDefectCheckBase):
    pass

class SingleDefectCheck(SingleDefectCheckBase):
    id: int

    class Config:
        from_attributes = True

class BatchDefectCheckBase(BaseModel):
    seq: Optional[int] = None
    comp_pn: Optional[str] = None
    standardized_desc: Optional[str] = None
    type: Optional[str] = None
    cust: Optional[str] = None
    comp_name: Optional[str] = None
    position: Optional[str] = None
    quantity: Optional[float] = None
    yes_flag: Optional[int] = None
    no_flag: Optional[int] = None
    defect_status: Optional[str] = None
    defect_positions: Optional[str] = None
    defect_quantity: Optional[int] = None
    aircraft_no: Optional[str] = None
    sale_wo: Optional[str] = None
    plan_year_month: Optional[str] = None
    local_photo_url: Optional[str] = None
    global_photo_url: Optional[str] = None
    defect_desc_preview: Optional[str] = None
    desc_text: Optional[str] = None
    loc_text: Optional[str] = None
    qty_text: Optional[str] = None

class BatchDefectCheckCreate(BatchDefectCheckBase):
    pass

class BatchDefectCheckUpdate(BatchDefectCheckBase):
    pass

class BatchDefectCheck(BatchDefectCheckBase):
    id: int

    class Config:
        from_attributes = True

class SeatDefectCheckBase(BaseModel):
    seq: Optional[int] = None
    comp_pn: Optional[str] = None
    standardized_desc: Optional[str] = None
    type: Optional[str] = None
    cust: Optional[str] = None
    comp_name: Optional[str] = None
    loc: Optional[str] = None
    inspector: Optional[str] = None
    yes_flag: Optional[int] = None
    no_flag: Optional[int] = None
    defect_status: Optional[str] = None
    defect_positions: Optional[str] = None
    defect_quantity: Optional[int] = None
    aircraft_no: Optional[str] = None
    sale_wo: Optional[str] = None
    plan_year_month: Optional[str] = None
    local_photo_url: Optional[str] = None
    global_photo_url: Optional[str] = None
    custom_positions_input: Optional[str] = None
    defect_desc_preview: Optional[str] = None
    desc_text: Optional[str] = None
    loc_text: Optional[str] = None
    qty_text: Optional[str] = None

class SeatDefectCheckCreate(SeatDefectCheckBase):
    pass

class SeatDefectCheckUpdate(SeatDefectCheckBase):
    pass

class SeatDefectCheck(SeatDefectCheckBase):
    id: int

    class Config:
        from_attributes = True

class CrewSeatDefectCheckBase(BaseModel):
    seq: Optional[int] = None
    comp_pn: Optional[str] = None
    standardized_desc: Optional[str] = None
    type: Optional[str] = None
    cust: Optional[str] = None
    comp_name: Optional[str] = None
    loc: Optional[str] = None
    inspector: Optional[str] = None
    yes_flag: Optional[int] = None
    no_flag: Optional[int] = None
    defect_status: Optional[str] = None
    defect_positions: Optional[str] = None
    defect_quantity: Optional[int] = None
    aircraft_no: Optional[str] = None
    sale_wo: Optional[str] = None
    plan_year_month: Optional[str] = None
    local_photo_url: Optional[str] = None
    global_photo_url: Optional[str] = None
    custom_positions_input: Optional[str] = None
    defect_desc_preview: Optional[str] = None
    desc_text: Optional[str] = None
    loc_text: Optional[str] = None
    qty_text: Optional[str] = None

class CrewSeatDefectCheckCreate(CrewSeatDefectCheckBase):
    pass

class CrewSeatDefectCheckUpdate(CrewSeatDefectCheckBase):
    pass

class CrewSeatDefectCheck(CrewSeatDefectCheckBase):
    id: int

    class Config:
        from_attributes = True
