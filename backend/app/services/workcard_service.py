from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from app.models.workcard import WorkCard, WorkCardType
from app.schemas.workcard import WorkCardCreate, WorkCardUpdate
from app.services.index_data_service import IndexDataService
from app.services.configuration_service import ConfigurationService
from app.services.llm_provider_manager import get_service_for_current_model
from app.core.config import settings
import pandas as pd
import os
import asyncio
import json
import logging
from io import BytesIO

class WorkCardService:
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = get_service_for_current_model()

    def get_workcards(
        self,
        configuration_id: Optional[int] = None,
        system: Optional[str] = None,
        component: Optional[str] = None,
        is_cleaned: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[WorkCard]:
        """获取工卡列表"""
        query = self.db.query(WorkCard)
        
        if configuration_id:
            query = query.filter(WorkCard.configuration_id == configuration_id)
        if system:
            query = query.filter(WorkCard.system == system)
        if component:
            query = query.filter(WorkCard.component == component)
        if is_cleaned is not None:
            query = query.filter(WorkCard.is_cleaned == is_cleaned)
        
        return query.offset(skip).limit(limit).all()

    def get_workcard_by_id(self, workcard_id: int) -> Optional[WorkCard]:
        """根据ID获取工卡"""
        return self.db.query(WorkCard).filter(WorkCard.id == workcard_id).first()

    def get_workcard_groups(self, is_cleaned: Optional[bool] = True) -> List[Dict[str, Any]]:
        """
        获取工卡分组列表（按飞机号、机型、MSN、AMM/IPC EFF分组）
        
        返回每个分组的统计信息
        """
        from sqlalchemy import func
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            query = self.db.query(
                WorkCard.aircraft_number,
                WorkCard.aircraft_type,
                WorkCard.msn,
                WorkCard.amm_ipc_eff,
                WorkCard.configuration_id,
                func.count(WorkCard.id).label('count'),
                func.min(WorkCard.id).label('min_id')
            )
            
            if is_cleaned is not None:
                query = query.filter(WorkCard.is_cleaned == is_cleaned)
            
            # 只返回有识别字段的记录（至少有一个识别字段不为空）
            query = query.filter(
                or_(
                    WorkCard.aircraft_number.isnot(None),
                    WorkCard.aircraft_type.isnot(None),
                    WorkCard.msn.isnot(None),
                    WorkCard.amm_ipc_eff.isnot(None)
                )
            )
            
            # 按识别字段分组
            results = query.group_by(
                WorkCard.aircraft_number,
                WorkCard.aircraft_type,
                WorkCard.msn,
                WorkCard.amm_ipc_eff,
                WorkCard.configuration_id
            ).all()
            
            logger.info(f"查询到 {len(results)} 个分组")
            
            groups = []
            for result in results:
                # 确保configuration_id不为None
                config_id = result.configuration_id
                if config_id is None:
                    logger.warning(f"分组配置ID为None，使用默认值0: {result}")
                    config_id = 0
                
                group_data = {
                    'aircraft_number': result.aircraft_number if result.aircraft_number else '',
                    'aircraft_type': result.aircraft_type if result.aircraft_type else '',
                    'msn': result.msn if result.msn else '',
                    'amm_ipc_eff': result.amm_ipc_eff if result.amm_ipc_eff else '',
                    'configuration_id': int(config_id),
                    'count': int(result.count),
                    'min_id': int(result.min_id)
                }
                groups.append(group_data)
            
            logger.info(f"返回 {len(groups)} 个分组")
            return groups
            
        except Exception as e:
            logger.error(f"获取工卡分组失败: {str(e)}", exc_info=True)
            raise

    def delete_workcard_group(
        self,
        aircraft_number: Optional[str] = None,
        aircraft_type: Optional[str] = None,
        msn: Optional[str] = None,
        amm_ipc_eff: Optional[str] = None,
        configuration_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        删除整个工卡分组（根据识别字段删除该组下的所有工卡）
        """
        logger = logging.getLogger(__name__)
        logger.info(f"开始删除工卡分组 - 飞机号: {aircraft_number}, 机型: {aircraft_type}, MSN: {msn}, AMM/IPC EFF: {amm_ipc_eff}")
        
        try:
            # 获取该组下的所有工卡
            workcards = self.get_workcards_by_group(
                aircraft_number=aircraft_number,
                aircraft_type=aircraft_type,
                msn=msn,
                amm_ipc_eff=amm_ipc_eff,
                configuration_id=configuration_id
            )
            
            if not workcards:
                return {
                    "success": False,
                    "message": "未找到匹配的工卡数据",
                    "deleted_count": 0
                }
            
            # 删除所有工卡
            deleted_count = 0
            for workcard in workcards:
                try:
                    self.db.delete(workcard)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除工卡 {workcard.id} 失败: {str(e)}")
            
            self.db.commit()
            
            logger.info(f"成功删除 {deleted_count} 条工卡")
            
            return {
                "success": True,
                "message": f"成功删除 {deleted_count} 条工卡",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除工卡分组失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"删除失败: {str(e)}",
                "deleted_count": 0
            }

    def get_workcards_by_group(
        self,
        aircraft_number: Optional[str] = None,
        aircraft_type: Optional[str] = None,
        msn: Optional[str] = None,
        amm_ipc_eff: Optional[str] = None,
        configuration_id: Optional[int] = None
    ) -> List[WorkCard]:
        """
        根据识别字段获取同一组下的所有工卡
        """
        query = self.db.query(WorkCard)
        
        # 构建查询条件：所有识别字段都匹配（考虑NULL值）
        conditions = []
        
        # 对于每个识别字段，如果传入的是空字符串，则匹配NULL；如果传入值，则精确匹配
        if aircraft_number is not None:
            if aircraft_number == '':
                conditions.append(
                    or_(
                        WorkCard.aircraft_number.is_(None),
                        WorkCard.aircraft_number == ''
                    )
                )
            else:
                conditions.append(WorkCard.aircraft_number == aircraft_number)
        
        if aircraft_type is not None:
            if aircraft_type == '':
                conditions.append(
                    or_(
                        WorkCard.aircraft_type.is_(None),
                        WorkCard.aircraft_type == ''
                    )
                )
            else:
                conditions.append(WorkCard.aircraft_type == aircraft_type)
        
        if msn is not None:
            if msn == '':
                conditions.append(
                    or_(
                        WorkCard.msn.is_(None),
                        WorkCard.msn == ''
                    )
                )
            else:
                conditions.append(WorkCard.msn == msn)
        
        if amm_ipc_eff is not None:
            if amm_ipc_eff == '':
                conditions.append(
                    or_(
                        WorkCard.amm_ipc_eff.is_(None),
                        WorkCard.amm_ipc_eff == ''
                    )
                )
            else:
                conditions.append(WorkCard.amm_ipc_eff == amm_ipc_eff)
        
        if configuration_id is not None:
            conditions.append(WorkCard.configuration_id == configuration_id)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        return query.order_by(WorkCard.id).all()

    def create_workcard(self, workcard: WorkCardCreate) -> WorkCard:
        """创建新工卡"""
        # 处理原始数据备份
        raw_data_json = None
        if workcard.raw_data:
            raw_data_json = json.dumps(workcard.raw_data, ensure_ascii=False)
        
        db_workcard = WorkCard(
            workcard_number=workcard.workcard_number,
            title=workcard.title,
            description=workcard.description,
            system=workcard.system,
            component=workcard.component,
            location=workcard.location,
            action=workcard.action,
            configuration_id=workcard.configuration_id,
            workcard_type_id=workcard.workcard_type_id,
            # 单机构型识别字段
            aircraft_number=workcard.aircraft_number,
            aircraft_type=workcard.aircraft_type,
            msn=workcard.msn,
            amm_ipc_eff=workcard.amm_ipc_eff,
            # 清洗后的索引字段
            main_area=workcard.main_area,
            main_component=workcard.main_component,
            first_level_subcomponent=workcard.first_level_subcomponent,
            second_level_subcomponent=workcard.second_level_subcomponent,
            orientation=workcard.orientation,
            defect_subject=workcard.defect_subject,
            defect_description=workcard.defect_description,
            location_index=workcard.location_index,
            quantity=workcard.quantity,
            # 原始数据备份
            raw_data=raw_data_json
        )
        self.db.add(db_workcard)
        self.db.commit()
        self.db.refresh(db_workcard)
        return db_workcard

    def update_workcard(self, workcard_id: int, workcard: WorkCardUpdate) -> Optional[WorkCard]:
        """更新工卡"""
        db_workcard = self.get_workcard_by_id(workcard_id)
        if not db_workcard:
            return None
        
        update_data = workcard.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_workcard, field, value)
        
        self.db.commit()
        self.db.refresh(db_workcard)
        return db_workcard

    def delete_workcard(self, workcard_id: int) -> bool:
        """删除工卡"""
        workcard = self.get_workcard_by_id(workcard_id)
        if not workcard:
            return False
        
        self.db.delete(workcard)
        self.db.commit()
        return True

    def batch_import_workcards(self, configuration_id: int, file_path: str) -> dict:
        """批量导入工卡数据"""
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            imported_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    workcard = WorkCard(
                        workcard_number=str(row.get('workcard_number', '')),
                        title=str(row.get('title', '')),
                        description=str(row.get('description', '')),
                        system=str(row.get('system', '')),
                        component=str(row.get('component', '')),
                        location=str(row.get('location', '')),
                        action=str(row.get('action', '')),
                        configuration_id=configuration_id,
                        workcard_type_id=1  # 默认工卡类型
                    )
                    self.db.add(workcard)
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

    def get_workcard_types(self) -> List[WorkCardType]:
        """获取工卡类型列表"""
        return self.db.query(WorkCardType).all()

    def create_workcard_type(self, name: str, description: str = None) -> WorkCardType:
        """创建工卡类型"""
        workcard_type = WorkCardType(name=name, description=description)
        self.db.add(workcard_type)
        self.db.commit()
        self.db.refresh(workcard_type)
        return workcard_type

    def export_workcards_to_excel(
        self,
        aircraft_number: Optional[str] = None,
        aircraft_type: Optional[str] = None,
        msn: Optional[str] = None,
        amm_ipc_eff: Optional[str] = None,
        configuration_id: Optional[int] = None
    ):
        """导出指定分组下的工卡数据到Excel"""
        try:
            # 获取该组下的所有工卡
            workcards = self.get_workcards_by_group(
                aircraft_number=aircraft_number,
                aircraft_type=aircraft_type,
                msn=msn,
                amm_ipc_eff=amm_ipc_eff,
                configuration_id=configuration_id
            )
            
            if not workcards:
                raise ValueError("该分组下没有工卡数据")
            
            # 准备Excel数据
            excel_data = []
            for item in workcards:
                excel_data.append({
                    '工卡指令号': item.workcard_number or '',
                    '标题': item.title or '',
                    '描述': item.description or '',
                    '系统': item.system or '',
                    '部件': item.component or '',
                    '位置': item.location or '',
                    '操作': item.action or '',
                    '飞机号': item.aircraft_number or '',
                    '机型': item.aircraft_type or '',
                    'MSN': item.msn or '',
                    'AMM/IPC EFF': item.amm_ipc_eff or '',
                    '主区域': item.main_area or '',
                    '主部件': item.main_component or '',
                    '一级子部件': item.first_level_subcomponent or '',
                    '二级子部件': item.second_level_subcomponent or '',
                    '方位': item.orientation or '',
                    '缺陷主体': item.defect_subject or '',
                    '缺陷描述': item.defect_description or '',
                    '位置索引': item.location_index or '',
                    '数量': item.quantity or '',
                    '是否已清洗': '是' if item.is_cleaned else '否',
                    '清洗置信度': item.cleaning_confidence or 0,
                    '清洗备注': item.cleaning_notes or '',
                })
            
            # 创建DataFrame
            df = pd.DataFrame(excel_data)
            
            # 创建Excel文件到内存
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='工卡数据')
            
            output.seek(0)
            return output
            
        except Exception as e:
            raise Exception(f"导出Excel失败: {str(e)}")

    def import_workcards_from_excel(
        self,
        file_path: str,
        aircraft_number: Optional[str] = None,
        aircraft_type: Optional[str] = None,
        msn: Optional[str] = None,
        amm_ipc_eff: Optional[str] = None,
        configuration_id: Optional[int] = None,
        replace: bool = False
    ) -> Dict[str, Any]:
        """从Excel导入工卡数据到指定分组"""
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, sheet_name=0)
            
            # 如果replace为True，先删除该分组下的所有工卡
            if replace:
                existing_workcards = self.get_workcards_by_group(
                    aircraft_number=aircraft_number,
                    aircraft_type=aircraft_type,
                    msn=msn,
                    amm_ipc_eff=amm_ipc_eff,
                    configuration_id=configuration_id
                )
                for workcard in existing_workcards:
                    self.db.delete(workcard)
                self.db.commit()
            
            # 字段名称映射（中文到英文）
            field_name_map = {
                '工卡指令号': 'workcard_number',
                '标题': 'title',
                '描述': 'description',
                '系统': 'system',
                '部件': 'component',
                '位置': 'location',
                '操作': 'action',
                '飞机号': 'aircraft_number',
                '机型': 'aircraft_type',
                'MSN': 'msn',
                'AMM/IPC EFF': 'amm_ipc_eff',
                '主区域': 'main_area',
                '主部件': 'main_component',
                '一级子部件': 'first_level_subcomponent',
                '二级子部件': 'second_level_subcomponent',
                '方位': 'orientation',
                '缺陷主体': 'defect_subject',
                '缺陷描述': 'defect_description',
                '位置索引': 'location_index',
                '数量': 'quantity',
            }
            
            imported_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # 构建工卡数据
                    workcard_data = {
                        'workcard_number': '',
                        'title': '',
                        'system': '',
                        'component': '',
                        'configuration_id': configuration_id or 1,  # 默认构型ID
                        'workcard_type_id': 1,  # 默认工卡类型
                    }
                    
                    # 映射字段
                    for col_name in df.columns:
                        col_name_str = str(col_name).strip()
                        if col_name_str in field_name_map:
                            field_key = field_name_map[col_name_str]
                            value = row[col_name]
                            if pd.notna(value):
                                workcard_data[field_key] = str(value).strip()
                    
                    # 如果没有从Excel中读取到识别字段，使用传入的参数
                    if not workcard_data.get('aircraft_number') and aircraft_number:
                        workcard_data['aircraft_number'] = aircraft_number
                    if not workcard_data.get('aircraft_type') and aircraft_type:
                        workcard_data['aircraft_type'] = aircraft_type
                    if not workcard_data.get('msn') and msn:
                        workcard_data['msn'] = msn
                    if not workcard_data.get('amm_ipc_eff') and amm_ipc_eff:
                        workcard_data['amm_ipc_eff'] = amm_ipc_eff
                    
                    # 验证必填字段
                    if not workcard_data.get('workcard_number'):
                        raise ValueError("工卡指令号不能为空")
                    if not workcard_data.get('title'):
                        raise ValueError("标题不能为空")
                    if not workcard_data.get('system'):
                        raise ValueError("系统不能为空")
                    if not workcard_data.get('component'):
                        raise ValueError("部件不能为空")
                    
                    # 创建工卡
                    workcard = WorkCard(**workcard_data)
                    self.db.add(workcard)
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"行 {index + 2}: {str(e)}")  # +2因为Excel行号从1开始，且第1行是表头
            
            # 提交事务
            self.db.commit()
            
            return {
                "message": "导入完成",
                "imported_count": imported_count,
                "error_count": error_count,
                "errors": errors
            }
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"导入Excel失败: {str(e)}")

    def clean_workcard_data(
        self, 
        raw_data: List[Dict[str, Any]], 
        configuration_id: int
    ) -> Dict[str, Any]:
        """清洗工卡数据"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"开始清洗数据，原始数据条数: {len(raw_data)}, 构型ID: {configuration_id}")
            
            # 加载构型配置和索引数据
            index_service = IndexDataService(self.db)
            config_service = ConfigurationService(self.db)
            
            # 获取索引数据（不限制数量）
            all_index_data = index_service.get_index_data(
                configuration_id=configuration_id,
                limit=10000  # 获取所有索引数据
            )
            logger.info(f"加载索引数据条数: {len(all_index_data)}")
            
            # 获取构型配置的独立对照字段
            config = config_service.get_configuration_by_id(configuration_id)
            field_mapping = config.field_mapping if config and config.field_mapping else {}
            logger.info(f"独立对照字段: {field_mapping}")
            
            # 生成独立对照字段列表
            independent_fields = {
                'orientation': field_mapping.get('orientation', []),
                'defectSubject': field_mapping.get('defectSubject', []),
                'defectDescription': field_mapping.get('defectDescription', []),
                'location': field_mapping.get('location', []),
                'quantity': field_mapping.get('quantity', [])
            }
            
            # 使用异步函数进行清洗
            cleaned_results = asyncio.run(self._batch_clean_with_qwen(
                raw_data, all_index_data, independent_fields
            ))
            logger.info(f"清洗完成，返回条数: {len(cleaned_results)}")
            
            return {
                "success": True,
                "cleaned_count": len(cleaned_results),
                "total_count": len(raw_data),
                "data": cleaned_results
            }
            
        except Exception as e:
            import traceback
            logger.error(f"清洗失败: {str(e)}, 错误详情: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"清洗失败: {str(e)}",
                "cleaned_count": 0,
                "total_count": len(raw_data),
                "data": []
            }
    
    async def _batch_clean_with_qwen(
        self,
        raw_data: List[Dict[str, Any]],
        index_data: List,
        independent_fields: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """使用Qwen批量清洗数据 - 层级递进匹配"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"开始批量清洗，数据条数: {len(raw_data)}")
        
        results = []
        
        for idx, item in enumerate(raw_data):
            try:
                # 准备描述内容 - 支持多种可能的描述字段名称
                description = (item.get('描述') or item.get('description') or 
                              item.get('工卡描述') or item.get('工卡内容') or
                              item.get('内容') or '')
                
                # 获取中文和英文描述
                description_cn = item.get('描述') or item.get('工卡描述') or item.get('内容') or ''
                description_en = item.get('description') or item.get('Description') or item.get('描述_英文') or item.get('英文描述') or item.get('description_eng') or ''
                
                # 如果没有找到描述字段，尝试使用第一个非空字符串字段
                if not description and isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str) and value.strip():
                            description = value
                            if not description_cn and ('描述' in key or '内容' in key):
                                description_cn = value
                            if not description_en and ('description' in key.lower() or 'eng' in key.lower()):
                                description_en = value
                            break
                
                if not description:
                    # 如果没有描述，添加空索引字段
                    default_index_fields = {
                        "main_area": "",
                        "main_component": "",
                        "first_level_subcomponent": "",
                        "second_level_subcomponent": "",
                        "orientation": "",
                        "defect_subject": "",
                        "defect_description": "",
                        "location": "",
                        "quantity": ""
                    }
                    item_with_index = {
                        **item,
                        **default_index_fields,
                        '工卡指令号': item.get('工卡指令号') or item.get('指令号') or item.get('WC Number') or item.get('workcard_number') or item.get('Workcard Number') or item.get('工卡号') or item.get('工卡编号') or '',
                        '工卡描述（中文）': description_cn,
                        '工卡描述（英文）': description_en
                    }
                    results.append(item_with_index)
                    continue
                
                # 使用层级递进匹配进行清洗
                logger.info(f"清洗第 {idx + 1} 条数据，描述长度: {len(description)}")
                cleaned_result = await self._clean_with_hierarchical_matching(
                    description, description_cn, description_en, index_data, independent_fields
                )
                logger.info(f"清洗结果: {cleaned_result}")
                
                # 确保 cleaned_result 包含所有9个索引字段（即使为空字符串）
                default_index_fields = {
                    "main_area": "",
                    "main_component": "",
                    "first_level_subcomponent": "",
                    "second_level_subcomponent": "",
                    "orientation": "",
                    "defect_subject": "",
                    "defect_description": "",
                    "location": "",
                    "quantity": ""
                }
                # 合并默认字段和清洗结果
                complete_cleaned_result = {**default_index_fields, **cleaned_result}
                
                # 合并原始数据和清洗后的结果，保留原始重要字段
                result_item = {
                    **item,
                    **complete_cleaned_result,  # 确保包含所有9个索引字段
                    # 确保保留工卡指令号和描述字段
                    '工卡指令号': item.get('工卡指令号') or item.get('指令号') or item.get('WC Number') or item.get('workcard_number') or item.get('Workcard Number') or item.get('工卡号') or item.get('工卡编号') or '',
                    '工卡描述（中文）': description_cn,
                    '工卡描述（英文）': description_en
                }
                results.append(result_item)
                
            except Exception as e:
                # 如果清洗失败，保留原始数据并添加空索引字段
                logger.error(f"清洗第 {idx + 1} 条数据失败: {str(e)}")
                default_index_fields = {
                    "main_area": "",
                    "main_component": "",
                    "first_level_subcomponent": "",
                    "second_level_subcomponent": "",
                    "orientation": "",
                    "defect_subject": "",
                    "defect_description": "",
                    "location": "",
                    "quantity": ""
                }
                error_item = {
                    **item,
                    **default_index_fields,
                    '工卡指令号': item.get('工卡指令号') or item.get('指令号') or item.get('WC Number') or item.get('workcard_number') or item.get('Workcard Number') or item.get('工卡号') or item.get('工卡编号') or '',
                    '工卡描述（中文）': description_cn,
                    '工卡描述（英文）': description_en,
                    '清洗错误': str(e)
                }
                results.append(error_item)
        
        logger.info(f"批量清洗完成，成功: {len(results)}")
        return results
    
    def _build_index_context(self, index_data: List, independent_fields: Dict[str, List[str]]) -> str:
        """构建索引数据上下文"""
        # 提取唯一的层级字段值
        main_areas = set()
        main_components = set()
        first_level_subs = set()
        second_level_subs = set()
        
        for idx in index_data:
            if hasattr(idx, 'main_area'):
                main_areas.add(idx.main_area)
                main_components.add(idx.main_component)
                first_level_subs.add(idx.first_level_subcomponent)
                second_level_subs.add(idx.second_level_subcomponent)
        
        # 构建上下文字符串
        context = "构型索引数据参考：\n"
        context += f"主区域: {', '.join(list(main_areas)[:10])}\n"
        context += f"主部件: {', '.join(list(main_components)[:10])}\n"
        context += f"一级子部件: {', '.join(list(first_level_subs)[:10])}\n"
        context += f"二级子部件: {', '.join(list(second_level_subs)[:10])}\n\n"
        
        # 添加独立对照字段
        context += "独立对照字段参考：\n"
        for field, values in independent_fields.items():
            if values:
                field_name_cn = {
                    'orientation': '方位',
                    'defectSubject': '缺陷主体',
                    'defectDescription': '缺陷描述',
                    'location': '位置',
                    'quantity': '数量'
                }.get(field, field)
                context += f"{field_name_cn}: {', '.join(values[:10])}\n"
        
        return context
    
    async def _clean_with_qwen(
        self, 
        description: str, 
        index_context: str,
        independent_fields: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """使用Qwen清洗单条数据"""
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info("【大模型交互 - 工卡数据清洗（旧版方法）】")
        logger.info(f"输入描述长度: {len(description)}")
        logger.info(f"输入描述内容: {description[:500]}{'...' if len(description) > 500 else ''}")
        logger.info(f"索引上下文长度: {len(index_context)}")
        logger.info(f"独立对照字段: {independent_fields}")
        logger.info("-" * 80)
        
        prompt = f"""
        {index_context}
        
        请根据上述构型索引数据和独立对照字段，对以下工卡描述进行分析和分解：
        
        原始工卡描述：
        {description}
        
        要求：
        1. 根据构型索引数据的层级字段（主区域、主部件、一级子部件、二级子部件）提取和分配相关内容
        2. 根据独立对照字段（方位、缺陷主体、缺陷描述、位置、数量）提取相关信息
        3. 按照字段名称和含义，将描述内容分解到各个字段中
        4. 如果没有相关内容，字段值为空字符串""
        5. 二级子部件的权重最高，需要最精确匹配
        6. 只能返回以下9个字段，不要添加其他字段
        
        请返回JSON格式的结果：
        {{
            "main_area": "主区域值或空字符串",
            "main_component": "主部件值或空字符串",
            "first_level_subcomponent": "一级子部件值或空字符串",
            "second_level_subcomponent": "二级子部件值或空字符串",
            "orientation": "方位值或空字符串",
            "defect_subject": "缺陷主体值或空字符串",
            "defect_description": "缺陷描述值或空字符串",
            "location": "位置值或空字符串",
            "quantity": "数量值或空字符串"
        }}
        
        重要：只返回这9个字段，不要返回原始描述或其他字段。
        """
        
        logger.info("正在调用大模型API进行清洗...")
        logger.info(f"提示词总长度: {len(prompt)} 字符")
        
        try:
            response = self.llm_service.generate_text(
                prompt, 
                system_prompt="你是一个专业的航空维修数据分析和清洗助手，擅长将非结构化的维修描述分解为标准化的结构化数据。",
                temperature=0.1,
                max_tokens=1500
            )
            
            logger.info(f"大模型API调用完成，success: {response.get('success')}, error: {response.get('error', '')}")
            
            if response["success"]:
                json_result = self.llm_service.parse_json_response(response["text"])
                if json_result["success"]:
                    result = json_result["data"]
                    logger.info("【清洗结果】")
                    logger.info(f"清洗成功 - 结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    logger.info("=" * 80)
                    return result
                else:
                    logger.warning(f"【清洗失败 - JSON解析错误】错误: {json_result.get('error', '未知错误')}")
                    logger.warning(f"原始文本前500字符: {json_result.get('raw_text', '')[:500]}")
                    logger.info("=" * 80)
                    return {}
            else:
                logger.error(f"【清洗失败 - API调用错误】错误: {response.get('error', '未知错误')}")
                logger.info("=" * 80)
                return {}
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"【清洗失败 - 异常】异常: {str(e)}")
            logger.error(f"错误详情: {error_detail}")
            logger.info("=" * 80)
            return {}
    
    def _build_hierarchical_index(self, index_data: List) -> Dict[str, Dict[str, Dict[str, List[str]]]]:
        """构建层级索引结构：主区域 -> 主部件 -> 一级子部件 -> 二级子部件列表"""
        hierarchy = {}
        
        for idx in index_data:
            main_area = idx.main_area if hasattr(idx, 'main_area') else ''
            main_component = idx.main_component if hasattr(idx, 'main_component') else ''
            first_level = idx.first_level_subcomponent if hasattr(idx, 'first_level_subcomponent') else ''
            second_level = idx.second_level_subcomponent if hasattr(idx, 'second_level_subcomponent') else ''
            
            if not main_area:
                continue
            
            if main_area not in hierarchy:
                hierarchy[main_area] = {}
            
            if main_component not in hierarchy[main_area]:
                hierarchy[main_area][main_component] = {}
            
            if first_level not in hierarchy[main_area][main_component]:
                hierarchy[main_area][main_component][first_level] = []
            
            if second_level and second_level not in hierarchy[main_area][main_component][first_level]:
                hierarchy[main_area][main_component][first_level].append(second_level)
        
        return hierarchy
    
    async def _clean_with_hierarchical_matching(
        self,
        description: str,
        description_cn: str,
        description_en: str,
        index_data: List,
        independent_fields: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """使用层级递进匹配清洗数据 - 一次性调用Qwen，通过提示词规则实现层级匹配"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info(f"【开始清洗缺陷数据】描述长度: {len(description)}")
        logger.info(f"缺陷描述内容: {description[:500]}{'...' if len(description) > 500 else ''}")
        logger.info("-" * 80)
        
        # 构建层级索引结构，用于生成提示词
        hierarchy = self._build_hierarchical_index(index_data)
        logger.info(f"索引数据层级结构: {len(hierarchy)} 个主区域")
        
        # 构建层级结构的文本描述，供大模型参考
        hierarchy_text = self._build_hierarchy_text(hierarchy)
        
        # 构建独立对照字段的JSON格式
        import json
        independent_fields_json = json.dumps({
            "orientation": independent_fields.get('orientation', []),
            "defectSubject": independent_fields.get('defectSubject', []),
            "defectDescription": independent_fields.get('defectDescription', []),
            "location": independent_fields.get('location', []),
            "quantity": independent_fields.get('quantity', [])
        }, ensure_ascii=False, indent=2)
        
        # 构建优化后的提示词（基于简化版提示词方案）
        prompt = f"""
你是一个航空维修工卡分析专家。请根据提供的索引数据表，将英文工卡描述分类为结构化的层级数据。

【核心原则 - 最重要】

⚠️ 绝对禁止：不应该在结构化的时候把不存在的词和词义也不匹配的词体现在分类中。

✅ 分类规则：
1. 词一样：分类结果中的词必须与工卡描述中的词完全一致
2. 词义相似：如果词不完全一样，但词义相似，可以使用（如BACKREST和SEAT BACK）
3. 禁止引入不存在的词：绝对不能把工卡描述中不存在的词体现在分类结果中

【常见错误示例】

❌ 错误：工卡描述"GALLEY DOOR M718 MIDDLE HINGE BROKEN"
     分类：一级子部件: DOOR FRAME（错误！工卡描述中没有"FRAME"）
✅ 正确：一级子部件: HINGE（存在）

❌ 错误：工卡描述"CABIN RH #1 DOOR FWD FRAME LINING LOWER VIEW PORT BROKEN"
     分类：一级子部件: DOOR FRAME（错误！工卡描述中没有"FRAME"）
✅ 正确：一级子部件: LINING（存在），二级子部件: VIEWPORT（VIEW PORT词义相同）

【索引表结构】

{hierarchy_text}

【独立对照字段参考】（JSON格式）：
{independent_fields_json}

【分类步骤】

1. 识别主区域：根据工卡描述中的区域标识词，在索引表中查找匹配的主区域（词一样或词义相似）
2. 识别主部件：在已匹配主区域下的主部件列表中查找匹配的主部件（词一样或词义相似）
3. 识别一级子部件：在已匹配主部件下的一级子部件列表中查找匹配的一级子部件（词一样或词义相似）
4. 识别二级子部件：在已匹配一级子部件下的二级子部件列表中查找匹配的二级子部件（词一样或词义相似）
5. 识别独立对照字段：从独立对照字段中匹配方位、缺陷主体、缺陷描述、位置、数量

【特殊处理】

1. 位置信息（M718、#1、23D等）→ 放在"location"字段，不作为部件分类
2. 型号信息（M718、M234等）→ 放在"location"字段，不作为部件分类
3. 方向词（UPPER、LOWER、MIDDLE等）：
   - 如果是部件名称的一部分（如UPPER ARMREST）→ 可以作为子部件
   - 如果只是位置描述 → 放在"location"字段

【词义相似示例】

- BACKREST ↔ SEAT BACK
- VIEW PORT ↔ VIEWPORT
- E/C ↔ ECONOMY CLASS
- F/C ↔ FIRST CLASS
- ARMREST COVER ↔ COVER（在ARMREST下）
- 驾驶舱 = Cockpit = 驾驶室
- 客舱 = Cabin = 客舱区域
- 座椅 = Seat = 座位

【工卡描述】

{description}

【输出格式】

请返回JSON格式的结果，严格按照以下格式：
{{
    "main_area": "主区域值（必须从索引表主区域中选择，词一样或词义相似）或空字符串",
    "main_component": "主部件值（必须从该主区域下的主部件列表中选择）或空字符串",
    "first_level_subcomponent": "一级子部件值（必须从该主区域->主部件下的一级子部件列表中选择）或空字符串",
    "second_level_subcomponent": "二级子部件值（必须从该主区域->主部件->一级子部件下的二级子部件列表中选择）或空字符串",
    "orientation": "方位值（从独立对照字段中选择）或空字符串",
    "defect_subject": "缺陷主体值（从独立对照字段中选择）或空字符串",
    "defect_description": "缺陷描述值（从独立对照字段中选择）或空字符串",
    "location": "位置值（位置信息、型号信息、方向词等）或空字符串",
    "quantity": "数量值（从独立对照字段中选择）或空字符串"
}}

【质量检查】

返回结果前检查：
1. ✅ 分类结果中的每个词是否都在工卡描述中存在或词义相似？
2. ✅ 是否引入了工卡描述中不存在的词？
3. ✅ 层级关系是否符合索引表的结构？
4. ✅ 位置信息是否正确分离到"location"字段？

【重要提醒】

1. 严格遵守"词一样或词义相似"原则
2. 禁止引入不存在的词
3. 位置信息和型号信息必须正确分离
4. 层级关系必须符合索引表结构
5. 只返回JSON格式，不要添加任何其他说明文字、注释或markdown标记
"""
        
        logger.info("正在调用大模型API进行清洗...")
        logger.info(f"提示词总长度: {len(prompt)} 字符")
        
        # 定义系统提示词（基于简化版提示词方案）
        system_prompt = """你是一个航空维修工卡分析专家。请严格遵守以下核心原则：
1. 词一样：分类结果中的词必须与工卡描述中的词完全一致
2. 词义相似：如果词不完全一样，但词义相似，可以使用（如BACKREST和SEAT BACK）
3. 绝对禁止引入不存在的词：绝对不能把工卡描述中不存在的词体现在分类结果中
4. 必须严格遵循层级递进关系（主区域→主部件→一级子部件→二级子部件），不能跨层级匹配"""
        
        logger.info(f"系统提示词长度: {len(system_prompt)} 字符")
        
        # 估算token数（粗略：中文1字符≈1token，英文1词≈1token）
        total_length = len(prompt) + len(system_prompt)
        estimated_input_tokens = total_length
        logger.info(f"估算输入token数: ~{estimated_input_tokens}")
        
        # LLM 上下文窗口设置（根据使用的大模型调整）
        # Qwen-plus: 通常32K tokens
        LLM_CONTEXT_WINDOW = 32000  # LLM 的上下文窗口
        available_output_tokens = LLM_CONTEXT_WINDOW - estimated_input_tokens
        
        logger.info(f"LLM上下文窗口: {LLM_CONTEXT_WINDOW} tokens")
        logger.info(f"估算可用输出token空间: ~{available_output_tokens} tokens")
        
        # 根据提示词长度动态调整max_tokens
        # 如果提示词很长，需要更多的输出token空间，但不能超过可用空间
        if estimated_input_tokens > 25000:
            logger.error(f"⚠️⚠️ 提示词过长！估算token数 {estimated_input_tokens} 接近或超过上下文窗口限制！")
            logger.error(f"⚠️⚠️ 可用输出空间仅 {available_output_tokens} tokens，可能无法生成响应！")
            max_tokens = max(1000, available_output_tokens - 1000)  # 保留1000 tokens缓冲
            logger.warning(f"⚠️ 设置max_tokens为 {max_tokens}（可能仍然不足）")
        elif estimated_input_tokens > 20000:
            logger.warning(f"⚠️ 提示词很长！估算token数 {estimated_input_tokens}")
            max_tokens = min(4000, available_output_tokens - 2000)  # 保留2000 tokens缓冲
            logger.warning(f"⚠️ 增加max_tokens到 {max_tokens}")
        elif estimated_input_tokens > 15000:
            logger.warning(f"提示词较长，估算token数 {estimated_input_tokens}")
            max_tokens = min(3000, available_output_tokens - 1000)  # 保留1000 tokens缓冲
            logger.info(f"设置max_tokens为 {max_tokens}")
        elif estimated_input_tokens > 5000:
            max_tokens = 4000  # 提示词很长时，增加输出token
            logger.warning(f"提示词较长，增加max_tokens到 {max_tokens}")
        elif estimated_input_tokens > 3000:
            max_tokens = 3000
            logger.info(f"提示词中等长度，设置max_tokens为 {max_tokens}")
        else:
            max_tokens = 2000  # 默认值
            logger.info(f"使用默认max_tokens: {max_tokens}")
        
        try:
            response = self.llm_service.generate_text(
                prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=max_tokens
            )
            
            logger.info(f"大模型API调用完成，success: {response.get('success')}, error: {response.get('error', '')}")
            
            if not response.get("success"):
                logger.error(f"大模型API调用失败: {response.get('error', '未知错误')}")
        except Exception as e:
            logger.error(f"调用大模型API时发生异常: {str(e)}", exc_info=True)
            response = {
                "success": False,
                "error": f"调用大模型API时发生异常: {str(e)}",
                "text": ""
            }
        
        # 定义默认的9个索引字段
        default_fields = {
            "main_area": "",
            "main_component": "",
            "first_level_subcomponent": "",
            "second_level_subcomponent": "",
            "orientation": "",
            "defect_subject": "",
            "defect_description": "",
            "location": "",
            "quantity": ""
        }
        
        if response.get("success"):
            logger.info("-" * 80)
            logger.info("大模型返回成功，开始解析JSON结果...")
            json_result = self.llm_service.parse_json_response(response.get("text", ""))
            if json_result.get("success"):
                cleaned_data = json_result.get("data", {}) if json_result.get("data") else {}
                result = {**default_fields, **cleaned_data}
                logger.info(f"【清洗结果】")
                logger.info(f"主区域: {result.get('main_area', '')}")
                logger.info(f"主部件: {result.get('main_component', '')}")
                logger.info(f"一级子部件: {result.get('first_level_subcomponent', '')}")
                logger.info(f"二级子部件: {result.get('second_level_subcomponent', '')}")
                logger.info(f"方位: {result.get('orientation', '')}")
                logger.info(f"缺陷主体: {result.get('defect_subject', '')}")
                logger.info(f"缺陷描述: {result.get('defect_description', '')}")
                logger.info(f"位置: {result.get('location', '')}")
                logger.info(f"数量: {result.get('quantity', '')}")
                logger.info("=" * 80)
                return result
            else:
                logger.warning(f"JSON解析失败: {json_result.get('error', '未知错误')}")
                logger.warning(f"原始文本前500字符: {json_result.get('raw_text', '')[:500]}")
                # 添加提取到的JSON字符串日志
                extracted_json = json_result.get('extracted_json', '')
                if extracted_json:
                    logger.warning(f"提取到的JSON字符串长度: {len(extracted_json)}")
                    logger.warning(f"提取到的JSON字符串前500字符: {extracted_json[:500]}")
                    logger.warning(f"提取到的JSON字符串后100字符: {extracted_json[-100:]}")
                    # 检查括号匹配
                    open_braces = extracted_json.count('{')
                    close_braces = extracted_json.count('}')
                    logger.warning(f"提取到的JSON括号检查 - 开括号: {open_braces}, 闭括号: {close_braces}")
                logger.info("=" * 80)
                return default_fields
        else:
            logger.error(f"大模型调用失败，返回默认空字段。错误信息: {response.get('error', '未知错误')}")
            logger.info("=" * 80)
            return default_fields
    
    def _build_hierarchy_text(self, hierarchy: Dict[str, Dict[str, Dict[str, List[str]]]]) -> str:
        """构建层级结构的文本描述（JSON格式，更紧凑）"""
        import json
        
        # 1. 所有主区域列表（JSON格式）
        main_areas = list(hierarchy.keys())
        main_areas_json = json.dumps(main_areas, ensure_ascii=False)
        
        # 2. 主区域与主部件对应关系（JSON格式）
        area_component_map = {}
        for main_area, components in hierarchy.items():
            area_component_map[main_area] = list(components.keys())
        area_component_json = json.dumps(area_component_map, ensure_ascii=False)
        
        # 3. 完整层级结构（JSON格式，使用indent=1减少空间占用）
        # 格式：{"主区域": {"主部件": {"一级子部件": ["二级子部件1", "二级子部件2", ...]}}}
        hierarchy_json = json.dumps(hierarchy, ensure_ascii=False, indent=1)
        
        # 构建提示词文本（使用JSON格式，更紧凑）
        text = "【构型索引数据】（JSON格式，嵌套结构表示层级关系：主区域→主部件→一级子部件→二级子部件列表）\n\n"
        text += "1. 所有主区域列表：\n"
        text += main_areas_json + "\n\n"
        
        text += "2. 主区域与主部件对应关系：\n"
        text += area_component_json + "\n\n"
        
        text += "3. 完整层级结构（JSON格式，嵌套结构表示层级关系）：\n"
        text += hierarchy_json + "\n\n"
        
        text += "说明：上述JSON格式中，嵌套的键值对表示层级关系。例如 {\"驾驶舱\": {\"座椅\": {\"安全带\": [\"xxx\", \"yyy\"]}}} 表示：\n"
        text += "- 主区域：驾驶舱\n"
        text += "- 主部件：座椅\n"
        text += "- 一级子部件：安全带\n"
        text += "- 二级子部件：xxx, yyy\n"
        
        return text

    def save_cleaned_workcards(
        self,
        cleaned_data: List[Dict[str, Any]],
        configuration_id: int,
        aircraft_number: Optional[str] = None,
        aircraft_type: Optional[str] = None,
        msn: Optional[str] = None,
        amm_ipc_eff: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        保存清洗后的工卡数据到数据库
        
        参数:
            cleaned_data: 清洗后的工卡数据列表
            configuration_id: 构型配置ID
            aircraft_number: 飞机号（例如B-XXXX）
            aircraft_type: 机型（如果不提供，将从configuration获取）
            msn: MSN（如果不提供，将从configuration获取）
            amm_ipc_eff: AMM/IPC EFF（如果不提供，将从configuration获取）
        
        返回:
            包含保存结果的字典
        """
        logger = logging.getLogger(__name__)
        logger.info(f"开始保存清洗后的工卡数据，数据条数: {len(cleaned_data)}, 构型ID: {configuration_id}")
        
        try:
            # 获取构型配置，用于获取默认的识别字段
            config_service = ConfigurationService(self.db)
            config = config_service.get_configuration_by_id(configuration_id)
            
            if not config:
                return {
                    "success": False,
                    "message": f"构型配置未找到，ID: {configuration_id}",
                    "saved_count": 0,
                    "total_count": len(cleaned_data),
                    "skipped_count": 0,
                    "errors": [f"构型配置未找到，ID: {configuration_id}"]
                }
            
            # 确定识别字段的值（优先使用传入的参数，否则使用configuration的值）
            final_aircraft_type = aircraft_type or config.aircraft_type or ""
            final_msn = msn or config.msn or ""
            final_amm_ipc_eff = amm_ipc_eff or config.amm_ipc_eff or ""
            
            logger.info(f"识别字段 - 飞机号: {aircraft_number}, 机型: {final_aircraft_type}, MSN: {final_msn}, AMM/IPC EFF: {final_amm_ipc_eff}")
            
            # 获取默认工卡类型（假设存在ID为1的工卡类型）
            workcard_type_id = 1
            workcard_type = self.db.query(WorkCardType).filter(WorkCardType.id == workcard_type_id).first()
            if not workcard_type:
                # 如果不存在，创建一个默认类型
                workcard_type = WorkCardType(name="标准工卡", description="标准工卡类型")
                self.db.add(workcard_type)
                self.db.commit()
                self.db.refresh(workcard_type)
                workcard_type_id = workcard_type.id
            
            saved_count = 0
            skipped_count = 0
            errors = []
            
            # 批量保存清洗后的数据
            for idx, item in enumerate(cleaned_data):
                try:
                    # 提取工卡编号（支持多种可能的字段名）
                    workcard_number = (
                        item.get('工卡指令号') or 
                        item.get('指令号') or 
                        item.get('WC Number') or 
                        item.get('workcard_number') or 
                        item.get('Workcard Number') or 
                        item.get('工卡号') or 
                        item.get('工卡编号') or 
                        f"WC-{idx+1}"
                    )
                    
                    # 检查是否已存在相同工卡编号和识别字段的记录
                    existing_query = self.db.query(WorkCard).filter(
                        WorkCard.workcard_number == workcard_number,
                        WorkCard.configuration_id == configuration_id
                    )
                    if aircraft_number:
                        existing_query = existing_query.filter(WorkCard.aircraft_number == aircraft_number)
                    if final_aircraft_type:
                        existing_query = existing_query.filter(WorkCard.aircraft_type == final_aircraft_type)
                    if final_msn:
                        existing_query = existing_query.filter(WorkCard.msn == final_msn)
                    if final_amm_ipc_eff:
                        existing_query = existing_query.filter(WorkCard.amm_ipc_eff == final_amm_ipc_eff)
                    
                    existing = existing_query.first()
                    if existing:
                        skipped_count += 1
                        logger.debug(f"跳过已存在的工卡: {workcard_number}")
                        continue
                    
                    # 提取标题和描述
                    title = (
                        item.get('title') or 
                        item.get('标题') or 
                        item.get('工卡标题') or 
                        item.get('工卡指令号') or
                        workcard_number
                    )
                    if not title or title == "":
                        title = workcard_number
                    
                    description = (
                        item.get('description') or 
                        item.get('描述') or 
                        item.get('工卡描述') or 
                        item.get('工卡描述（中文）') or 
                        item.get('工卡描述（英文）') or
                        ""
                    )
                    
                    # 提取系统和部件（如果没有，使用清洗后的索引字段）
                    system = (
                        item.get('system') or 
                        item.get('系统') or 
                        item.get('main_area') or 
                        ""
                    )
                    if not system or system == "":
                        system = "未分类"
                    
                    component = (
                        item.get('component') or 
                        item.get('部件') or 
                        item.get('main_component') or 
                        ""
                    )
                    if not component or component == "":
                        component = "未分类"
                    
                    # 提取位置和动作
                    location = item.get('location') or item.get('位置') or None
                    action = item.get('action') or item.get('动作') or item.get('执行动作') or None
                    
                    # 提取清洗后的索引字段（9个字段）
                    main_area = item.get('main_area') or ""
                    main_component = item.get('main_component') or ""
                    first_level_subcomponent = item.get('first_level_subcomponent') or ""
                    second_level_subcomponent = item.get('second_level_subcomponent') or ""
                    orientation = item.get('orientation') or ""
                    defect_subject = item.get('defect_subject') or ""
                    defect_description = item.get('defect_description') or ""
                    # location_index 优先使用清洗后的location索引字段，其次使用原始location
                    location_index = item.get('location_index') or item.get('location') or ""
                    quantity = item.get('quantity') or ""
                    
                    # 准备原始数据备份（JSON格式）
                    raw_data_json = json.dumps(item, ensure_ascii=False)
                    
                    # 辅助函数：安全地strip字符串
                    def safe_strip(value):
                        if value is None:
                            return None
                        if isinstance(value, str):
                            stripped = value.strip()
                            return stripped if stripped else None
                        return str(value).strip() if str(value).strip() else None
                    
                    # 确保必填字段不为空
                    if not title or (isinstance(title, str) and title.strip() == ""):
                        title = workcard_number
                    if not system or (isinstance(system, str) and system.strip() == ""):
                        system = "未分类"
                    if not component or (isinstance(component, str) and component.strip() == ""):
                        component = "未分类"
                    
                    # 创建工卡记录
                    workcard = WorkCard(
                        workcard_number=str(workcard_number).strip() if workcard_number else "",
                        title=str(title).strip() if title else workcard_number,
                        description=safe_strip(description),
                        system=str(system).strip() if system else "未分类",
                        component=str(component).strip() if component else "未分类",
                        location=safe_strip(location),
                        action=safe_strip(action),
                        configuration_id=configuration_id,
                        workcard_type_id=workcard_type_id,
                        # 单机构型识别字段
                        aircraft_number=safe_strip(aircraft_number),
                        aircraft_type=safe_strip(final_aircraft_type),
                        msn=safe_strip(final_msn),
                        amm_ipc_eff=safe_strip(final_amm_ipc_eff),
                        # 清洗后的索引字段
                        main_area=safe_strip(main_area),
                        main_component=safe_strip(main_component),
                        first_level_subcomponent=safe_strip(first_level_subcomponent),
                        second_level_subcomponent=safe_strip(second_level_subcomponent),
                        orientation=safe_strip(orientation),
                        defect_subject=safe_strip(defect_subject),
                        defect_description=safe_strip(defect_description),
                        location_index=safe_strip(location_index),
                        quantity=safe_strip(quantity),
                        # 原始数据备份
                        raw_data=raw_data_json,
                        # 清洗状态
                        is_cleaned=True,
                        cleaning_confidence=1.0,
                        cleaning_notes="已保存清洗后的数据"
                    )
                    
                    self.db.add(workcard)
                    # 立即提交每条记录，确保独立性
                    try:
                        self.db.commit()
                        saved_count += 1
                        
                        # 每100条记录一次进度
                        if saved_count % 100 == 0:
                            logger.info(f"已保存 {saved_count} 条工卡数据")
                    except Exception as commit_error:
                        # 提交失败，回滚当前事务
                        self.db.rollback()
                        raise commit_error
                    
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    error_msg = f"第 {idx + 1} 条数据保存失败: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"{error_msg}\n详细信息: {error_detail}")
                    # 打印完整的错误信息以便调试
                    logger.error(f"数据项内容: {item}")
                    
                    # 确保回滚当前失败的事务，不影响下一条记录
                    try:
                        self.db.rollback()
                    except:
                        pass
                    
                    continue
            
            # 所有记录处理完成（每条都已立即提交）
            logger.info(f"保存完成 - 成功: {saved_count}, 跳过: {skipped_count}, 错误: {len(errors)}")
            
            return {
                "success": True,
                "message": f"成功保存 {saved_count} 条工卡数据，跳过 {skipped_count} 条，错误 {len(errors)} 条",
                "saved_count": saved_count,
                "total_count": len(cleaned_data),
                "skipped_count": skipped_count,
                "errors": errors
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"保存清洗后数据失败: {str(e)}\n详细信息: {error_detail}", exc_info=True)
            return {
                "success": False,
                "message": f"保存失败: {str(e)}",
                "saved_count": 0,
                "total_count": len(cleaned_data),
                "skipped_count": 0,
                "errors": [f"{str(e)}: {error_detail}"]
            }

