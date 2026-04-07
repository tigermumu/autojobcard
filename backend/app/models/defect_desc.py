from sqlalchemy import Column, Integer, String, Text, Float
from app.core.database import Base

class StandardDefectDescription(Base):
    __tablename__ = "standard_defect_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    seq = Column(Integer, nullable=True)
    comp_pn = Column(String(50), nullable=True)
    standardized_desc = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)
    cust = Column(String(50), nullable=True)
    comp_name = Column(String(100), nullable=True)

class CustomDefectDescription(Base):
    __tablename__ = "custom_defect_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    seq = Column(Integer, nullable=True)
    comp_pn = Column(String(50), nullable=True)
    standardized_desc = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)
    cust = Column(String(50), nullable=True)
    comp_name = Column(String(100), nullable=True)

class SingleDefectCheck(Base):
    __tablename__ = "galley_lav_defect_checks"

    id = Column(Integer, primary_key=True, index=True)
    seq = Column(Integer, nullable=True)
    comp_pn = Column(String(50), nullable=True)
    standardized_desc = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)
    cust = Column(String(50), nullable=True)
    comp_name = Column(String(100), nullable=True)
    loc = Column(String(200), nullable=True)
    inspector = Column(String(50), nullable=True)
    yes_flag = Column(Integer, nullable=True)
    no_flag = Column(Integer, nullable=True)
    defect_status = Column(String(200), nullable=True)
    defect_positions = Column(Text, nullable=True)
    defect_quantity = Column(Integer, nullable=True)
    aircraft_no = Column(String(50), nullable=True)
    sale_wo = Column(String(100), nullable=True)
    plan_year_month = Column(String(20), nullable=True)
    local_photo_url = Column(String(500), nullable=True)
    global_photo_url = Column(String(500), nullable=True)
    defect_desc_preview = Column(Text, nullable=True)
    desc_text = Column(Text, nullable=True)
    loc_text = Column(Text, nullable=True)
    qty_text = Column(String(100), nullable=True)

class BatchDefectCheck(Base):
    __tablename__ = "panel_defect_checks"

    id = Column(Integer, primary_key=True, index=True)
    seq = Column(Integer, nullable=True)
    comp_pn = Column(String(50), nullable=True)
    standardized_desc = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)
    cust = Column(String(50), nullable=True)
    comp_name = Column(String(100), nullable=True)
    position = Column(String(200), nullable=True)
    quantity = Column(Float, nullable=True)
    yes_flag = Column(Integer, nullable=True)
    no_flag = Column(Integer, nullable=True)
    defect_status = Column(String(200), nullable=True)
    defect_positions = Column(Text, nullable=True)
    defect_quantity = Column(Integer, nullable=True)
    aircraft_no = Column(String(50), nullable=True)
    sale_wo = Column(String(100), nullable=True)
    plan_year_month = Column(String(20), nullable=True)
    local_photo_url = Column(String(500), nullable=True)
    global_photo_url = Column(String(500), nullable=True)
    defect_desc_preview = Column(Text, nullable=True)
    desc_text = Column(Text, nullable=True)
    loc_text = Column(Text, nullable=True)
    qty_text = Column(String(100), nullable=True)

class SeatDefectCheck(Base):
    __tablename__ = "seat_defect_checks"

    id = Column(Integer, primary_key=True, index=True)
    seq = Column(Integer, nullable=True)
    comp_pn = Column(String(50), nullable=True)
    standardized_desc = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)
    cust = Column(String(50), nullable=True)
    comp_name = Column(String(100), nullable=True)
    loc = Column(String(200), nullable=True)
    inspector = Column(String(50), nullable=True)
    yes_flag = Column(Integer, nullable=True)
    no_flag = Column(Integer, nullable=True)
    defect_status = Column(String(200), nullable=True)
    defect_positions = Column(Text, nullable=True)
    defect_quantity = Column(Integer, nullable=True)
    aircraft_no = Column(String(50), nullable=True)
    sale_wo = Column(String(100), nullable=True)
    plan_year_month = Column(String(20), nullable=True)
    local_photo_url = Column(String(500), nullable=True)
    global_photo_url = Column(String(500), nullable=True)
    custom_positions_input = Column(Text, nullable=True)
    defect_desc_preview = Column(Text, nullable=True)
    desc_text = Column(Text, nullable=True)
    loc_text = Column(Text, nullable=True)
    qty_text = Column(String(100), nullable=True)

class CrewSeatDefectCheck(Base):
    __tablename__ = "crew_seat_defect_checks"

    id = Column(Integer, primary_key=True, index=True)
    seq = Column(Integer, nullable=True)
    comp_pn = Column(String(50), nullable=True)
    standardized_desc = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)
    cust = Column(String(50), nullable=True)
    comp_name = Column(String(100), nullable=True)
    loc = Column(String(200), nullable=True)
    inspector = Column(String(50), nullable=True)
    yes_flag = Column(Integer, nullable=True)
    no_flag = Column(Integer, nullable=True)
    defect_status = Column(String(200), nullable=True)
    defect_positions = Column(Text, nullable=True)
    defect_quantity = Column(Integer, nullable=True)
    aircraft_no = Column(String(50), nullable=True)
    sale_wo = Column(String(100), nullable=True)
    plan_year_month = Column(String(20), nullable=True)
    local_photo_url = Column(String(500), nullable=True)
    global_photo_url = Column(String(500), nullable=True)
    custom_positions_input = Column(Text, nullable=True)
    defect_desc_preview = Column(Text, nullable=True)
    desc_text = Column(Text, nullable=True)
    loc_text = Column(Text, nullable=True)
    qty_text = Column(String(100), nullable=True)
