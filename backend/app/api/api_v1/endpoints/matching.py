from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging
import asyncio
import uuid
from app.core.database import get_db
from app.core.redis import set_matching_progress, get_matching_progress
from app.schemas.matching import (
    MatchingResultResponse, CandidateWorkCardResponse,
    MatchingRequest, MatchingConfig
)
from app.services.matching_service import MatchingService

router = APIRouter()

@router.post("/defect/{defect_record_id}/match")
def match_defect_record(
    defect_record_id: int,
    config: MatchingConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """为缺陷记录执行匹配"""
    service = MatchingService(db)
    return service.match_defect_record(defect_record_id, config, background_tasks)

@router.post("/defect-list/{defect_list_id}/batch-match")
def batch_match_defect_list(
    defect_list_id: int,
    config: MatchingConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量匹配缺陷清单"""
    service = MatchingService(db)
    return service.batch_match_defect_list(defect_list_id, config, background_tasks)

@router.post("/batch-match")
def batch_match_defect_list_new(
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量匹配缺陷数据与工卡数据（新接口）"""
    from pydantic import BaseModel
    from app.services.defect_service import DefectService
    from app.services.workcard_service import WorkCardService
    from app.services.llm_provider_manager import get_service_for_current_model
    
    logger = logging.getLogger(__name__)
    
    try:
        class MatchDefectRequest(BaseModel):
            defect_list_id: int
            workcard_group: dict
        
        req = MatchDefectRequest(**request)
        
        # 获取缺陷记录
        defect_service = DefectService(db)
        defect_records = defect_service.get_defect_records(req.defect_list_id)
        
        # 刷新所有记录，确保从数据库重新加载最新的raw_data（包含清洗后的字段）
        for record in defect_records:
            db.refresh(record)
            logger.debug(f"刷新缺陷记录 {record.id}，raw_data类型: {type(record.raw_data)}")
        
        if not defect_records:
            return {
                "success": False,
                "message": "未找到缺陷记录",
                "results": []
            }
        
        # 获取工卡分组下的所有工卡
        workcard_service = WorkCardService(db)
        all_workcards = workcard_service.get_workcards_by_group(
            aircraft_number=req.workcard_group.get("aircraft_number"),
            aircraft_type=req.workcard_group.get("aircraft_type"),
            msn=req.workcard_group.get("msn"),
            amm_ipc_eff=req.workcard_group.get("amm_ipc_eff"),
            configuration_id=req.workcard_group.get("configuration_id")
        )
        
        if not all_workcards:
            return {
                "success": False,
                "message": "未找到工卡数据",
                "results": []
            }
        
        logger.info(f"开始匹配，缺陷记录数: {len(defect_records)}, 工卡总数: {len(all_workcards)}")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化进度
        initial_progress = {
            "task_id": task_id,
            "status": "processing",
            "total": len(defect_records),
            "completed": 0,
            "current": None,
            "statistics": {
                "matched": 0,
                "failed": 0,
                "candidates_found": 0
            }
        }
        set_matching_progress(task_id, initial_progress)
        
        # 获取当前选择的大模型服务
        llm_service = get_service_for_current_model()
        
        # 在后台执行匹配任务
        background_tasks.add_task(
            _batch_match_with_llm_sync,
            task_id,
            defect_records,
            all_workcards,
            llm_service,
            db,
            logger
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "匹配任务已启动",
            "total": len(defect_records)
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"匹配错误: {str(e)}")
        logger.error(f"错误详情: {error_detail}")
        return {
            "success": False,
            "message": f"匹配失败: {str(e)}",
            "results": [],
            "error": str(e)
        }


def _batch_match_with_llm_sync(
    task_id: str,
    defect_records,
    all_workcards,
    llm_service,
    db: Session,
    logger
):
    """使用大模型批量匹配缺陷记录与工卡（同步版本，支持进度更新）"""
    results = []
    total = len(defect_records)
    matched_count = 0
    failed_count = 0
    total_candidates = 0
    
    try:
        for idx, defect_record in enumerate(defect_records):
            # 更新进度
            current_progress = {
                "task_id": task_id,
                "status": "processing",
                "total": total,
                "completed": idx,
                "current": {
                    "defect_id": defect_record.id,
                    "defect_number": defect_record.defect_number,
                    "description": (defect_record.description or defect_record.title or "")[:50] + ("..." if len(defect_record.description or defect_record.title or "") > 50 else "")
                },
                "statistics": {
                    "matched": matched_count,
                    "failed": failed_count,
                    "candidates_found": total_candidates
                }
            }
            set_matching_progress(task_id, current_progress)
            
            try:
                logger.info(f"匹配缺陷记录 {idx + 1}/{len(defect_records)}, 缺陷编号: {defect_record.defect_number}")
                
                # 从 DefectCleanedData 表中获取清洗后的9个字段（优先）
                # 如果没有，则从 raw_data 中提取（向后兼容）
                from app.models.defect_cleaned import DefectCleanedData
                
                defect_cleaned_fields = {}
                description_cn = ""
                description_en = ""
                
                # 优先从 DefectCleanedData 表读取
                cleaned_data = db.query(DefectCleanedData).filter(
                    DefectCleanedData.defect_record_id == defect_record.id
                ).first()
                
                if cleaned_data:
                    defect_cleaned_fields = {
                        "main_area": cleaned_data.main_area or '',
                        "main_component": cleaned_data.main_component or '',
                        "first_level_subcomponent": cleaned_data.first_level_subcomponent or '',
                        "second_level_subcomponent": cleaned_data.second_level_subcomponent or '',
                        "orientation": cleaned_data.orientation or '',
                        "defect_subject": cleaned_data.defect_subject or '',
                        "defect_description": cleaned_data.defect_description or '',
                        "location": cleaned_data.location or '',
                        "quantity": cleaned_data.quantity or ''
                    }
                    description_cn = cleaned_data.description_cn or ''
                    logger.info(f"从 DefectCleanedData 表读取清洗字段: main_area='{defect_cleaned_fields.get('main_area', '')}', main_component='{defect_cleaned_fields.get('main_component', '')}', first_level_subcomponent='{defect_cleaned_fields.get('first_level_subcomponent', '')}'")
                else:
                    # 向后兼容：从 raw_data 中提取
                    logger.warning(f"缺陷记录 {defect_record.id} 没有 DefectCleanedData 记录，尝试从 raw_data 读取")
                    if defect_record.raw_data and isinstance(defect_record.raw_data, dict):
                        defect_cleaned_fields = {
                            "main_area": defect_record.raw_data.get('main_area', ''),
                            "main_component": defect_record.raw_data.get('main_component', ''),
                            "first_level_subcomponent": defect_record.raw_data.get('first_level_subcomponent', ''),
                            "second_level_subcomponent": defect_record.raw_data.get('second_level_subcomponent', ''),
                            "orientation": defect_record.raw_data.get('orientation', ''),
                            "defect_subject": defect_record.raw_data.get('defect_subject', ''),
                            "defect_description": defect_record.raw_data.get('defect_description', ''),
                            "location": defect_record.raw_data.get('location', ''),
                            "quantity": defect_record.raw_data.get('quantity', '')
                        }
                        logger.info(f"从raw_data中提取的清洗字段: main_area='{defect_cleaned_fields.get('main_area', '')}', main_component='{defect_cleaned_fields.get('main_component', '')}'")
                    else:
                        logger.warning(f"缺陷记录 {defect_record.id} (缺陷编号: {defect_record.defect_number}) 的raw_data为空或不是字典类型")

                description_data = MatchingService._extract_descriptions(defect_record)
                if description_data["description_cn"]:
                    description_cn = description_data["description_cn"]
                elif not description_cn:
                    description_cn = json.dumps(defect_cleaned_fields, ensure_ascii=False, indent=2)
                    logger.info(f"使用清洗后的9个字段构建工卡描述（中文）JSON: {description_cn[:200]}...")
                else:
                    description_cn = description_cn.strip()

                description_en = description_data["description_en"]
                
                # 分步筛选策略：逐步缩小候选工卡范围，减少向大模型提交的数据量
                # 第一步：主区域筛选（粗筛选）
                # 第二步：主部件筛选（中筛选）
                # 第三步：一级子部件筛选（细筛选）
                
                main_area = defect_cleaned_fields.get('main_area', '').strip()
                main_component = defect_cleaned_fields.get('main_component', '').strip()
                first_level_subcomponent = defect_cleaned_fields.get('first_level_subcomponent', '').strip()
                
                logger.info(f"开始分步筛选，初始工卡数量: {len(all_workcards)}")
                logger.info(f"缺陷记录字段 - 主区域: {main_area}, 主部件: {main_component}, 一级子部件: {first_level_subcomponent}")
                
                # 辅助函数：检查字段匹配（支持中英文同义词和部分匹配）
                def field_match(defect_field: str, workcard_field: str, strict: bool = False) -> bool:
                    """
                    检查字段是否匹配，支持包含关系和同义词
                    strict=True: 严格模式，主区域必须完全匹配或同义词匹配，不允许包含关系
                    strict=False: 宽松模式，允许包含关系匹配
                    """
                    if not defect_field or not workcard_field:
                        return False
                    
                    # 完全匹配
                    if defect_field == workcard_field:
                        return True
                    
                    # 同义词匹配（优先检查）
                    synonyms_map = {
                        '驾驶舱': ['Cockpit', '驾驶室', '驾驶舱区域'],
                        '客舱': ['Cabin', '客舱区域'],
                        '座椅': ['Seat', '座位'],
                        '安全带': ['Safety Belt', 'Seat Belt', '安全扣带']
                    }
                    for key, synonyms in synonyms_map.items():
                        if defect_field == key and workcard_field in synonyms:
                            return True
                        if workcard_field == key and defect_field in synonyms:
                            return True
                    
                    # 如果是严格模式（主区域匹配），不允许包含关系匹配
                    if strict:
                        return False
                    
                    # 包含关系匹配（仅用于非主区域字段）
                    # 只有当其中一个字段是另一个字段的子串时才匹配
                    if defect_field in workcard_field or workcard_field in defect_field:
                        return True
                    
                    return False
                
                # 第一步：主区域筛选（粗筛选）- 必须严格匹配
                step1_workcards = []
                if main_area:
                    for workcard in all_workcards:
                        workcard_main_area = (workcard.main_area or '').strip()
                        # 主区域必须严格匹配（完全匹配或同义词匹配，不允许包含关系）
                        if workcard_main_area and field_match(main_area, workcard_main_area, strict=True):
                            step1_workcards.append(workcard)
                    logger.info(f"第一步（主区域筛选，严格模式）后工卡数量: {len(step1_workcards)}")
                    if len(step1_workcards) == 0:
                        logger.warning(f"缺陷记录 {defect_record.defect_number} 主区域 '{main_area}' 没有匹配到任何工卡，返回空结果")
                        results.append({
                            "defect_record_id": defect_record.id,
                            "defect_number": defect_record.defect_number,
                            "description_cn": description_cn,
                            "description_en": description_en,
                            "candidates": []
                        })
                        continue
                else:
                    logger.warning(f"缺陷记录 {defect_record.defect_number} 没有主区域，无法进行匹配（主区域是必填字段）")
                    results.append({
                        "defect_record_id": defect_record.id,
                        "defect_number": defect_record.defect_number,
                        "description_cn": description_cn,
                        "description_en": description_en,
                        "candidates": []
                    })
                    continue
                
                # 如果第一步筛选后数量<=20，直接进入大模型匹配
                if len(step1_workcards) <= 20:
                    filtered_workcards = step1_workcards
                    logger.info(f"第一步筛选后工卡数量({len(filtered_workcards)})<=20，直接进入大模型匹配")
                else:
                    # 第二步：主部件筛选（中筛选）
                    step2_workcards = []
                    if main_component:
                        priority1 = []  # 主区域+主部件都匹配
                        priority2 = []  # 只有主区域匹配
                        
                        for workcard in step1_workcards:
                            workcard_main_component = (workcard.main_component or '').strip()
                            if workcard_main_component and field_match(main_component, workcard_main_component):
                                priority1.append(workcard)
                            else:
                                priority2.append(workcard)
                        
                        # 优先使用主区域+主部件都匹配的
                        # 如果数量不足5条，可以补充一些只有主区域匹配的工卡（但不超过10条）
                        if priority1:
                            step2_workcards = priority1
                            if len(step2_workcards) < 5 and priority2:
                                # 只补充到5条，确保至少有基本的候选数量，但不要太多不匹配的
                                step2_workcards.extend(priority2[:5 - len(step2_workcards)])
                            logger.info(f"第二步（主部件筛选）后工卡数量: {len(step2_workcards)} (主区域+主部件匹配: {len(priority1)}, 仅主区域匹配: {len(priority2)})")
                        else:
                            # 如果主部件都不匹配，只保留少量只有主区域匹配的工卡（最多10条）
                            step2_workcards = priority2[:10] if priority2 else []
                            logger.warning(f"第二步（主部件筛选）没有匹配的工卡，只保留 {len(step2_workcards)} 条仅主区域匹配的工卡")
                    else:
                        step2_workcards = step1_workcards[:30]  # 如果没有主部件，保留前30条
                        logger.warning(f"缺陷记录 {defect_record.defect_number} 没有主部件，跳过第二步筛选，保留前30条")
                    
                    # 如果第二步筛选后数量<=20，直接进入大模型匹配
                    if len(step2_workcards) <= 20:
                        filtered_workcards = step2_workcards
                        logger.info(f"第二步筛选后工卡数量({len(filtered_workcards)})<=20，直接进入大模型匹配")
                    else:
                        # 第三步：一级子部件筛选（细筛选）
                        step3_workcards = []
                        if first_level_subcomponent:
                            priority1 = []  # 主区域+主部件+一级子部件都匹配
                            priority2 = []  # 主区域+主部件匹配（但一级子部件不匹配）
                            
                            for workcard in step2_workcards:
                                workcard_first_level = (workcard.first_level_subcomponent or '').strip()
                                if workcard_first_level and field_match(first_level_subcomponent, workcard_first_level):
                                    priority1.append(workcard)
                                else:
                                    priority2.append(workcard)
                            
                            # 优先使用主区域+主部件+一级子部件都匹配的
                            # 如果数量不足5条，可以补充一些主区域+主部件匹配的工卡（但不超过10条）
                            if priority1:
                                step3_workcards = priority1
                                if len(step3_workcards) < 5 and priority2:
                                    # 只补充到5条，确保至少有基本的候选数量
                                    step3_workcards.extend(priority2[:5 - len(step3_workcards)])
                                logger.info(f"第三步（一级子部件筛选）后工卡数量: {len(step3_workcards)} (全部匹配: {len(priority1)}, 部分匹配: {len(priority2)})")
                            else:
                                # 如果一级子部件都不匹配，只保留少量主区域+主部件匹配的工卡（最多10条）
                                step3_workcards = priority2[:10] if priority2 else []
                                logger.warning(f"第三步（一级子部件筛选）没有匹配的工卡，只保留 {len(step3_workcards)} 条主区域+主部件匹配的工卡")
                        else:
                            step3_workcards = step2_workcards[:20]  # 如果没有一级子部件，保留前20条
                            logger.warning(f"缺陷记录 {defect_record.defect_number} 没有一级子部件，跳过第三步筛选，保留前20条")
                        
                        filtered_workcards = step3_workcards
                        logger.info(f"第三步筛选后工卡数量: {len(filtered_workcards)}")
                
                logger.info(f"最终筛选后工卡数量: {len(filtered_workcards)} (从 {len(all_workcards)} 条减少到 {len(filtered_workcards)} 条，减少 {((1 - len(filtered_workcards)/len(all_workcards)) * 100):.1f}%)")
                
                if not filtered_workcards:
                    logger.warning(f"缺陷记录 {defect_record.defect_number} 没有筛选到匹配的工卡（主区域: {main_area}, 主部件: {main_component}）")
                    # 如果没有筛选到工卡，返回空结果
                    results.append({
                        "defect_record_id": defect_record.id,
                        "defect_number": defect_record.defect_number,
                        "description_cn": description_cn,  # 工卡描述（中文）
                        "description_en": description_en,
                        "candidates": []
                    })
                    continue
                
                # 第二步：将缺陷记录的9个字段组合成JSON，准备传递给大模型
                defect_json = json.dumps(defect_cleaned_fields, ensure_ascii=False)
                logger.debug(f"缺陷记录JSON: {defect_json}")
                
                # 第三步：将筛选后的工卡也组合成JSON列表，传递给大模型
                workcard_json_list = []
                for workcard in filtered_workcards:
                    workcard_fields = {
                        "id": workcard.id,
                        "workcard_number": workcard.workcard_number,
                        "description": workcard.description or workcard.title or "",
                        "main_area": workcard.main_area or "",
                        "main_component": workcard.main_component or "",
                        "first_level_subcomponent": workcard.first_level_subcomponent or "",
                        "second_level_subcomponent": workcard.second_level_subcomponent or "",
                        "orientation": workcard.orientation or "",
                        "defect_subject": workcard.defect_subject or "",
                        "defect_description": workcard.defect_description or "",
                        "location_index": workcard.location_index or "",
                        "quantity": workcard.quantity or ""
                    }
                    workcard_json_list.append(workcard_fields)
                
                logger.info(f"准备调用大模型，缺陷记录 {defect_record.defect_number}，候选工卡数: {len(workcard_json_list)}")
                
                # 第四步：调用大模型进行对比
                candidates = _match_with_llm(
                    defect_json,
                    workcard_json_list,
                    description_cn,  # 使用description_cn作为工卡描述（中文）
                    llm_service,
                    logger
                )
                
                logger.info(f"大模型返回候选工卡数: {len(candidates)}")
                
                # 记录最终返回的工卡描述（中文）值
                logger.info(f"缺陷记录 {defect_record.id} (缺陷编号: {defect_record.defect_number}) 的工卡描述（中文）: {description_cn[:200] if description_cn else '(空)'}")

                description_data = MatchingService._extract_descriptions(defect_record)
                description_en = description_data["description_en"]
                result_item = {
                    "defect_record_id": defect_record.id,
                    "defect_number": defect_record.defect_number,
                    "description_cn": description_cn,  # 工卡描述（中文）- 从清洗后的raw_data中获取
                    "description_en": description_en,
                    "candidates": candidates
                }
                logger.info(f"返回的匹配结果项: {json.dumps(result_item, ensure_ascii=False, default=str)[:500]}")
                results.append(result_item)
                
                # 更新统计信息
                if len(candidates) > 0:
                    matched_count += 1
                    total_candidates += len(candidates)
            
            except Exception as e:
                logger.error(f"匹配缺陷记录 {defect_record.id} 失败: {str(e)}", exc_info=True)
                failed_count += 1
                # 如果匹配失败，返回空结果
                # 尝试获取工卡描述（中文）
                description_data = MatchingService._extract_descriptions(defect_record)
                failed_description_cn = description_data["description_cn"]
                failed_description_en = description_data["description_en"]
                
                results.append({
                    "defect_record_id": defect_record.id,
                    "defect_number": defect_record.defect_number,
                    "description_cn": failed_description_cn,  # 工卡描述（中文）
                    "description_en": failed_description_en,
                    "candidates": []
                })
        
            # 更新最终进度（每处理完一条记录）
            final_progress = {
                "task_id": task_id,
                "status": "processing",
                "total": total,
                "completed": idx + 1,
                "current": {
                    "defect_id": defect_record.id,
                    "defect_number": defect_record.defect_number,
                    "description": (defect_record.description or defect_record.title or "")[:50] + ("..." if len(defect_record.description or defect_record.title or "") > 50 else "")
                },
                "statistics": {
                    "matched": matched_count,
                    "failed": failed_count,
                    "candidates_found": total_candidates
                }
            }
            set_matching_progress(task_id, final_progress)
    
    except Exception as e:
        logger.error(f"匹配任务循环执行失败: {str(e)}", exc_info=True)
        error_progress = {
            "task_id": task_id,
            "status": "failed",
            "total": total,
            "completed": 0,
            "current": None,
            "statistics": {
                "matched": matched_count,
                "failed": failed_count,
                "candidates_found": total_candidates
            },
            "error": f"任务执行中断: {str(e)}"
        }
        set_matching_progress(task_id, error_progress, expire_seconds=7200)
        return []

    # 匹配完成，保存结果
    try:
        matching_service = MatchingService(db)
        matching_service.save_batch_results(results)
        
        # 更新完成状态
        completed_progress = {
            "task_id": task_id,
            "status": "completed",
            "total": total,
            "completed": total,
            "current": None,
            "statistics": {
                "matched": matched_count,
                "failed": failed_count,
                "candidates_found": total_candidates
            }
        }
        set_matching_progress(task_id, completed_progress, expire_seconds=7200)  # 完成后保存2小时
        logger.info(f"匹配任务 {task_id} 完成，共处理 {total} 条记录，匹配成功 {matched_count} 条，失败 {failed_count} 条")
    except Exception as e:
        logger.error(f"保存匹配结果失败: {str(e)}", exc_info=True)
        # 即使保存失败，也更新进度状态为失败
        error_progress = {
            "task_id": task_id,
            "status": "failed",
            "total": total,
            "completed": total,
            "current": None,
            "statistics": {
                "matched": matched_count,
                "failed": failed_count,
                "candidates_found": total_candidates
            },
            "error": str(e)
        }
        set_matching_progress(task_id, error_progress, expire_seconds=7200)


@router.get("/batch-contexts")
def get_batch_contexts(
    db: Session = Depends(get_db)
):
    """获取可用于批量开卡调试的上下文列表"""
    service = MatchingService(db)
    return service.get_available_batch_contexts()


@router.get("/saved-results")
def get_saved_results(
    defect_list_id: int,
    configuration_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取已保存的缺陷匹配结果"""
    service = MatchingService(db)
    results = service.get_saved_match_results(defect_list_id, configuration_id)
    return {
        "success": True,
        "results": results
    }

@router.get("/progress/{task_id}")
def get_matching_progress_endpoint(task_id: str):
    """获取匹配进度"""
    progress = get_matching_progress(task_id)
    if not progress:
        return {
            "status": "not_found",
            "message": "任务不存在或已过期"
        }
    return progress


def _match_with_llm(
    defect_json: str,
    workcard_json_list: list,
    defect_description: str,
    llm_service,
    logger
):
    """使用大模型对比缺陷记录和工卡列表，返回候选工卡"""
    # 辅助函数：检查字段匹配（用于后处理验证）
    def field_match(defect_field: str, workcard_field: str, strict: bool = False) -> bool:
        """检查字段是否匹配，支持包含关系和同义词"""
        if not defect_field or not workcard_field:
            return False
        if defect_field == workcard_field:
            return True
        synonyms_map = {
            '驾驶舱': ['Cockpit', '驾驶室', '驾驶舱区域'],
            '客舱': ['Cabin', '客舱区域'],
            '座椅': ['Seat', '座位'],
            '安全带': ['Safety Belt', 'Seat Belt', '安全扣带']
        }
        for key, synonyms in synonyms_map.items():
            if defect_field == key and workcard_field in synonyms:
                return True
            if workcard_field == key and defect_field in synonyms:
                return True
        if strict:
            return False
        if defect_field in workcard_field or workcard_field in defect_field:
            return True
        return False
    
    try:
        # 如果工卡列表为空，直接返回
        if not workcard_json_list or len(workcard_json_list) == 0:
            logger.warning("工卡列表为空，无法进行匹配")
            return []
        
        # 筛选后的工卡列表应该已经通过分步筛选控制在20条以内
        if len(workcard_json_list) > 30:
            logger.warning(f"筛选后的工卡列表仍然较长({len(workcard_json_list)}条)，建议进一步优化筛选逻辑")
        
        # 构建提示词（优化版：参考清洗阶段的优化）
        workcard_list_str = json.dumps(workcard_json_list, ensure_ascii=False, indent=2)
        
        prompt = f"""
【匹配任务】
你是一个专业的航空维修数据匹配专家。请根据以下目标缺陷记录，从候选工卡列表中选出最匹配的5条工卡。

【目标缺陷记录】（清洗后的9个字段，JSON格式）：
{defect_json}

【目标缺陷记录的原始描述】（工卡描述中文）：
{defect_description}

【候选工卡列表】（共 {len(workcard_json_list)} 条，已通过主区域/主部件/一级子部件筛选，JSON数组格式）：
{workcard_list_str}

【匹配规则和权重】：

**字段权重（用于计算相似度）**：
1. 主区域：10%
2. 主部件：15%
3. 一级子部件：20%
4. 二级子部件：35%（最重要）
5. 方位：5%
6. 缺陷主体：10%
7. 缺陷描述：5%

**匹配优先级（必须严格遵守）**：
1. 优先级1：主区域+主部件+二级子部件都匹配 → 相似度80-100分
2. 优先级2：主区域+主部件匹配 → 相似度60-79分
3. 优先级3：主区域匹配 → 相似度40-59分
4. **重要约束**：
   - 如果主区域不匹配，相似度必须为0分，不能返回该工卡
   - 如果主区域匹配但主部件不匹配，相似度不能超过60分
   - 必须严格遵循层级递进关系，不能跨层级匹配

**语义匹配规则（严格限制）**：
1. 支持中英文同义词识别，例如：
   - 驾驶舱 = Cockpit = 驾驶室 = 驾驶舱区域
   - 客舱 = Cabin = 客舱区域
   - 座椅 = Seat = 座位
   - 安全带 = Safety Belt = Seat Belt = 安全扣带
2. **主区域匹配必须严格**：
   - 主区域必须完全匹配或同义词匹配
   - "客舱"不能匹配"驾驶舱"，"驾驶舱"不能匹配"客舱"
   - 不同主区域之间不能进行语义匹配
3. **主部件和子部件匹配**：
   - 支持部分匹配：如果描述中包含索引数据中的关键词，可以进行部分匹配
   - 但必须在同一主区域下进行匹配
4. **严格约束**：
   - 不能跨主区域匹配（例如：客舱的部件不能匹配驾驶舱的工卡）
   - 语义理解不能违反层级递进关系

**匹配步骤**：
1. 首先检查主区域是否匹配（支持同义词）
2. 然后检查主部件是否匹配（支持同义词）
3. 再检查一级子部件是否匹配（支持同义词）
4. 重点检查二级子部件是否匹配（权重最高）
5. 最后检查其他字段（方位、缺陷主体、缺陷描述等）
6. 根据匹配的字段和权重计算相似度分数

【匹配示例】：

示例1：
目标缺陷记录：
{{
  "main_area": "驾驶舱",
  "main_component": "第三观察员座椅",
  "first_level_subcomponent": "安全带",
  "second_level_subcomponent": "",
  "defect_subject": "TSO",
  "defect_description": "模糊"
}}

候选工卡1：
{{
  "id": 1,
  "main_area": "驾驶舱",
  "main_component": "第三观察员座椅",
  "first_level_subcomponent": "安全带",
  "second_level_subcomponent": ""
}}
→ 匹配结果：相似度95分（主区域+主部件+一级子部件完全匹配）

候选工卡2：
{{
  "id": 2,
  "main_area": "驾驶舱",
  "main_component": "第三观察员座椅",
  "first_level_subcomponent": "座椅垫"
}}
→ 匹配结果：相似度70分（主区域+主部件匹配，但一级子部件不匹配）

【输出要求】：
请返回JSON格式的结果，包含相似度评分最高的前5个候选工卡：

{{
    "candidates": [
        {{
            "id": 工卡ID（整数）,
            "workcard_number": "工卡指令号（字符串）",
            "description": "工卡描述（字符串）",
            "similarity_score": 相似度分数（0-100的浮点数）,
            "matching_reasons": ["匹配原因1（字符串）", "匹配原因2（字符串）"],
            "field_matches": {{
                "main_area": true/false,
                "main_component": true/false,
                "first_level_subcomponent": true/false,
                "second_level_subcomponent": true/false,
                "orientation": true/false,
                "defect_subject": true/false,
                "defect_description": true/false
            }}
        }},
        ...
    ]
}}

【重要提示】：
1. 只返回JSON格式，不要添加任何其他说明文字、注释或markdown标记
2. 确保返回的JSON格式正确，可以被直接解析
3. 至少返回1个候选工卡（即使相似度较低）
4. 相似度分数必须是0-100之间的数字
5. 必须严格遵循层级递进关系，不能跨层级匹配
6. 支持语义匹配和同义词识别，不要求完全一致
"""
        
        logger.info(f"开始调用大模型进行匹配，候选工卡数: {len(workcard_json_list)}")
        logger.debug(f"提示词长度: {len(prompt)}")
        
        system_prompt = "你是一个专业的航空维修数据匹配专家，擅长分析缺陷记录与工卡记录的相似度。你必须严格遵守以下规则：1. 层级递进匹配规则（主区域→主部件→一级子部件→二级子部件），不能跨层级匹配；2. 主区域必须严格匹配，不同主区域之间不能匹配（例如：'客舱'不能匹配'驾驶舱'）；3. 如果主区域不匹配，相似度必须为0分；4. 支持中英文同义词识别（例如：'驾驶舱'可以匹配'Cockpit'、'驾驶室'），但必须在同一主区域下；5. 相似度评分必须准确反映匹配程度，不能给不匹配的工卡高分。"
        
        response = llm_service.generate_text(
            prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=3000
        )
        
        logger.info(f"大模型API调用完成，success: {response.get('success')}")
        
        if not response.get("success"):
            error_msg = response.get('error', '未知错误')
            logger.error(f"大模型调用失败: {error_msg}")
            logger.error(f"大模型响应: {response}")
            return []
        
        response_text = response.get("text", "")
        logger.info(f"大模型返回文本长度: {len(response_text)}")
        logger.debug(f"大模型返回文本前1000字符: {response_text[:1000]}")
        
        # 解析大模型返回的JSON
        json_result = llm_service.parse_json_response(response_text)
        if not json_result.get("success"):
            error_msg = json_result.get('error', '未知错误')
            logger.error(f"JSON解析失败: {error_msg}")
            logger.error(f"原始文本前1000字符: {response_text[:1000]}")
            logger.error(f"原始文本完整内容: {response_text}")
            return []
        
        candidates_data = json_result.get("data", {})
        logger.info(f"解析后的数据: {json.dumps(candidates_data, ensure_ascii=False, indent=2)[:500]}")
        
        if not candidates_data:
            logger.warning("大模型返回的数据为空")
            logger.warning(f"原始响应文本: {response_text}")
            return []
        
        candidates = candidates_data.get("candidates", [])
        if not candidates:
            logger.warning("大模型返回的候选工卡列表为空")
            logger.warning(f"解析后的完整数据: {json.dumps(candidates_data, ensure_ascii=False, indent=2)}")
            logger.warning(f"原始响应文本: {response_text}")
            return []
        
        logger.info(f"大模型返回了 {len(candidates)} 个候选工卡")
        
        # 解析缺陷记录的主区域（用于验证匹配结果）
        try:
            defect_data = json.loads(defect_json)
            defect_main_area = defect_data.get('main_area', '').strip()
        except:
            defect_main_area = ''
        
        # 确保返回的候选工卡格式正确，并验证主区域匹配
        formatted_candidates = []
        for candidate in candidates:
            try:
                candidate_id = int(candidate.get("id", 0))
                similarity_score = float(candidate.get("similarity_score", 0.0))
                
                # 验证主区域匹配：如果缺陷记录有主区域，必须与工卡的主区域匹配
                if defect_main_area:
                    # 从工卡列表中查找该工卡的主区域
                    workcard_data = next((w for w in workcard_json_list if w.get('id') == candidate_id), None)
                    if workcard_data:
                        workcard_main_area = (workcard_data.get('main_area') or '').strip()
                        # 检查主区域是否匹配（严格模式）
                        if workcard_main_area and not field_match(defect_main_area, workcard_main_area, strict=True):
                            logger.warning(f"过滤掉主区域不匹配的工卡: ID={candidate_id}, 缺陷主区域='{defect_main_area}', 工卡主区域='{workcard_main_area}', 相似度={similarity_score}")
                            continue
                        # 如果主区域不匹配，强制将相似度设为0
                        if not workcard_main_area or not field_match(defect_main_area, workcard_main_area, strict=True):
                            similarity_score = 0.0
                            logger.warning(f"工卡 {candidate_id} 主区域不匹配，将相似度设为0")
                
                formatted_candidates.append({
                    "id": candidate_id,
                    "workcard_number": candidate.get("workcard_number", ""),
                    "description": candidate.get("description", ""),
                    "similarity_score": similarity_score,
                    "matching_reasons": candidate.get("matching_reasons", []),
                    "field_matches": candidate.get("field_matches", {})  # 字段级别的匹配信息
                })
            except Exception as e:
                logger.warning(f"格式化候选工卡失败: {str(e)}, 候选工卡数据: {candidate}")
                continue
        
        # 按相似度排序
        formatted_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # 过滤掉相似度为0的工卡
        formatted_candidates = [c for c in formatted_candidates if c["similarity_score"] > 0]
        
        # 限制最多返回5个
        formatted_candidates = formatted_candidates[:5]
        
        logger.info(f"大模型匹配完成，返回 {len(formatted_candidates)} 个候选工卡")
        return formatted_candidates
        
    except Exception as e:
        import traceback
        logger.error(f"大模型匹配过程出错: {str(e)}", exc_info=True)
        logger.error(f"错误详情: {traceback.format_exc()}")
        return []

@router.get("/defect/{defect_record_id}/candidates", response_model=List[CandidateWorkCardResponse])
def get_candidate_workcards(
    defect_record_id: int,
    threshold: float = 75.0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取缺陷记录的候选工卡"""
    service = MatchingService(db)
    return service.get_candidate_workcards(defect_record_id, threshold, limit)

@router.get("/defect/{defect_record_id}/results", response_model=List[MatchingResultResponse])
def get_matching_results(
    defect_record_id: int,
    db: Session = Depends(get_db)
):
    """获取缺陷记录的匹配结果"""
    service = MatchingService(db)
    return service.get_matching_results(defect_record_id)

@router.post("/defect/{defect_record_id}/select-candidate")
def select_candidate_workcard(
    defect_record_id: int,
    workcard_id: int,
    db: Session = Depends(get_db)
):
    """选择候选工卡"""
    service = MatchingService(db)
    success = service.select_candidate_workcard(defect_record_id, workcard_id)
    if not success:
        raise HTTPException(status_code=404, detail="缺陷记录或工卡未找到")
    return {"message": "候选工卡选择成功"}

@router.get("/defect-list/{defect_list_id}/statistics")
def get_matching_statistics(defect_list_id: int, db: Session = Depends(get_db)):
    """获取匹配统计信息"""
    service = MatchingService(db)
    return service.get_matching_statistics(defect_list_id)

@router.post("/algorithm/config")
def update_algorithm_config(
    config: MatchingConfig,
    db: Session = Depends(get_db)
):
    """更新匹配算法配置"""
    service = MatchingService(db)
    return service.update_algorithm_config(config)
