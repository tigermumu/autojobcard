from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, distinct
from typing import List, Optional, Dict, Any
from app.models.defect import DefectRecord, DefectList
from app.models.workcard import WorkCard
from app.models.matching import MatchingResult, CandidateWorkCard
from app.schemas.matching import MatchingConfig, MatchingRequest
from app.services.llm_service import LLMService
from app.services.similarity_service import SimilarityService
from fastapi import BackgroundTasks
import asyncio

class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = LLMService()
        self.similarity_service = SimilarityService()

    @staticmethod
    def _extract_descriptions(record: DefectRecord) -> Dict[str, str]:
        description_cn = ""
        description_en = ""
        if record.cleaned_data:
            description_cn = (record.cleaned_data.description_cn or "").strip()
        raw_data = {}
        if record.raw_data:
            if isinstance(record.raw_data, dict):
                raw_data = record.raw_data
            elif isinstance(record.raw_data, str):
                try:
                    import json
                    raw_data = json.loads(record.raw_data)
                except Exception:
                    raw_data = {}

        if raw_data:
            description_cn = (
                raw_data.get("description_cn")
                or raw_data.get("工卡描述（中文）")
                or raw_data.get("工卡描述(中文)")
                or description_cn
            )
            if isinstance(description_cn, str):
                description_cn = description_cn.strip()

            candidate_keys = [
                "description_en",
                "descriptionEng",
                "英文描述",
                "工卡描述（英文）",
                "工卡描述(英文)",
            ]
            for key in candidate_keys:
                value = raw_data.get(key)
                if value and isinstance(value, str):
                    description_en = value.strip()
                    if description_en:
                        break

        if not description_cn:
            description_cn = (record.description or record.title or "").strip()

        return {
            "description_cn": description_cn,
            "description_en": description_en,
        }

    def match_defect_record(
        self, 
        defect_record_id: int, 
        config: MatchingConfig,
        background_tasks: BackgroundTasks
    ) -> dict:
        """为缺陷记录执行匹配"""
        defect_record = self.db.query(DefectRecord).filter(
            DefectRecord.id == defect_record_id
        ).first()
        
        if not defect_record:
            raise ValueError("缺陷记录未找到")
        
        # 在后台执行匹配任务
        background_tasks.add_task(
            self._execute_matching_task,
            defect_record_id,
            config
        )
        
        return {
            "message": "匹配任务已启动",
            "defect_record_id": defect_record_id,
            "status": "processing"
        }

    async def _execute_matching_task(self, defect_record_id: int, config: MatchingConfig):
        """执行匹配任务"""
        try:
            # 获取缺陷记录
            defect_record = self.db.query(DefectRecord).filter(
                DefectRecord.id == defect_record_id
            ).first()
            
            if not defect_record:
                return
            
            # 获取构型配置
            defect_list = self.db.query(DefectList).filter(
                DefectList.id == defect_record.defect_list_id
            ).first()
            
            if not defect_list:
                return
            
            # 筛选候选工卡
            candidate_workcards = self.db.query(WorkCard).filter(
                and_(
                    WorkCard.configuration_id == defect_list.configuration_id,
                    WorkCard.is_cleaned == True,
                    or_(
                        WorkCard.system == defect_record.system,
                        WorkCard.component == defect_record.component
                    )
                )
            ).all()
            
            # 计算相似度
            matching_results = []
            for workcard in candidate_workcards:
                similarity_score = self.similarity_service.calculate_similarity(
                    defect_record, workcard, config.field_weights
                )
                
                # 创建匹配结果
                matching_result = MatchingResult(
                    defect_record_id=defect_record_id,
                    workcard_id=workcard.id,
                    similarity_score=similarity_score,
                    is_candidate=similarity_score >= config.similarity_threshold,
                    matching_details=self._generate_matching_details(
                        defect_record, workcard, similarity_score
                    ),
                    algorithm_version=config.algorithm_version
                )
                
                matching_results.append(matching_result)
                
                # 如果是候选工卡，创建候选记录
                if similarity_score >= config.similarity_threshold:
                    candidate = CandidateWorkCard(
                        defect_record_id=defect_record_id,
                        workcard_id=workcard.id,
                        similarity_score=similarity_score
                    )
                    self.db.add(candidate)
            
            # 批量保存匹配结果
            self.db.add_all(matching_results)
            
            # 更新缺陷记录状态
            defect_record.is_matched = True
            
            self.db.commit()
            
        except Exception as e:
            print(f"匹配任务执行失败: {str(e)}")
            self.db.rollback()

    def batch_match_defect_list(
        self,
        defect_list_id: int,
        config: MatchingConfig,
        background_tasks: BackgroundTasks
    ) -> dict:
        """批量匹配缺陷清单"""
        defect_list = self.db.query(DefectList).filter(
            DefectList.id == defect_list_id
        ).first()
        
        if not defect_list:
            raise ValueError("缺陷清单未找到")
        
        # 获取所有未匹配的缺陷记录
        defect_records = self.db.query(DefectRecord).filter(
            and_(
                DefectRecord.defect_list_id == defect_list_id,
                DefectRecord.is_matched == False
            )
        ).all()
        
        # 为每个缺陷记录启动匹配任务
        for defect_record in defect_records:
            background_tasks.add_task(
                self._execute_matching_task,
                defect_record.id,
                config
            )
        
        return {
            "message": f"批量匹配任务已启动，共 {len(defect_records)} 条记录",
            "defect_list_id": defect_list_id,
            "total_records": len(defect_records),
            "status": "processing"
        }

    def get_candidate_workcards(
        self,
        defect_record_id: int,
        threshold: float = 75.0,
        limit: int = 10
    ) -> List[CandidateWorkCard]:
        """获取缺陷记录的候选工卡"""
        return self.db.query(CandidateWorkCard).filter(
            and_(
                CandidateWorkCard.defect_record_id == defect_record_id,
                CandidateWorkCard.similarity_score >= threshold
            )
        ).order_by(desc(CandidateWorkCard.similarity_score)).limit(limit).all()

    def get_matching_results(self, defect_record_id: int) -> List[MatchingResult]:
        """获取缺陷记录的匹配结果"""
        return self.db.query(MatchingResult).filter(
            MatchingResult.defect_record_id == defect_record_id
        ).order_by(desc(MatchingResult.similarity_score)).all()

    def select_candidate_workcard(self, defect_record_id: int, workcard_id: int) -> bool:
        """选择候选工卡"""
        # 更新候选工卡选择状态
        candidate = self.db.query(CandidateWorkCard).filter(
            and_(
                CandidateWorkCard.defect_record_id == defect_record_id,
                CandidateWorkCard.workcard_id == workcard_id
            )
        ).first()
        
        if not candidate:
            return False
        
        candidate.is_selected = True
        
        # 更新缺陷记录
        defect_record = self.db.query(DefectRecord).filter(
            DefectRecord.id == defect_record_id
        ).first()
        
        if defect_record:
            defect_record.is_selected = True
            defect_record.selected_workcard_id = workcard_id
        
        self.db.commit()
        return True

    def get_matching_statistics(self, defect_list_id: int) -> dict:
        """获取匹配统计信息"""
        total_defects = self.db.query(DefectRecord).filter(
            DefectRecord.defect_list_id == defect_list_id
        ).count()
        
        matched_defects = self.db.query(DefectRecord).filter(
            and_(
                DefectRecord.defect_list_id == defect_list_id,
                DefectRecord.is_matched == True
            )
        ).count()
        
        selected_defects = self.db.query(DefectRecord).filter(
            and_(
                DefectRecord.defect_list_id == defect_list_id,
                DefectRecord.is_selected == True
            )
        ).count()
        
        return {
            "total_defects": total_defects,
            "matched_defects": matched_defects,
            "selected_defects": selected_defects,
            "match_rate": (matched_defects / total_defects * 100) if total_defects > 0 else 0,
            "selection_rate": (selected_defects / total_defects * 100) if total_defects > 0 else 0
        }

    def update_algorithm_config(self, config: MatchingConfig) -> dict:
        """更新匹配算法配置"""
        # 这里可以将配置保存到数据库或配置文件
        return {
            "message": "算法配置更新成功",
            "config": config.dict()
        }

    def save_batch_results(
        self,
        results: List[Dict[str, Any]]
    ) -> None:
        """将批量匹配结果保存到数据库"""
        if not results:
            return

        for item in results:
            defect_record_id = item.get("defect_record_id")
            if not defect_record_id:
                continue

            candidates = item.get("candidates", [])

            # 删除旧的候选与匹配结果
            self.db.query(CandidateWorkCard).filter(
                CandidateWorkCard.defect_record_id == defect_record_id
            ).delete(synchronize_session=False)

            self.db.query(MatchingResult).filter(
                MatchingResult.defect_record_id == defect_record_id
            ).delete(synchronize_session=False)

            # 若已有选择但不在新结果中，重置
            defect_record = self.db.query(DefectRecord).filter(
                DefectRecord.id == defect_record_id
            ).first()
            if defect_record and defect_record.selected_workcard_id:
                if not any(c.get("id") == defect_record.selected_workcard_id for c in candidates):
                    defect_record.selected_workcard_id = None
                    defect_record.is_selected = False

            # 保存新的候选与匹配结果
            for candidate in candidates:
                workcard_id = candidate.get("id")
                if not workcard_id:
                    continue

                matching_details = {
                    "matching_reasons": candidate.get("matching_reasons", []),
                    "field_matches": candidate.get("field_matches", {})
                }
                matching_result = MatchingResult(
                    defect_record_id=defect_record_id,
                    workcard_id=workcard_id,
                    similarity_score=candidate.get("similarity_score", 0.0),
                    is_candidate=True,
                    matching_details=matching_details
                )
                self.db.add(matching_result)

                candidate_entry = CandidateWorkCard(
                    defect_record_id=defect_record_id,
                    workcard_id=workcard_id,
                    similarity_score=candidate.get("similarity_score", 0.0)
                )
                self.db.add(candidate_entry)

            if defect_record:
                defect_record.is_matched = True

        self.db.commit()

    def get_available_batch_contexts(self) -> List[Dict[str, Any]]:
        """获取可用于批量开卡调试的上下文信息"""
        query = (
            self.db.query(
                DefectList.id.label("defect_list_id"),
                DefectList.title.label("defect_list_title"),
                DefectList.aircraft_number.label("defect_list_aircraft_number"),
                WorkCard.configuration_id.label("configuration_id"),
                WorkCard.aircraft_number.label("workcard_aircraft_number"),
                WorkCard.aircraft_type.label("workcard_aircraft_type"),
                WorkCard.msn.label("workcard_msn"),
                WorkCard.amm_ipc_eff.label("workcard_amm_ipc_eff"),
                func.count(distinct(CandidateWorkCard.defect_record_id)).label("defect_count"),
                func.count(CandidateWorkCard.id).label("candidate_count"),
                func.max(CandidateWorkCard.created_at).label("latest_candidate_at")
            )
            .join(DefectRecord, DefectRecord.defect_list_id == DefectList.id)
            .join(CandidateWorkCard, CandidateWorkCard.defect_record_id == DefectRecord.id)
            .join(WorkCard, WorkCard.id == CandidateWorkCard.workcard_id)
            .group_by(
                DefectList.id,
                DefectList.title,
                DefectList.aircraft_number,
                WorkCard.configuration_id,
                WorkCard.aircraft_number,
                WorkCard.aircraft_type,
                WorkCard.msn,
                WorkCard.amm_ipc_eff
            )
            .order_by(func.max(CandidateWorkCard.created_at).desc())
        )

        contexts: List[Dict[str, Any]] = []
        for row in query.all():
            contexts.append({
                "defect_list": {
                    "id": row.defect_list_id,
                    "title": row.defect_list_title,
                    "aircraft_number": row.defect_list_aircraft_number
                },
                "workcard_group": {
                    "configuration_id": row.configuration_id,
                    "aircraft_number": row.workcard_aircraft_number,
                    "aircraft_type": row.workcard_aircraft_type,
                    "msn": row.workcard_msn,
                    "amm_ipc_eff": row.workcard_amm_ipc_eff
                },
                "defect_count": row.defect_count or 0,
                "candidate_count": row.candidate_count or 0,
                "latest_candidate_at": row.latest_candidate_at
            })
        return contexts

    def get_saved_match_results(
        self,
        defect_list_id: int,
        configuration_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """从数据库中获取已保存的匹配结果"""
        defect_records_query = self.db.query(DefectRecord).filter(
            DefectRecord.defect_list_id == defect_list_id
        )

        if configuration_id is not None:
            defect_records_query = defect_records_query.join(
                CandidateWorkCard,
                CandidateWorkCard.defect_record_id == DefectRecord.id
            ).join(
                WorkCard,
                WorkCard.id == CandidateWorkCard.workcard_id
            ).filter(
                WorkCard.configuration_id == configuration_id
            ).distinct(DefectRecord.id)

        defect_records = defect_records_query.all()
        results: List[Dict[str, Any]] = []

        for record in defect_records:
            candidates_query = self.db.query(CandidateWorkCard, WorkCard).join(
                WorkCard,
                WorkCard.id == CandidateWorkCard.workcard_id
            ).filter(
                CandidateWorkCard.defect_record_id == record.id
            ).order_by(desc(CandidateWorkCard.similarity_score))

            if configuration_id is not None:
                candidates_query = candidates_query.filter(
                    WorkCard.configuration_id == configuration_id
                )

            candidates_data = []
            for candidate, workcard in candidates_query.all():
                candidates_data.append({
                    "id": workcard.id,
                    "workcard_number": workcard.workcard_number,
                    "description": workcard.description,
                    "similarity_score": candidate.similarity_score,
                    "is_selected": candidate.is_selected,
                })

            if not candidates_data:
                continue

            descriptions = self._extract_descriptions(record)
            description_cn = descriptions["description_cn"]
            description_en = descriptions["description_en"]

            results.append({
                "defect_record_id": record.id,
                "defect_number": record.defect_number,
                "description_cn": description_cn or record.description or record.title,
                "description_en": description_en,
                "candidates": candidates_data,
                "selected_workcard_id": record.selected_workcard_id,
                "issued_workcard_number": record.issued_workcard_number  # 已开出的工卡号
            })

        return results

    def _generate_matching_details(
        self,
        defect_record: DefectRecord,
        workcard: WorkCard,
        similarity_score: float
    ) -> Dict[str, Any]:
        """生成匹配详情"""
        return {
            "system_match": defect_record.system == workcard.system,
            "component_match": defect_record.component == workcard.component,
            "description_similarity": similarity_score,
            "matching_fields": {
                "defect_system": defect_record.system,
                "workcard_system": workcard.system,
                "defect_component": defect_record.component,
                "workcard_component": workcard.component
            }
        }

