from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas.index_data import (
    IndexDataResponse, IndexDataCreate, IndexDataUpdate, 
    IndexDataHierarchy, IndexDataImport, IndexDataReplace
)
from app.services.index_data_service import IndexDataService

router = APIRouter()

@router.get("/", response_model=List[IndexDataResponse])
def get_index_data(
    configuration_id: Optional[int] = Query(None),
    main_area: Optional[str] = Query(None),
    main_component: Optional[str] = Query(None),
    first_level_subcomponent: Optional[str] = Query(None),
    second_level_subcomponent: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取索引数据列表"""
    service = IndexDataService(db)
    return service.get_index_data(
        configuration_id=configuration_id,
        main_area=main_area,
        main_component=main_component,
        first_level_subcomponent=first_level_subcomponent,
        second_level_subcomponent=second_level_subcomponent,
        skip=skip,
        limit=limit
    )

@router.get("/{index_data_id}", response_model=IndexDataResponse)
def get_index_data_by_id(index_data_id: int, db: Session = Depends(get_db)):
    """获取特定索引数据"""
    service = IndexDataService(db)
    index_data = service.get_index_data_by_id(index_data_id)
    if not index_data:
        raise HTTPException(status_code=404, detail="索引数据未找到")
    return index_data

@router.post("/", response_model=IndexDataResponse)
def create_index_data(
    index_data: IndexDataCreate,
    db: Session = Depends(get_db)
):
    """创建新的索引数据"""
    service = IndexDataService(db)
    return service.create_index_data(index_data)

@router.put("/{index_data_id}", response_model=IndexDataResponse)
def update_index_data(
    index_data_id: int,
    index_data: IndexDataUpdate,
    db: Session = Depends(get_db)
):
    """更新索引数据"""
    service = IndexDataService(db)
    updated_index_data = service.update_index_data(index_data_id, index_data)
    if not updated_index_data:
        raise HTTPException(status_code=404, detail="索引数据未找到")
    return updated_index_data

@router.delete("/{index_data_id}")
def delete_index_data(index_data_id: int, db: Session = Depends(get_db)):
    """删除索引数据"""
    service = IndexDataService(db)
    success = service.delete_index_data(index_data_id)
    if not success:
        raise HTTPException(status_code=404, detail="索引数据未找到")
    return {"message": "索引数据删除成功"}

@router.get("/configuration/{configuration_id}/hierarchy", response_model=List[IndexDataHierarchy])
def get_hierarchy_data(configuration_id: int, db: Session = Depends(get_db)):
    """获取层级结构数据"""
    service = IndexDataService(db)
    return service.get_hierarchy_data(configuration_id)

@router.get("/configuration/{configuration_id}/unique-values")
def get_unique_values(
    configuration_id: int,
    field: str = Query(..., description="字段名"),
    db: Session = Depends(get_db)
):
    """获取指定字段的唯一值"""
    service = IndexDataService(db)
    return service.get_unique_values(field, configuration_id)

@router.post("/batch-import")
def batch_import_index_data(
    configuration_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """批量导入索引数据"""
    service = IndexDataService(db)
    
    # 保存上传的文件
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        content = file.file.read()
        tmp_file.write(content)
        tmp_file.flush()
        
        result = service.batch_import_index_data(configuration_id, tmp_file.name)
        
        # 清理临时文件
        import os
        os.unlink(tmp_file.name)
        
        return result

@router.put("/configuration/{configuration_id}/replace", response_model=dict)
def replace_all_index_data(
    configuration_id: int,
    payload: IndexDataReplace,
    db: Session = Depends(get_db)
):
    """原子性替换指定构型下的所有索引数据"""
    service = IndexDataService(db)
    count = service.replace_all_index_data(configuration_id, payload.data)
    return {"message": f"成功更新 {count} 条索引数据", "count": count}

@router.get("/configuration/{configuration_id}/statistics")
def get_statistics(configuration_id: int, db: Session = Depends(get_db)):
    """获取索引数据统计信息"""
    service = IndexDataService(db)
    return service.get_statistics(configuration_id)
