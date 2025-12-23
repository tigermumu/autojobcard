from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from app.models.index_data import IndexData
from app.schemas.index_data import IndexDataCreate, IndexDataUpdate, IndexDataHierarchy, IndexDataBase
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
        limit: Optional[int] = None
    ) -> List[IndexData]:
        """获取索引数据列表
        
        Args:
            limit: 如果为None，则返回所有记录；如果指定，则限制返回数量
        """
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
        
        query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        
        return query.all()

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

    def batch_import_index_data(self, configuration_id: int, file_path: str, replace: bool = True) -> dict:
        """批量导入索引数据
        
        Args:
            configuration_id: 构型ID
            file_path: Excel文件路径
            replace: 是否替换现有数据（True=先删除再导入，False=追加导入）
        """
        import os
        
        # 验证文件是否存在
        if not os.path.exists(file_path):
            raise ValueError(f"文件不存在: {file_path}")
        
        try:
            # 读取Excel文件
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except Exception as e:
                # 尝试使用xlrd引擎读取.xls文件
                try:
                    df = pd.read_excel(file_path, engine='xlrd')
                except Exception:
                    raise ValueError(f"无法读取Excel文件，请确保文件格式正确: {str(e)}")
            
            # 检查DataFrame是否为空
            if df.empty:
                raise ValueError("Excel文件中没有数据")
            
            # 如果选择替换模式，先删除现有数据
            if replace:
                deleted_count = self.db.query(IndexData).filter(
                    IndexData.configuration_id == configuration_id
                ).delete(synchronize_session=False)
            
            imported_count = 0
            error_count = 0
            errors = []
            
            # 字段映射（中文列名到数据库字段）
            field_mapping = {
                '主区域': 'main_area',
                '主部件': 'main_component',
                '一级子部件': 'first_level_subcomponent',
                '二级子部件': 'second_level_subcomponent',
                '方位': 'orientation',
                '缺陷主体': 'defect_subject',
                '缺陷描述': 'defect_description',
                '位置': 'location',
                '数量': 'quantity'
            }
            
            # 批量处理数据，提高性能
            batch_size = 100
            batch_data = []
            
            for index, row in df.iterrows():
                try:
                    # 检查是否为空行（所有必需字段都为空）
                    # 检查主区域、主部件、一级子部件、二级子部件是否全部为空
                    main_fields = ['主区域', '主部件', '一级子部件', '二级子部件']
                    is_empty_row = True
                    for field in main_fields:
                        if field in df.columns:
                            value = row.get(field)
                            if pd.notna(value) and str(value).strip():
                                is_empty_row = False
                                break
                    
                    # 如果所有主要字段都为空，跳过这一行
                    if is_empty_row:
                        continue
                    
                    # 构建数据字典，所有字段都设置为可选（None或实际值）
                    data_dict = {'configuration_id': configuration_id}
                    
                    # 遍历所有字段映射，确保所有字段都被设置（即使列不存在也设为None）
                    for chinese_field, db_field in field_mapping.items():
                        if chinese_field in df.columns:
                            value = row.get(chinese_field)
                            if pd.notna(value) and str(value).strip():
                                data_dict[db_field] = str(value).strip()
                            else:
                                data_dict[db_field] = None
                        else:
                            # 如果Excel中没有该列，也显式设置为None
                            data_dict[db_field] = None
                    
                    # 创建索引数据对象（所有字段都是可选的）
                    index_data = IndexData(**data_dict)
                    batch_data.append(index_data)
                    
                    # 批量提交以提高性能
                    if len(batch_data) >= batch_size:
                        self.db.add_all(batch_data)
                        self.db.commit()
                        imported_count += len(batch_data)
                        batch_data = []
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"行 {index + 2}: {str(e)}"  # +2 因为Excel行号从1开始，且第1行是表头
                    errors.append(error_msg)
                    # 如果错误太多，提前终止
                    if error_count > 100:
                        errors.append(f"... 错误过多，已停止处理")
                        break
            
            # 提交剩余的数据
            if batch_data:
                self.db.add_all(batch_data)
                self.db.commit()
                imported_count += len(batch_data)
            
            return {
                "message": "批量导入完成",
                "imported_count": imported_count,
                "error_count": error_count,
                "errors": errors[:50] if len(errors) > 50 else errors  # 限制错误信息数量
            }
            
        except ValueError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise Exception(f"导入失败: {str(e)}")

    def replace_all_index_data(self, configuration_id: int, data_list: List[IndexDataBase]) -> int:
        """
        原子性地替换指定构型下的所有索引数据。
        先删除，再新增，在同一个事务中进行。
        返回新增的记录数量。
        """
        try:
            # 1. 删除现有数据
            self.db.query(IndexData).filter(IndexData.configuration_id == configuration_id).delete(synchronize_session=False)
            
            # 2. 批量准备新数据对象
            new_records = []
            for item in data_list:
                # 转换 Pydantic model 为 dict，排除不需要的字段（如果有）
                record_data = item.dict(exclude_unset=True)
                record_data['configuration_id'] = configuration_id
                new_records.append(IndexData(**record_data))
            
            # 3. 批量插入
            if new_records:
                self.db.add_all(new_records)
            
            # 4. 提交事务
            self.db.commit()
            
            return len(new_records)
            
        except Exception as e:
            self.db.rollback()
            raise e

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

    def export_to_excel(self, configuration_id: int):
        """导出指定构型的索引数据到Excel"""
        try:
            # 获取所有索引数据
            all_data = self.db.query(IndexData).filter(
                IndexData.configuration_id == configuration_id
            ).all()
            
            if not all_data:
                raise ValueError("该构型下没有索引数据")
            
            # 准备Excel数据
            excel_data = []
            for item in all_data:
                excel_data.append({
                    '主区域': item.main_area,
                    '主部件': item.main_component,
                    '一级子部件': item.first_level_subcomponent or '',
                    '二级子部件': item.second_level_subcomponent or '',
                    '方位': item.orientation or '',
                    '缺陷主体': item.defect_subject or '',
                    '缺陷描述': item.defect_description or '',
                    '位置': item.location or '',
                    '数量': item.quantity or ''
                })
            
            # 创建DataFrame
            df = pd.DataFrame(excel_data)
            
            # 创建Excel文件到内存
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='索引数据')
            
            output.seek(0)
            return output
            
        except Exception as e:
            raise Exception(f"导出Excel失败: {str(e)}")
