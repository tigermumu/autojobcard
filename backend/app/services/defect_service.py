from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from app.models.defect import DefectList, DefectRecord
from app.models.defect_cleaned import DefectCleanedData
from app.schemas.defect import DefectListCreate, DefectListUpdate, DefectRecordCreate, DefectRecordUpdate
import pandas as pd
import numpy as np
import os
import csv
import io
from datetime import datetime

class DefectService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _extract_english_description(raw: Dict[str, Any]) -> str:
        if not isinstance(raw, dict):
            return ""

        candidate_keys = [
            "description_en",
            "descriptionEng",
            "英文描述",
            "工卡描述（英文）",
            "工卡描述(英文)",
            "工卡描述英文",
            "Description",
            "description",
        ]

        for key in candidate_keys:
            # 同时也尝试不同的大小写和全角/半角括号变体
            variants = {
                key, key.lower(), key.upper(),
                key.replace("（", "(").replace("）", ")"),
                key.replace("(", "（").replace(")", "）")
            }
            for variant in variants:
                value = raw.get(variant)
                if value and isinstance(value, (str, bytes)):
                    val_str = value.decode('utf-8') if isinstance(value, bytes) else value
                    stripped = val_str.strip()
                    if stripped:
                        return stripped

        for key, value in raw.items():
            if not value or not isinstance(value, (str, bytes)):
                continue
            key_str = str(key).lower()
            if "英文" in str(key) or "english" in key_str:
                val_str = value.decode('utf-8') if isinstance(value, bytes) else value
                stripped = val_str.strip()
                if stripped:
                    return stripped

        return ""

    @staticmethod
    def _extract_chinese_description(raw: Dict[str, Any]) -> str:
        if not isinstance(raw, dict):
            return ""

        candidate_keys = [
            "description_cn",
            "descriptionChn",
            "中文描述",
            "工卡描述（中文）",
            "工卡描述(中文)",
            "工卡描述中文",
            "描述",
            "工卡描述",
            "title",
            "Title",
        ]

        for key in candidate_keys:
            variants = {
                key, key.lower(), key.upper(),
                key.replace("（", "(").replace("）", ")"),
                key.replace("(", "（").replace(")", "）")
            }
            for variant in variants:
                value = raw.get(variant)
                if value and isinstance(value, (str, bytes)):
                    val_str = value.decode('utf-8') if isinstance(value, bytes) else value
                    stripped = val_str.strip()
                    if stripped:
                        return stripped

        for key, value in raw.items():
            if not value or not isinstance(value, (str, bytes)):
                continue
            key_str = str(key).lower()
            if "中文" in str(key) or "chinese" in key_str or "描述" in str(key):
                val_str = value.decode('utf-8') if isinstance(value, bytes) else value
                stripped = val_str.strip()
                if stripped:
                    return stripped

        return ""

    @staticmethod
    def _extract_defect_number(raw: Dict[str, Any]) -> str:
        if not isinstance(raw, dict):
            return ""

        candidate_keys = [
            "defect_number",
            "defectNumber",
            "缺陷编号",
            "编号",
            "No.",
            "Number",
        ]

        for key in candidate_keys:
            for variant in {key, key.lower(), key.upper()}:
                value = raw.get(variant)
                if value:
                    return str(value).strip()

        return ""

    def get_defect_lists(
        self,
        aircraft_number: Optional[str] = None,
        status: Optional[str] = None,
        configuration_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DefectList]:
        """获取缺陷清单列表"""
        query = self.db.query(DefectList)
        
        if aircraft_number:
            query = query.filter(DefectList.aircraft_number == aircraft_number)
        if status:
            query = query.filter(DefectList.status == status)
        if configuration_id:
            query = query.filter(DefectList.configuration_id == configuration_id)
        
        return query.offset(skip).limit(limit).all()

    def get_defect_list_by_id(self, defect_list_id: int) -> Optional[DefectList]:
        """根据ID获取缺陷清单"""
        return self.db.query(DefectList).filter(DefectList.id == defect_list_id).first()

    def create_defect_list(self, defect_list: DefectListCreate) -> DefectList:
        """创建新的缺陷清单"""
        db_defect_list = DefectList(
            aircraft_number=defect_list.aircraft_number,
            title=defect_list.title,
            description=defect_list.description,
            configuration_id=defect_list.configuration_id
        )
        self.db.add(db_defect_list)
        self.db.commit()
        self.db.refresh(db_defect_list)
        return db_defect_list

    def update_defect_list(self, defect_list_id: int, defect_list: DefectListUpdate) -> Optional[DefectList]:
        """更新缺陷清单"""
        db_defect_list = self.get_defect_list_by_id(defect_list_id)
        if not db_defect_list:
            return None
        
        update_data = defect_list.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_defect_list, field, value)
        
        self.db.commit()
        self.db.refresh(db_defect_list)
        return db_defect_list

    def upload_defect_data(self, defect_list_id: int, file) -> dict:
        """上传缺陷数据文件"""
        import logging
        logger = logging.getLogger(__name__)
        
        defect_list = self.get_defect_list_by_id(defect_list_id)
        if not defect_list:
            raise ValueError("缺陷清单未找到")
        
        def replace_nan_with_none(obj):
            """递归地将 NaN 值替换为 None，以便正确序列化为 JSON"""
            if isinstance(obj, dict):
                return {k: replace_nan_with_none(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_nan_with_none(item) for item in obj]
            elif pd.isna(obj) or (isinstance(obj, float) and np.isnan(obj)):
                return None
            else:
                return obj
        
        try:
            logger.info(f"开始上传缺陷数据文件，缺陷清单ID: {defect_list_id}")
            logger.info(f"文件名: {file.filename if hasattr(file, 'filename') else '未知'}")
            logger.info(f"文件类型: {file.content_type if hasattr(file, 'content_type') else '未知'}")
            
            # 读取Excel文件（直接使用file.file，FastAPI的UploadFile对象支持）
            # 将"相关工卡序号"列强制读取为字符串类型，以保留前导零
            dtype_dict = {}
            # 尝试识别可能的列名（中英文变体）
            possible_column_keywords = [
                '相关工卡序号', 'Item No', 'Ref No', 'Reference Item', 
                'item_no', 'ref_no', 'reference_item',
                'ItemNo', 'RefNo', 'ReferenceItem'
            ]
            try:
                # 先读取第一行来识别列名
                df_preview = pd.read_excel(file.file, nrows=1)
                for col in df_preview.columns:
                    col_str = str(col).strip()
                    # 使用灵活的匹配方式：检查列名是否包含关键词
                    for keyword in possible_column_keywords:
                        if keyword.lower() in col_str.lower() or col_str == keyword:
                            dtype_dict[col] = str
                            logger.info(f"识别到'相关工卡序号'列: {col}，将强制读取为字符串类型")
                            break
                # 重新读取完整文件，应用dtype
                file.file.seek(0)  # 重置文件指针
                df = pd.read_excel(file.file, dtype=dtype_dict)
                logger.info(f"成功读取Excel文件，共 {len(df)} 行数据")
            except Exception as e:
                logger.error(f"读取Excel文件失败: {str(e)}", exc_info=True)
                return {
                    "message": f"读取Excel文件失败: {str(e)}",
                    "imported_count": 0,
                    "error_count": 0,
                    "errors": [f"读取Excel文件失败: {str(e)}"]
                }
            
            imported_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # 将 row 转换为字典，并处理 NaN 值
                    raw_data_dict = row.to_dict()
                    # 替换 NaN 为 None
                    raw_data_cleaned = replace_nan_with_none(raw_data_dict)
                    
                    # 处理"相关工卡序号"列，确保保留前导零
                    # 尝试识别可能的列名（中英文变体）
                    workcard_item_keywords = [
                        '相关工卡序号', 'Item No', 'Ref No', 'Reference Item',
                        'item_no', 'ref_no', 'reference_item',
                        'ItemNo', 'RefNo', 'ReferenceItem'
                    ]
                    for key in raw_data_cleaned.keys():
                        key_str = str(key).strip()
                        # 使用灵活的匹配方式：检查列名是否包含关键词
                        for keyword in workcard_item_keywords:
                            if keyword.lower() in key_str.lower() or key_str == keyword:
                                value = raw_data_cleaned[key]
                                if value is not None:
                                    # 如果是数字类型，格式化为5位字符串（补零）
                                    if isinstance(value, (int, float)) and not pd.isna(value):
                                        try:
                                            num = int(float(value))
                                            raw_data_cleaned[key] = f"{num:05d}"  # 格式化为5位数字，不足补零
                                        except (ValueError, TypeError):
                                            pass
                                    # 如果已经是字符串，确保是字符串类型（保留原始格式）
                                    elif isinstance(value, str):
                                        raw_data_cleaned[key] = value
                                break  # 找到第一个匹配的列名就处理，避免重复处理
                    
                    # 获取中文描述作为 title
                    title = self._extract_chinese_description(raw_data_cleaned)
                    # 获取英文描述作为 description
                    description = self._extract_english_description(raw_data_cleaned)
                    # 获取缺陷编号
                    defect_number = self._extract_defect_number(raw_data_cleaned)
                    if not defect_number:
                        defect_number = f'DEF-{index+1}'
                    
                    # 检查是否已存在相同缺陷编号的记录（在同一缺陷清单中）
                    existing_record = self.db.query(DefectRecord).filter(
                        and_(
                            DefectRecord.defect_number == defect_number,
                            DefectRecord.defect_list_id == defect_list_id
                        )
                    ).first()
                    
                    if existing_record:
                        # 如果已存在，跳过或更新（这里选择跳过，避免重复）
                        error_count += 1
                        errors.append(f"行 {index + 1}: 缺陷编号 {defect_number} 已存在，跳过")
                        continue
                    
                    defect_record = DefectRecord(
                        defect_number=defect_number,
                        title=title,
                        description=description,
                        system=str(row.get('system', '')) if pd.notna(row.get('system')) else '',
                        component=str(row.get('component', '')) if pd.notna(row.get('component')) else '',
                        location=str(row.get('location', '')) if pd.notna(row.get('location')) else '',
                        severity=str(row.get('severity', 'minor')) if pd.notna(row.get('severity')) else 'minor',
                        raw_data=raw_data_cleaned,
                        defect_list_id=defect_list_id
                    )
                    self.db.add(defect_record)
                    imported_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"行 {index + 1}: {str(e)}")
            
            self.db.commit()
            
            logger.info(f"上传完成，成功导入 {imported_count} 条，失败 {error_count} 条")
            if errors and len(errors) > 0:
                logger.warning(f"上传过程中的错误: {errors[:10]}")  # 只记录前10个错误
            
            return {
                "message": "缺陷数据上传成功",
                "imported_count": imported_count,
                "error_count": error_count,
                "errors": errors
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"上传缺陷数据文件时发生异常: {str(e)}")
            logger.error(f"错误详情: {error_detail}")
            self.db.rollback()
            return {
                "message": f"上传失败: {str(e)}",
                "imported_count": 0,
                "error_count": 0,
                "errors": [str(e)]
            }

    def get_defect_records(
        self,
        defect_list_id: int,
        is_matched: Optional[bool] = None,
        is_selected: Optional[bool] = None
    ) -> List[DefectRecord]:
        """获取缺陷记录列表"""
        query = self.db.query(DefectRecord).filter(DefectRecord.defect_list_id == defect_list_id)
        
        if is_matched is not None:
            query = query.filter(DefectRecord.is_matched == is_matched)
        if is_selected is not None:
            query = query.filter(DefectRecord.is_selected == is_selected)
        
        return query.all()

    def create_defect_record(self, defect_record: DefectRecordCreate) -> DefectRecord:
        """创建新的缺陷记录"""
        db_defect_record = DefectRecord(
            defect_number=defect_record.defect_number,
            title=defect_record.title,
            description=defect_record.description,
            system=defect_record.system,
            component=defect_record.component,
            location=defect_record.location,
            severity=defect_record.severity,
            raw_data=defect_record.raw_data,
            defect_list_id=defect_record.defect_list_id
        )
        self.db.add(db_defect_record)
        self.db.commit()
        self.db.refresh(db_defect_record)
        return db_defect_record

    def delete_defect_record(self, defect_record_id: int) -> bool:
        """删除缺陷记录及其关联数据"""
        from app.models.matching import MatchingResult, CandidateWorkCard
        
        # 查找缺陷记录
        defect_record = self.db.query(DefectRecord).filter(
            DefectRecord.id == defect_record_id
        ).first()
        
        if not defect_record:
            return False
        
        try:
            # 删除关联的匹配结果
            matching_results = self.db.query(MatchingResult).filter(
                MatchingResult.defect_record_id == defect_record_id
            ).all()
            for result in matching_results:
                self.db.delete(result)
            
            # 删除关联的候选工卡
            candidate_workcards = self.db.query(CandidateWorkCard).filter(
                CandidateWorkCard.defect_record_id == defect_record_id
            ).all()
            for candidate in candidate_workcards:
                self.db.delete(candidate)
            
            # 删除关联的清洗数据
            cleaned_data = self.db.query(DefectCleanedData).filter(
                DefectCleanedData.defect_record_id == defect_record_id
            ).all()
            for cleaned in cleaned_data:
                self.db.delete(cleaned)
            
            # 删除缺陷记录本身
            self.db.delete(defect_record)
            
            # 提交事务
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"删除缺陷记录失败: {str(e)}", exc_info=True)
            raise

    def delete_defect_list(self, defect_list_id: int) -> bool:
        """删除缺陷清单及其关联数据（缺陷记录/清洗数据/匹配结果/候选工卡/导入批次）"""
        from app.models.matching import MatchingResult, CandidateWorkCard
        from app.models.import_batch import ImportBatch, ImportBatchItem
        import logging

        logger = logging.getLogger(__name__)

        defect_list = self.get_defect_list_by_id(defect_list_id)
        if not defect_list:
            return False

        try:
            record_rows = self.db.query(DefectRecord.id).filter(
                DefectRecord.defect_list_id == defect_list_id
            ).all()
            record_ids = [r[0] for r in record_rows]

            # 删除与缺陷记录相关的数据
            if record_ids:
                self.db.query(MatchingResult).filter(
                    MatchingResult.defect_record_id.in_(record_ids)
                ).delete(synchronize_session=False)

                self.db.query(CandidateWorkCard).filter(
                    CandidateWorkCard.defect_record_id.in_(record_ids)
                ).delete(synchronize_session=False)

                self.db.query(DefectCleanedData).filter(
                    DefectCleanedData.defect_record_id.in_(record_ids)
                ).delete(synchronize_session=False)

                # 先删导入批次明细（如果存在引用 defect_record_id）
                self.db.query(ImportBatchItem).filter(
                    ImportBatchItem.defect_record_id.in_(record_ids)
                ).delete(synchronize_session=False)

                self.db.query(DefectRecord).filter(
                    DefectRecord.id.in_(record_ids)
                ).delete(synchronize_session=False)

            # 删除与缺陷清单相关的导入批次（以及其 items）
            batch_rows = self.db.query(ImportBatch.id).filter(
                ImportBatch.defect_list_id == defect_list_id
            ).all()
            batch_ids = [b[0] for b in batch_rows]
            if batch_ids:
                self.db.query(ImportBatchItem).filter(
                    ImportBatchItem.batch_id.in_(batch_ids)
                ).delete(synchronize_session=False)
                self.db.query(ImportBatch).filter(
                    ImportBatch.id.in_(batch_ids)
                ).delete(synchronize_session=False)

            # 删除缺陷清单本身
            self.db.delete(defect_list)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除缺陷清单失败: {str(e)}", exc_info=True)
            raise

    def select_workcard_for_defect(self, defect_record_id: int, workcard_id: int) -> bool:
        """为缺陷记录选择工卡"""
        defect_record = self.db.query(DefectRecord).filter(DefectRecord.id == defect_record_id).first()
        if not defect_record:
            return False
        
        defect_record.is_selected = True
        defect_record.selected_workcard_id = workcard_id
        defect_record.is_matched = True
        
        self.db.commit()
        return True

    def get_unmatched_defects(self, defect_list_id: int) -> List[DefectRecord]:
        """获取未匹配的缺陷记录"""
        return self.db.query(DefectRecord).filter(
            and_(
                DefectRecord.defect_list_id == defect_list_id,
                DefectRecord.is_matched == False
            )
        ).all()

    def export_unmatched_defects(self, defect_list_id: int, format: str = "csv") -> dict:
        """导出未匹配的缺陷记录"""
        unmatched_defects = self.get_unmatched_defects(defect_list_id)
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow([
                'defect_number', 'title', 'description', 'system', 
                'component', 'location', 'severity'
            ])
            
            # 写入数据
            for defect in unmatched_defects:
                writer.writerow([
                    defect.defect_number,
                    defect.title,
                    defect.description,
                    defect.system,
                    defect.component,
                    defect.location,
                    defect.severity
                ])
            
            return {
                "message": "导出成功",
                "data": output.getvalue(),
                "count": len(unmatched_defects)
            }
        
        return {
            "message": "不支持的导出格式",
            "data": "",
            "count": 0
        }

    def clean_defect_data_with_progress(
        self,
        defect_list_id: int,
        configuration_id: int,
        workcard_service,
        limit: Optional[int] = None,
        progress_callback=None
    ) -> dict:
        """清洗缺陷数据（带进度回调）"""
        from typing import Dict, Any, List
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        defect_list = self.get_defect_list_by_id(defect_list_id)
        if not defect_list:
            return {
                "success": False,
                "message": "缺陷清单未找到",
                "cleaned_count": 0,
                "total_count": 0,
                "cleaned_data": []
            }
        
        defect_records = self.get_defect_records(defect_list_id)
        if not defect_records:
            return {
                "success": False,
                "message": "缺陷记录为空",
                "cleaned_count": 0,
                "total_count": 0,
                "cleaned_data": []
            }
        
        # 支持断点续传：如果指定了 resume=True，只处理未清洗的记录
        # 检查是否有未清洗的记录
        unprocessed_records = [r for r in defect_records if not getattr(r, 'is_cleaned', False)]
        
        # 如果指定了限制数量，只处理前N条（用于测试）
        if limit:
            if unprocessed_records:
                defect_records = unprocessed_records[:limit]
                logger.info(f"测试模式：只清洗前 {limit} 条未清洗数据")
            else:
                defect_records = defect_records[:limit]
                logger.info(f"测试模式：只清洗前 {limit} 条数据（所有记录都已清洗）")
        else:
            # 默认只处理未清洗的记录（断点续传）
            if unprocessed_records:
                defect_records = unprocessed_records
                logger.info(f"断点续传模式：发现 {len(unprocessed_records)} 条未清洗记录，{len(defect_records) - len(unprocessed_records)} 条已清洗")
            else:
                logger.info(f"所有记录都已清洗，将重新清洗所有记录")
        
        total_count = len(defect_records)
        total_all_count = len(self.get_defect_records(defect_list_id))
        
        # 更新缺陷清单状态
        defect_list.cleaning_status = "processing"
        defect_list.processing_stage = "cleaning"
        defect_list.last_processed_at = datetime.now()
        self.db.commit()
        
        # 获取索引数据
        from app.services.index_data_service import IndexDataService
        from app.services.configuration_service import ConfigurationService
        
        index_service = IndexDataService(self.db)
        config_service = ConfigurationService(self.db)
        
        if progress_callback:
            progress_callback(0, total_count, "正在加载索引数据...")
        
        index_data = index_service.get_index_data(configuration_id=configuration_id, limit=10000)
        
        if not index_data:
            return {
                "success": False,
                "message": "未找到索引数据",
                "cleaned_count": 0,
                "total_count": total_count,
                "cleaned_data": []
            }
        
        logger.info(f"加载索引数据条数: {len(index_data)}")
        
        # 获取构型配置的独立对照字段
        config = config_service.get_configuration_by_id(configuration_id)
        field_mapping = config.field_mapping if config and config.field_mapping else {}
        
        # 生成独立对照字段列表
        independent_fields = {
            'orientation': field_mapping.get('orientation', []),
            'defectSubject': field_mapping.get('defectSubject', []),
            'defectDescription': field_mapping.get('defectDescription', []),
            'location': field_mapping.get('location', []),
            'quantity': field_mapping.get('quantity', [])
        }
        
        logger.info(f"独立对照字段: {independent_fields}")
        
        # 使用异步批量清洗，带进度回调
        # 分批处理，每批处理完后保存状态
        batch_size = 50  # 每批处理50条
        cleaned_data = []
        cleaned_count = 0
        
        for batch_start in range(0, total_count, batch_size):
            batch_end = min(batch_start + batch_size, total_count)
            batch_records = defect_records[batch_start:batch_end]
            
            logger.info(f"处理清洗批次 {batch_start + 1}-{batch_end}/{total_count}")
            
            # 处理当前批次
            cleaned_results = asyncio.run(
                self._batch_clean_defect_records_with_progress(
                    batch_records,
                    index_data,
                    independent_fields,
                    workcard_service,
                    progress_callback
                )
            )
            
            if progress_callback:
                progress_callback(batch_end, total_count, f"正在保存批次 {batch_start + 1}-{batch_end} 的清洗结果...")
            
            # 更新缺陷记录并收集结果
            for record, cleaned_result in zip(batch_records, cleaned_results):
                try:
                    if cleaned_result and isinstance(cleaned_result, dict):
                        # 提取原始描述（清洗前的工卡描述），分别提取中文和英文描述
                        # 优先从 raw_data 中提取，确保中文和英文描述分开处理
                        description_cn = ""
                        description_en = ""
                        
                        if record.raw_data:
                            raw_data_temp = {}
                            try:
                                if isinstance(record.raw_data, dict):
                                    raw_data_temp = record.raw_data
                                elif isinstance(record.raw_data, str):
                                    import json
                                    raw_data_temp = json.loads(record.raw_data)
                            except Exception:
                                raw_data_temp = {}
                            
                            # 提取中文描述
                            if isinstance(raw_data_temp, dict):
                                description_cn = (
                                    raw_data_temp.get('description_cn') or
                                    raw_data_temp.get('工卡描述（中文）') or
                                    raw_data_temp.get('工卡描述(中文)') or
                                    raw_data_temp.get('描述') or
                                    raw_data_temp.get('工卡描述') or
                                    ""
                                )
                                if description_cn and isinstance(description_cn, str):
                                    description_cn = description_cn.strip()
                                
                                # 提取英文描述
                                description_en = (
                                    raw_data_temp.get('description_en') or
                                    raw_data_temp.get('descriptionEng') or
                                    raw_data_temp.get('工卡描述（英文）') or
                                    raw_data_temp.get('工卡描述(英文)') or
                                    raw_data_temp.get('英文描述') or
                                    raw_data_temp.get('description') or
                                    raw_data_temp.get('Description') or
                                    ""
                                )
                                if description_en and isinstance(description_en, str):
                                    description_en = description_en.strip()
                        
                        # 确保如果原始数据中中文描述为空，则保持为空，不要用其他字段填充
                        # 不再从 record.description 或 record.title 获取，因为这些可能包含英文描述
                        if not description_cn:
                            description_cn = ""
                        
                        # 如果原始数据中英文描述为空，则保持为空
                        if not description_en:
                            description_en = ""
                        
                        # 更新缺陷记录的原始数据，添加清洗后的索引字段
                        raw_data = record.raw_data or {}
                        if isinstance(raw_data, str):
                            try:
                                import json
                                raw_data = json.loads(raw_data)
                            except Exception:
                                raw_data = {}
                        
                        # 如果还没有提取到英文描述，尝试从 raw_data 中提取
                        if not description_en:
                            description_en = self._extract_english_description(raw_data)
                        raw_data.update({
                            'main_area': cleaned_result.get('main_area', ''),
                            'main_component': cleaned_result.get('main_component', ''),
                            'first_level_subcomponent': cleaned_result.get('first_level_subcomponent', ''),
                            'second_level_subcomponent': cleaned_result.get('second_level_subcomponent', ''),
                            'orientation': cleaned_result.get('orientation', ''),
                            'defect_subject': cleaned_result.get('defect_subject', ''),
                            'defect_description': cleaned_result.get('defect_description', ''),
                            'location': cleaned_result.get('location', ''),
                            'quantity': cleaned_result.get('quantity', ''),
                            'description_cn': description_cn,  # 保持原始中文描述，如果为空则保持为空
                            'description_en': description_en,  # 保持原始英文描述，如果为空则保持为空
                            'cleaned_at': datetime.now().isoformat()
                        })
                        record.raw_data = raw_data
                        
                        # 保存或更新清洗后的数据到专门的表 DefectCleanedData
                        cleaned_data_record = self.db.query(DefectCleanedData).filter(
                            DefectCleanedData.defect_record_id == record.id
                        ).first()
                        
                        if cleaned_data_record:
                            # 更新现有记录
                            cleaned_data_record.main_area = cleaned_result.get('main_area', '')
                            cleaned_data_record.main_component = cleaned_result.get('main_component', '')
                            cleaned_data_record.first_level_subcomponent = cleaned_result.get('first_level_subcomponent', '')
                            cleaned_data_record.second_level_subcomponent = cleaned_result.get('second_level_subcomponent', '')
                            cleaned_data_record.orientation = cleaned_result.get('orientation', '')
                            cleaned_data_record.defect_subject = cleaned_result.get('defect_subject', '')
                            cleaned_data_record.defect_description = cleaned_result.get('defect_description', '')
                            cleaned_data_record.location = cleaned_result.get('location', '')
                            cleaned_data_record.quantity = cleaned_result.get('quantity', '')
                            cleaned_data_record.description_cn = description_cn  # 保持原始中文描述，如果为空则保持为空
                            cleaned_data_record.is_cleaned = True
                            cleaned_data_record.cleaned_at = datetime.now()
                            logger.info(f"更新缺陷记录 {record.id} 的清洗数据到 DefectCleanedData 表")
                        else:
                            # 创建新记录
                            cleaned_data_record = DefectCleanedData(
                                defect_record_id=record.id,
                                main_area=cleaned_result.get('main_area', ''),
                                main_component=cleaned_result.get('main_component', ''),
                                first_level_subcomponent=cleaned_result.get('first_level_subcomponent', ''),
                                second_level_subcomponent=cleaned_result.get('second_level_subcomponent', ''),
                                orientation=cleaned_result.get('orientation', ''),
                                defect_subject=cleaned_result.get('defect_subject', ''),
                                defect_description=cleaned_result.get('defect_description', ''),
                                location=cleaned_result.get('location', ''),
                                quantity=cleaned_result.get('quantity', ''),
                                description_cn=description_cn,  # 保持原始中文描述，如果为空则保持为空
                                is_cleaned=True
                            )
                            self.db.add(cleaned_data_record)
                            logger.info(f"创建缺陷记录 {record.id} 的清洗数据到 DefectCleanedData 表")
                        
                        # 更新缺陷记录的处理状态
                        record.is_cleaned = True
                        record.cleaned_at = datetime.now()
                        
                        # 更新基础字段（如果清洗结果中有更好的值）
                        if cleaned_result.get('main_area'):
                            # 可以将 main_area 映射到 system
                            if not record.system or record.system.strip() == '':
                                record.system = cleaned_result.get('main_area', record.system)
                        if cleaned_result.get('main_component'):
                            if not record.component or record.component.strip() == '':
                                record.component = cleaned_result.get('main_component', record.component)
                        if cleaned_result.get('location'):
                            record.location = cleaned_result.get('location', record.location)
                        
                        cleaned_data.append({
                            "id": record.id,
                            "defect_number": record.defect_number,
                            "description_cn": description_cn,  # 保持原始中文描述，如果为空则保持为空
                            "description_en": description_en,
                            "system": record.system,
                            "component": record.component,
                            "location": record.location,
                            **cleaned_result
                        })
                        cleaned_count += 1
                    else:
                        logger.warning(f"缺陷记录 {record.id} 清洗结果为空")
                    
                except Exception as e:
                    logger.error(f"更新缺陷记录 {record.id} 失败: {str(e)}")
                    continue
            
            # 每批处理完后立即提交，保存进度
            try:
                self.db.commit()
                logger.info(f"批次 {batch_start + 1}-{batch_end} 清洗完成，已保存到数据库")
                
                # 更新缺陷清单的清洗进度
                cleaning_progress = (batch_end / total_all_count) * 100 if total_all_count > 0 else 100
                defect_list.cleaning_progress = min(cleaning_progress, 100.0)
                defect_list.last_processed_at = datetime.now()
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                logger.error(f"保存批次 {batch_start + 1}-{batch_end} 清洗结果失败: {str(e)}")
        
        # 所有批次处理完成，更新最终状态
        try:
            # 检查是否所有记录都已清洗
            all_records = self.get_defect_records(defect_list_id)
            all_cleaned = all([getattr(r, 'is_cleaned', False) for r in all_records])
            
            if all_cleaned:
                defect_list.cleaning_status = "completed"
                defect_list.cleaning_progress = 100.0
                defect_list.processing_stage = "matching"  # 清洗完成，进入匹配阶段
                logger.info(f"所有缺陷记录已清洗完成")
            else:
                defect_list.cleaning_status = "processing"  # 部分完成，保持处理中状态
                logger.info(f"部分缺陷记录已清洗，还有未清洗的记录")
            
            defect_list.last_processed_at = datetime.now()
            self.db.commit()
            logger.info(f"成功清洗并保存 {cleaned_count} 条缺陷数据到数据库")
            # 验证保存是否成功：随机检查一条记录
            if cleaned_count > 0 and defect_records:
                sample_record = defect_records[0]
                self.db.refresh(sample_record)  # 刷新记录，确保从数据库重新加载
                if sample_record.raw_data and isinstance(sample_record.raw_data, dict):
                    sample_main_area = sample_record.raw_data.get('main_area', '')
                    logger.info(f"验证保存结果 - 示例记录 {sample_record.id}: main_area='{sample_main_area}'")
                else:
                    logger.warning(f"验证保存结果 - 示例记录 {sample_record.id} 的raw_data为空或不是字典")
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存清洗结果失败: {str(e)}")
            return {
                "success": False,
                "message": f"保存清洗结果失败: {str(e)}",
                "cleaned_count": 0,
                "total_count": total_count,
                "cleaned_data": []
            }
        
        return {
            "success": True,
            "message": f"成功清洗 {cleaned_count}/{total_count} 条缺陷数据",
            "cleaned_count": cleaned_count,
            "total_count": total_count,
            "cleaned_data": cleaned_data
        }

    def clean_defect_data(
        self,
        defect_list_id: int,
        configuration_id: int,
        workcard_service,
        limit: Optional[int] = None
    ) -> dict:
        """清洗缺陷数据（复用工卡清洗逻辑）"""
        from typing import Dict, Any, List
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        defect_list = self.get_defect_list_by_id(defect_list_id)
        if not defect_list:
            return {
                "success": False,
                "message": "缺陷清单未找到",
                "cleaned_count": 0,
                "total_count": 0,
                "cleaned_data": []
            }
        
        defect_records = self.get_defect_records(defect_list_id)
        if not defect_records:
            return {
                "success": False,
                "message": "缺陷记录为空",
                "cleaned_count": 0,
                "total_count": 0,
                "cleaned_data": []
            }
        
        # 如果指定了限制数量，只处理前N条（用于测试）
        if limit:
            defect_records = defect_records[:limit]
            logger.info(f"测试模式：只清洗前 {limit} 条数据")
        
        # 获取索引数据
        from app.services.index_data_service import IndexDataService
        from app.services.configuration_service import ConfigurationService
        
        index_service = IndexDataService(self.db)
        config_service = ConfigurationService(self.db)
        
        index_data = index_service.get_index_data(configuration_id=configuration_id, limit=10000)
        
        if not index_data:
            return {
                "success": False,
                "message": "未找到索引数据",
                "cleaned_count": 0,
                "total_count": len(defect_records),
                "cleaned_data": []
            }
        
        logger.info(f"加载索引数据条数: {len(index_data)}")
        
        # 获取构型配置的独立对照字段
        config = config_service.get_configuration_by_id(configuration_id)
        field_mapping = config.field_mapping if config and config.field_mapping else {}
        
        # 生成独立对照字段列表
        independent_fields = {
            'orientation': field_mapping.get('orientation', []),
            'defectSubject': field_mapping.get('defectSubject', []),
            'defectDescription': field_mapping.get('defectDescription', []),
            'location': field_mapping.get('location', []),
            'quantity': field_mapping.get('quantity', [])
        }
        
        logger.info(f"独立对照字段: {independent_fields}")
        
        # 使用异步批量清洗
        cleaned_results = asyncio.run(
            self._batch_clean_defect_records(
                defect_records,
                index_data,
                independent_fields,
                workcard_service
            )
        )
        
        cleaned_data = []
        cleaned_count = 0
        
        # 更新缺陷记录并收集结果
        for record, cleaned_result in zip(defect_records, cleaned_results):
            try:
                if cleaned_result and isinstance(cleaned_result, dict):
                    # 提取原始描述（清洗前的工卡描述），分别提取中文和英文描述
                    # 优先从 raw_data 中提取，确保中文和英文描述分开处理
                    description_cn = ""
                    description_en = ""
                    
                    if record.raw_data:
                        raw_data_temp = {}
                        try:
                            if isinstance(record.raw_data, dict):
                                raw_data_temp = record.raw_data
                            elif isinstance(record.raw_data, str):
                                import json
                                raw_data_temp = json.loads(record.raw_data)
                        except Exception:
                            raw_data_temp = {}
                        
                        # 提取中文描述
                        if isinstance(raw_data_temp, dict):
                            description_cn = (
                                raw_data_temp.get('description_cn') or
                                raw_data_temp.get('工卡描述（中文）') or
                                raw_data_temp.get('工卡描述(中文)') or
                                raw_data_temp.get('描述') or
                                raw_data_temp.get('工卡描述') or
                                ""
                            )
                            if description_cn and isinstance(description_cn, str):
                                description_cn = description_cn.strip()
                            
                            # 提取英文描述
                            description_en = (
                                raw_data_temp.get('description_en') or
                                raw_data_temp.get('descriptionEng') or
                                raw_data_temp.get('工卡描述（英文）') or
                                raw_data_temp.get('工卡描述(英文)') or
                                raw_data_temp.get('英文描述') or
                                raw_data_temp.get('description') or
                                raw_data_temp.get('Description') or
                                ""
                            )
                            if description_en and isinstance(description_en, str):
                                description_en = description_en.strip()
                    
                    # 确保如果原始数据中中文描述为空，则保持为空，不要用其他字段填充
                    # 不再从 record.description 或 record.title 获取，因为这些可能包含英文描述
                    if not description_cn:
                        description_cn = ""
                    
                    # 如果原始数据中英文描述为空，则保持为空
                    if not description_en:
                        description_en = ""
                    
                    # 更新缺陷记录的原始数据，添加清洗后的索引字段
                    raw_data = record.raw_data or {}
                    if isinstance(raw_data, str):
                        try:
                            import json
                            raw_data = json.loads(raw_data)
                        except Exception:
                            raw_data = {}
                    
                    # 如果还没有提取到英文描述，尝试从 raw_data 中提取
                    if not description_en:
                        description_en = self._extract_english_description(raw_data)
                    raw_data.update({
                        'main_area': cleaned_result.get('main_area', ''),
                        'main_component': cleaned_result.get('main_component', ''),
                        'first_level_subcomponent': cleaned_result.get('first_level_subcomponent', ''),
                        'second_level_subcomponent': cleaned_result.get('second_level_subcomponent', ''),
                        'orientation': cleaned_result.get('orientation', ''),
                        'defect_subject': cleaned_result.get('defect_subject', ''),
                        'defect_description': cleaned_result.get('defect_description', ''),
                        'location': cleaned_result.get('location', ''),
                        'quantity': cleaned_result.get('quantity', ''),
                        'description_cn': description_cn,  # 保持原始中文描述，如果为空则保持为空
                        'description_en': description_en,  # 保持原始英文描述，如果为空则保持为空
                        'cleaned_at': datetime.now().isoformat()
                    })
                    record.raw_data = raw_data
                    
                    # 保存或更新清洗后的数据到专门的表 DefectCleanedData
                    cleaned_data_record = self.db.query(DefectCleanedData).filter(
                        DefectCleanedData.defect_record_id == record.id
                    ).first()
                    
                    if cleaned_data_record:
                        # 更新现有记录
                        cleaned_data_record.main_area = cleaned_result.get('main_area', '')
                        cleaned_data_record.main_component = cleaned_result.get('main_component', '')
                        cleaned_data_record.first_level_subcomponent = cleaned_result.get('first_level_subcomponent', '')
                        cleaned_data_record.second_level_subcomponent = cleaned_result.get('second_level_subcomponent', '')
                        cleaned_data_record.orientation = cleaned_result.get('orientation', '')
                        cleaned_data_record.defect_subject = cleaned_result.get('defect_subject', '')
                        cleaned_data_record.defect_description = cleaned_result.get('defect_description', '')
                        cleaned_data_record.location = cleaned_result.get('location', '')
                        cleaned_data_record.quantity = cleaned_result.get('quantity', '')
                        cleaned_data_record.description_cn = description_cn  # 保持原始中文描述，如果为空则保持为空
                        cleaned_data_record.is_cleaned = True
                        cleaned_data_record.cleaned_at = datetime.now()
                        logger.info(f"更新缺陷记录 {record.id} 的清洗数据到 DefectCleanedData 表")
                    else:
                        # 创建新记录
                        cleaned_data_record = DefectCleanedData(
                            defect_record_id=record.id,
                            main_area=cleaned_result.get('main_area', ''),
                            main_component=cleaned_result.get('main_component', ''),
                            first_level_subcomponent=cleaned_result.get('first_level_subcomponent', ''),
                            second_level_subcomponent=cleaned_result.get('second_level_subcomponent', ''),
                            orientation=cleaned_result.get('orientation', ''),
                            defect_subject=cleaned_result.get('defect_subject', ''),
                            defect_description=cleaned_result.get('defect_description', ''),
                            location=cleaned_result.get('location', ''),
                            quantity=cleaned_result.get('quantity', ''),
                            description_cn=description_cn,  # 保持原始中文描述，如果为空则保持为空
                            is_cleaned=True
                        )
                        self.db.add(cleaned_data_record)
                        logger.info(f"创建缺陷记录 {record.id} 的清洗数据到 DefectCleanedData 表")
                    
                    # 更新基础字段（如果清洗结果中有更好的值）
                    if cleaned_result.get('main_area'):
                        # 可以将 main_area 映射到 system
                        if not record.system or record.system.strip() == '':
                            record.system = cleaned_result.get('main_area', record.system)
                    if cleaned_result.get('main_component'):
                        if not record.component or record.component.strip() == '':
                            record.component = cleaned_result.get('main_component', record.component)
                    if cleaned_result.get('location'):
                        record.location = cleaned_result.get('location', record.location)
                    
                    cleaned_data.append({
                        "id": record.id,
                        "defect_number": record.defect_number,
                        "description_cn": description_cn,  # 保持原始中文描述，如果为空则保持为空  # 工卡描述（中文）- 统一使用此字段
                        "system": record.system,
                        "component": record.component,
                        "location": record.location,
                        **cleaned_result
                    })
                    cleaned_count += 1
                else:
                    logger.warning(f"缺陷记录 {record.id} 清洗结果为空")
                    
            except Exception as e:
                logger.error(f"更新缺陷记录 {record.id} 失败: {str(e)}")
                continue
        
        # 提交数据库更改
        try:
            self.db.commit()
            logger.info(f"成功清洗并保存 {cleaned_count} 条缺陷数据到数据库")
            # 验证保存是否成功：随机检查一条记录
            if cleaned_count > 0 and defect_records:
                sample_record = defect_records[0]
                self.db.refresh(sample_record)  # 刷新记录，确保从数据库重新加载
                if sample_record.raw_data and isinstance(sample_record.raw_data, dict):
                    sample_main_area = sample_record.raw_data.get('main_area', '')
                    logger.info(f"验证保存结果 - 示例记录 {sample_record.id}: main_area='{sample_main_area}'")
                else:
                    logger.warning(f"验证保存结果 - 示例记录 {sample_record.id} 的raw_data为空或不是字典")
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存清洗结果失败: {str(e)}")
            return {
                "success": False,
                "message": f"保存清洗结果失败: {str(e)}",
                "cleaned_count": 0,
                "total_count": len(defect_records),
                "cleaned_data": []
            }
        
        return {
            "success": True,
            "message": f"成功清洗 {cleaned_count}/{len(defect_records)} 条缺陷数据",
            "cleaned_count": cleaned_count,
            "total_count": len(defect_records),
            "cleaned_data": cleaned_data
        }
    
    async def _batch_clean_defect_records(
        self,
        defect_records: List[DefectRecord],
        index_data: List,
        independent_fields: Dict[str, List[str]],
        workcard_service
    ) -> List[Dict[str, Any]]:
        """批量清洗缺陷记录"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"开始批量清洗缺陷数据，数据条数: {len(defect_records)}")
        
        results = []
        
        for idx, record in enumerate(defect_records):
            description_cn = ""
            description_en = ""
            raw_data: Dict[str, Any] = {}
            try:
                if record.raw_data:
                    if isinstance(record.raw_data, dict):
                        raw_data = record.raw_data
                    elif isinstance(record.raw_data, str):
                        try:
                            import json
                            raw_data = json.loads(record.raw_data)
                        except Exception:
                            raw_data = {}
                else:
                    raw_data = {}

                # 准备描述内容 - 优先使用 description，其次 title，最后尝试从 raw_data 中提取
                description = record.description or record.title or ""
                
                # 如果 description 和 title 都为空，尝试从 raw_data 中提取
                if not description and raw_data:
                    
                    # 方法1: 尝试常见的描述字段名（支持多种字段名格式）
                    description = (
                        raw_data.get('description') or 
                        raw_data.get('Description') or
                        raw_data.get('DESCRIPTION') or
                        raw_data.get('描述') or 
                        raw_data.get('工卡描述') or 
                        raw_data.get('故障描述') or 
                        raw_data.get('缺陷描述') or
                        raw_data.get('title') or
                        raw_data.get('Title') or
                        raw_data.get('TITLE') or
                        raw_data.get('标题') or
                        ""
                    )
                    
                    # 方法2: 如果方法1没找到，尝试从所有值中查找包含"描述"关键字的字段
                    if not description:
                        for key, value in raw_data.items():
                            if value and isinstance(value, str):
                                # 检查键名或值中是否包含描述相关的关键字
                                key_lower = str(key).lower()
                                value_lower = value.lower()
                                if any(keyword in key_lower or keyword in value_lower[:50] for keyword in ['描述', 'description', 'desc', '故障', '缺陷', '问题', '内容']):
                                    if len(value.strip()) > 10:  # 确保是有效的描述内容
                                        description = value
                                        logger.info(f"从 raw_data 的非标准字段 '{key}' 中提取到描述")
                                        break
                    
                    # 方法3: 如果还没找到，尝试找最长的非空文本字段（可能是描述内容）
                    if not description:
                        longest_text = ""
                        longest_key = None
                        for key, value in raw_data.items():
                            if value and isinstance(value, str) and value.strip():
                                # 跳过明显不是描述的字段（如编号、日期等）
                                key_str = str(key).lower()
                                value_str = value.strip()
                                # 跳过：编号、日期、数字等短字段
                                if len(value_str) > len(longest_text) and len(value_str) > 20:
                                    # 排除明显不是描述的内容
                                    if not value_str.replace('.', '').replace('-', '').isdigit():
                                        if not any(skip_word in key_str for skip_word in ['编号', 'number', 'id', '日期', 'date', '时间', 'time']):
                                            longest_text = value_str
                                            longest_key = key
                        
                        if longest_text:
                            description = longest_text
                            logger.info(f"从 raw_data 中提取到最长文本字段 '{longest_key}' 作为描述，长度: {len(description)}")
                    
                    # 如果找到的是字符串，确保去除空白
                    if description and isinstance(description, str):
                        description = description.strip()
                        # 如果提取的内容太短，可能不是有效的描述
                        if len(description) < 5:
                            description = ""
                
                if description:
                    logger.info(f"从 raw_data 中提取到描述，缺陷编号: {record.defect_number}，描述长度: {len(description)}，描述预览: {description[:100]}...")
                
                # 只从 raw_data 中提取中文描述，不要用 description 填充
                description_cn = ""
                if raw_data:
                    maybe_cn = (
                        raw_data.get('description_cn')
                        or raw_data.get('工卡描述（中文）')
                        or raw_data.get('工卡描述(中文)')
                        or ""
                    )
                    if isinstance(maybe_cn, str) and maybe_cn.strip():
                        description_cn = maybe_cn.strip()
                
                # 如果原始数据中中文描述为空，则保持为空，不要用 description 填充
                if not description_cn:
                    description_cn = ""
                
                # 如果 description 为空，尝试用 description_cn 填充（用于清洗）
                if not description and description_cn:
                    description = description_cn

                description_en = self._extract_english_description(raw_data)
                
                # 如果仍然没有描述，记录日志并跳过
                if not description:
                    logger.warning(f"缺陷记录 {idx + 1}/{len(defect_records)} (ID: {record.id}, 缺陷编号: {record.defect_number}) 没有描述内容，跳过大模型调用")
                    logger.warning(f"  - record.description: {record.description}")
                    logger.warning(f"  - record.title: {record.title}")
                    if record.raw_data and isinstance(record.raw_data, dict):
                        logger.warning(f"  - raw_data keys: {list(record.raw_data.keys())}")
                        # 记录所有非空值，帮助调试
                        non_empty_values = {k: str(v)[:100] for k, v in record.raw_data.items() if v and str(v).strip()}
                        logger.warning(f"  - raw_data 非空值预览: {non_empty_values}")
                    else:
                        logger.warning(f"  - raw_data: {type(record.raw_data)}")
                    # 如果没有描述，返回空索引字段
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
                    empty_result = {
                        **default_index_fields,
                        "description_cn": description_cn,
                        "description_en": description_en,
                    }
                    results.append(empty_result)
                    continue
                
                # 使用层级递进匹配进行清洗
                logger.info(f"清洗缺陷记录 {idx + 1}/{len(defect_records)}，缺陷编号: {record.defect_number}，描述: {description[:100]}...")
                logger.info(f"准备调用大模型进行清洗，索引数据条数: {len(index_data)}")
                
                # 使用 description 进行清洗（如果 description_cn 为空，则使用 description，但不保存到 description_cn）
                cleaned_result = await workcard_service._clean_with_hierarchical_matching(
                    description or "",
                    description or "",
                    description_en,
                    index_data,
                    independent_fields
                )
                
                logger.info(f"缺陷记录 {idx + 1} 清洗完成，结果: {cleaned_result}")
                
                # 确保 cleaned_result 包含所有9个索引字段
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
                complete_cleaned_result = {
                    **default_index_fields,
                    **cleaned_result,
                    "description_cn": description_cn,  # 保持原始中文描述，如果为空则保持为空
                    "description_en": description_en,
                }
                results.append(complete_cleaned_result)
                
            except Exception as e:
                logger.error(f"清洗缺陷记录 {record.id} (第 {idx + 1} 条) 失败: {str(e)}")
                # 如果清洗失败，返回空索引字段
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
                error_result = {
                    **default_index_fields,
                    "description_cn": description_cn,
                    "description_en": description_en,
                    "清洗错误": str(e)
                }
                results.append(error_result)
        
        logger.info(f"批量清洗完成，返回条数: {len(results)}")
        return results
    
    async def _batch_clean_defect_records_with_progress(
        self,
        defect_records: List[DefectRecord],
        index_data: List,
        independent_fields: Dict[str, List[str]],
        workcard_service,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """批量清洗缺陷记录（带进度回调）"""
        import logging
        import json
        logger = logging.getLogger(__name__)
        logger.info(f"开始批量清洗缺陷数据，数据条数: {len(defect_records)}")
        
        results = []
        total_count = len(defect_records)

        for idx, record in enumerate(defect_records):
            description_cn = ""
            description_en = ""
            raw_data: Dict[str, Any] = {}
            try:
                # 更新进度
                if progress_callback:
                    progress_callback(idx, total_count, f"正在清洗第 {idx + 1}/{total_count} 条缺陷数据...")
                if record.raw_data:
                    if isinstance(record.raw_data, dict):
                        raw_data = record.raw_data
                    elif isinstance(record.raw_data, str):
                        try:
                            raw_data = json.loads(record.raw_data)
                        except Exception:
                            raw_data = {}
                
                # 准备描述内容 - 优先使用 description，其次 title，最后尝试从 raw_data 中提取
                description = record.description or record.title or ""
                
                if not description and raw_data:
                    # 方法1: 尝试常见的描述字段名（支持多种字段名格式）
                    description = (
                        raw_data.get('description')
                        or raw_data.get('Description')
                        or raw_data.get('DESCRIPTION')
                        or raw_data.get('描述')
                        or raw_data.get('工卡描述')
                        or raw_data.get('故障描述')
                        or raw_data.get('缺陷描述')
                        or raw_data.get('title')
                        or raw_data.get('Title')
                        or raw_data.get('TITLE')
                        or raw_data.get('标题')
                        or ""
                    )
                    
                    # 方法2: 如果方法1没找到，尝试从所有值中查找包含"描述"关键字的字段
                    if not description:
                        for key, value in raw_data.items():
                            if value and isinstance(value, str):
                                key_lower = str(key).lower()
                                value_lower = value.lower()
                                if any(keyword in key_lower or keyword in value_lower[:50] for keyword in ['描述', 'description', 'desc', '故障', '缺陷', '问题', '内容']):
                                    if len(value.strip()) > 10:
                                        description = value
                                        logger.info(f"从 raw_data 的非标准字段 '{key}' 中提取到描述")
                                        break
                    
                    # 方法3: 如果还没找到，尝试找最长的非空文本字段（可能是描述内容）
                    if not description:
                        longest_text = ""
                        longest_key = None
                        for key, value in raw_data.items():
                            if value and isinstance(value, str) and value.strip():
                                key_str = str(key).lower()
                                value_str = value.strip()
                                if len(value_str) > len(longest_text) and len(value_str) > 20:
                                    if not value_str.replace('.', '').replace('-', '').isdigit():
                                        if not any(skip_word in key_str for skip_word in ['编号', 'number', 'id', '日期', 'date', '时间', 'time']):
                                            longest_text = value_str
                                            longest_key = key
                        if longest_text:
                            description = longest_text
                            logger.info(f"从 raw_data 中提取到最长文本字段 '{longest_key}' 作为描述，长度: {len(description)}")
                
                if description and isinstance(description, str):
                    description = description.strip()
                    if len(description) < 5:
                        description = ""

                # 只从 raw_data 中提取中文描述，不要用 description 填充
                description_cn = ""
                if raw_data:
                    maybe_cn = (
                        raw_data.get('description_cn')
                        or raw_data.get('工卡描述（中文）')
                        or raw_data.get('工卡描述(中文)')
                        or ""
                    )
                    if isinstance(maybe_cn, str) and maybe_cn.strip():
                        description_cn = maybe_cn.strip()
                
                # 如果原始数据中中文描述为空，则保持为空，不要用 description 填充
                if not description_cn:
                    description_cn = ""
                
                # 如果 description 为空，尝试用 description_cn 填充（用于清洗）
                if not description and description_cn:
                    description = description_cn

                description_en = self._extract_english_description(raw_data) if raw_data else ""

                if not description:
                    logger.warning(f"缺陷记录 {idx + 1}/{total_count} (ID: {record.id}, 缺陷编号: {record.defect_number}) 没有描述内容，跳过大模型调用")
                    logger.warning(f"  - record.description: {record.description}")
                    logger.warning(f"  - record.title: {record.title}")
                    if raw_data:
                        logger.warning(f"  - raw_data keys: {list(raw_data.keys())}")
                        # 记录所有非空值，帮助调试
                        non_empty_values = {k: str(v)[:100] for k, v in raw_data.items() if v and str(v).strip()}
                        logger.warning(f"  - raw_data 非空值预览: {non_empty_values}")
                    else:
                        logger.warning(f"  - raw_data: {type(record.raw_data)}")
                    # 如果没有描述，返回空索引字段
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
                    empty_result = {
                        **default_index_fields,
                        "defect_record_id": record.id,
                        "defect_number": record.defect_number,
                        "description_cn": description_cn,
                    "description_en": description_en,
                    }
                    results.append(empty_result)
                    continue
                
                # 使用层级递进匹配进行清洗
                logger.info(f"清洗缺陷记录 {idx + 1}/{total_count}，缺陷编号: {record.defect_number}，描述: {description[:100]}...")
                logger.info(f"准备调用大模型进行清洗，索引数据条数: {len(index_data)}")
                
                # 使用 description 进行清洗（如果 description_cn 为空，则使用 description，但不保存到 description_cn）
                cleaned_result = await workcard_service._clean_with_hierarchical_matching(
                    description or "",
                    description or "",
                    description_en,
                    index_data,
                    independent_fields
                )
                
                logger.info(f"缺陷记录 {idx + 1} 清洗完成，结果: {cleaned_result}")
                
                # 确保 cleaned_result 包含所有9个索引字段
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
                complete_cleaned_result = {
                    **default_index_fields,
                    **cleaned_result,
                    "defect_record_id": record.id,
                    "defect_number": record.defect_number,
                    "description_cn": description_cn,  # 保持原始中文描述，如果为空则保持为空
                    "description_en": description_en,
                }
                results.append(complete_cleaned_result)
                
            except Exception as e:
                logger.error(f"清洗缺陷记录 {record.id} (第 {idx + 1} 条) 失败: {str(e)}")
                # 如果清洗失败，返回空索引字段
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
                error_result = {
                    **default_index_fields,
                    "defect_record_id": record.id,
                    "defect_number": record.defect_number,
                    "description_cn": description_cn,
                    "description_en": description_en,
                    "清洗错误": str(e)
                }
                results.append(error_result)
        
        logger.info(f"批量清洗完成，返回条数: {len(results)}")
        return results

