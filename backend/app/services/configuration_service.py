from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.configuration import Configuration, IndexFile
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate
import os
import json
from datetime import datetime
import pandas as pd
from io import BytesIO
from sqlalchemy.exc import IntegrityError

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
        # name 是唯一键；先查重给出友好提示，避免直接抛出 sqlite IntegrityError
        existing = (
            self.db.query(Configuration)
            .filter(Configuration.name == configuration.name)
            .first()
        )
        if existing:
            raise ValueError(f"构型名称已存在：{configuration.name}（请修改名称或在列表中编辑该构型）")

        # 获取所有字段，使用dict方式创建
        config_data = configuration.dict(exclude_unset=True)
        db_configuration = Configuration(**config_data)
        self.db.add(db_configuration)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            # 兜底：并发/竞态导致的重复
            raise ValueError(f"构型名称已存在：{configuration.name}（请修改名称或在列表中编辑该构型）")
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

    def export_field_mapping_to_excel(self, configuration_id: int):
        """导出独立索引字段（field_mapping）到Excel"""
        configuration = self.get_configuration_by_id(configuration_id)
        if not configuration:
            raise ValueError("构型配置未找到")
        
        # 获取field_mapping，如果没有则使用空字典
        field_mapping = configuration.field_mapping or {}
        
        # 字段名称映射（中文显示名）
        field_name_map = {
            'orientation': '方位',
            'defectSubject': '缺陷主体',
            'defectDescription': '缺陷描述',
            'location': '位置',
            'quantity': '数量'
        }
        
        # 准备Excel数据 - 每个字段一列，值按行展开
        max_rows = 0
        excel_data = {}
        
        for field_key, field_name in field_name_map.items():
            values = field_mapping.get(field_key, [])
            if isinstance(values, list):
                excel_data[field_name] = values
                max_rows = max(max_rows, len(values))
            else:
                excel_data[field_name] = []
        
        # 确保所有列长度一致（用空字符串填充）
        for field_name in excel_data.keys():
            while len(excel_data[field_name]) < max_rows:
                excel_data[field_name].append('')
        
        # 创建DataFrame
        df = pd.DataFrame(excel_data)
        
        # 创建Excel文件到内存
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='独立索引字段')
        
        output.seek(0)
        return output

    def import_field_mapping_from_excel(self, configuration_id: int, file_path: str) -> Dict[str, Any]:
        """从Excel导入独立索引字段（field_mapping）"""
        configuration = self.get_configuration_by_id(configuration_id)
        if not configuration:
            raise ValueError("构型配置未找到")
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, sheet_name=0)
            
            # 字段名称映射（中文到英文）
            field_name_map = {
                '方位': 'orientation',
                '缺陷主体': 'defectSubject',
                '缺陷描述': 'defectDescription',
                '位置': 'location',
                '数量': 'quantity'
            }
            
            # 初始化field_mapping
            field_mapping = {}
            
            # 处理每一列
            for col_name in df.columns:
                col_name_str = str(col_name).strip()
                if col_name_str in field_name_map:
                    field_key = field_name_map[col_name_str]
                    # 获取该列的所有非空值
                    values = df[col_name].dropna().astype(str).str.strip()
                    # 过滤空字符串
                    values = values[values != ''].tolist()
                    # 去重
                    values = list(dict.fromkeys(values))  # 保持顺序的去重
                    field_mapping[field_key] = values
                else:
                    # 尝试直接匹配英文字段名
                    if col_name_str in field_name_map.values():
                        field_key = col_name_str
                        values = df[col_name].dropna().astype(str).str.strip()
                        values = values[values != ''].tolist()
                        values = list(dict.fromkeys(values))
                        field_mapping[field_key] = values
            
            # 确保所有字段都存在（即使为空列表）
            for field_key in field_name_map.values():
                if field_key not in field_mapping:
                    field_mapping[field_key] = []
            
            # 更新配置
            configuration.field_mapping = field_mapping
            self.db.commit()
            self.db.refresh(configuration)
            
            # 统计导入的数据
            total_values = sum(len(v) for v in field_mapping.values())
            
            return {
                "message": "导入成功",
                "field_mapping": field_mapping,
                "total_values": total_values
            }
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"导入Excel失败: {str(e)}")