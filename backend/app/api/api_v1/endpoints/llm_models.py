from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm_provider_manager import (
    LLMModel,
    get_current_model,
    get_model_metadata,
    get_service_for_model,
    list_available_models,
    set_current_model,
)

router = APIRouter()


class ModelSelectRequest(BaseModel):
    model: str


@router.get("/models")
def list_models():
    """获取可用大模型列表及当前选择"""
    current_model = get_current_model()
    metadata = get_model_metadata(current_model)
    return {
        "data": list_available_models(),
        "current_model": {
            "value": current_model.value,
            "label": metadata["label"],
            "description": metadata["description"],
            "provider": metadata["provider"]
        }
    }


@router.post("/models/select")
def select_model(request: ModelSelectRequest):
    """切换当前大模型"""
    try:
        target_model = LLMModel(request.model)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的大模型: {request.model}")

    # 预先初始化，确保可用
    get_service_for_model(target_model)
    set_current_model(target_model)

    metadata = get_model_metadata(target_model)
    return {
        "message": f"已切换至{metadata['label']}模型",
        "current_model": {
            "value": target_model.value,
            "label": metadata["label"],
            "description": metadata["description"],
            "provider": metadata["provider"]
        }
    }










