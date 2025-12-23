from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from urllib.parse import quote
from app.core.database import get_db
from app.models.configuration import Configuration, IndexFile
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate, ConfigurationResponse, IndexFileResponse
from app.services.configuration_service import ConfigurationService
import tempfile
import os

router = APIRouter()

@router.get("/", response_model=List[ConfigurationResponse])
def get_configurations(db: Session = Depends(get_db)):
    """获取所有构型配置"""
    service = ConfigurationService(db)
    return service.get_all_configurations()

@router.get("/{configuration_id}", response_model=ConfigurationResponse)
def get_configuration(configuration_id: int, db: Session = Depends(get_db)):
    """获取特定构型配置"""
    service = ConfigurationService(db)
    configuration = service.get_configuration_by_id(configuration_id)
    if not configuration:
        raise HTTPException(status_code=404, detail="构型配置未找到")
    return configuration

@router.post("/", response_model=ConfigurationResponse)
def create_configuration(
    configuration: ConfigurationCreate,
    db: Session = Depends(get_db)
):
    """创建新的构型配置"""
    service = ConfigurationService(db)
    return service.create_configuration(configuration)

@router.put("/{configuration_id}", response_model=ConfigurationResponse)
def update_configuration(
    configuration_id: int,
    configuration: ConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """更新构型配置"""
    service = ConfigurationService(db)
    updated_config = service.update_configuration(configuration_id, configuration)
    if not updated_config:
        raise HTTPException(status_code=404, detail="构型配置未找到")
    return updated_config

@router.post("/{configuration_id}/upload-index")
def upload_index_file(
    configuration_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传索引文件"""
    service = ConfigurationService(db)
    return service.upload_index_file(configuration_id, file)

@router.get("/{configuration_id}/index-files", response_model=List[IndexFileResponse])
def get_index_files(
    configuration_id: int,
    db: Session = Depends(get_db)
):
    """获取构型的索引文件列表"""
    service = ConfigurationService(db)
    return service.get_index_files(configuration_id)

@router.get("/{configuration_id}/field-mapping/export")
def export_field_mapping_excel(configuration_id: int, db: Session = Depends(get_db)):
    """导出独立索引字段（field_mapping）到Excel"""
    try:
        service = ConfigurationService(db)
        excel_file = service.export_field_mapping_to_excel(configuration_id)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"独立索引字段_{configuration_id}_{timestamp}.xlsx"
        
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

@router.post("/{configuration_id}/field-mapping/import")
def import_field_mapping_excel(
    configuration_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """从Excel导入独立索引字段（field_mapping）"""
    tmp_file_path = None
    try:
        service = ConfigurationService(db)
        
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
        result = service.import_field_mapping_from_excel(configuration_id, tmp_file_path)
        
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
