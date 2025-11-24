from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.configuration import Configuration, IndexFile
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate
import os
import json
from datetime import datetime

class ConfigurationService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_configurations(self) -> List[Configuration]:
        """获取所有构型配置"""
        return self.db.query(Configuration).all()

    def get_configuration_by_id(self, configuration_id: int) -> Optional[Configuration]:
        """根据ID获取构型配置"""
        return self.db.query(Configuration).filter(Configuration.id == configuration_id).first()

    def create_configuration(self, configuration: ConfigurationCreate) -> Configuration:
        """创建新的构型配置"""
        # 获取所有字段，使用dict方式创建
        config_data = configuration.dict(exclude_unset=True)
        db_configuration = Configuration(**config_data)
        self.db.add(db_configuration)
        self.db.commit()
        self.db.refresh(db_configuration)
        return db_configuration

    def update_configuration(self, configuration_id: int, configuration: ConfigurationUpdate) -> Optional[Configuration]:
        """更新构型配置"""
        db_configuration = self.get_configuration_by_id(configuration_id)
        if not db_configuration:
            return None
        
        update_data = configuration.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_configuration, field, value)
        
        self.db.commit()
        self.db.refresh(db_configuration)
        return db_configuration

    def upload_index_file(self, configuration_id: int, file) -> dict:
        """上传索引文件"""
        configuration = self.get_configuration_by_id(configuration_id)
        if not configuration:
            raise ValueError("构型配置未找到")
        
        # 保存文件
        upload_dir = f"uploads/index_files/{configuration_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
        
        # 创建索引文件记录
        index_file = IndexFile(
            filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            file_type=file.content_type,
            configuration_id=configuration_id
        )
        
        self.db.add(index_file)
        self.db.commit()
        self.db.refresh(index_file)
        
        return {
            "message": "索引文件上传成功",
            "file_id": index_file.id,
            "file_path": file_path
        }

    def get_index_files(self, configuration_id: int) -> List[IndexFile]:
        """获取构型的索引文件列表"""
        return self.db.query(IndexFile).filter(IndexFile.configuration_id == configuration_id).all()

    def delete_configuration(self, configuration_id: int) -> bool:
        """删除构型配置"""
        configuration = self.get_configuration_by_id(configuration_id)
        if not configuration:
            return False
        
        self.db.delete(configuration)
        self.db.commit()
        return True

