from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from app.models.index_data import IndexData
from app.schemas.index_data import IndexDataCreate, IndexDataUpdate, IndexDataHierarchy
import pandas as pd
import os

class IndexDataService:
    def __init__(self, db: Session):
        self.db = db

    def get_index_data(
        self,
        configuration_id: Optional[int] = None,
        main_area: Optional[str] = None,
        main_component: Optional[str] = None,
        first_level_subcomponent: Optional[str] = None,
        second_level_subcomponent: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[IndexData]:
        """获取索引数据列表"""
        query = self.db.query(IndexData)
        
        if configuration_id:
            query = query.filter(IndexData.configuration_id == configuration_id)
        if main_area:
            query = query.filter(IndexData.main_area == main_area)
        if main_component:
            query = query.filter(IndexData.main_component == main_component)
        if first_level_subcomponent:
            query = query.filter(IndexData.first_level_subcomponent == first_level_subcomponent)
        if second_level_subcomponent:
            query = query.filter(IndexData.second_level_subcomponent == second_level_subcomponent)
        
        return query.offset(skip).limit(limit).all()

    def get_index_data_by_id(self, index_data_id: int) -> Optional[IndexData]:
        """根据ID获取索引数据"""
        return self.db.query(IndexData).filter(IndexData.id == index_data_id).first()

    def create_index_data(self, index_data: IndexDataCreate) -> IndexData:
        """创建新的索引数据"""
        db_index_data = IndexData(
            main_area=index_data.main_area,
            main_component=index_data.main_component,
            first_level_subcomponent=index_data.first_level_subcomponent,
            second_level_subcomponent=index_data.second_level_subcomponent,
            orientation=index_data.orientation,
            defect_subject=index_data.defect_subject,
            defect_description=index_data.defect_description,
            location=index_data.location,
            quantity=index_data.quantity,
            configuration_id=index_data.configuration_id
        )
        self.db.add(db_index_data)
        self.db.commit()
        self.db.refresh(db_index_data)
        return db_index_data

    def update_index_data(self, index_data_id: int, index_data: IndexDataUpdate) -> Optional[IndexData]:
        """更新索引数据"""
        db_index_data = self.get_index_data_by_id(index_data_id)
        if not db_index_data:
            return None
        
        update_data = index_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_index_data, field, value)
        
        self.db.commit()
        self.db.refresh(db_index_data)
        return db_index_data

    def delete_index_data(self, index_data_id: int) -> bool:
        """删除索引数据"""
        index_data = self.get_index_data_by_id(index_data_id)
        if not index_data:
            return False
        
        self.db.delete(index_data)
        self.db.commit()
        return True

    def get_hierarchy_data(self, configuration_id: int) -> List[IndexDataHierarchy]:
        """获取层级结构数据"""
        # 获取所有数据
        all_data = self.db.query(IndexData).filter(
            IndexData.configuration_id == configuration_id
        ).all()
        
        # 按主区域分组
        hierarchy = {}
        for data in all_data:
            if data.main_area not in hierarchy:
                hierarchy[data.main_area] = {}
            
            if data.main_component not in hierarchy[data.main_area]:
                hierarchy[data.main_area][data.main_component] = {}
            
            if data.first_level_subcomponent not in hierarchy[data.main_area][data.main_component]:
                hierarchy[data.main_area][data.main_component][data.first_level_subcomponent] = []
            
            hierarchy[data.main_area][data.main_component][data.first_level_subcomponent].append({
                "id": data.id,
                "second_level_subcomponent": data.second_level_subcomponent,
                "orientation": data.orientation,
                "defect_subject": data.defect_subject,
                "defect_description": data.defect_description,
                "location": data.location,
                "quantity": data.quantity
            })
        
        # 转换为响应格式
        result = []
        for main_area, main_components in hierarchy.items():
            main_components_list = []
            for main_component, first_level_components in main_components.items():
                first_level_list = []
                for first_level, second_level_items in first_level_components.items():
                    first_level_list.append({
                        "name": first_level,
                        "second_level_subcomponents": second_level_items
                    })
                
                main_components_list.append({
                    "name": main_component,
                    "first_level_subcomponents": first_level_list
                })
            
            result.append({
                "main_area": main_area,
                "main_components": main_components_list
            })
        
        return result

    def get_unique_values(self, field: str, configuration_id: Optional[int] = None) -> List[str]:
        """获取指定字段的唯一值"""
        query = self.db.query(getattr(IndexData, field)).distinct()
        
        if configuration_id:
            query = query.filter(IndexData.configuration_id == configuration_id)
        
        results = query.all()
        return [result[0] for result in results if result[0] is not None]

    def batch_import_index_data(self, configuration_id: int, file_path: str) -> dict:
        """批量导入索引数据"""
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 验证必需字段
            required_fields = [
                '主区域', '主部件', '一级子部件', '二级子部件'
            ]
            
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                return {
                    "message": f"缺少必需字段: {', '.join(missing_fields)}",
                    "imported_count": 0,
                    "error_count": 0,
                    "errors": [f"缺少字段: {', '.join(missing_fields)}"]
                }
            
            imported_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    index_data = IndexData(
                        main_area=str(row.get('主区域', '')),
                        main_component=str(row.get('主部件', '')),
                        first_level_subcomponent=str(row.get('一级子部件', '')),
                        second_level_subcomponent=str(row.get('二级子部件', '')),
                        orientation=str(row.get('方位', '')) if pd.notna(row.get('方位')) else None,
                        defect_subject=str(row.get('缺陷主体', '')) if pd.notna(row.get('缺陷主体')) else None,
                        defect_description=str(row.get('缺陷描述', '')) if pd.notna(row.get('缺陷描述')) else None,
                        location=str(row.get('位置', '')) if pd.notna(row.get('位置')) else None,
                        quantity=str(row.get('数量', '')) if pd.notna(row.get('数量')) else None,
                        configuration_id=configuration_id
                    )
                    self.db.add(index_data)
                    imported_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"行 {index + 1}: {str(e)}")
            
            self.db.commit()
            
            return {
                "message": "批量导入完成",
                "imported_count": imported_count,
                "error_count": error_count,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "message": f"导入失败: {str(e)}",
                "imported_count": 0,
                "error_count": 0,
                "errors": [str(e)]
            }

    def get_statistics(self, configuration_id: int) -> dict:
        """获取索引数据统计信息"""
        total_count = self.db.query(IndexData).filter(
            IndexData.configuration_id == configuration_id
        ).count()
        
        main_areas = self.db.query(IndexData.main_area).filter(
            IndexData.configuration_id == configuration_id
        ).distinct().count()
        
        main_components = self.db.query(IndexData.main_component).filter(
            IndexData.configuration_id == configuration_id
        ).distinct().count()
        
        first_level_subcomponents = self.db.query(IndexData.first_level_subcomponent).filter(
            IndexData.configuration_id == configuration_id
        ).distinct().count()
        
        second_level_subcomponents = self.db.query(IndexData.second_level_subcomponent).filter(
            IndexData.configuration_id == configuration_id
        ).distinct().count()
        
        return {
            "total_count": total_count,
            "main_areas": main_areas,
            "main_components": main_components,
            "first_level_subcomponents": first_level_subcomponents,
            "second_level_subcomponents": second_level_subcomponents
        }



