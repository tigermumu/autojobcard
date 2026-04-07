from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.database import get_db
from app.models.defect_scheme import DefectScheme, DefectStep, DefectMaterial
from app.schemas.defect_scheme import DefectScheme as DefectSchemeSchema
from app.schemas.defect_scheme import DefectSchemeCreate, DefectSchemeUpdate

router = APIRouter()

def _normalize_material_payload(materials: list) -> list:
    normalized = []
    for idx, mat_in in enumerate(materials):
        mat_data = mat_in.dict() if hasattr(mat_in, "dict") else dict(mat_in)
        seq = mat_data.get("material_seq")
        if seq is None or seq <= 0:
            seq = idx + 1
        mat_data["material_seq"] = seq
        normalized.append(mat_data)

    latest_by_seq = {}
    for mat_data in normalized:
        latest_by_seq[mat_data["material_seq"]] = mat_data

    return [latest_by_seq[seq] for seq in sorted(latest_by_seq.keys())]

@router.get("/", response_model=List[DefectSchemeSchema])
def read_defect_schemes(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    comp_pn: Optional[str] = None,
    keyword: Optional[str] = None
) -> Any:
    """
    Retrieve defect schemes.
    """
    query = db.query(DefectScheme)
    
    if comp_pn:
        query = query.filter(DefectScheme.comp_pn == comp_pn)
    
    if keyword:
        # Search in jc_desc_en, key_words_1, key_words_2
        search = f"%{keyword}%"
        query = query.filter(
            or_(
                DefectScheme.comp_pn.ilike(search),
                DefectScheme.jc_desc_en.ilike(search),
                DefectScheme.key_words_1.ilike(search),
                DefectScheme.key_words_2.ilike(search),
                DefectScheme.jc_desc_cn.ilike(search),
                DefectScheme.candidate_history_wo.ilike(search),
                DefectScheme.refer_manual.ilike(search)
            )
        )
        
    schemes = query.offset(skip).limit(limit).all()
    return schemes

@router.post("/", response_model=DefectSchemeSchema)
def create_defect_scheme(
    *,
    db: Session = Depends(get_db),
    scheme_in: DefectSchemeCreate
) -> Any:
    """
    Create new defect scheme with steps and materials.
    Automatically handles defect_catalog increment, trade, and manhour aggregation.
    """
    # 0. Check for duplicate based on comp_pn and description (jc_desc_en/jc_desc_cn)
    # If a scheme with same comp_pn and same description already exists, return it instead of creating a new one.
    if (not scheme_in.defect_catalog or scheme_in.defect_catalog == 0) and (scheme_in.jc_desc_en or scheme_in.jc_desc_cn):
        duplicate_query = db.query(DefectScheme).filter(
            DefectScheme.comp_pn == scheme_in.comp_pn
        )
        
        if scheme_in.jc_desc_en:
            duplicate_query = duplicate_query.filter(DefectScheme.jc_desc_en == scheme_in.jc_desc_en)
        
        if scheme_in.jc_desc_cn:
            duplicate_query = duplicate_query.filter(DefectScheme.jc_desc_cn == scheme_in.jc_desc_cn)
            
        existing_dup = duplicate_query.first()
        if existing_dup:
            return existing_dup

    # 1. Handle defect_catalog auto-increment if not provided or 0
    if not scheme_in.defect_catalog or scheme_in.defect_catalog == 0:
        max_catalog = db.query(func.max(DefectScheme.defect_catalog)).filter(
            DefectScheme.comp_pn == scheme_in.comp_pn
        ).scalar()
        scheme_in.defect_catalog = (max_catalog or 0) + 1

    # Check uniqueness (still necessary to prevent race conditions or if manually provided)
    existing = db.query(DefectScheme).filter(
        DefectScheme.comp_pn == scheme_in.comp_pn,
        DefectScheme.defect_catalog == scheme_in.defect_catalog
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Defect scheme with comp_pn '{scheme_in.comp_pn}' and defect_catalog '{scheme_in.defect_catalog}' already exists.")

    # 2. Auto-calculate trade and manhour from steps if provided
    total_manhour = 0.0
    first_trade = None
    
    if scheme_in.steps:
        for idx, step in enumerate(scheme_in.steps):
            # Sum manhour
            if step.manhour:
                total_manhour += step.manhour
            
            # Get first trade
            if idx == 0 and step.trade:
                first_trade = step.trade
    
    # Update scheme_in values if not manually provided
    if scheme_in.manhour is None or scheme_in.manhour == 0:
        scheme_in.manhour = total_manhour
        
    if not scheme_in.trade and first_trade:
        scheme_in.trade = first_trade

    # Create Scheme
    scheme_data = scheme_in.dict(exclude={"steps"})
    scheme = DefectScheme(**scheme_data)
    db.add(scheme)
    db.flush() # Get ID

    # Create Steps
    try:
        for step_in in scheme_in.steps:
            step_data = step_in.dict(exclude={"materials"})
            step = DefectStep(scheme_id=scheme.id, **step_data)
            db.add(step)
            db.flush() # Get ID
            
            # Create Materials
            normalized_materials = _normalize_material_payload(step_in.materials)
            for mat_data in normalized_materials:
                mat = DefectMaterial(step_id=step.id, **mat_data)
                db.add(mat)

        db.commit()
        db.refresh(scheme)
        return scheme
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create defect scheme: {str(e)}")

@router.put("/{id}", response_model=DefectSchemeSchema)
def update_defect_scheme(
    *,
    db: Session = Depends(get_db),
    id: int,
    scheme_in: DefectSchemeUpdate
) -> Any:
    """
    Update a defect scheme.
    Replaces steps and materials if provided.
    """
    scheme = db.query(DefectScheme).filter(DefectScheme.id == id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Defect scheme not found")

    # Update Scheme fields
    update_data = scheme_in.dict(exclude={"steps"}, exclude_unset=True)
    for field, value in update_data.items():
        setattr(scheme, field, value)

    try:
        if scheme_in.steps is not None:
            existing_steps = {step.step_number: step for step in scheme.steps}
            incoming_step_numbers = set()

            for step_in in scheme_in.steps:
                incoming_step_numbers.add(step_in.step_number)
                step_data = step_in.dict(exclude={"materials"})
                existing_step = existing_steps.get(step_in.step_number)

                if existing_step:
                    for field, value in step_data.items():
                        setattr(existing_step, field, value)
                    step = existing_step
                else:
                    step = DefectStep(scheme_id=id, **step_data)
                    db.add(step)
                    db.flush()

                normalized_materials = _normalize_material_payload(step_in.materials)
                existing_materials = {
                    material.material_seq: material
                    for material in step.materials
                    if material.material_seq is not None
                }
                incoming_material_seqs = set()

                for mat_data in normalized_materials:
                    mat_seq = mat_data["material_seq"]
                    incoming_material_seqs.add(mat_seq)
                    existing_material = existing_materials.get(mat_seq)
                    if existing_material:
                        for field, value in mat_data.items():
                            setattr(existing_material, field, value)
                    else:
                        db.add(DefectMaterial(step_id=step.id, **mat_data))

                for material in list(step.materials):
                    if material.material_seq is None or material.material_seq not in incoming_material_seqs:
                        db.delete(material)

            for step_number, existing_step in existing_steps.items():
                if step_number not in incoming_step_numbers:
                    db.delete(existing_step)

        db.commit()
        db.refresh(scheme)
        return scheme
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update defect scheme: {str(e)}")

@router.delete("/{id}", response_model=DefectSchemeSchema)
def delete_defect_scheme(
    *,
    db: Session = Depends(get_db),
    id: int
) -> Any:
    """
    Delete a defect scheme.
    """
    scheme = db.query(DefectScheme).filter(DefectScheme.id == id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Defect scheme not found")
    
    db.delete(scheme)
    db.commit()
    return scheme
