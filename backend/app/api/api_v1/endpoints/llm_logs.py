"""
大模型交互日志查看API
"""
from fastapi import APIRouter, Query
from typing import Optional
import logging
import os
from pathlib import Path

router = APIRouter()

@router.get("/llm-interactions")
def get_llm_interactions(
    limit: int = Query(10, ge=1, le=100, description="返回的日志条数"),
    log_file: Optional[str] = Query(None, description="日志文件路径（可选）")
):
    """
    获取大模型交互日志
    
    注意：这是一个简化版本，实际生产环境应该使用日志管理系统
    这里返回的是最近的控制台日志信息
    """
    # 获取日志记录器
    logger = logging.getLogger("app.services.qwen_service")
    
    # 尝试从日志文件读取（如果配置了文件日志）
    logs = []
    
    # 检查是否有日志文件配置
    if log_file and os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 获取最后N行
                logs = lines[-limit:] if len(lines) > limit else lines
        except Exception as e:
            return {
                "success": False,
                "message": f"读取日志文件失败: {str(e)}",
                "logs": []
            }
    else:
        # 如果没有日志文件，返回提示信息
        return {
            "success": True,
            "message": "日志记录在控制台输出中。请查看后端控制台或配置日志文件。",
            "logs": [],
            "hint": "要查看详细日志，请：\n1. 查看后端运行的控制台输出\n2. 配置日志文件（在logging配置中设置）\n3. 日志包含完整的提示词、JSON内容和模型响应"
        }
    
    return {
        "success": True,
        "logs": logs,
        "count": len(logs)
    }













