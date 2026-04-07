from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import asyncio
from pydantic import BaseModel
from app.core.database import get_db
from app.schemas.defect import (
    DefectListResponse, DefectListCreate, DefectRecordResponse,
    DefectRecordCreate, DefectListUpdate
)
from app.services.defect_service import DefectService
from app.models.defect import DefectList

router = APIRouter()

@router.get("/lists", response_model=List[DefectListResponse])
def get_defect_lists(
    aircraft_number: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    configuration_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取缺陷清单列表"""
    service = DefectService(db)
    return service.get_defect_lists(
        aircraft_number=aircraft_number,
        status=status,
        configuration_id=configuration_id,
        skip=skip,
        limit=limit
    )

@router.get("/lists/{defect_list_id}", response_model=DefectListResponse)
def get_defect_list(defect_list_id: int, db: Session = Depends(get_db)):
    """获取特定缺陷清单"""
    service = DefectService(db)
    defect_list = service.get_defect_list_by_id(defect_list_id)
    if not defect_list:
        raise HTTPException(status_code=404, detail="缺陷清单未找到")
    return defect_list

@router.post("/lists", response_model=DefectListResponse)
def create_defect_list(
    defect_list: DefectListCreate,
    db: Session = Depends(get_db)
):
    """创建新的缺陷清单"""
    service = DefectService(db)
    return service.create_defect_list(defect_list)

@router.put("/lists/{defect_list_id}", response_model=DefectListResponse)
def update_defect_list(
    defect_list_id: int,
    defect_list: DefectListUpdate,
    db: Session = Depends(get_db)
):
    """更新缺陷清单"""
    service = DefectService(db)
    updated_defect_list = service.update_defect_list(defect_list_id, defect_list)
    if not updated_defect_list:
        raise HTTPException(status_code=404, detail="缺陷清单未找到")
    return updated_defect_list

@router.delete("/lists/{defect_list_id}")
def delete_defect_list(defect_list_id: int, db: Session = Depends(get_db)):
    """删除缺陷清单及其关联数据"""
    service = DefectService(db)
    success = service.delete_defect_list(defect_list_id)
    if not success:
        raise HTTPException(status_code=404, detail="缺陷清单未找到")
    return {"message": "缺陷清单删除成功"}

@router.post("/lists/{defect_list_id}/upload")
def upload_defect_data(
    defect_list_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传缺陷数据文件"""
    service = DefectService(db)
    return service.upload_defect_data(defect_list_id, file)

@router.get("/lists/{defect_list_id}/records", response_model=List[DefectRecordResponse])
def get_defect_records(
    defect_list_id: int,
    is_matched: Optional[bool] = Query(None),
    is_selected: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """获取缺陷记录列表"""
    service = DefectService(db)
    return service.get_defect_records(
        defect_list_id=defect_list_id,
        is_matched=is_matched,
        is_selected=is_selected
    )

@router.post("/records", response_model=DefectRecordResponse)
def create_defect_record(
    defect_record: DefectRecordCreate,
    db: Session = Depends(get_db)
):
    """创建新的缺陷记录"""
    service = DefectService(db)
    return service.create_defect_record(defect_record)

class SelectWorkcardRequest(BaseModel):
    workcard_id: int


class UpdateIssuedWorkcardNumberRequest(BaseModel):
    issued_workcard_number: str


def format_workcard_number_to_short(original: str) -> str:
    """
    将 NR/000000324 格式转换为 50324 格式
    规则：去掉 NR/ 前缀和前5个字符(00000)，保留后4位数字，然后在前面加上 5
    例如：NR/000000324 → 0324 → 50324
    """
    if not original:
        return ""
    # 如果已经是短格式（以5开头且全是数字），直接返回
    if original.isdigit() or (original.startswith("5") and original[1:].isdigit()):
        return original
    # 如果不是 NR/ 格式，直接返回原值
    if not original.startswith("NR/"):
        return original
    # 去掉 NR/ 前缀，保留后4位数字
    num_part = original.replace("NR/", "")
    last_4_digits = num_part[-4:].zfill(4)
    return "5" + last_4_digits


@router.put("/records/{defect_record_id}/select-workcard")
def select_workcard(
    defect_record_id: int,
    payload: SelectWorkcardRequest,
    db: Session = Depends(get_db)
):
    """为缺陷记录选择工卡"""
    service = DefectService(db)
    success = service.select_workcard_for_defect(defect_record_id, payload.workcard_id)
    if not success:
        raise HTTPException(status_code=404, detail="缺陷记录或工卡未找到")
    return {"message": "工卡选择成功"}


@router.put("/records/{defect_record_id}/issued-workcard-number")
def update_issued_workcard_number(
    defect_record_id: int,
    payload: UpdateIssuedWorkcardNumberRequest,
    db: Session = Depends(get_db)
):
    """更新缺陷记录的已开出工卡号"""
    from app.models.defect import DefectRecord
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        defect_record = db.query(DefectRecord).filter(DefectRecord.id == defect_record_id).first()
        if not defect_record:
            raise HTTPException(status_code=404, detail="缺陷记录未找到")
        
        # 检查字段是否存在（兼容性处理）
        if not hasattr(defect_record, 'issued_workcard_number'):
            logger.warning(f"缺陷记录表缺少 issued_workcard_number 字段，请运行数据库迁移: alembic upgrade head")
            raise HTTPException(status_code=500, detail="数据库字段不存在，请运行数据库迁移")
        
        # 将工卡号转换为短格式存储（如 50324）
        short_format = format_workcard_number_to_short(payload.issued_workcard_number)
        defect_record.issued_workcard_number = short_format
        db.commit()
        db.refresh(defect_record)
        
        logger.info(f"成功更新缺陷记录 {defect_record_id} 的工卡号为: {short_format}")
        return {
            "message": "工卡号更新成功",
            "issued_workcard_number": defect_record.issued_workcard_number
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新工卡号失败: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新工卡号失败: {str(e)}")

@router.delete("/records/{defect_record_id}")
def delete_defect_record(
    defect_record_id: int,
    db: Session = Depends(get_db)
):
    """删除缺陷记录及其关联数据"""
    service = DefectService(db)
    success = service.delete_defect_record(defect_record_id)
    if not success:
        raise HTTPException(status_code=404, detail="缺陷记录未找到")
    return {"message": "缺陷记录删除成功"}

@router.get("/lists/{defect_list_id}/unmatched", response_model=List[DefectRecordResponse])
def get_unmatched_defects(defect_list_id: int, db: Session = Depends(get_db)):
    """获取未匹配的缺陷记录"""
    service = DefectService(db)
    return service.get_unmatched_defects(defect_list_id)

@router.post("/lists/{defect_list_id}/export")
def export_unmatched_defects(
    defect_list_id: int,
    format: str = "csv",
    db: Session = Depends(get_db)
):
    """导出未匹配的缺陷记录"""
    service = DefectService(db)
    return service.export_unmatched_defects(defect_list_id, format)

@router.get("/lists/{defect_list_id}/export-cleaned")
def export_cleaned_data(
    defect_list_id: int,
    db: Session = Depends(get_db)
):
    """导出清洗后的缺陷数据"""
    from app.models.defect_cleaned import DefectCleanedData
    from app.models.defect import DefectRecord
    import pandas as pd
    import io
    
    defect_records = db.query(DefectRecord).filter(
        DefectRecord.defect_list_id == defect_list_id,
        DefectRecord.is_cleaned == True
    ).all()
    
    if not defect_records:
        raise HTTPException(status_code=404, detail="未找到已清洗的缺陷记录")
    
    export_data = []
    for record in defect_records:
        cleaned_data = db.query(DefectCleanedData).filter(
            DefectCleanedData.defect_record_id == record.id
        ).first()
        
        if cleaned_data:
            export_data.append({
                '缺陷编号': record.defect_number,
                '工卡描述（中文）': cleaned_data.description_cn or '',
                '工卡描述（英文）': getattr(record, 'raw_data', {}).get('description_en', '') if isinstance(getattr(record, 'raw_data', {}), dict) else '',
                '主区域': cleaned_data.main_area or '',
                '主部件': cleaned_data.main_component or '',
                '一级子部件': cleaned_data.first_level_subcomponent or '',
                '二级子部件': cleaned_data.second_level_subcomponent or '',
                '方位': cleaned_data.orientation or '',
                '缺陷主体': cleaned_data.defect_subject or '',
                '缺陷描述': cleaned_data.defect_description or '',
                '位置': cleaned_data.location or '',
                '数量': cleaned_data.quantity or '',
                '清洗时间': cleaned_data.cleaned_at.strftime('%Y-%m-%d %H:%M:%S') if cleaned_data.cleaned_at else ''
            })
    
    df = pd.DataFrame(export_data)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    # Starlette 会用 latin-1 编码 header，中文文件名会触发 UnicodeEncodeError
    # 这里同时提供 ASCII filename + RFC5987 filename*（UTF-8）
    from urllib.parse import quote
    ascii_filename = f"cleaned_defects_{defect_list_id}.xlsx"
    utf8_filename = quote(f"清洗后的缺陷数据_{defect_list_id}.xlsx")
    content_disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{utf8_filename}"

    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition}
    )

@router.get("/lists/{defect_list_id}/export-matched")
def export_matched_data(
    defect_list_id: int,
    configuration_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """导出匹配结果"""
    from app.services.matching_service import MatchingService
    import pandas as pd
    import io
    
    matching_service = MatchingService(db)
    results = matching_service.get_saved_match_results(defect_list_id, configuration_id)
    
    if not results:
        raise HTTPException(status_code=404, detail="未找到匹配结果")
    
    export_data = []
    for result in results:
        candidates = result.get('candidates', [])
        highest_score = max([c.get('similarity_score', 0) for c in candidates]) if candidates else 0
        best_candidate = next((c for c in candidates if c.get('similarity_score') == highest_score), None)
        
        export_data.append({
            '缺陷编号': result.get('defect_number', ''),
            '工卡描述（中文）': result.get('description_cn', ''),
            '工卡描述（英文）': result.get('description_en', ''),
            '匹配状态': '已匹配' if highest_score >= 90 else '未匹配',
            '最高相似度': f"{highest_score:.1f}%" if highest_score > 0 else '无候选工卡',
            '最佳候选工卡号': best_candidate.get('workcard_number', '') if best_candidate else '',
            '已选择工卡号': result.get('selected_workcard_id', '') or '',
            '候选工卡数量': len(candidates)
        })
    
    df = pd.DataFrame(export_data)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    # Starlette 会用 latin-1 编码 header，中文文件名会触发 UnicodeEncodeError
    # 这里同时提供 ASCII filename + RFC5987 filename*（UTF-8）
    from urllib.parse import quote
    ascii_filename = f"matched_results_{defect_list_id}.xlsx"
    utf8_filename = quote(f"匹配结果_{defect_list_id}.xlsx")
    content_disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{utf8_filename}"

    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition}
    )

@router.get("/lists/{defect_list_id}/processing-status")
def get_processing_status(
    defect_list_id: int,
    db: Session = Depends(get_db)
):
    """获取缺陷清单的处理状态"""
    from app.models.defect import DefectRecord
    
    defect_list = db.query(DefectList).filter(DefectList.id == defect_list_id).first()
    if not defect_list:
        raise HTTPException(status_code=404, detail="缺陷清单未找到")
    
    all_records = db.query(DefectRecord).filter(DefectRecord.defect_list_id == defect_list_id).all()
    total_count = len(all_records)
    cleaned_count = sum(1 for r in all_records if getattr(r, 'is_cleaned', False))
    matched_count = sum(1 for r in all_records if getattr(r, 'is_matched', False))
    
    return {
        "defect_list_id": defect_list_id,
        "total_records": total_count,
        "cleaned_count": cleaned_count,
        "matched_count": matched_count,
        "cleaning_status": getattr(defect_list, 'cleaning_status', 'pending'),
        "cleaning_progress": getattr(defect_list, 'cleaning_progress', 0.0),
        "matching_status": getattr(defect_list, 'matching_status', 'pending'),
        "matching_progress": getattr(defect_list, 'matching_progress', 0.0),
        "processing_stage": getattr(defect_list, 'processing_stage', 'upload'),
        "last_processed_at": defect_list.last_processed_at.isoformat() if getattr(defect_list, 'last_processed_at', None) else None
    }

@router.post("/clean")
def clean_defect_data(
    request: dict,
    db: Session = Depends(get_db)
):
    """清洗缺陷数据（使用索引数据表）"""
    from app.services.workcard_service import WorkCardService
    from pydantic import BaseModel
    
    class CleanDefectRequest(BaseModel):
        defect_list_id: int
        configuration_id: int
        limit: Optional[int] = None  # 可选：限制清洗数量（用于测试）
    
    req = CleanDefectRequest(**request)
    service = DefectService(db)
    workcard_service = WorkCardService(db)
    result = service.clean_defect_data(
        req.defect_list_id, 
        req.configuration_id, 
        workcard_service,
        limit=req.limit
    )
    return result

@router.post("/clean-stream")
async def clean_defect_data_stream(
    request: dict,
    db: Session = Depends(get_db)
):
    """清洗缺陷数据（使用SSE流式返回进度）"""
    from app.services.workcard_service import WorkCardService
    from pydantic import BaseModel
    import threading
    import queue
    
    class CleanDefectRequest(BaseModel):
        defect_list_id: int
        configuration_id: int
        limit: Optional[int] = None
    
    req = CleanDefectRequest(**request)
    service = DefectService(db)
    workcard_service = WorkCardService(db)
    
    async def generate_progress():
        """生成器函数，用于发送SSE事件"""
        try:
            # 发送初始消息
            start_data = {'type': 'start', 'message': '开始清洗缺陷数据'}
            yield f"data: {json.dumps(start_data)}\n\n"
            
            # 创建一个队列来传递进度更新（使用线程安全的queue）
            progress_queue = queue.Queue()
            result_container = {'result': None, 'error': None}
            
            # 定义进度回调函数
            def progress_callback(current: int, total: int, message: str = ""):
                """进度回调函数，在清洗过程中调用"""
                try:
                    progress_queue.put({
                        'type': 'progress',
                        'current': current,
                        'total': total,
                        'message': message
                    })
                except Exception as e:
                    print(f"进度回调错误: {e}")
            
            # 在后台线程中执行清洗
            def run_cleaning():
                """在后台线程中执行清洗任务"""
                try:
                    result = service.clean_defect_data_with_progress(
                        req.defect_list_id,
                        req.configuration_id,
                        workcard_service,
                        limit=req.limit,
                        progress_callback=progress_callback
                    )
                    result_container['result'] = result
                    progress_queue.put({'type': 'complete'})
                except Exception as e:
                    result_container['error'] = str(e)
                    progress_queue.put({'type': 'error'})
            
            # 启动清洗线程
            cleaning_thread = threading.Thread(target=run_cleaning, daemon=True)
            cleaning_thread.start()
            
            # 监听进度更新并发送SSE事件
            while True:
                try:
                    # 等待进度更新，设置超时避免无限等待
                    try:
                        progress_update = progress_queue.get(timeout=0.5)
                    except queue.Empty:
                        # 检查线程是否完成
                        if not cleaning_thread.is_alive():
                            # 线程已完成，检查是否有错误
                            if result_container['error']:
                                error_data = {
                                    'type': 'error',
                                    'message': result_container['error']
                                }
                                yield f"data: {json.dumps(error_data)}\n\n"
                                break
                            # 等待最后的完成消息
                            continue
                        # 继续等待
                        continue
                    
                    if progress_update.get('type') == 'complete':
                        # 清洗完成
                        result = result_container['result']
                        if result:
                            complete_data = {
                                'type': 'complete',
                                'success': result.get('success', False),
                                'cleaned_count': result.get('cleaned_count', 0),
                                'total_count': result.get('total_count', 0),
                                'cleaned_data': result.get('cleaned_data', []),
                                'message': result.get('message', '清洗完成')
                            }
                            yield f"data: {json.dumps(complete_data)}\n\n"
                        else:
                            error_data = {
                                'type': 'error',
                                'message': '清洗完成但未返回结果'
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                        break
                    elif progress_update.get('type') == 'error':
                        # 发生错误
                        error_msg = result_container['error'] or '清洗失败'
                        error_data = {
                            'type': 'error',
                            'message': error_msg
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"
                        break
                    else:
                        # 进度更新
                        current = progress_update.get('current', 0)
                        total = progress_update.get('total', 0)
                        percent = int((current / total * 100)) if total > 0 else 0
                        progress_data = {
                            'type': 'progress',
                            'current': current,
                            'total': total,
                            'percent': percent,
                            'message': progress_update.get('message', '')
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
                
                except Exception as e:
                    error_data = {
                        'type': 'error',
                        'message': f'进度更新错误: {str(e)}'
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    break
            
            # 等待清洗线程完成
            cleaning_thread.join(timeout=1)
            
        except Exception as e:
            error_data = {
                'type': 'error',
                'message': f'清洗过程发生错误: {str(e)}'
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )