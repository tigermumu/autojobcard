from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.localwash import KeywordDictItem
from app.schemas.localwash import (
    KeywordDictCreate,
    KeywordDictDetail,
    KeywordDictOut,
    KeywordDictOptionOut,
    KeywordDictItemOut,
    KeywordDictItemCreate,
    KeywordDictItemUpdate,
    GlobalKeywordCreate,
    GlobalKeywordUpdate,
    GlobalKeywordOut,
    LocalCleanDefectsRequest,
    LocalCleanDefectsResponse,
    LocalCleanRequestBase,
    LocalCleanWorkcardsResponse,
    LocalCleanWorkcardsUploadRequest,
    LocalCleanWorkcardsUploadResponse,
    LocalMatchDefectsRequest,
    LocalMatchDefectsResponse,
    LocalMatchStatsResponse,
    LocalAvailableCleanedDefectsResponse,
)
from app.services.localwash_service import LocalWashService

router = APIRouter()


@router.get("/dicts", response_model=List[KeywordDictOut])
def list_keyword_dicts(
    configuration_id: int = Query(...),
    db: Session = Depends(get_db),
):
    service = LocalWashService(db)
    return service.list_dicts(configuration_id)


@router.get("/dicts/options", response_model=List[KeywordDictOptionOut])
def list_keyword_dict_options(db: Session = Depends(get_db)):
    """用于前端下拉：列出所有可用的关键词字典版本。"""
    service = LocalWashService(db)
    return service.list_dict_options()


@router.get("/dicts/{dict_id}", response_model=KeywordDictDetail)
def get_keyword_dict(dict_id: int, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    d = service.get_dict(dict_id)
    if not d:
        raise HTTPException(status_code=404, detail="关键词字典未找到")
    # force load items
    _ = d.items
    return d


@router.get("/keywords/global", response_model=List[GlobalKeywordOut])
def list_global_keywords(
    q: Optional[str] = Query(None, description="关键词模糊查询"),
    db: Session = Depends(get_db),
):
    service = LocalWashService(db)
    return service.list_global_keywords(q)


@router.post("/keywords/global", response_model=GlobalKeywordOut)
def create_global_keyword(payload: GlobalKeywordCreate, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    try:
        return service.create_global_keyword(payload.keyword, payload.enabled)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/keywords/global/{item_id}", response_model=GlobalKeywordOut)
def update_global_keyword(item_id: int, payload: GlobalKeywordUpdate, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    try:
        item = service.update_global_keyword(item_id, payload.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not item:
        raise HTTPException(status_code=404, detail="关键词未找到")
    return item


@router.delete("/keywords/global/{item_id}")
def delete_global_keyword(item_id: int, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    ok = service.delete_global_keyword(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="关键词未找到")
    return {"success": True}


@router.post("/dicts", response_model=KeywordDictDetail)
def create_keyword_dict(payload: KeywordDictCreate, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    try:
        d = service.create_dict(
            configuration_id=payload.configuration_id,
            version=payload.version,
            remark=payload.remark,
            items=[i.model_dump() for i in payload.items],
        )
        # reload with items
        d2 = service.get_dict(d.id)
        _ = d2.items if d2 else None
        return d2
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dicts/import", response_model=KeywordDictDetail)
def import_keyword_dict_from_file(
    configuration_id: int = Form(...),
    version: str = Form(...),
    remark: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    导入关键词字典：
    - 支持 tidy 格式（列：dimension, main_component, keyword, enabled）
    - 支持 sheet3 wide 格式（列：main_component + sub/location/orientation/status，单元格用逗号分隔）
    """
    import pandas as pd
    import re

    service = LocalWashService(db)
    try:
        filename = (file.filename or "").lower()
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(file.file)
        else:
            df = pd.read_csv(file.file, encoding="utf-8")

        df.columns = [str(c).strip() for c in df.columns]

        items = []

        def split_keywords(cell) -> List[str]:
            if cell is None:
                return []
            s = str(cell).strip()
            if not s or s.lower() == "nan":
                return []
            # 支持中文逗号/英文逗号/分号
            parts = re.split(r"[，,;；]\s*", s)
            return [p.strip() for p in parts if p and p.strip()]

        # tidy format
        if "dimension" in df.columns and "keyword" in df.columns:
            for _, row in df.iterrows():
                dim = str(row.get("dimension", "")).strip().lower()
                kw = str(row.get("keyword", "")).strip()
                if not dim or not kw:
                    continue
                mc = row.get("main_component")
                enabled = row.get("enabled", True)
                items.append(
                    {
                        "dimension": dim,
                        "main_component": str(mc).strip() if mc is not None and str(mc).strip().lower() != "nan" else None,
                        "keyword": kw,
                        "enabled": bool(enabled) if str(enabled).strip() != "" else True,
                    }
                )
        else:
            # wide format: try to normalize column names
            col_map = {c.lower(): c for c in df.columns}
            main_col = col_map.get("main_component") or col_map.get("main") or col_map.get("主部件") or col_map.get("主部件关键词")
            if not main_col:
                raise ValueError("无法识别主部件列：请提供 main_component 或 Main Component 列")

            sub_col = col_map.get("sub") or col_map.get("sub_component") or col_map.get("子部件") or col_map.get("子部件关键词")
            loc_col = col_map.get("location") or col_map.get("位置") or col_map.get("位置关键词")
            ori_col = col_map.get("orientation") or col_map.get("方向") or col_map.get("方位") or col_map.get("方向关键词")
            status_col = col_map.get("status") or col_map.get("condition") or col_map.get("状态") or col_map.get("状态关键词")
            action_col = col_map.get("action") or col_map.get("动作") or col_map.get("动作关键词")

            # 状态列（Status/Condition）按需求是“全局有效”，因此对全文件汇总去重后再写入一次
            global_status_set = set()
            # 动作列（Action）按需求是“全局有效”，对全文件汇总去重后再写入一次
            global_action_set = set()

            for _, row in df.iterrows():
                main_list = split_keywords(row.get(main_col))
                if not main_list:
                    continue

                sub_list = split_keywords(row.get(sub_col)) if sub_col else []
                loc_list = split_keywords(row.get(loc_col)) if loc_col else []
                ori_list = split_keywords(row.get(ori_col)) if ori_col else []
                status_list = split_keywords(row.get(status_col)) if status_col else []
                action_list = split_keywords(row.get(action_col)) if action_col else []

                # 对每个主部件同义词都复制一套绑定词，确保“锁定主部件”后的语境一致
                for main_kw in main_list:
                    items.append({"dimension": "main", "main_component": None, "keyword": main_kw, "enabled": True})
                    for kw in sub_list:
                        items.append({"dimension": "sub", "main_component": main_kw, "keyword": kw, "enabled": True})
                    for kw in loc_list:
                        items.append({"dimension": "location", "main_component": main_kw, "keyword": kw, "enabled": True})
                    for kw in ori_list:
                        items.append({"dimension": "orientation", "main_component": main_kw, "keyword": kw, "enabled": True})
                for kw in status_list:
                    if kw:
                        global_status_set.add(kw)
                for kw in action_list:
                    if kw:
                        global_action_set.add(kw)

            for kw in sorted(global_status_set):
                items.append({"dimension": "status", "main_component": None, "keyword": kw, "enabled": True})
            for kw in sorted(global_action_set):
                items.append({"dimension": "action", "main_component": None, "keyword": kw, "enabled": True})

        # 去重：按 (dimension, main_component, keyword) 组合去重
        # 每个条目之间相互比较，完全重复的条目只保留一条
        # main_component 需要归一化：None、空字符串、实际值统一处理
        # keyword 和 dimension 忽略大小写差异进行比较
        seen = set()
        deduplicated_items = []
        duplicate_count = 0
        
        for item in items:
            # 归一化 main_component：None 和空字符串都视为 None，并转换为小写进行比较
            main_comp_raw = item.get("main_component")
            if main_comp_raw is None or (isinstance(main_comp_raw, str) and not main_comp_raw.strip()):
                main_comp_normalized = None
                main_comp_to_save = None
            else:
                main_comp_str = str(main_comp_raw).strip()
                main_comp_normalized = main_comp_str.lower()  # 用于比较
                main_comp_to_save = main_comp_str  # 保留原始大小写
            
            # 归一化 keyword：去除首尾空格，转换为小写进行比较，但保留原始大小写
            keyword_raw = str(item.get("keyword", "")).strip()
            keyword_normalized = keyword_raw.lower()  # 用于比较
            keyword_to_save = keyword_raw  # 保留原始大小写
            
            # 归一化 dimension：转换为小写进行比较
            dimension_raw = str(item.get("dimension", "")).strip()
            dimension_normalized = dimension_raw.lower()
            
            # 构建唯一键（用于比较是否重复）
            unique_key = (dimension_normalized, main_comp_normalized, keyword_normalized)
            
            if unique_key not in seen:
                seen.add(unique_key)
                # 保留原始值的大小写和格式
                deduplicated_items.append({
                    "dimension": dimension_normalized,  # dimension统一使用小写
                    "main_component": main_comp_to_save,  # 保留原始大小写
                    "keyword": keyword_to_save,  # 保留原始大小写
                    "enabled": item.get("enabled", True),
                })
            else:
                duplicate_count += 1
        
        items = deduplicated_items

        # 记录去重统计信息到remark中（如果remark为空则创建，否则追加）
        original_remark = remark or ""
        total_before_dedup = len(items) + duplicate_count
        dedup_info = f"[去重] 去重前: {total_before_dedup} 条，去重后: {len(items)} 条，去除重复: {duplicate_count} 条"
        if original_remark:
            final_remark = f"{original_remark} | {dedup_info}"
        else:
            final_remark = dedup_info

        # 检查版本是否已存在，如果冲突则自动追加后缀
        from app.models.localwash import KeywordDict
        final_version = version
        suffix = 0
        while db.query(KeywordDict).filter(
            KeywordDict.configuration_id == configuration_id,
            KeywordDict.version == final_version
        ).first():
            suffix += 1
            final_version = f"{version}-{suffix}"

        d = service.create_dict(configuration_id=configuration_id, version=final_version, remark=final_remark, items=items)
        d2 = service.get_dict(d.id)
        _ = d2.items if d2 else None
        return d2
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.put("/dict-items/{item_id}", response_model=KeywordDictItemOut)
def update_keyword_dict_item(item_id: int, payload: KeywordDictItemUpdate, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    item = service.update_dict_item(item_id, payload.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="关键词条目未找到")
    return item


@router.post("/dict-items", response_model=KeywordDictItemOut)
def create_keyword_dict_item(
    dict_id: int = Query(..., description="关键词字典ID"),
    payload: KeywordDictItemCreate = ...,
    db: Session = Depends(get_db),
):
    service = LocalWashService(db)
    try:
        item = service.create_dict_item(
            dict_id=dict_id,
            item=payload.model_dump(),
        )
        return item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/dict-items/{item_id}", response_model=dict)
def delete_keyword_dict_item(item_id: int, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    ok = service.delete_dict_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="关键词条目未找到")
    return {"success": True}


@router.post("/clean/workcards", response_model=LocalCleanWorkcardsResponse)
def local_clean_workcards(payload: LocalCleanRequestBase, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    try:
        compiled, total, cleaned, skipped = service.clean_all_workcards(
            payload.configuration_id, dict_id=payload.dict_id, cabin_layout=payload.cabin_layout
        )
        return LocalCleanWorkcardsResponse(
            success=True,
            configuration_id=payload.configuration_id,
            dict_id=compiled.dict_id,
            dict_version=compiled.version,
            total=total,
            cleaned=cleaned,
            skipped=skipped,
            message=f"本地清洗工卡完成：共 {total} 条，清洗 {cleaned} 条，跳过 {skipped} 条",
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clean/workcards", response_model=LocalCleanWorkcardsUploadResponse)
def get_clean_workcards(
    configuration_id: int = Query(...),
    dict_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    source: str = Query("upload", description="数据来源：upload=上传(workcard_clean_local_upload), history=历史(workcard_clean_local)"),
    cabin_layout: Optional[str] = Query(None, description="客舱布局筛选"),
    db: Session = Depends(get_db),
):
    """
    查看已落库的本地清洗工卡数据。
    默认查看 upload 表的数据，也可指定 history 查看 historical clean 表。
    """
    service = LocalWashService(db)
    rows, total = service.get_clean_workcards(
        configuration_id=configuration_id,
        dict_id=dict_id,
        skip=skip,
        limit=limit,
        source=source,
        cabin_layout=cabin_layout,
    )
    
    # 构造返回体
    # 为了复用前端 LocalCleanWorkcardsUploadResponse 类型 (含 cleaned_data 数组)，
    # 这里做一下适配
    cleaned_data = [
        {
            "workcard_number": r.workcard_number,
            "description_cn": r.description_cn,
            "description_en": r.description_en,
            "main_component": r.main_component,
            "sub_component": r.sub_component,
            "location": r.location,
            "orientation": r.orientation,
            "status": r.status,
            "action": r.action,
        }
        for r in rows
    ]

    return LocalCleanWorkcardsUploadResponse(
        success=True,
        configuration_id=configuration_id,
        dict_id=dict_id or 0,
        dict_version="", # 查询列表时版本号可能不一致，暂不返回或取第一条
        total=total,
        cleaned=len(cleaned_data),
        skipped=0,
        cleaned_data=cleaned_data,
        message=f"查询成功：共 {total} 条数据",
    )


@router.post("/clean/workcards/upload", response_model=LocalCleanWorkcardsUploadResponse)
def local_clean_workcards_upload(payload: LocalCleanWorkcardsUploadRequest, db: Session = Depends(get_db)):
    """
    本地清洗（历史工卡）：直接清洗前端上传的 Excel 行数据。
    用于 /workcard/add 在 local 模式下的“本地清洗工卡库”按钮。
    """
    service = LocalWashService(db)
    try:
        compiled, total, cleaned, skipped, out_rows, configuration_id = service.clean_uploaded_workcards(
            dict_id=payload.dict_id,
            rows=[r.model_dump() for r in payload.rows],
        )
        return LocalCleanWorkcardsUploadResponse(
            success=True,
            configuration_id=configuration_id,
            dict_id=compiled.dict_id,
            dict_version=compiled.version,
            total=total,
            cleaned=cleaned,
            skipped=skipped,
            cleaned_data=out_rows,
            message=f"本地清洗工卡完成：共 {total} 条，清洗 {cleaned} 条，跳过 {skipped} 条",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/clean/workcards/upload/save", response_model=LocalCleanWorkcardsResponse)
def local_save_cleaned_workcards_upload(payload: LocalCleanWorkcardsUploadRequest, db: Session = Depends(get_db)):
    """保存：对上传的历史工卡执行本地清洗并落库到 workcard_clean_local_upload。"""
    service = LocalWashService(db)
    try:
        compiled, total, cleaned, skipped = service.save_uploaded_workcards_cleaned(
            dict_id=payload.dict_id,
            rows=[r.model_dump() for r in payload.rows],
            cabin_layout=payload.cabin_layout,
        )
        d = service.get_dict(compiled.dict_id)
        return LocalCleanWorkcardsResponse(
            success=True,
            configuration_id=d.configuration_id if d else 0,
            dict_id=compiled.dict_id,
            dict_version=compiled.version,
            total=total,
            cleaned=cleaned,
            skipped=skipped,
            message=f"已保存本地清洗工卡结果：共 {total} 条，清洗 {cleaned} 条，跳过 {skipped} 条",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/clean/defects", response_model=LocalCleanDefectsResponse)
def local_clean_defects(payload: LocalCleanDefectsRequest, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    try:
        compiled, rows, total, cleaned, skipped = service.clean_defects_in_list(
            defect_list_id=payload.defect_list_id,
            configuration_id=payload.configuration_id,
            dict_id=payload.dict_id,
        )
        # fill defect_number for UI
        from app.models.defect import DefectRecord
        id_list = [r.defect_record_id for r in rows]
        number_map = {}
        if id_list:
            number_map = {
                dr.id: dr.defect_number
                for dr in db.query(DefectRecord).filter(DefectRecord.id.in_(id_list)).all()
            }
        cleaned_out = [
            {
                "defect_record_id": r.defect_record_id,
                "defect_number": number_map.get(r.defect_record_id, ""),
                "description_cn": r.description_cn or "",
                "description_en": r.description_en or "",
                "main_component": r.main_component,
                "sub_component": r.sub_component,
                "location": r.location,
                "orientation": r.orientation,
                "status": r.status,
                "action": getattr(r, "action", None),
            }
            for r in rows
        ]
        return LocalCleanDefectsResponse(
            success=True,
            defect_list_id=payload.defect_list_id,
            configuration_id=payload.configuration_id,
            dict_id=compiled.dict_id,
            dict_version=compiled.version,
            total=total,
            cleaned=cleaned,
            skipped=skipped,
            cleaned_data=cleaned_out,
            message=f"本地清洗缺陷完成：共 {total} 条，清洗 {cleaned} 条，跳过 {skipped} 条",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/match/defects", response_model=LocalMatchDefectsResponse)
def local_match_defects(payload: LocalMatchDefectsRequest, db: Session = Depends(get_db)):
    service = LocalWashService(db)
    try:
        compiled, results = service.match_defects(
            defect_list_id=payload.defect_list_id,
            configuration_id=payload.configuration_id,
            dict_id=payload.dict_id,
            source=payload.source,
            cabin_layout=payload.cabin_layout,
        )
        return LocalMatchDefectsResponse(
            success=True,
            defect_list_id=payload.defect_list_id,
            configuration_id=payload.configuration_id,
            dict_id=compiled.dict_id,
            dict_version=compiled.version,
            results=results,
            message="本地匹配完成",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/match/stats", response_model=LocalMatchStatsResponse)
def local_match_stats(
    defect_list_id: int = Query(...),
    configuration_id: int = Query(...),
    dict_id: int = Query(...),
    cabin_layout: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    service = LocalWashService(db)
    return service.get_match_stats(defect_list_id, configuration_id, dict_id, cabin_layout)


@router.get("/match/export")
def local_export_matches(
    defect_list_id: int = Query(...),
    configuration_id: int = Query(...),
    dict_id: int = Query(...),
    cabin_layout: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    service = LocalWashService(db)
    content = service.export_matched_defects(defect_list_id, configuration_id, dict_id, cabin_layout)
    
    filename = f"match_results_{defect_list_id}.xlsx"
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/clean/workcards/cabin-layouts")
def get_available_cabin_layouts(
    configuration_id: int = Query(...),
    source: str = Query("upload", description="数据来源：upload 或 history"),
    db: Session = Depends(get_db),
):
    """获取所有可用的客舱布局列表"""
    service = LocalWashService(db)
    layouts = service.get_available_cabin_layouts(
        configuration_id=configuration_id,
        source=source
    )
    return {"cabin_layouts": layouts}

@router.get("/dicts/check-duplicates")
def check_dict_duplicates(
    db: Session = Depends(get_db),
):
    """检查词典管理表中的重复数据"""
    from collections import defaultdict
    from sqlalchemy import func
    
    # 获取所有词条
    all_items = db.query(KeywordDictItem).all()
    
    # 按 (dimension, main_component, keyword) 分组统计（忽略大小写）
    groups = defaultdict(list)
    
    for item in all_items:
        # 归一化用于比较
        dimension = (item.dimension or "").strip().lower()
        main_comp = (item.main_component or "").strip().lower() if item.main_component else None
        keyword = (item.keyword or "").strip().lower()
        
        # 构建唯一键
        unique_key = (dimension, main_comp, keyword)
        groups[unique_key].append({
            "id": item.id,
            "dict_id": item.dict_id,
            "dimension": item.dimension,
            "main_component": item.main_component,
            "keyword": item.keyword,
            "enabled": item.enabled,
        })
    
    # 找出重复的条目
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    
    # 特别检查 main=cabin, sub=actuator 的情况
    cabin_items = db.query(KeywordDictItem).filter(
        func.lower(KeywordDictItem.dimension) == 'main',
        func.lower(KeywordDictItem.keyword) == 'cabin'
    ).all()
    
    actuator_items = db.query(KeywordDictItem).filter(
        func.lower(KeywordDictItem.dimension) == 'sub',
        func.lower(KeywordDictItem.keyword) == 'actuator'
    ).all()
    
    # 格式化重复数据
    duplicate_list = []
    total_duplicate_items = 0
    for (dim, main_comp, keyword), items in sorted(duplicates.items()):
        total_duplicate_items += len(items)
        duplicate_list.append({
            "dimension": dim,
            "main_component": main_comp or None,
            "keyword": keyword,
            "count": len(items),
            "items": items
        })
    
    return {
        "total_items": len(all_items),
        "unique_combinations": len(groups),
        "duplicate_combinations": len(duplicates),
        "total_duplicate_items": total_duplicate_items,
        "can_reduce": total_duplicate_items - len(duplicates),
        "duplicates": duplicate_list,
        "cabin_items": [{"id": item.id, "dict_id": item.dict_id, "keyword": item.keyword} for item in cabin_items],
        "actuator_items": [{"id": item.id, "dict_id": item.dict_id, "main_component": item.main_component, "keyword": item.keyword} for item in actuator_items],
    }

@router.get("/clean/workcards/export")
def export_cleaned_workcards(
    configuration_id: int = Query(...),
    dict_id: Optional[int] = Query(None),
    source: str = Query("history", description="数据来源：upload 或 history"),
    cabin_layout: Optional[str] = Query(None, description="客舱布局筛选"),
    db: Session = Depends(get_db),
):
    """导出已清洗的历史工卡客舱部件到Excel"""
    from fastapi.responses import StreamingResponse
    from datetime import datetime
    from urllib.parse import quote
    
    service = LocalWashService(db)
    content = service.export_cleaned_workcards(
        configuration_id=configuration_id,
        dict_id=dict_id,
        source=source,
        cabin_layout=cabin_layout
    )
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    layout_suffix = f"_{cabin_layout}" if cabin_layout else ""
    filename = f"已清洗工卡_{configuration_id}{layout_suffix}_{timestamp}.xlsx"
    encoded_filename = quote(filename, safe='')
    
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )
@router.get("/clean/defects/available-lists", response_model=LocalAvailableCleanedDefectsResponse)
def get_available_cleaned_defect_lists(
    configuration_id: int = Query(...),
    dict_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """获取所有已执行本地清洗的缺陷清单列表"""
    service = LocalWashService(db)
    lists = service.get_available_cleaned_defect_lists(
        configuration_id=configuration_id,
        dict_id=dict_id
    )
    return LocalAvailableCleanedDefectsResponse(success=True, defect_lists=lists)


@router.get("/clean/defects", response_model=LocalCleanDefectsResponse)
def get_cleaned_defects_api(
    defect_list_id: int = Query(...),
    configuration_id: int = Query(...),
    dict_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """获取指定缺陷清单的本地清洗结构化结果"""
    service = LocalWashService(db)
    try:
        rows = service.get_cleaned_defects(
            defect_list_id=defect_list_id,
            configuration_id=configuration_id,
            dict_id=dict_id
        )
        d = service.get_dict(dict_id) if dict_id else service.get_latest_dict_for_configuration(configuration_id)
        
        from app.models.defect import DefectRecord
        id_list = [r.defect_record_id for r in rows]
        number_map = {}
        if id_list:
            number_map = {
                dr.id: dr.defect_number
                for dr in db.query(DefectRecord).filter(DefectRecord.id.in_(id_list)).all()
            }
            
        cleaned_out = [
            {
                "defect_record_id": r.defect_record_id,
                "defect_number": number_map.get(r.defect_record_id, ""),
                "description_cn": r.description_cn or "",
                "description_en": r.description_en or "",
                "main_component": r.main_component,
                "sub_component": r.sub_component,
                "location": r.location,
                "orientation": r.orientation,
                "status": r.status,
                "action": r.action,
            }
            for r in rows
        ]
        
        return LocalCleanDefectsResponse(
            success=True,
            defect_list_id=defect_list_id,
            configuration_id=configuration_id,
            dict_id=d.id if d else 0,
            dict_version=d.version if d else "",
            total=len(rows),
            cleaned=len(rows),
            skipped=0,
            cleaned_data=cleaned_out,
            message="成功获取已保存的本地清洗结果"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/clean/workcards/cabin-layouts")
def delete_cabin_layout_api(
    configuration_id: int = Query(...),
    cabin_layout: str = Query(...),
    source: str = Query("upload"),
    db: Session = Depends(get_db),
):
    """删除指定的客舱布局清洗数据"""
    service = LocalWashService(db)
    success = service.delete_cabin_layout(configuration_id, cabin_layout, source)
    return {"success": success, "message": "删除成功" if success else "删除失败"}


@router.delete("/clean/defects/cleaned-list")
def delete_cleaned_defect_list_api(
    defect_list_id: int = Query(...),
    configuration_id: int = Query(...),
    dict_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """删除指定缺陷清单的本地清洗结构化结果"""
    service = LocalWashService(db)
    success = service.delete_cleaned_defect_list(defect_list_id, configuration_id, dict_id)
    return {"success": success, "message": "删除成功" if success else "删除失败"}
