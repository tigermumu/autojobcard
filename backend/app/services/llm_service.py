from typing import Dict, Any, List
from app.services.llm_provider_manager import get_service_for_current_model

class LLMService:
    def __init__(self):
        pass

    async def validate_workcard_data(self, workcard_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证工卡数据"""
        service = get_service_for_current_model()
        return await service.validate_workcard_data(workcard_data)

    async def clean_workcard_description(self, description: str) -> str:
        """清洗工卡描述"""
        service = get_service_for_current_model()
        return await service.clean_workcard_description(description)

    async def classify_workcard_system(self, description: str, title: str) -> str:
        """分类工卡系统"""
        service = get_service_for_current_model()
        return await service.classify_workcard_system(description, title)

    async def extract_key_information(self, text: str) -> Dict[str, Any]:
        """提取关键信息"""
        service = get_service_for_current_model()
        return await service.extract_key_information(text)

    async def compare_defect_workcard(
        self,
        defect_description: str,
        workcard_description: str
    ) -> Dict[str, Any]:
        """比较缺陷描述与工卡描述"""
        service = get_service_for_current_model()
        return await service.compare_defect_workcard(defect_description, workcard_description)

    def batch_validate_workcards(self, workcards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量验证工卡数据"""
        service = get_service_for_current_model()
        return service.batch_validate_workcards(workcards)
