from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.defect_desc import (
    StandardDefectDescription,
    CustomDefectDescription,
    SingleDefectCheck,
    BatchDefectCheck,
    SeatDefectCheck,
    CrewSeatDefectCheck,
)
import os
import re
from uuid import uuid4
from datetime import datetime
from app.schemas.defect_desc import (
    StandardDefectDesc,
    StandardDefectDescCreate,
    StandardDefectDescUpdate,
    CustomDefectDesc,
    CustomDefectDescCreate,
    CustomDefectDescUpdate,
    SingleDefectCheck as SingleDefectCheckSchema,
    SingleDefectCheckCreate,
    SingleDefectCheckUpdate,
    BatchDefectCheck as BatchDefectCheckSchema,
    BatchDefectCheckCreate,
    BatchDefectCheckUpdate,
    SeatDefectCheck as SeatDefectCheckSchema,
    SeatDefectCheckCreate,
    SeatDefectCheckUpdate,
    CrewSeatDefectCheck as CrewSeatDefectCheckSchema,
    CrewSeatDefectCheckCreate,
    CrewSeatDefectCheckUpdate,
)

router = APIRouter()
custom_router = APIRouter()
single_router = APIRouter()
batch_router = APIRouter()
seat_router = APIRouter()
crew_seat_router = APIRouter()

SEAT_PREVIEW_ORDER = ["L", "A", "B", "C", "D", "E", "M", "F", "G", "H", "I", "J", "K", "R"]

def _norm_str(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return v

def _require_nonempty(name: str, value: Optional[str]) -> str:
    s = _norm_str(value)
    if not s:
        raise HTTPException(status_code=400, detail=f"{name} 不能为空")
    return s

def _split_positions(raw: Optional[str]) -> List[str]:
    s = _norm_str(raw)
    if not s:
        return []
    return [x.strip() for x in re.split(r"[;；,，|｜、\n\r\t ]+", s) if x.strip()]

def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result

def _sort_seat_preview_positions(values: List[str]) -> List[str]:
    idx = {value: order for order, value in enumerate(SEAT_PREVIEW_ORDER)}
    uniq = _dedupe_keep_order(values)
    ranked = sorted([value for value in uniq if value in idx], key=lambda value: idx[value])
    others = [value for value in uniq if value not in idx]
    return ranked + others

def _qty_to_text(value: Optional[int]) -> Optional[str]:
    if value is None:
        return None
    try:
        qty = int(value)
    except Exception:
        return None
    if qty <= 0:
        return None
    return f"{qty} EA"

def _derive_yes_no_flags(yes_flag: Optional[int], no_flag: Optional[int]) -> tuple[int, int]:
    yes = 1 if yes_flag == 1 else 0
    no = 1 if no_flag == 1 else 0
    if (yes + no) != 1:
        raise HTTPException(status_code=400, detail="yes_flag/no_flag 必须二选一")
    return yes, no

def _required_or_optional_loc(model, value: Optional[str]) -> Optional[str]:
    if model is SeatDefectCheck:
        return _require_nonempty("loc", value)
    return _norm_str(value)

def _apply_optional_filter(q, column, value: Optional[str]):
    if value is None:
        return q.filter(column.is_(None))
    return q.filter(column == value)

def _build_derived_preview_fields(
    module_kind: str,
    is_defect: bool,
    standardized_desc: Optional[str],
    defect_status: Optional[str],
    defect_positions: Optional[str],
    defect_quantity: Optional[int],
    loc: Optional[str] = None,
    position: Optional[str] = None,
) -> dict:
    if not is_defect:
        return {
            "defect_desc_preview": None,
            "desc_text": None,
            "loc_text": None,
            "qty_text": None,
        }

    base_desc = _norm_str(standardized_desc) or ""
    status_text = _norm_str(defect_status) or ""
    desc_text = f"{base_desc}{status_text}" or None
    positions = _split_positions(defect_positions)
    qty_text = _qty_to_text(defect_quantity)

    if module_kind == "seat":
        seat_loc = _norm_str(loc) or ""
        loc_text = f"{seat_loc}{''.join(_sort_seat_preview_positions(positions))}" or None
    elif module_kind == "crew-seat":
        loc_text = " ".join(_dedupe_keep_order(positions)) or None
    elif module_kind == "batch":
        loc_text = " ".join(_dedupe_keep_order(positions)) or _norm_str(position)
    else:
        loc_text = " ".join(_dedupe_keep_order(positions)) or _norm_str(loc)

    preview = None
    if desc_text or loc_text or qty_text:
        preview = f"{desc_text or ''}，LOC：{loc_text or ''}，QTY：{qty_text or ''}"

    return {
        "defect_desc_preview": preview,
        "desc_text": desc_text,
        "loc_text": loc_text,
        "qty_text": qty_text,
    }

def _normalize_standard_desc_columns(df):
    column_map = {
        "id": "id",
        "ID": "id",
        "序号": "seq",
        "seq": "seq",
        "SEQ": "seq",
        "部件件号": "comp_pn",
        "comp_pn": "comp_pn",
        "COMP_PN": "comp_pn",
        "标准化描述": "standardized_desc",
        "standardized_desc": "standardized_desc",
        "STANDARDIZED_DESC": "standardized_desc",
        "机型": "type",
        "type": "type",
        "客户": "cust",
        "cust": "cust",
        "部件名称": "comp_name",
        "comp_name": "comp_name",
    }
    df = df.rename(columns={c: column_map.get(c, c) for c in df.columns})
    keep = ["seq", "comp_pn", "standardized_desc", "type", "cust", "comp_name"]
    present = [c for c in keep if c in df.columns]
    df = df[present].copy()
    for c in present:
        df[c] = df[c].where(df[c].notna(), None)
        df[c] = df[c].apply(lambda v: v.strip() if isinstance(v, str) else v)
    if "seq" in df.columns:
        def to_int(v):
            if v is None:
                return None
            if isinstance(v, (int,)):
                return int(v)
            if isinstance(v, float):
                if v != v:
                    return None
                return int(v)
            if isinstance(v, str):
                s = v.strip()
                if s == "":
                    return None
                try:
                    return int(float(s))
                except Exception:
                    return None
            return None
        df["seq"] = df["seq"].apply(to_int)
    return df

def _next_standard_seq(db: Session) -> int:
    max_seq = db.query(func.max(StandardDefectDescription.seq)).scalar()
    return int(max_seq or 0) + 1

def _resequence_standard_desc(db: Session):
    rows = (
        db.query(StandardDefectDescription)
        .order_by(StandardDefectDescription.id.asc())
        .all()
    )
    for idx, row in enumerate(rows, start=1):
        row.seq = idx

@router.get("/export")
def export_descs(
    db: Session = Depends(get_db)
):
    rows = db.query(StandardDefectDescription).all()
    import pandas as pd
    import io
    df = pd.DataFrame([{
        "seq": r.seq,
        "comp_pn": r.comp_pn,
        "standardized_desc": r.standardized_desc,
        "type": r.type,
        "cust": r.cust,
        "comp_name": r.comp_name,
    } for r in rows])
    if df.empty:
        df = pd.DataFrame(columns=["seq", "comp_pn", "standardized_desc", "type", "cust", "comp_name"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")
    headers = {
        "Content-Disposition": 'attachment; filename="standard_defect_desc.csv"'
    }
    return StreamingResponse(io.BytesIO(data), media_type="text/csv; charset=utf-8", headers=headers)

@router.get("/options")
def get_standard_desc_options(
    type: Optional[str] = Query(None),
    cust: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    t = _norm_str(type)
    c = _norm_str(cust)

    types = [
        r[0] for r in db.query(StandardDefectDescription.type)
        .filter(StandardDefectDescription.type.isnot(None))
        .filter(StandardDefectDescription.type != "")
        .distinct()
        .order_by(StandardDefectDescription.type.asc())
        .all()
    ]

    custs: List[str] = []
    if t:
        custs = [
            r[0] for r in db.query(StandardDefectDescription.cust)
            .filter(StandardDefectDescription.type == t)
            .filter(StandardDefectDescription.cust.isnot(None))
            .filter(StandardDefectDescription.cust != "")
            .distinct()
            .order_by(StandardDefectDescription.cust.asc())
            .all()
        ]

    comp_names: List[str] = []
    if t and c:
        comp_names = [
            r[0] for r in db.query(StandardDefectDescription.comp_name)
            .filter(StandardDefectDescription.type == t)
            .filter(StandardDefectDescription.cust == c)
            .filter(StandardDefectDescription.comp_name.isnot(None))
            .filter(StandardDefectDescription.comp_name != "")
            .distinct()
            .order_by(StandardDefectDescription.comp_name.asc())
            .all()
        ]

    return {"types": types, "custs": custs, "comp_names": comp_names}

@router.get("/match", response_model=List[StandardDefectDesc])
def match_standard_descs(
    type: str = Query(...),
    cust: str = Query(...),
    comp_name: str = Query(...),
    db: Session = Depends(get_db)
):
    t = _require_nonempty("type", type)
    c = _require_nonempty("cust", cust)
    n = _require_nonempty("comp_name", comp_name)
    q = (
        db.query(StandardDefectDescription)
        .filter(StandardDefectDescription.type == t)
        .filter(StandardDefectDescription.cust == c)
        .filter(StandardDefectDescription.comp_name == n)
        .order_by(StandardDefectDescription.seq.asc(), StandardDefectDescription.id.asc())
    )
    return q.all()

@router.post("/defect-photos/upload")
async def upload_defect_photo(
    kind: str = Query(..., pattern="^(local|global)$"),
    file: UploadFile = File(...),
):
    ct = (file.content_type or "").lower()
    if not ct.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片文件")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")

    ext = os.path.splitext(file.filename or "")[1].lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    if ext not in allowed:
        if ct == "image/jpeg":
            ext = ".jpg"
        elif ct == "image/png":
            ext = ".png"
        elif ct == "image/webp":
            ext = ".webp"
        elif ct == "image/bmp":
            ext = ".bmp"
        else:
            ext = ".jpg"

    day = datetime.now().strftime("%Y%m%d")
    rel_dir = os.path.join("defect_photos", day)
    abs_dir = os.path.join("uploads", rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    name = f"{uuid4().hex}_{kind}{ext}"
    abs_path = os.path.join(abs_dir, name)
    with open(abs_path, "wb") as f:
        f.write(data)

    url = "/" + "/".join(["uploads", rel_dir.replace("\\", "/"), name]).replace("//", "/")
    return {"success": True, "kind": kind, "url": url}

def _standard_key(type: Optional[str], cust: Optional[str], comp_name: Optional[str], standardized_desc: Optional[str]):
    t = _norm_str(type)
    c = _norm_str(cust)
    n = _norm_str(comp_name)
    d = _norm_str(standardized_desc)
    if not (t and c and n and d):
        return None
    return (t, c, n, d)

@custom_router.get("/", response_model=List[CustomDefectDesc])
def list_custom_descs(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None)
):
    q = db.query(CustomDefectDescription)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (CustomDefectDescription.standardized_desc.ilike(like)) |
            (CustomDefectDescription.comp_pn.ilike(like)) |
            (CustomDefectDescription.comp_name.ilike(like)) |
            (CustomDefectDescription.type.ilike(like)) |
            (CustomDefectDescription.cust.ilike(like))
        )
    return q.offset(skip).limit(limit).all()

@custom_router.post("/", response_model=CustomDefectDesc)
def create_custom_desc(
    payload: CustomDefectDescCreate,
    db: Session = Depends(get_db)
):
    obj = CustomDefectDescription(**payload.dict(exclude_unset=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@custom_router.put("/{id}", response_model=CustomDefectDesc)
def update_custom_desc(
    id: int,
    payload: CustomDefectDescUpdate,
    db: Session = Depends(get_db)
):
    obj = db.query(CustomDefectDescription).filter(CustomDefectDescription.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@custom_router.delete("/{id}", response_model=CustomDefectDesc)
def delete_custom_desc(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(CustomDefectDescription).filter(CustomDefectDescription.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj)
    db.commit()
    return obj

@custom_router.post("/bulk")
def bulk_create_custom_descs(
    payload: List[CustomDefectDescCreate],
    db: Session = Depends(get_db)
):
    existing_keys = set()
    existing = db.query(
        CustomDefectDescription.type,
        CustomDefectDescription.cust,
        CustomDefectDescription.comp_name,
        CustomDefectDescription.standardized_desc,
    ).all()
    for t, c, n, d in existing:
        k = _standard_key(t, c, n, d)
        if k:
            existing_keys.add(k)

    inserted = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    for item in payload:
        k = _standard_key(item.type, item.cust, item.comp_name, item.standardized_desc)
        if not k:
            skipped_invalid += 1
            continue
        if k in existing_keys:
            skipped_duplicates += 1
            continue
        existing_keys.add(k)
        obj = CustomDefectDescription(**item.dict(exclude_unset=True))
        db.add(obj)
        inserted += 1
    db.commit()
    return {"success": True, "inserted": inserted, "skipped_duplicates": skipped_duplicates, "skipped_invalid": skipped_invalid}

@custom_router.post("/{id}/move-to-standard")
def move_custom_to_standard(
    id: int,
    delete_source: bool = Query(True),
    db: Session = Depends(get_db)
):
    src = db.query(CustomDefectDescription).filter(CustomDefectDescription.id == id).first()
    if not src:
        raise HTTPException(status_code=404, detail="not found")
    k = _standard_key(src.type, src.cust, src.comp_name, src.standardized_desc)
    if not k:
        raise HTTPException(status_code=400, detail="type/cust/comp_name/standardized_desc 必须非空")
    exists = db.query(StandardDefectDescription).filter(
        StandardDefectDescription.type == k[0],
        StandardDefectDescription.cust == k[1],
        StandardDefectDescription.comp_name == k[2],
        StandardDefectDescription.standardized_desc == k[3],
    ).first()
    if exists:
        return {"success": True, "moved": False, "reason": "duplicate"}
    dst = StandardDefectDescription(
        seq=_next_standard_seq(db),
        comp_pn=src.comp_pn,
        standardized_desc=src.standardized_desc,
        type=src.type,
        cust=src.cust,
        comp_name=src.comp_name,
    )
    db.add(dst)
    if delete_source:
        db.delete(src)
    db.commit()
    return {"success": True, "moved": True}

@router.post("/import")
async def import_descs(
    mode: str = Query("replace", pattern="^(replace|append)$"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    content = await file.read()
    filename = (file.filename or "").lower()
    import pandas as pd
    import io
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="仅支持 .csv 或 .xlsx 文件")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析文件失败: {str(e)}")

    df = _normalize_standard_desc_columns(df)
    records = df.to_dict(orient="records")

    if mode == "replace":
        db.query(StandardDefectDescription).delete()
        db.commit()

    existing_keys = set()
    existing = db.query(
        StandardDefectDescription.type,
        StandardDefectDescription.cust,
        StandardDefectDescription.comp_name,
        StandardDefectDescription.standardized_desc,
    ).all()
    for t, c, n, d in existing:
        t2, c2, n2, d2 = _norm_str(t), _norm_str(c), _norm_str(n), _norm_str(d)
        if t2 and c2 and n2 and d2:
            existing_keys.add((t2, c2, n2, d2))

    max_seq_in_db = db.query(func.max(StandardDefectDescription.seq)).scalar()
    next_seq = int(max_seq_in_db or 0)

    inserted = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    for rec in records:
        t2 = _norm_str(rec.get("type"))
        c2 = _norm_str(rec.get("cust"))
        n2 = _norm_str(rec.get("comp_name"))
        d2 = _norm_str(rec.get("standardized_desc"))
        if not (t2 and c2 and n2 and d2):
            skipped_invalid += 1
            continue
        k = (t2, c2, n2, d2)
        if k in existing_keys:
            skipped_duplicates += 1
            continue
        existing_keys.add(k)
        next_seq += 1
        data = dict(rec)
        data["seq"] = next_seq
        obj = StandardDefectDescription(**data)
        db.add(obj)
        inserted += 1
    db.commit()
    return {
        "success": True,
        "inserted": inserted,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid": skipped_invalid,
        "mode": mode
    }

@single_router.post("/bulk")
def bulk_create_single_checks(
    payload: List[SingleDefectCheckCreate],
    mode: str = Query("replace", pattern="^(replace|append)$"),
    db: Session = Depends(get_db)
):
    if mode == "replace" and payload:
        keys = set()
        for item in payload:
            t = _require_nonempty("type", item.type)
            c = _require_nonempty("cust", item.cust)
            n = _require_nonempty("comp_name", item.comp_name)
            pn = _require_nonempty("comp_pn", item.comp_pn)
            loc = _require_nonempty("loc", item.loc)
            a = _require_nonempty("aircraft_no", item.aircraft_no)
            s = _require_nonempty("sale_wo", item.sale_wo)
            p = _require_nonempty("plan_year_month", item.plan_year_month)
            insp = _require_nonempty("inspector", item.inspector)
            keys.add((
                t,
                c,
                n,
                pn,
                loc,
                a,
                s,
                p,
                insp,
            ))
        deleted = 0
        for t, c, n, pn, loc, a, s, p, insp in keys:
            q = db.query(SingleDefectCheck)
            q = q.filter(SingleDefectCheck.type == t)
            q = q.filter(SingleDefectCheck.cust == c)
            q = q.filter(SingleDefectCheck.comp_name == n)
            q = q.filter(SingleDefectCheck.comp_pn == pn)
            q = q.filter(SingleDefectCheck.loc == loc)
            q = q.filter(SingleDefectCheck.aircraft_no == a)
            q = q.filter(SingleDefectCheck.sale_wo == s)
            q = q.filter(SingleDefectCheck.plan_year_month == p)
            q = q.filter(SingleDefectCheck.inspector == insp)
            deleted += q.delete(synchronize_session=False)
        db.commit()
    else:
        deleted = 0

    inserted = 0
    for item in payload:
        t = _require_nonempty("type", item.type)
        c = _require_nonempty("cust", item.cust)
        n = _require_nonempty("comp_name", item.comp_name)
        d = _require_nonempty("standardized_desc", item.standardized_desc)
        pn = _require_nonempty("comp_pn", item.comp_pn)
        loc = _require_nonempty("loc", item.loc)
        a = _require_nonempty("aircraft_no", item.aircraft_no)
        s = _require_nonempty("sale_wo", item.sale_wo)
        p = _require_nonempty("plan_year_month", item.plan_year_month)
        insp = _require_nonempty("inspector", item.inspector)

        yes = 1 if item.yes_flag == 1 else 0
        no = 1 if item.no_flag == 1 else 0
        if (yes + no) != 1:
            raise HTTPException(status_code=400, detail="yes_flag/no_flag 必须二选一")

        defect_status = _norm_str(getattr(item, "defect_status", None))
        defect_positions = _norm_str(getattr(item, "defect_positions", None))
        defect_quantity = getattr(item, "defect_quantity", None)
        local_photo_url = _norm_str(getattr(item, "local_photo_url", None))
        global_photo_url = _norm_str(getattr(item, "global_photo_url", None))
        if yes == 1:
            pos_list = [s.strip() for s in str(defect_positions).split(";") if s.strip()] if defect_positions else []
            defect_positions = ";".join(pos_list) if pos_list else None
            if defect_quantity is None:
                defect_quantity = len(pos_list) if pos_list else None
            if defect_quantity is not None:
                try:
                    defect_quantity = int(defect_quantity)
                except Exception:
                    raise HTTPException(status_code=400, detail="defect_quantity 必须为整数")
                if defect_quantity <= 0:
                    raise HTTPException(status_code=400, detail="defect_quantity 必须大于 0")
        else:
            defect_status = None
            defect_positions = None
            defect_quantity = None
            local_photo_url = None
            global_photo_url = None

        data = item.dict(exclude_unset=True)
        data["type"] = t
        data["cust"] = c
        data["comp_name"] = n
        data["standardized_desc"] = d
        data["comp_pn"] = pn
        data["loc"] = loc
        data["aircraft_no"] = a
        data["sale_wo"] = s
        data["plan_year_month"] = p
        data["inspector"] = insp
        data["yes_flag"] = 1 if yes == 1 else None
        data["no_flag"] = 1 if no == 1 else None
        data["defect_status"] = defect_status
        data["defect_positions"] = defect_positions
        data["defect_quantity"] = defect_quantity
        data["local_photo_url"] = local_photo_url
        data["global_photo_url"] = global_photo_url
        data.update(_build_derived_preview_fields(
            "single",
            is_defect=yes == 1,
            standardized_desc=d,
            defect_status=defect_status,
            defect_positions=defect_positions,
            defect_quantity=defect_quantity,
            loc=loc,
        ))

        obj = SingleDefectCheck(**data)
        db.add(obj)
        inserted += 1
    db.commit()
    return {"success": True, "inserted": inserted, "deleted": deleted, "mode": mode}

@router.get("/", response_model=List[StandardDefectDesc])
def list_descs(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None)
):
    q = db.query(StandardDefectDescription)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (StandardDefectDescription.standardized_desc.ilike(like)) |
            (StandardDefectDescription.comp_pn.ilike(like)) |
            (StandardDefectDescription.comp_name.ilike(like)) |
            (StandardDefectDescription.type.ilike(like)) |
            (StandardDefectDescription.cust.ilike(like))
        )
    q = q.order_by(StandardDefectDescription.seq.asc(), StandardDefectDescription.id.asc())
    return q.offset(skip).limit(limit).all()

@router.post("/", response_model=StandardDefectDesc)
def create_desc(
    payload: StandardDefectDescCreate,
    db: Session = Depends(get_db)
):
    data = payload.dict(exclude_unset=True)
    data["seq"] = _next_standard_seq(db)
    obj = StandardDefectDescription(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/{id}", response_model=StandardDefectDesc)
def update_desc(
    id: int,
    payload: StandardDefectDescUpdate,
    db: Session = Depends(get_db)
):
    obj = db.query(StandardDefectDescription).filter(StandardDefectDescription.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{id}", response_model=StandardDefectDesc)
def delete_desc(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(StandardDefectDescription).filter(StandardDefectDescription.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj)
    db.flush()
    _resequence_standard_desc(db)
    db.commit()
    return obj

@single_router.get("/", response_model=List[SingleDefectCheckSchema])
def list_single_checks(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None)
):
    q = db.query(SingleDefectCheck)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (SingleDefectCheck.standardized_desc.ilike(like)) |
            (SingleDefectCheck.defect_desc_preview.ilike(like)) |
            (SingleDefectCheck.desc_text.ilike(like)) |
            (SingleDefectCheck.loc_text.ilike(like)) |
            (SingleDefectCheck.comp_pn.ilike(like)) |
            (SingleDefectCheck.comp_name.ilike(like)) |
            (SingleDefectCheck.type.ilike(like)) |
            (SingleDefectCheck.cust.ilike(like)) |
            (SingleDefectCheck.loc.ilike(like)) |
            (SingleDefectCheck.inspector.ilike(like)) |
            (SingleDefectCheck.aircraft_no.ilike(like)) |
            (SingleDefectCheck.sale_wo.ilike(like))
        )
    return q.offset(skip).limit(limit).all()

@single_router.post("/", response_model=SingleDefectCheckSchema)
def create_single_check(
    payload: SingleDefectCheckCreate,
    db: Session = Depends(get_db)
):
    data = payload.dict(exclude_unset=True)
    yes, no = _derive_yes_no_flags(data.get("yes_flag"), data.get("no_flag"))
    data.update(_build_derived_preview_fields(
        "single",
        is_defect=yes == 1,
        standardized_desc=data.get("standardized_desc"),
        defect_status=data.get("defect_status"),
        defect_positions=data.get("defect_positions"),
        defect_quantity=data.get("defect_quantity"),
        loc=data.get("loc"),
    ))
    obj = SingleDefectCheck(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@single_router.get("/{id}", response_model=SingleDefectCheckSchema)
def get_single_check(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(SingleDefectCheck).filter(SingleDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    return obj

@single_router.put("/{id}", response_model=SingleDefectCheckSchema)
def update_single_check(
    id: int,
    payload: SingleDefectCheckUpdate,
    db: Session = Depends(get_db)
):
    obj = db.query(SingleDefectCheck).filter(SingleDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    updates = payload.dict(exclude_unset=True)
    yes, no = _derive_yes_no_flags(
        updates.get("yes_flag", obj.yes_flag),
        updates.get("no_flag", obj.no_flag),
    )
    merged = {
        "standardized_desc": updates.get("standardized_desc", obj.standardized_desc),
        "defect_status": updates.get("defect_status", obj.defect_status),
        "defect_positions": updates.get("defect_positions", obj.defect_positions),
        "defect_quantity": updates.get("defect_quantity", obj.defect_quantity),
        "loc": updates.get("loc", obj.loc),
    }
    updates.update(_build_derived_preview_fields("single", is_defect=yes == 1, **merged))
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@single_router.delete("/{id}", response_model=SingleDefectCheckSchema)
def delete_single_check(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(SingleDefectCheck).filter(SingleDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj)
    db.commit()
    return obj

def _bulk_create_seat_like_checks(model, payload: List, mode: str, db: Session):
    module_kind = "seat" if model is SeatDefectCheck else "crew-seat"
    if mode == "replace" and payload:
        keys = set()
        for item in payload:
            t = _require_nonempty("type", item.type)
            c = _require_nonempty("cust", item.cust)
            n = _require_nonempty("comp_name", item.comp_name)
            pn = _require_nonempty("comp_pn", item.comp_pn)
            loc = _required_or_optional_loc(model, item.loc)
            a = _require_nonempty("aircraft_no", item.aircraft_no)
            s = _require_nonempty("sale_wo", item.sale_wo)
            p = _require_nonempty("plan_year_month", item.plan_year_month)
            insp = _require_nonempty("inspector", item.inspector)
            keys.add((t, c, n, pn, loc, a, s, p, insp))
        deleted = 0
        for t, c, n, pn, loc, a, s, p, insp in keys:
            q = db.query(model)
            q = q.filter(model.type == t)
            q = q.filter(model.cust == c)
            q = q.filter(model.comp_name == n)
            q = q.filter(model.comp_pn == pn)
            q = _apply_optional_filter(q, model.loc, loc)
            q = q.filter(model.aircraft_no == a)
            q = q.filter(model.sale_wo == s)
            q = q.filter(model.plan_year_month == p)
            q = q.filter(model.inspector == insp)
            deleted += q.delete(synchronize_session=False)
        db.commit()
    else:
        deleted = 0

    inserted = 0
    for item in payload:
        t = _require_nonempty("type", item.type)
        c = _require_nonempty("cust", item.cust)
        n = _require_nonempty("comp_name", item.comp_name)
        d = _require_nonempty("standardized_desc", item.standardized_desc)
        pn = _require_nonempty("comp_pn", item.comp_pn)
        loc = _required_or_optional_loc(model, item.loc)
        a = _require_nonempty("aircraft_no", item.aircraft_no)
        s = _require_nonempty("sale_wo", item.sale_wo)
        p = _require_nonempty("plan_year_month", item.plan_year_month)
        insp = _require_nonempty("inspector", item.inspector)

        yes, no = _derive_yes_no_flags(
            getattr(item, "yes_flag", None),
            getattr(item, "no_flag", None),
        )

        defect_status = _norm_str(getattr(item, "defect_status", None))
        defect_positions = _norm_str(getattr(item, "defect_positions", None))
        defect_quantity = getattr(item, "defect_quantity", None)
        local_photo_url = _norm_str(getattr(item, "local_photo_url", None))
        global_photo_url = _norm_str(getattr(item, "global_photo_url", None))
        custom_positions_input = _norm_str(getattr(item, "custom_positions_input", None))
        if yes == 1:
            pos_list = [x.strip() for x in str(defect_positions).split(";") if x.strip()] if defect_positions else []
            defect_positions = ";".join(pos_list) if pos_list else None
            if defect_quantity is None:
                defect_quantity = len(pos_list) if pos_list else None
            if defect_quantity is not None:
                try:
                    defect_quantity = int(defect_quantity)
                except Exception:
                    raise HTTPException(status_code=400, detail="defect_quantity 必须为整数")
                if defect_quantity <= 0:
                    raise HTTPException(status_code=400, detail="defect_quantity 必须大于 0")
        else:
            defect_status = None
            defect_positions = None
            defect_quantity = None
            local_photo_url = None
            global_photo_url = None

        data = item.dict(exclude_unset=True)
        data["type"] = t
        data["cust"] = c
        data["comp_name"] = n
        data["standardized_desc"] = d
        data["comp_pn"] = pn
        data["loc"] = loc
        data["aircraft_no"] = a
        data["sale_wo"] = s
        data["plan_year_month"] = p
        data["inspector"] = insp
        data["yes_flag"] = 1 if yes == 1 else None
        data["no_flag"] = 1 if no == 1 else None
        data["defect_status"] = defect_status
        data["defect_positions"] = defect_positions
        data["defect_quantity"] = defect_quantity
        data["local_photo_url"] = local_photo_url
        data["global_photo_url"] = global_photo_url
        data["custom_positions_input"] = custom_positions_input
        data.update(_build_derived_preview_fields(
            module_kind,
            is_defect=yes == 1,
            standardized_desc=d,
            defect_status=defect_status,
            defect_positions=defect_positions,
            defect_quantity=defect_quantity,
            loc=loc,
        ))

        obj = model(**data)
        db.add(obj)
        inserted += 1
    db.commit()
    return {"success": True, "inserted": inserted, "deleted": deleted, "mode": mode}

@seat_router.post("/bulk")
def bulk_create_seat_checks(
    payload: List[SeatDefectCheckCreate],
    mode: str = Query("replace", pattern="^(replace|append)$"),
    db: Session = Depends(get_db)
):
    return _bulk_create_seat_like_checks(SeatDefectCheck, payload, mode, db)

@seat_router.get("/", response_model=List[SeatDefectCheckSchema])
def list_seat_checks(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None)
):
    q = db.query(SeatDefectCheck)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (SeatDefectCheck.standardized_desc.ilike(like)) |
            (SeatDefectCheck.defect_desc_preview.ilike(like)) |
            (SeatDefectCheck.desc_text.ilike(like)) |
            (SeatDefectCheck.loc_text.ilike(like)) |
            (SeatDefectCheck.comp_pn.ilike(like)) |
            (SeatDefectCheck.comp_name.ilike(like)) |
            (SeatDefectCheck.type.ilike(like)) |
            (SeatDefectCheck.cust.ilike(like)) |
            (SeatDefectCheck.loc.ilike(like)) |
            (SeatDefectCheck.inspector.ilike(like)) |
            (SeatDefectCheck.aircraft_no.ilike(like)) |
            (SeatDefectCheck.sale_wo.ilike(like))
        )
    return q.offset(skip).limit(limit).all()

@seat_router.post("/", response_model=SeatDefectCheckSchema)
def create_seat_check(
    payload: SeatDefectCheckCreate,
    db: Session = Depends(get_db)
):
    data = payload.dict(exclude_unset=True)
    yes, no = _derive_yes_no_flags(data.get("yes_flag"), data.get("no_flag"))
    data.update(_build_derived_preview_fields(
        "seat",
        is_defect=yes == 1,
        standardized_desc=data.get("standardized_desc"),
        defect_status=data.get("defect_status"),
        defect_positions=data.get("defect_positions"),
        defect_quantity=data.get("defect_quantity"),
        loc=data.get("loc"),
    ))
    obj = SeatDefectCheck(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@seat_router.get("/{id}", response_model=SeatDefectCheckSchema)
def get_seat_check(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(SeatDefectCheck).filter(SeatDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    return obj

@seat_router.put("/{id}", response_model=SeatDefectCheckSchema)
def update_seat_check(
    id: int,
    payload: SeatDefectCheckUpdate,
    db: Session = Depends(get_db)
):
    obj = db.query(SeatDefectCheck).filter(SeatDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    updates = payload.dict(exclude_unset=True)
    yes, no = _derive_yes_no_flags(
        updates.get("yes_flag", obj.yes_flag),
        updates.get("no_flag", obj.no_flag),
    )
    merged = {
        "standardized_desc": updates.get("standardized_desc", obj.standardized_desc),
        "defect_status": updates.get("defect_status", obj.defect_status),
        "defect_positions": updates.get("defect_positions", obj.defect_positions),
        "defect_quantity": updates.get("defect_quantity", obj.defect_quantity),
        "loc": updates.get("loc", obj.loc),
    }
    updates.update(_build_derived_preview_fields("seat", is_defect=yes == 1, **merged))
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@seat_router.delete("/{id}", response_model=SeatDefectCheckSchema)
def delete_seat_check(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(SeatDefectCheck).filter(SeatDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj)
    db.commit()
    return obj

@crew_seat_router.post("/bulk")
def bulk_create_crew_seat_checks(
    payload: List[CrewSeatDefectCheckCreate],
    mode: str = Query("replace", pattern="^(replace|append)$"),
    db: Session = Depends(get_db)
):
    return _bulk_create_seat_like_checks(CrewSeatDefectCheck, payload, mode, db)

@crew_seat_router.get("/", response_model=List[CrewSeatDefectCheckSchema])
def list_crew_seat_checks(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None)
):
    q = db.query(CrewSeatDefectCheck)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (CrewSeatDefectCheck.standardized_desc.ilike(like)) |
            (CrewSeatDefectCheck.defect_desc_preview.ilike(like)) |
            (CrewSeatDefectCheck.desc_text.ilike(like)) |
            (CrewSeatDefectCheck.loc_text.ilike(like)) |
            (CrewSeatDefectCheck.comp_pn.ilike(like)) |
            (CrewSeatDefectCheck.comp_name.ilike(like)) |
            (CrewSeatDefectCheck.type.ilike(like)) |
            (CrewSeatDefectCheck.cust.ilike(like)) |
            (CrewSeatDefectCheck.loc.ilike(like)) |
            (CrewSeatDefectCheck.inspector.ilike(like)) |
            (CrewSeatDefectCheck.aircraft_no.ilike(like)) |
            (CrewSeatDefectCheck.sale_wo.ilike(like))
        )
    return q.offset(skip).limit(limit).all()

@crew_seat_router.post("/", response_model=CrewSeatDefectCheckSchema)
def create_crew_seat_check(
    payload: CrewSeatDefectCheckCreate,
    db: Session = Depends(get_db)
):
    data = payload.dict(exclude_unset=True)
    yes, no = _derive_yes_no_flags(data.get("yes_flag"), data.get("no_flag"))
    data.update(_build_derived_preview_fields(
        "crew-seat",
        is_defect=yes == 1,
        standardized_desc=data.get("standardized_desc"),
        defect_status=data.get("defect_status"),
        defect_positions=data.get("defect_positions"),
        defect_quantity=data.get("defect_quantity"),
        loc=data.get("loc"),
    ))
    obj = CrewSeatDefectCheck(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@crew_seat_router.get("/{id}", response_model=CrewSeatDefectCheckSchema)
def get_crew_seat_check(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(CrewSeatDefectCheck).filter(CrewSeatDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    return obj

@crew_seat_router.put("/{id}", response_model=CrewSeatDefectCheckSchema)
def update_crew_seat_check(
    id: int,
    payload: CrewSeatDefectCheckUpdate,
    db: Session = Depends(get_db)
):
    obj = db.query(CrewSeatDefectCheck).filter(CrewSeatDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    updates = payload.dict(exclude_unset=True)
    yes, no = _derive_yes_no_flags(
        updates.get("yes_flag", obj.yes_flag),
        updates.get("no_flag", obj.no_flag),
    )
    merged = {
        "standardized_desc": updates.get("standardized_desc", obj.standardized_desc),
        "defect_status": updates.get("defect_status", obj.defect_status),
        "defect_positions": updates.get("defect_positions", obj.defect_positions),
        "defect_quantity": updates.get("defect_quantity", obj.defect_quantity),
        "loc": updates.get("loc", obj.loc),
    }
    updates.update(_build_derived_preview_fields("crew-seat", is_defect=yes == 1, **merged))
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@crew_seat_router.delete("/{id}", response_model=CrewSeatDefectCheckSchema)
def delete_crew_seat_check(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(CrewSeatDefectCheck).filter(CrewSeatDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj)
    db.commit()
    return obj

@batch_router.post("/bulk")
def bulk_create_batch_checks(
    payload: List[BatchDefectCheckCreate],
    mode: str = Query("replace", pattern="^(replace|append)$"),
    db: Session = Depends(get_db)
):
    if mode == "replace" and payload:
        keys = set()
        for item in payload:
            t = _require_nonempty("type", item.type)
            c = _require_nonempty("cust", item.cust)
            n = _require_nonempty("comp_name", item.comp_name)
            pn = _require_nonempty("comp_pn", item.comp_pn)
            a = _require_nonempty("aircraft_no", item.aircraft_no)
            s = _require_nonempty("sale_wo", item.sale_wo)
            p = _require_nonempty("plan_year_month", item.plan_year_month)
            keys.add((t, c, n, pn, a, s, p))
        deleted = 0
        for t, c, n, pn, a, s, p in keys:
            q = db.query(BatchDefectCheck)
            q = q.filter(BatchDefectCheck.type == t)
            q = q.filter(BatchDefectCheck.cust == c)
            q = q.filter(BatchDefectCheck.comp_name == n)
            q = q.filter(BatchDefectCheck.comp_pn == pn)
            q = q.filter(BatchDefectCheck.aircraft_no == a)
            q = q.filter(BatchDefectCheck.sale_wo == s)
            q = q.filter(BatchDefectCheck.plan_year_month == p)
            deleted += q.delete(synchronize_session=False)
        db.commit()
    else:
        deleted = 0

    inserted = 0
    for item in payload:
        t = _require_nonempty("type", item.type)
        c = _require_nonempty("cust", item.cust)
        n = _require_nonempty("comp_name", item.comp_name)
        d = _require_nonempty("standardized_desc", item.standardized_desc)
        pn = _require_nonempty("comp_pn", item.comp_pn)
        a = _require_nonempty("aircraft_no", item.aircraft_no)
        s = _require_nonempty("sale_wo", item.sale_wo)
        p = _require_nonempty("plan_year_month", item.plan_year_month)

        yes, no = _derive_yes_no_flags(
            getattr(item, "yes_flag", None),
            getattr(item, "no_flag", None),
        )

        defect_status = _norm_str(getattr(item, "defect_status", None))
        defect_positions_in = _norm_str(getattr(item, "defect_positions", None)) or _norm_str(getattr(item, "position", None))
        defect_quantity = getattr(item, "defect_quantity", None)
        if defect_quantity is None:
            defect_quantity = getattr(item, "quantity", None)
        local_photo_url = _norm_str(getattr(item, "local_photo_url", None))
        global_photo_url = _norm_str(getattr(item, "global_photo_url", None))

        if yes == 1:
            pos_list = [x.strip() for x in str(defect_positions_in).split(";") if x.strip()] if defect_positions_in else []
            defect_positions = ";".join(pos_list) if pos_list else None
            if defect_quantity is None:
                defect_quantity = len(pos_list) if pos_list else None
            if defect_quantity is not None:
                try:
                    defect_quantity = int(defect_quantity)
                except Exception:
                    raise HTTPException(status_code=400, detail="defect_quantity 必须为整数")
                if defect_quantity <= 0:
                    raise HTTPException(status_code=400, detail="defect_quantity 必须大于 0")
            position = defect_positions
            quantity = float(defect_quantity) if defect_quantity is not None else None
        else:
            defect_status = None
            defect_positions = None
            defect_quantity = None
            position = None
            quantity = None
            local_photo_url = None
            global_photo_url = None

        data = item.dict(exclude_unset=True)
        data["type"] = t
        data["cust"] = c
        data["comp_name"] = n
        data["standardized_desc"] = d
        data["comp_pn"] = pn
        data["aircraft_no"] = a
        data["sale_wo"] = s
        data["plan_year_month"] = p
        data["yes_flag"] = 1 if yes == 1 else None
        data["no_flag"] = 1 if no == 1 else None
        data["defect_status"] = defect_status
        data["defect_positions"] = defect_positions
        data["defect_quantity"] = defect_quantity
        data["position"] = position
        data["quantity"] = quantity
        data["local_photo_url"] = local_photo_url
        data["global_photo_url"] = global_photo_url
        data.update(_build_derived_preview_fields(
            "batch",
            is_defect=yes == 1,
            standardized_desc=d,
            defect_status=defect_status,
            defect_positions=defect_positions,
            defect_quantity=defect_quantity,
            position=position,
        ))

        obj = BatchDefectCheck(**data)
        db.add(obj)
        inserted += 1
    db.commit()
    return {"success": True, "inserted": inserted, "deleted": deleted, "mode": mode}

@batch_router.get("/", response_model=List[BatchDefectCheckSchema])
def list_batch_checks(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None)
):
    q = db.query(BatchDefectCheck)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (BatchDefectCheck.standardized_desc.ilike(like)) |
            (BatchDefectCheck.defect_desc_preview.ilike(like)) |
            (BatchDefectCheck.desc_text.ilike(like)) |
            (BatchDefectCheck.loc_text.ilike(like)) |
            (BatchDefectCheck.comp_pn.ilike(like)) |
            (BatchDefectCheck.comp_name.ilike(like)) |
            (BatchDefectCheck.type.ilike(like)) |
            (BatchDefectCheck.cust.ilike(like)) |
            (BatchDefectCheck.position.ilike(like)) |
            (BatchDefectCheck.defect_status.ilike(like)) |
            (BatchDefectCheck.defect_positions.ilike(like)) |
            (BatchDefectCheck.aircraft_no.ilike(like)) |
            (BatchDefectCheck.sale_wo.ilike(like))
        )
    return q.offset(skip).limit(limit).all()

@batch_router.post("/", response_model=BatchDefectCheckSchema)
def create_batch_check(
    payload: BatchDefectCheckCreate,
    db: Session = Depends(get_db)
):
    data = payload.dict(exclude_unset=True)
    yes, no = _derive_yes_no_flags(data.get("yes_flag"), data.get("no_flag"))
    data.update(_build_derived_preview_fields(
        "batch",
        is_defect=yes == 1,
        standardized_desc=data.get("standardized_desc"),
        defect_status=data.get("defect_status"),
        defect_positions=data.get("defect_positions"),
        defect_quantity=data.get("defect_quantity"),
        position=data.get("position"),
    ))
    obj = BatchDefectCheck(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@batch_router.get("/{id}", response_model=BatchDefectCheckSchema)
def get_batch_check(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(BatchDefectCheck).filter(BatchDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    return obj

@batch_router.put("/{id}", response_model=BatchDefectCheckSchema)
def update_batch_check(
    id: int,
    payload: BatchDefectCheckUpdate,
    db: Session = Depends(get_db)
):
    obj = db.query(BatchDefectCheck).filter(BatchDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    updates = payload.dict(exclude_unset=True)
    yes, no = _derive_yes_no_flags(
        updates.get("yes_flag", obj.yes_flag),
        updates.get("no_flag", obj.no_flag),
    )
    merged = {
        "standardized_desc": updates.get("standardized_desc", obj.standardized_desc),
        "defect_status": updates.get("defect_status", obj.defect_status),
        "defect_positions": updates.get("defect_positions", obj.defect_positions),
        "defect_quantity": updates.get("defect_quantity", obj.defect_quantity),
        "position": updates.get("position", obj.position),
    }
    updates.update(_build_derived_preview_fields("batch", is_defect=yes == 1, **merged))
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@batch_router.delete("/{id}", response_model=BatchDefectCheckSchema)
def delete_batch_check(
    id: int,
    db: Session = Depends(get_db)
):
    obj = db.query(BatchDefectCheck).filter(BatchDefectCheck.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj)
    db.commit()
    return obj
