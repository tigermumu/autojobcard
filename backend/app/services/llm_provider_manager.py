from enum import Enum
from typing import Dict, List

from app.core.config import settings
from app.services.gemini_service import get_gemini_service
from app.services.qwen_service import get_qwen_service


class LLMModel(str, Enum):
    QWEN = "Qwen"
    GEMINI = "Gemini"


_MODEL_METADATA: Dict[LLMModel, Dict[str, str]] = {
    LLMModel.QWEN: {
        "label": "Qwen",
        "description": "阿里云通义千问模型，适用于中文语境下的专业处理",
        "provider": "Alibaba Cloud"
    },
    LLMModel.GEMINI: {
        "label": "Gemini",
        "description": "Google Gemini 2.5 Flash，擅长多语言和快速响应",
        "provider": "Google"
    }
}


def _resolve_default_model() -> LLMModel:
    default_value = settings.DEFAULT_LLM_MODEL
    for model in LLMModel:
        if model.value.lower() == default_value.lower():
            return model
    return LLMModel.QWEN


_current_model: LLMModel = _resolve_default_model()


def get_current_model() -> LLMModel:
    return _current_model


def set_current_model(model: LLMModel) -> None:
    global _current_model
    _current_model = model


def get_model_metadata(model: LLMModel) -> Dict[str, str]:
    return _MODEL_METADATA[model]


def list_available_models() -> List[Dict[str, str]]:
    return [
        {
            "value": model.value,
            "label": metadata["label"],
            "description": metadata["description"],
            "provider": metadata["provider"]
        }
        for model, metadata in _MODEL_METADATA.items()
    ]


def get_service_for_model(model: LLMModel):
    if model == LLMModel.QWEN:
        return get_qwen_service()
    if model == LLMModel.GEMINI:
        return get_gemini_service()
    raise ValueError(f"不支持的大模型类型: {model}")


def get_service_for_current_model():
    return get_service_for_model(get_current_model())










