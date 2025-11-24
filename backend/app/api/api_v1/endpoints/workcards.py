from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas.workcard import (
    WorkCardResponse, WorkCardCreate, WorkCardUpdate,
    CleanWorkCardRequest, CleanWorkCardResponse,
    SaveCleanedWorkCardRequest, SaveCleanedWorkCardResponse,
    WorkCardGroup
)
from app.services.workcard_service import WorkCardService

router = APIRouter()

# 注意：特殊路由（/groups, /by-group等）必须在参数路由/{workcard_id}之前定义，避免路由冲突

@router.get("/groups", response_model=List[WorkCardGroup])
def get_workcard_groups(
    is_cleaned: Optional[str] = Query(default="true", description="是否只显示已清洗的工卡分组 (true/false)"),
    db: Session = Depends(get_db)
):
    """获取工卡分组列表（按飞机号、机型、MSN、AMM/IPC EFF分组）"""
    try:
        service = WorkCardService(db)
        # 将字符串转换为布尔值
        is_cleaned_bool = True
        if is_cleaned is not None:
            is_cleaned_bool = is_cleaned.lower() in ('true', '1', 'yes', 'on')
        groups = service.get_workcard_groups(is_cleaned=is_cleaned_bool)
        
        # 验证并转换数据
        result = []
        for group in groups:
            try:
                result.append(WorkCardGroup(**group))
            except Exception as e:
                # 如果某个分组数据有问题，记录日志但继续处理其他分组
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"分组数据验证失败: {group}, 错误: {str(e)}")
                continue
        
        return result
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"获取工卡分组失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取工卡分组失败: {str(e)}")

@router.get("/by-group", response_model=List[WorkCardResponse])
def get_workcards_by_group(
    aircraft_number: Optional[str] = Query(None),
    aircraft_type: Optional[str] = Query(None),
    msn: Optional[str] = Query(None),
    amm_ipc_eff: Optional[str] = Query(None),
    configuration_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """根据识别字段获取同一组下的所有工卡"""
    service = WorkCardService(db)
    workcards = service.get_workcards_by_group(
        aircraft_number=aircraft_number,
        aircraft_type=aircraft_type,
        msn=msn,
        amm_ipc_eff=amm_ipc_eff,
        configuration_id=configuration_id
    )
    return workcards

@router.delete("/groups")
def delete_workcard_group(
    aircraft_number: Optional[str] = Query(None),
    aircraft_type: Optional[str] = Query(None),
    msn: Optional[str] = Query(None),
    amm_ipc_eff: Optional[str] = Query(None),
    configuration_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """删除整个工卡分组（根据识别字段删除该组下的所有工卡）"""
    service = WorkCardService(db)
    result = service.delete_workcard_group(
        aircraft_number=aircraft_number,
        aircraft_type=aircraft_type,
        msn=msn,
        amm_ipc_eff=amm_ipc_eff,
        configuration_id=configuration_id
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "删除失败"))
    return result

@router.get("/", response_model=List[WorkCardResponse])
def get_workcards(
    configuration_id: Optional[int] = Query(None),
    system: Optional[str] = Query(None),
    component: Optional[str] = Query(None),
    is_cleaned: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取工卡列表"""
    service = WorkCardService(db)
    return service.get_workcards(
        configuration_id=configuration_id,
        system=system,
        component=component,
        is_cleaned=is_cleaned,
        skip=skip,
        limit=limit
    )

@router.post("/", response_model=WorkCardResponse)
def create_workcard(workcard: WorkCardCreate, db: Session = Depends(get_db)):
    """创建新工卡"""
    service = WorkCardService(db)
    return service.create_workcard(workcard)

@router.get("/{workcard_id}", response_model=WorkCardResponse)
def get_workcard(workcard_id: int, db: Session = Depends(get_db)):
    """获取特定工卡"""
    service = WorkCardService(db)
    workcard = service.get_workcard_by_id(workcard_id)
    if not workcard:
        raise HTTPException(status_code=404, detail="工卡未找到")
    return workcard

@router.put("/{workcard_id}", response_model=WorkCardResponse)
def update_workcard(
    workcard_id: int,
    workcard: WorkCardUpdate,
    db: Session = Depends(get_db)
):
    """更新工卡"""
    service = WorkCardService(db)
    updated_workcard = service.update_workcard(workcard_id, workcard)
    if not updated_workcard:
        raise HTTPException(status_code=404, detail="工卡未找到")
    return updated_workcard

@router.delete("/{workcard_id}")
def delete_workcard(workcard_id: int, db: Session = Depends(get_db)):
    """删除工卡"""
    service = WorkCardService(db)
    success = service.delete_workcard(workcard_id)
    if not success:
        raise HTTPException(status_code=404, detail="工卡未找到")
    return {"message": "工卡删除成功"}

@router.post("/batch-import")
def batch_import_workcards(
    configuration_id: int,
    file_path: str,
    db: Session = Depends(get_db)
):
    """批量导入工卡数据"""
    service = WorkCardService(db)
    return service.batch_import_workcards(configuration_id, file_path)

@router.post("/clean", response_model=CleanWorkCardResponse)
def clean_workcard_data(
    request: CleanWorkCardRequest,
    db: Session = Depends(get_db)
):
    """清洗工卡数据"""
    service = WorkCardService(db)
    return service.clean_workcard_data(request.raw_data, request.configuration_id)

@router.post("/save-cleaned", response_model=SaveCleanedWorkCardResponse)
def save_cleaned_workcards(
    request: SaveCleanedWorkCardRequest,
    db: Session = Depends(get_db)
):
    """
    保存清洗后的工卡数据到数据库
    
    将清洗完成的工卡数据保存为标准工卡数据库的单机构型数据表，
    使用飞机号、机型、MSN、AMM/IPC EFF作为识别标志
    """
    service = WorkCardService(db)
    result = service.save_cleaned_workcards(
        cleaned_data=request.cleaned_data,
        configuration_id=request.configuration_id,
        aircraft_number=request.aircraft_number,
        aircraft_type=request.aircraft_type,
        msn=request.msn,
        amm_ipc_eff=request.amm_ipc_eff
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "保存失败"))
    
    return SaveCleanedWorkCardResponse(
        success=result["success"],
        saved_count=result["saved_count"],
        total_count=result["total_count"],
        skipped_count=result["skipped_count"],
        errors=result["errors"],
        message=result["message"]
    )
