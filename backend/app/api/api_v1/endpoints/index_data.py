from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from urllib.parse import quote
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
    limit: Optional[int] = Query(None, ge=1, le=100000, description="返回的记录数，不指定则返回所有记录"),
    db: Session = Depends(get_db)
):
    """获取索引数据列表（不指定limit则返回所有记录）"""
    service = IndexDataService(db)
    return service.get_index_data(
        configuration_id=configuration_id,
        main_area=main_area,
        main_component=main_component,
        first_level_subcomponent=first_level_subcomponent,
        second_level_subcomponent=second_level_subcomponent,
        skip=skip,
        limit=limit  # None表示返回所有记录
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
    replace: bool = Query(True, description="是否替换现有数据（True=替换，False=追加）"),
    db: Session = Depends(get_db)
):
    """批量导入索引数据（默认替换模式）"""
    import tempfile
    import os
    
    tmp_file_path = None
    try:
        service = IndexDataService(db)
        
        # 验证文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.xlsx', '.xls']:
            raise HTTPException(status_code=400, detail="只支持 .xlsx 或 .xls 格式的文件")
        
        # 保存上传的文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = file.file.read()
            if not content:
                raise HTTPException(status_code=400, detail="文件内容为空")
            tmp_file.write(content)
            tmp_file.flush()
            tmp_file_path = tmp_file.name
        
        # 执行导入
        result = service.batch_import_index_data(configuration_id, tmp_file_path, replace=replace)
        
        # 检查导入结果
        if result.get("error_count", 0) > 0 and result.get("imported_count", 0) == 0:
            raise HTTPException(
                status_code=400, 
                detail=f"导入失败: {result.get('message', '未知错误')}"
            )
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入过程中发生错误: {str(e)}")
    finally:
        # 确保清理临时文件
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass  # 忽略清理文件的错误

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

@router.get("/configuration/{configuration_id}/export")
def export_index_data_excel(configuration_id: int, db: Session = Depends(get_db)):
    """导出指定构型的索引数据到Excel"""
    try:
        service = IndexDataService(db)
        excel_file = service.export_to_excel(configuration_id)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"索引数据表_{configuration_id}_{timestamp}.xlsx"
        
        # 使用URL编码处理中文文件名
        encoded_filename = quote(filename, safe='')
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
