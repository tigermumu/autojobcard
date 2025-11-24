from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.configuration import Configuration, IndexFile
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate, ConfigurationResponse, IndexFileResponse
from app.services.configuration_service import ConfigurationService

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
