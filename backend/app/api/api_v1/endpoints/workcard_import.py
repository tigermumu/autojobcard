from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.defect import DefectRecord
from app.services.workcard_import_service import (
    WorkCardImportParams,
    WorkCardImportService,
    WorkcardInfo,
    HistoryWorkcardInfo,
    StepInfo,
    LogEntry,
    Artifact,
)

router = APIRouter()


def get_service() -> WorkCardImportService:
    return WorkCardImportService()


class WorkcardInfoSchema(BaseModel):
    rid: str = Field(..., description="工卡RID")
    index: int = Field(..., description="序号（从1开始）")

    @classmethod
    def from_entity(cls, data: WorkcardInfo) -> "WorkcardInfoSchema":
        return cls(rid=data.rid, index=data.index)


class HistoryWorkcardInfoSchema(WorkcardInfoSchema):
    phase: str = ""
    zone: str = ""
    trade: str = ""

    @classmethod
    def from_entity(cls, data: HistoryWorkcardInfo) -> "HistoryWorkcardInfoSchema":
        return cls(
            rid=data.rid,
            index=data.index,
            phase=data.phase,
            zone=data.zone,
            trade=data.trade,
        )


class LogEntrySchema(BaseModel):
    step: str
    message: str
    detail: Optional[str] = None

    @classmethod
    def from_entity(cls, data: LogEntry) -> "LogEntrySchema":
        detail = None
        if data.detail is not None:
            try:
                # 限制detail字段大小，避免JSON序列化问题
                detail_str = str(data.detail)
                # 如果超过2000字符，截断并添加提示
                if len(detail_str) > 2000:
                    detail = detail_str[:2000] + f"\n... (内容已截断，原始长度: {len(detail_str)} 字符)"
                else:
                    detail = detail_str
            except Exception as e:
                # 如果转换失败，记录错误但不影响整体流程
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"日志detail字段转换失败: {e}")
                detail = f"[日志内容转换失败: {str(e)}]"
        return cls(step=data.step, message=data.message, detail=detail)


class ArtifactSchema(BaseModel):
    step: str
    filename: str
    path: str

    @classmethod
    def from_entity(cls, data: Artifact) -> "ArtifactSchema":
        return cls(step=data.step, filename=data.filename, path=data.path)


class PreviewRequest(BaseModel):
    tail_no: str = Field(..., description="机尾号")
    src_work_order: str = Field(..., description="源工单号，用于查询待导入工卡")
    target_work_order: str = Field(..., description="目标工单号，用于查询历史工卡")
    work_group: str = Field(..., description="工作组编码")
    workcard_index: int = Field(0, description="目标工卡索引（从0开始，可选）")
    workcard_rid: Optional[str] = Field(None, description="目标工卡RID（可选）")
    cookies: Optional[str] = Field(None, description="企业系统访问所需 Cookies，优先于配置项")


class PreviewResponse(BaseModel):
    workcards: List[WorkcardInfoSchema]
    history_cards: List[HistoryWorkcardInfoSchema]
    logs: List[LogEntrySchema]
    artifacts: List[ArtifactSchema]


class RunRequest(PreviewRequest):
    history_card_index: int = Field(0, description="历史工卡索引（从0开始，可选）")
    history_rid: Optional[str] = Field(None, description="历史工卡RID（可选）")


class RunResponse(BaseModel):
    success: bool
    message: str
    workcards: List[WorkcardInfoSchema]
    history_cards: List[HistoryWorkcardInfoSchema]
    selected_workcard: Optional[WorkcardInfoSchema] = None
    selected_history_card: Optional[HistoryWorkcardInfoSchema] = None
    logs: List[LogEntrySchema]
    artifacts: List[ArtifactSchema]


class TestRequest(PreviewRequest):
    pass


class TestResponse(BaseModel):
    success: bool
    message: str
    logs: List[LogEntrySchema]
    artifacts: List[ArtifactSchema]


class ImportDefectRequest(BaseModel):
    defect_record_id: int = Field(..., description="缺陷记录ID")
    params: Dict[str, Any] = Field(..., description="导入参数字典")
    cookies: Optional[str] = Field(None, description="Cookie字符串")


class ImportDefectResponse(BaseModel):
    success: bool
    message: str
    workcard_number: Optional[str] = None
    logs: List[LogEntrySchema]
    artifacts: List[ArtifactSchema]


def _convert_logs(logs: List[LogEntry]) -> List[LogEntrySchema]:
    return [LogEntrySchema.from_entity(item) for item in logs]


def _convert_artifacts(artifacts: List[Artifact]) -> List[ArtifactSchema]:
    return [ArtifactSchema.from_entity(item) for item in artifacts]


def _convert_workcards(workcards: List[WorkcardInfo]) -> List[WorkcardInfoSchema]:
    return [WorkcardInfoSchema.from_entity(item) for item in workcards]


def _convert_history_cards(
    history_cards: List[HistoryWorkcardInfo],
) -> List[HistoryWorkcardInfoSchema]:
    return [HistoryWorkcardInfoSchema.from_entity(item) for item in history_cards]


def _build_params(
    request: PreviewRequest,
    history_card_index: int = 0,
    history_rid: Optional[str] = None,
) -> WorkCardImportParams:
    return WorkCardImportParams(
        tail_no=request.tail_no,
        src_work_order=request.src_work_order,
        target_work_order=request.target_work_order,
        work_group=request.work_group,
        workcard_index=request.workcard_index,
        workcard_rid=request.workcard_rid,
        history_card_index=history_card_index,
        history_rid=history_rid,
        cookies=request.cookies,
    )


@router.post("/preview", response_model=PreviewResponse)
def preview_workcards(
    request: PreviewRequest,
    service: WorkCardImportService = Depends(get_service),
):
    try:
        params = _build_params(request)
        preview = service.preview(params)
        return PreviewResponse(
            workcards=_convert_workcards(preview.workcards),
            history_cards=_convert_history_cards(preview.history_cards),
            logs=_convert_logs(preview.logs),
            artifacts=_convert_artifacts(preview.artifacts),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/test", response_model=TestResponse)
def test_connection(
    request: TestRequest,
    service: WorkCardImportService = Depends(get_service),
):
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("收到连通性测试请求")
        logger.debug(f"请求参数: tail_no={request.tail_no}, src_work_order={request.src_work_order}, target_work_order={request.target_work_order}, work_group={request.work_group}")
        
        params = _build_params(request)
        logger.debug("参数构建完成，开始调用服务方法")
        
        result = service.test_connection(params)
        
        logger.info(f"连通性测试完成，成功: {result.success}, 消息: {result.message}")
        logger.debug(f"日志数量: {len(result.logs)}, 文件数量: {len(result.artifacts)}")
        
        # 转换日志和文件
        try:
            converted_logs = _convert_logs(result.logs)
            converted_artifacts = _convert_artifacts(result.artifacts)
            logger.debug(f"日志转换完成，转换后数量: {len(converted_logs)}")
        except Exception as convert_exc:
            logger.error(f"转换日志或文件时发生错误: {convert_exc}", exc_info=True)
            logger.error(f"转换错误堆栈:\n{traceback.format_exc()}")
            converted_logs = []
            converted_artifacts = []
            converted_logs.append(LogEntrySchema(
                step="error",
                message=f"日志转换失败: {str(convert_exc)}",
                detail=None
            ))
        
        return TestResponse(
            success=result.success,
            message=result.message,
            logs=converted_logs,
            artifacts=converted_artifacts,
        )
    except Exception as exc:
        error_detail = str(exc)
        error_traceback = traceback.format_exc()
        logger.error(f"连通性测试API端点发生未捕获的异常: {error_detail}", exc_info=True)
        logger.error(f"完整错误堆栈:\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"连通性测试失败: {error_detail}") from exc


@router.post("/run", response_model=RunResponse)
def run_workcard_import(
    request: RunRequest,
    service: WorkCardImportService = Depends(get_service),
):
    try:
        params = _build_params(
            request,
            history_card_index=request.history_card_index,
            history_rid=request.history_rid,
        )
        result = service.run_workflow(params)
        selected_workcard = (
            WorkcardInfoSchema.from_entity(result.selected_workcard)
            if result.selected_workcard
            else None
        )
        selected_history = (
            HistoryWorkcardInfoSchema.from_entity(result.selected_history_card)
            if result.selected_history_card
            else None
        )
        return RunResponse(
            success=result.success,
            message=result.message,
            workcards=_convert_workcards(result.workcards),
            history_cards=_convert_history_cards(result.history_cards),
            selected_workcard=selected_workcard,
            selected_history_card=selected_history,
            logs=_convert_logs(result.logs),
            artifacts=_convert_artifacts(result.artifacts),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/import-defect", response_model=ImportDefectResponse)
def import_defect_to_nrc(
    request: ImportDefectRequest,
    service: WorkCardImportService = Depends(get_service),
    db: Session = Depends(get_db),
):
    """导入缺陷到NRC系统"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"开始导入缺陷，缺陷记录ID: {request.defect_record_id}")
        logger.debug(f"导入参数: {request.params}")
        
        success, message, workcard_number, logs, artifacts = service.import_defect_to_nrc(
            params=request.params,
            cookies=request.cookies,
        )
        
        logger.info(f"服务方法执行完成，成功: {success}, 消息: {message}, 工卡号: {workcard_number}")
        logger.debug(f"日志数量: {len(logs)}, 文件数量: {len(artifacts)}")
        
        # 如果导入成功且提取到工卡号，更新缺陷记录
        if success and workcard_number:
            try:
                logger.info(f"开始更新缺陷记录，缺陷记录ID: {request.defect_record_id}, 工卡号: {workcard_number}")
                defect_record = db.query(DefectRecord).filter(DefectRecord.id == request.defect_record_id).first()
                if defect_record:
                    logger.debug(f"找到缺陷记录: {defect_record.defect_number}")
                    # 检查字段是否存在（兼容性处理）
                    if hasattr(defect_record, 'issued_workcard_number'):
                        defect_record.issued_workcard_number = workcard_number
                        db.commit()
                        logger.info(f"成功更新缺陷记录，工卡号已保存: {workcard_number}")
                    else:
                        logger.warning(f"缺陷记录表缺少 issued_workcard_number 字段，请运行数据库迁移: alembic upgrade head")
                        logger.warning(f"工卡号 {workcard_number} 未保存到数据库，但导入已成功")
                else:
                    logger.warning(f"未找到缺陷记录，ID: {request.defect_record_id}")
            except Exception as db_exc:
                error_msg = str(db_exc)
                logger.error(f"更新缺陷记录时发生错误: {db_exc}", exc_info=True)
                logger.error(f"数据库错误堆栈:\n{traceback.format_exc()}")
                
                # 检查是否是字段不存在的错误
                if "does not exist" in error_msg or "UndefinedColumn" in error_msg:
                    logger.error("=" * 80)
                    logger.error("数据库字段不存在错误！")
                    logger.error("请运行以下命令执行数据库迁移：")
                    logger.error("  cd backend")
                    logger.error("  alembic upgrade head")
                    logger.error("=" * 80)
                    # 字段不存在时，记录警告但不影响返回
                    logger.warning(f"工卡号 {workcard_number} 未保存到数据库，但导入已成功")
                else:
                    # 其他数据库错误，回滚事务
                    db.rollback()
        
        # 转换日志和文件
        try:
            logger.debug("开始转换日志和文件")
            converted_logs = _convert_logs(logs)
            converted_artifacts = _convert_artifacts(artifacts)
            logger.debug(f"日志转换完成，转换后数量: {len(converted_logs)}")
        except Exception as convert_exc:
            logger.error(f"转换日志或文件时发生错误: {convert_exc}", exc_info=True)
            logger.error(f"转换错误堆栈:\n{traceback.format_exc()}")
            # 如果转换失败，使用空列表避免序列化问题
            converted_logs = []
            converted_artifacts = []
            # 添加错误日志到返回结果
            converted_logs.append(LogEntrySchema(
                step="error",
                message=f"日志转换失败: {str(convert_exc)}",
                detail=None
            ))
        
        # 构建响应
        try:
            logger.debug("开始构建响应对象")
            response = ImportDefectResponse(
                success=success,
                message=message,
                workcard_number=workcard_number,
                logs=converted_logs,
                artifacts=converted_artifacts,
            )
            logger.info(f"响应构建成功，准备返回")
            return response
        except Exception as response_exc:
            logger.error(f"构建响应对象时发生错误: {response_exc}", exc_info=True)
            logger.error(f"响应构建错误堆栈:\n{traceback.format_exc()}")
            raise
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as exc:
        error_detail = str(exc)
        error_traceback = traceback.format_exc()
        logger.error(f"导入缺陷时发生未捕获的异常: {error_detail}", exc_info=True)
        logger.error(f"完整错误堆栈:\n{error_traceback}")
        logger.error(f"请求参数: defect_record_id={request.defect_record_id}")
        raise HTTPException(status_code=500, detail=f"导入缺陷失败: {error_detail}") from exc


class StepInfoSchema(BaseModel):
    """步骤信息Schema"""
    rid: str = Field(..., description="步骤RID")
    index: int = Field(..., description="序号（从1开始）")
    phase: str = Field("", description="阶段")
    zone: str = Field("", description="区域")
    trade: str = Field("", description="工种")
    txt_area: str = Field("", description="区域文本")

    @classmethod
    def from_entity(cls, data: StepInfo) -> "StepInfoSchema":
        return cls(
            rid=data.rid,
            index=data.index,
            phase=data.phase,
            zone=data.zone,
            trade=data.trade,
            txt_area=data.txt_area,
        )


class ImportStepsRequest(BaseModel):
    """导入步骤请求"""
    jobcard_number: str = Field(..., description="工卡号（如 NR/000000300 或 50300）")
    target_work_order: str = Field(..., description="目标工单号（候选工卡的工卡指令号，用于 qJcWorkOrder）")
    source_work_order: str = Field(..., description="源工单号（导入参数配置的工作指令号 txtWO，用于 qWorkorder）")
    tail_no: str = Field(..., description="飞机号")
    work_group: str = Field(..., description="工作组编码")
    step_rids: Optional[List[str]] = Field(None, description="要导入的步骤ID列表（如果为None，则导入所有步骤）")
    cookies: Optional[str] = Field(None, description="企业系统访问所需 Cookies，优先于配置项")
    ref_manual: Optional[str] = Field(None, description="参考手册 (CMM_REFER)，如果提供则在导入步骤后执行 updateSteps 更新步骤描述")


class ImportStepsResponse(BaseModel):
    """导入步骤响应"""
    success: bool
    message: str
    jc_rid: Optional[str] = None
    jc_vid: Optional[str] = None
    total_steps: int = 0
    imported_count: int = 0
    failed_count: int = 0
    imported_steps: List[Dict[str, Any]] = Field(default_factory=list)
    failed_steps: List[Dict[str, Any]] = Field(default_factory=list)
    all_steps: List[Dict[str, Any]] = Field(default_factory=list)
    logs: List[LogEntrySchema]
    artifacts: List[ArtifactSchema]


@router.post("/import-steps", response_model=ImportStepsResponse)
def import_steps(
    request: ImportStepsRequest,
    service: WorkCardImportService = Depends(get_service),
):
    """导入工卡步骤到已开出的工卡"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=" * 80)
        logger.info("[API] 收到导入步骤请求")
        logger.info(f"工卡号: {request.jobcard_number}")
        logger.info(f"目标工单号（qJcWorkOrder）: {request.target_work_order}")
        logger.info(f"源工单号（qWorkorder）: {request.source_work_order}")
        logger.info(f"飞机号: {request.tail_no}")
        logger.info(f"工作组: {request.work_group}")
        logger.info(f"要导入的步骤ID: {request.step_rids}")
        logger.info(f"Cookie是否提供: {bool(request.cookies)}")
        logger.info(f"参考手册 (CMM_REFER): {request.ref_manual or 'N/A'}")
        logger.info("=" * 80)
        
        result = service.import_steps_workflow(
            jobcard_number=request.jobcard_number,
            target_work_order=request.target_work_order,  # qJcWorkOrder: 候选工卡的工卡指令号
            source_work_order=request.source_work_order,  # qWorkorder: 导入参数配置的工作指令号
            tail_no=request.tail_no,
            work_group=request.work_group,
            step_rids=request.step_rids,
            cookies=request.cookies,
            ref_manual=request.ref_manual,  # 参考手册，用于 updateSteps
        )
        
        logger.info("=" * 80)
        logger.info("[API] 步骤导入完成")
        logger.info(f"成功: {result.get('success')}")
        logger.info(f"消息: {result.get('message')}")
        if result.get('jc_rid'):
            logger.info(f"工卡ID: {result.get('jc_rid')}")
        if result.get('jc_vid'):
            logger.info(f"版本ID: {result.get('jc_vid')}")
        if result.get('total_steps'):
            logger.info(f"总步骤数: {result.get('total_steps')}")
        if result.get('imported_count'):
            logger.info(f"成功导入: {result.get('imported_count')}")
        if result.get('failed_count'):
            logger.info(f"失败数量: {result.get('failed_count')}")
        logger.info("=" * 80)
        
        # 转换日志和文件
        try:
            logs_data = result.get("logs", [])
            artifacts_data = result.get("artifacts", [])
            # logs_data 和 artifacts_data 已经是字典列表，需要转换为实体对象
            logs = [LogEntry(step=log.get("step", ""), message=log.get("message", ""), detail=log.get("detail")) for log in logs_data]
            artifacts = [Artifact(step=art.get("step", ""), filename=art.get("filename", ""), path=art.get("path", "")) for art in artifacts_data]
            converted_logs = _convert_logs(logs)
            converted_artifacts = _convert_artifacts(artifacts)
        except Exception as convert_exc:
            logger.error(f"转换日志或文件时发生错误: {convert_exc}", exc_info=True)
            converted_logs = []
            converted_artifacts = []
            converted_logs.append(LogEntrySchema(
                step="error",
                message=f"日志转换失败: {str(convert_exc)}",
                detail=None
            ))
        
        return ImportStepsResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            jc_rid=result.get("jc_rid"),
            jc_vid=result.get("jc_vid"),
            total_steps=result.get("total_steps", 0),
            imported_count=result.get("imported_count", 0),
            failed_count=result.get("failed_count", 0),
            imported_steps=result.get("imported_steps", []),
            failed_steps=result.get("failed_steps", []),
            all_steps=result.get("all_steps", []),
            logs=converted_logs,
            artifacts=converted_artifacts,
        )
    except Exception as exc:
        import traceback
        error_detail = str(exc)
        error_traceback = traceback.format_exc()
        logger.error(f"导入步骤时发生未捕获的异常: {error_detail}", exc_info=True)
        logger.error(f"完整错误堆栈:\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"导入步骤失败: {error_detail}") from exc


class ImportEnglishDefectRequest(BaseModel):
    params: Dict[str, Any] = Field(..., description="导入参数字典")
    cookies: Optional[str] = Field(None, description="Cookie字符串")
    enable_crn_check: bool = Field(False, description="是否启用相关工卡号(CRN)校验")


@router.post("/import-english-defect", response_model=ImportDefectResponse)
def import_english_defect_to_nrc(
    request: ImportEnglishDefectRequest,
    service: WorkCardImportService = Depends(get_service),
):
    """导入英文工卡到NRC系统"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"开始导入英文工卡")
        logger.debug(f"导入参数: {request.params}")
        
        success, message, workcard_number, logs, artifacts = service.import_english_defect_to_nrc(
            params=request.params,
            cookies=request.cookies,
            enable_crn_check=request.enable_crn_check,
        )
        
        logger.info(f"服务方法执行完成，成功: {success}, 消息: {message}, 工卡号: {workcard_number}")
        
        # 转换日志和文件
        try:
            converted_logs = _convert_logs(logs)
            converted_artifacts = _convert_artifacts(artifacts)
        except Exception as convert_exc:
            logger.error(f"转换日志或文件时发生错误: {convert_exc}", exc_info=True)
            converted_logs = []
            converted_artifacts = []
            converted_logs.append(LogEntrySchema(
                step="error",
                message=f"日志转换失败: {str(convert_exc)}",
                detail=None
            ))
        
        return ImportDefectResponse(
            success=success,
            message=message,
            workcard_number=workcard_number,
            logs=converted_logs,
            artifacts=converted_artifacts,
        )
        
    except Exception as exc:
        error_detail = str(exc)
        logger.error(f"导入英文工卡时发生未捕获的异常: {error_detail}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {error_detail}") from exc


class ACInfoRequest(BaseModel):
    tail_no: str = Field(..., description="飞机号")
    work_order: str = Field(..., description="工单号")
    cookies: Optional[str] = Field(None, description="Cookies")


class ACInfoResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str


@router.post("/ac-info", response_model=ACInfoResponse)
def get_ac_info(
    request: ACInfoRequest,
    service: WorkCardImportService = Depends(get_service),
):
    """获取飞机信息"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        data = service.get_aircraft_info(
            tail_no=request.tail_no,
            work_order=request.work_order,
            cookies=request.cookies,
        )
        
        if data:
            return ACInfoResponse(success=True, data=data, message="获取成功")
        else:
            return ACInfoResponse(success=False, data={}, message="未找到匹配的工单信息")
            
    except Exception as exc:
        logger.error(f"获取飞机信息失败: {exc}", exc_info=True)
        return ACInfoResponse(success=False, data={}, message=f"获取失败: {str(exc)}")


# ==================== 编写方案 API ====================

class WriteStepsRequest(BaseModel):
    """编写方案请求"""
    sale_wo: str = Field(..., description="工作指令号 (SaleWo)")
    ac_no: str = Field(..., description="飞机号 (ACNo)")
    jc_seq: str = Field(..., description="已开出工卡号 (jcSeq)")
    cmm_refer: str = Field(..., description="参考手册 (CMM_REFER)")
    owner_code: Optional[str] = Field(None, description="客户代码 (txtCust)")
    cookies: Optional[str] = Field(None, description="企业系统访问所需 Cookies")
    steps: Optional[List[Any]] = Field(None, description="自定义步骤列表 (如果提供则直接使用，不重新生成)，支持字符串或字典")


class WriteStepsResponse(BaseModel):
    """编写方案响应"""
    success: bool
    message: str
    jc_workorder_input: Optional[str] = None
    wo_rid: Optional[str] = None
    jc_rid: Optional[str] = None
    steps: List[Any] = Field(default_factory=list, description="生成的步骤列表")
    logs: List[str] = Field(default_factory=list)


@router.post("/write-steps", response_model=WriteStepsResponse)
def write_steps(request: WriteStepsRequest):
    """
    编写方案 - 根据工卡缺陷描述关键词自动生成方案步骤
    
    关键词匹配规则（按优先级）：
    1. WALLPAPER -> 4个固定步骤
    2. PAINT -> 2个步骤
    3. FAILED -> ADJUST
    4. BROKEN -> REPLACE
    5. MISSING -> INSTALL
    6. DIRTY -> CLEAN
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"收到编写方案请求: sale_wo={request.sale_wo}, ac_no={request.ac_no}, jc_seq={request.jc_seq}")
        
        # 导入 write_steps 模块
        from app.services.write_steps import run_update_steps
        
        # 执行编写方案
        result = run_update_steps(
            sale_wo=request.sale_wo,
            ac_no=request.ac_no,
            jc_seq=request.jc_seq,
            cmm_refer=request.cmm_refer,
            cookies=request.cookies,
            owner_code=request.owner_code,
            custom_steps=request.steps,
        )
        
        return WriteStepsResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            jc_workorder_input=result.get("jc_workorder_input"),
            wo_rid=result.get("wo_rid"),
            jc_rid=result.get("jc_rid"),
            steps=result.get("steps", []),
            logs=result.get("logs", []),
        )
        
    except Exception as exc:
        error_detail = str(exc)
        logger.error(f"编写方案失败: {error_detail}", exc_info=True)
        return WriteStepsResponse(
            success=False,
            message=f"编写方案失败: {error_detail}",
            logs=[f"ERROR: {error_detail}"],
        )


class BatchWriteStepsRequest(BaseModel):
    """批量编写方案请求"""
    items: List[WriteStepsRequest] = Field(..., description="编写方案请求列表")


class BatchWriteStepsItemResult(BaseModel):
    """批量编写方案单项结果"""
    jc_seq: str
    success: bool
    message: str
    steps: List[Any] = Field(default_factory=list)


class BatchWriteStepsResponse(BaseModel):
    """批量编写方案响应"""
    success: bool
    message: str
    total: int
    success_count: int
    failed_count: int
    results: List[BatchWriteStepsItemResult] = Field(default_factory=list)


@router.post("/batch-write-steps", response_model=BatchWriteStepsResponse)
def batch_write_steps(request: BatchWriteStepsRequest):
    """批量编写方案"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"收到批量编写方案请求，共 {len(request.items)} 项")
        
        from app.services.write_steps import run_update_steps
        
        results = []
        success_count = 0
        failed_count = 0
        
        for item in request.items:
            try:
                result = run_update_steps(
                    sale_wo=item.sale_wo,
                    ac_no=item.ac_no,
                    jc_seq=item.jc_seq,
                    cmm_refer=item.cmm_refer,
                    cookies=item.cookies,
                    owner_code=item.owner_code,
                    custom_steps=item.steps,
                )
                
                item_result = BatchWriteStepsItemResult(
                    jc_seq=item.jc_seq,
                    success=result.get("success", False),
                    message=result.get("message", ""),
                    steps=result.get("steps", []),
                )
                results.append(item_result)
                
                if result.get("success"):
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as item_exc:
                failed_count += 1
                results.append(BatchWriteStepsItemResult(
                    jc_seq=item.jc_seq,
                    success=False,
                    message=f"执行失败: {str(item_exc)}",
                    steps=[],
                ))
        
        return BatchWriteStepsResponse(
            success=failed_count == 0,
            message=f"批量编写方案完成，成功 {success_count} 项，失败 {failed_count} 项",
            total=len(request.items),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
        )
        
    except Exception as exc:
        error_detail = str(exc)
        logger.error(f"批量编写方案失败: {error_detail}", exc_info=True)
        return BatchWriteStepsResponse(
            success=False,
            message=f"批量编写方案失败: {error_detail}",
            total=len(request.items),
            success_count=0,
            failed_count=len(request.items),
            results=[],
        )


# ==================== 预览方案步骤 API ====================

class SchemeStep(BaseModel):
    """方案步骤结构"""
    step_number: int = Field(..., description="步骤序号")
    content_en: str = Field(..., description="步骤内容（英文）")
    content_cn: Optional[str] = Field("", description="步骤内容（中文）")
    man_hours: str = Field(..., description="工时 (schedmh)")
    manpower: str = Field(..., description="人力 (schedlabor)")
    trade: str = Field(..., description="工种 (schedtrade)")
    materials: List[Dict[str, Any]] = Field(default_factory=list, description="航材列表")


class PreviewStepsRequest(BaseModel):
    """预览方案步骤请求"""
    description_en: str = Field(..., description="工卡描述（英文）")
    ref_manual: str = Field(..., description="参考手册 (CMM_REFER)")


class PreviewStepsResponse(BaseModel):
    """预览方案步骤响应"""
    success: bool
    message: str
    steps: List[SchemeStep] = Field(default_factory=list)


@router.post("/preview-steps", response_model=PreviewStepsResponse)
def preview_steps(request: PreviewStepsRequest):
    """
    预览方案步骤 - 根据工卡描述和参考手册生成结构化步骤
    不涉及外部 API 调用，纯逻辑生成
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from app.services.write_steps import generate_structured_steps
        
        steps_data = generate_structured_steps(
            jcendesc=request.description_en,
            cmm_refer=request.ref_manual
        )
        
        return PreviewStepsResponse(
            success=True,
            message=f"成功生成 {len(steps_data)} 个步骤",
            steps=steps_data
        )
        
    except Exception as exc:
        logger.error(f"预览方案步骤失败: {exc}", exc_info=True)
        return PreviewStepsResponse(
            success=False,
            message=f"生成失败: {str(exc)}",
            steps=[]
        )

