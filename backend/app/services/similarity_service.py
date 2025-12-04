from typing import Dict, Any, List
from app.models.defect import DefectRecord
from app.models.workcard import WorkCard
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re

class SimilarityService:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )

    def calculate_similarity(
        self,
        defect_record: DefectRecord,
        workcard: WorkCard,
        field_weights: Dict[str, float]
    ) -> float:
        """计算缺陷记录与工卡的相似度"""
        
        # 检查是否有索引数据（从 raw_data 中提取）
        raw_data = defect_record.raw_data or {}
        has_index_data = (
            isinstance(raw_data, dict) and 
            (raw_data.get('主区域') or raw_data.get('主部件') or 
             raw_data.get('一级子部件') or raw_data.get('二级子部件'))
        )
        
        # 优先使用索引匹配方式
        if has_index_data:
            return self._calculate_index_based_similarity(
                defect_record, workcard, field_weights
            )
        
        # 向后兼容：如果没有索引数据，使用基础字段匹配
        system_score = self._calculate_field_similarity(
            defect_record.system, workcard.system
        )
        
        component_score = self._calculate_field_similarity(
            defect_record.component, workcard.component
        )
        
        description_score = self._calculate_text_similarity(
            defect_record.description or "",
            workcard.description or ""
        )
        
        total_score = (
            system_score * field_weights.get("system", 0.3) +
            component_score * field_weights.get("component", 0.3) +
            description_score * field_weights.get("description", 0.4)
        )
        
        return round(total_score * 100, 2)
    
    def _calculate_index_based_similarity(
        self,
        defect_record: DefectRecord,
        workcard: WorkCard,
        field_weights: Dict[str, float]
    ) -> float:
        """基于索引数据的相似度计算"""
        # 从缺陷记录的原始数据中提取索引字段
        raw_data = defect_record.raw_data or {}
        
        # 提取索引字段
        main_area = raw_data.get('主区域', '')
        main_component = raw_data.get('主部件', '')
        first_level_subcomponent = raw_data.get('一级子部件', '')
        second_level_subcomponent = raw_data.get('二级子部件', '')
        orientation = raw_data.get('方位', '')
        defect_subject = raw_data.get('缺陷主体', '')
        defect_description = raw_data.get('缺陷描述', '')
        
        # 从工卡中提取对应字段（需要根据实际工卡结构调整）
        workcard_main_area = getattr(workcard, 'main_area', '')
        workcard_main_component = getattr(workcard, 'main_component', '')
        workcard_first_level_subcomponent = getattr(workcard, 'first_level_subcomponent', '')
        workcard_second_level_subcomponent = getattr(workcard, 'second_level_subcomponent', '')
        workcard_orientation = getattr(workcard, 'orientation', '')
        workcard_defect_subject = getattr(workcard, 'defect_subject', '')
        
        # 计算各字段相似度
        main_area_score = self._calculate_field_similarity(main_area, workcard_main_area)
        main_component_score = self._calculate_field_similarity(main_component, workcard_main_component)
        first_level_subcomponent_score = self._calculate_field_similarity(
            first_level_subcomponent, workcard_first_level_subcomponent
        )
        second_level_subcomponent_score = self._calculate_field_similarity(
            second_level_subcomponent, workcard_second_level_subcomponent
        )
        orientation_score = self._calculate_field_similarity(orientation, workcard_orientation)
        defect_subject_score = self._calculate_field_similarity(defect_subject, workcard_defect_subject)
        defect_description_score = self._calculate_text_similarity(
            defect_description, workcard.description or ""
        )
        
        # 加权计算总相似度
        total_score = (
            main_area_score * field_weights.get("main_area", 0.05) +
            main_component_score * field_weights.get("main_component", 0.20) +
            first_level_subcomponent_score * field_weights.get("first_level_subcomponent", 0.35) +
            second_level_subcomponent_score * field_weights.get("second_level_subcomponent", 0.20) +
            orientation_score * field_weights.get("orientation", 0.05) +
            defect_subject_score * field_weights.get("defect_subject", 0.10) +
            defect_description_score * field_weights.get("defect_description", 0.05)
        )
        
        return round(total_score * 100, 2)

    def _calculate_field_similarity(self, field1: str, field2: str) -> float:
        """计算字段相似度"""
        if not field1 or not field2:
            return 0.0
        
        # 完全匹配
        if field1.lower() == field2.lower():
            return 1.0
        
        # 包含匹配
        if field1.lower() in field2.lower() or field2.lower() in field1.lower():
            return 0.8
        
        # 词汇相似度
        words1 = set(re.findall(r'\w+', field1.lower()))
        words2 = set(re.findall(r'\w+', field2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        try:
            # 使用TF-IDF向量化
            texts = [text1, text2]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # 计算余弦相似度
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return similarity
        except Exception:
            # 如果TF-IDF失败，使用简单的词汇重叠
            words1 = set(re.findall(r'\w+', text1.lower()))
            words2 = set(re.findall(r'\w+', text2.lower()))
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0

    def batch_calculate_similarity(
        self,
        defect_records: List[DefectRecord],
        workcards: List[WorkCard],
        field_weights: Dict[str, float]
    ) -> Dict[int, Dict[int, float]]:
        """批量计算相似度"""
        results = {}
        
        for defect_record in defect_records:
            results[defect_record.id] = {}
            for workcard in workcards:
                similarity = self.calculate_similarity(
                    defect_record, workcard, field_weights
                )
                results[defect_record.id][workcard.id] = similarity
        
        return results
