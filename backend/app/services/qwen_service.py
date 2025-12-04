"""
Qwen AI服务模块
基于demo2的AI模型管理器，专门用于飞机方案处理系统
"""
import json
import re
from typing import Dict, List, Optional, Any
from openai import OpenAI
from app.core.config import settings


class QwenService:
    """Qwen AI服务 - 专门用于飞机方案处理系统"""
    
    def __init__(self):
        """初始化Qwen服务"""
        self.client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL
        )
        self.model = settings.QWEN_MODEL
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: str = "你是一个专业的航空维修数据分析助手。",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            包含生成文本和元数据的字典
        """
        import logging
        import datetime
        logger = logging.getLogger(__name__)
        
        # 生成请求ID（基于时间戳）
        request_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # 开始标记 - 使用更明显的分隔符
        logger.info("")
        logger.info("╔" + "=" * 98 + "╗")
        logger.info("║" + " " * 30 + f"【大模型调用开始 - 请求ID: {request_id}】" + " " * 30 + "║")
        logger.info("╠" + "=" * 98 + "╣")
        logger.info(f"║ 模型: {self.model:<90} ║")
        logger.info(f"║ API Base URL: {str(self.client.base_url):<82} ║")
        logger.info(f"║ 提示词长度: {len(prompt)}, 系统提示词长度: {len(system_prompt):<60} ║")
        logger.info(f"║ Temperature: {temperature}, Max Tokens: {max_tokens:<60} ║")
        logger.info(f"║ 时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]:<80} ║")
        logger.info("╠" + "-" * 98 + "╣")
        logger.info("║" + " " * 10 + "【系统提示词】" + " " * 70 + "║")
        logger.info("╠" + "-" * 98 + "╣")
        # 系统提示词分行输出
        for line in system_prompt.split('\n'):
            logger.info(f"║ {line[:96]:<96} ║")
        logger.info("╠" + "-" * 98 + "╣")
        logger.info("║" + " " * 10 + "【用户提示词】" + " " * 70 + "║")
        logger.info("╠" + "-" * 98 + "╣")
        # 用户提示词分行输出
        for line in prompt.split('\n'):
            logger.info(f"║ {line[:96]:<96} ║")
        logger.info("╠" + "-" * 98 + "╣")
        logger.info("║ 正在发送API请求..." + " " * 80 + "║")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            response_text = response.choices[0].message.content if response.choices else ""
            logger.info("╠" + "-" * 98 + "╣")
            logger.info("║" + " " * 10 + f"【大模型API调用成功 - 请求ID: {request_id}】" + " " * 50 + "║")
            logger.info(f"║ 返回文本长度: {len(response_text):<88} ║")
            logger.info("╠" + "-" * 98 + "╣")
            logger.info("║" + " " * 10 + "【大模型返回内容】" + " " * 70 + "║")
            logger.info("╠" + "-" * 98 + "╣")
            # 返回内容分行输出
            for line in response_text.split('\n'):
                logger.info(f"║ {line[:96]:<96} ║")
            logger.info("╠" + "=" * 98 + "╣")
            logger.info("║" + " " * 30 + f"【大模型调用结束 - 请求ID: {request_id}】" + " " * 30 + "║")
            logger.info("╚" + "=" * 98 + "╝")
            logger.info("")
            
            return {
                "success": True,
                "text": response_text,
                "model": "Qwen",
                "error": ""
            }
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error("")
            logger.error("╔" + "=" * 98 + "╗")
            logger.error("║" + " " * 30 + f"【大模型API调用失败 - 请求ID: {request_id}】" + " " * 30 + "║")
            logger.error("╠" + "=" * 98 + "╣")
            logger.error(f"║ 错误信息: {str(e):<88} ║")
            logger.error("╠" + "-" * 98 + "╣")
            logger.error("║" + " " * 10 + "【错误详情】" + " " * 70 + "║")
            logger.error("╠" + "-" * 98 + "╣")
            # 错误详情分行输出
            for line in error_detail.split('\n'):
                logger.error(f"║ {line[:96]:<96} ║")
            logger.error("╠" + "=" * 98 + "╣")
            logger.error("║" + " " * 30 + f"【请求结束 - 请求ID: {request_id}】" + " " * 30 + "║")
            logger.error("╚" + "=" * 98 + "╝")
            logger.error("")
            return {
                "success": False,
                "error": f"Qwen API调用失败: {str(e)}",
                "text": ""
            }
    
    def parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        解析AI返回的JSON响应
        
        Args:
            text: AI返回的文本
            
        Returns:
            解析后的字典
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"parse_json_response: 输入文本长度 = {len(text)}")
        logger.debug(f"parse_json_response: 输入文本前200字符 = {repr(text[:200])}")
        
        try:
            # 尝试提取JSON块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                logger.info(f"parse_json_response: 使用 ```json``` 块提取，长度 = {len(json_str)}")
                logger.debug(f"parse_json_response: 提取的JSON字符串 = {repr(json_str[:500])}")
            else:
                # 尝试提取大括号内容
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    logger.info(f"parse_json_response: 使用 {{}} 块提取，长度 = {len(json_str)}")
                    logger.debug(f"parse_json_response: 提取的JSON字符串 = {repr(json_str[:500])}")
                else:
                    json_str = text.strip()
                    logger.warning(f"parse_json_response: 未找到JSON块，使用原始文本，长度 = {len(json_str)}")
                    logger.debug(f"parse_json_response: 原始文本 = {repr(json_str[:500])}")
            
            # 检查JSON字符串是否完整（简单检查）
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            logger.info(f"parse_json_response: JSON括号检查 - 开括号: {open_braces}, 闭括号: {close_braces}")
            if open_braces != close_braces:
                logger.warning(f"parse_json_response: ⚠️ JSON括号不匹配！可能被截断")
                logger.warning(f"parse_json_response: JSON字符串末尾50字符 = {repr(json_str[-50:])}")
            
            # 尝试解析JSON
            logger.debug(f"parse_json_response: 开始解析JSON...")
            result = json.loads(json_str)
            logger.info(f"parse_json_response: ✅ JSON解析成功")
            return {"success": True, "data": result, "error": ""}
        
        except json.JSONDecodeError as e:
            logger.error(f"parse_json_response: ❌ JSON解析失败: {str(e)}")
            logger.error(f"parse_json_response: 错误位置 - line {e.lineno}, column {e.colno}")
            logger.error(f"parse_json_response: 错误附近的文本 = {repr(json_str[max(0, e.pos-50):e.pos+50])}")
            logger.error(f"parse_json_response: 完整的JSON字符串长度 = {len(json_str)}")
            logger.error(f"parse_json_response: JSON字符串末尾100字符 = {repr(json_str[-100:])}")
            return {
                "success": False,
                "data": {},
                "error": f"JSON解析失败: {str(e)}",
                "raw_text": text,
                "extracted_json": json_str if 'json_str' in locals() else ""
            }
        except Exception as e:
            logger.error(f"parse_json_response: ❌ 解析错误: {str(e)}", exc_info=True)
            return {
                "success": False,
                "data": {},
                "error": f"解析错误: {str(e)}",
                "raw_text": text
            }
    
    async def validate_workcard_data(self, workcard_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用Qwen验证工卡数据"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info("【大模型交互 - 工卡数据验证】")
        logger.info(f"输入工卡数据: {json.dumps(workcard_data, ensure_ascii=False, indent=2)}")
        logger.info("-" * 80)
        
        try:
            prompt = f"""
            请分析以下工卡数据，验证其完整性和一致性：
            
            工卡数据：
            {json.dumps(workcard_data, ensure_ascii=False, indent=2)}
            
            请检查：
            1. 必填字段是否完整
            2. 数据格式是否正确
            3. 描述内容是否合理
            4. 系统、部件名称是否规范
            
            返回JSON格式的验证结果：
            {{
                "is_valid": true/false,
                "confidence": 0.0-1.0,
                "issues": ["问题1", "问题2"],
                "suggestions": ["建议1", "建议2"],
                "cleaned_data": {{}}
            }}
            """
            
            response = self.generate_text(prompt)
            if response["success"]:
                json_result = self.parse_json_response(response["text"])
                if json_result["success"]:
                    result = json_result["data"]
                    logger.info("║" + " " * 10 + "【验证结果】" + " " * 70 + "║")
                    logger.info("╠" + "-" * 98 + "╣")
                    result_json = json.dumps(result, ensure_ascii=False, indent=2)
                    for line in result_json.split('\n'):
                        logger.info(f"║ {line[:96]:<96} ║")
                    logger.info("╠" + "=" * 98 + "╣")
                    logger.info("║" + " " * 30 + f"【验证完成 - 请求ID: {request_id}】" + " " * 30 + "║")
                    logger.info("╚" + "=" * 98 + "╝")
                    logger.info("")
                    return result
                else:
                    result = {
                        "is_valid": False,
                        "confidence": 0.0,
                        "issues": [f"JSON解析失败: {json_result['error']}"],
                        "suggestions": [],
                        "cleaned_data": workcard_data
                    }
                    logger.warning("║" + " " * 10 + f"【验证失败 - JSON解析错误】错误: {json_result['error']}" + " " * 40 + "║")
                    logger.info("╚" + "=" * 98 + "╝")
                    logger.info("")
                    return result
            else:
                result = {
                    "is_valid": False,
                    "confidence": 0.0,
                    "issues": [f"Qwen调用失败: {response['error']}"],
                    "suggestions": [],
                    "cleaned_data": workcard_data
                }
                logger.error("║" + " " * 10 + f"【验证失败 - API调用错误】错误: {response['error']}" + " " * 40 + "║")
                logger.info("╚" + "=" * 98 + "╝")
                logger.info("")
                return result
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"【验证失败 - 异常】异常: {str(e)}")
            logger.error(f"错误详情: {error_detail}")
            logger.info("=" * 80)
            return {
                "is_valid": False,
                "confidence": 0.0,
                "issues": [f"验证失败: {str(e)}"],
                "suggestions": [],
                "cleaned_data": workcard_data
            }
    
    async def clean_workcard_description(self, description: str) -> str:
        """使用Qwen清洗工卡描述"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info("【大模型交互 - 工卡描述清洗】")
        logger.info(f"原始描述长度: {len(description)}")
        logger.info(f"原始描述内容: {description[:500]}{'...' if len(description) > 500 else ''}")
        logger.info("-" * 80)
        
        try:
            prompt = f"""
            请清洗和标准化以下工卡描述文本：
            
            原始描述：
            {description}
            
            要求：
            1. 去除无关信息
            2. 标准化术语
            3. 保持原意
            4. 使用简洁明了的语言
            
            返回清洗后的描述：
            """
            
            response = self.generate_text(prompt)
            if response["success"]:
                cleaned_result = response["text"].strip()
                logger.info("║" + " " * 10 + "【清洗结果】" + " " * 70 + "║")
                logger.info("╠" + "-" * 98 + "╣")
                logger.info(f"║ 清洗后描述长度: {len(cleaned_result):<88} ║")
                logger.info("║" + " " * 10 + "【清洗后描述内容】" + " " * 70 + "║")
                logger.info("╠" + "-" * 98 + "╣")
                cleaned_preview = cleaned_result[:500] + ('...' if len(cleaned_result) > 500 else '')
                for line in cleaned_preview.split('\n'):
                    logger.info(f"║ {line[:96]:<96} ║")
                logger.info("╠" + "=" * 98 + "╣")
                logger.info("║" + " " * 30 + f"【清洗完成 - 请求ID: {request_id}】" + " " * 30 + "║")
                logger.info("╚" + "=" * 98 + "╝")
                logger.info("")
                return cleaned_result
            else:
                logger.warning("║" + " " * 10 + f"【清洗失败 - API调用错误】错误: {response.get('error', '未知错误')}，返回原始描述" + " " * 20 + "║")
                logger.info("╚" + "=" * 98 + "╝")
                logger.info("")
                return description
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error("║" + " " * 10 + f"【清洗失败 - 异常】异常: {str(e)}" + " " * 50 + "║")
            logger.error("╠" + "-" * 98 + "╣")
            logger.error("║" + " " * 10 + "【错误详情】" + " " * 70 + "║")
            logger.error("╠" + "-" * 98 + "╣")
            for line in error_detail.split('\n'):
                logger.error(f"║ {line[:96]:<96} ║")
            logger.error("╚" + "=" * 98 + "╝")
            logger.error("")
            return description
    
    async def classify_workcard_system(self, description: str, title: str) -> str:
        """使用Qwen分类工卡系统"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info("【大模型交互 - 工卡系统分类】")
        logger.info(f"标题: {title}")
        logger.info(f"描述长度: {len(description)}")
        logger.info(f"描述内容: {description[:300]}{'...' if len(description) > 300 else ''}")
        logger.info("-" * 80)
        
        try:
            prompt = f"""
            根据以下工卡信息，判断其所属的系统类别：
            
            标题：{title}
            描述：{description}
            
            可能的系统类别包括：
            - 发动机系统
            - 液压系统
            - 电气系统
            - 燃油系统
            - 起落架系统
            - 导航系统
            - 通信系统
            - 空调系统
            - 其他
            
            请只返回最匹配的系统类别名称：
            """
            
            response = self.generate_text(prompt)
            if response["success"]:
                classified_result = response["text"].strip()
                logger.info("║" + " " * 10 + "【分类结果】" + " " * 70 + "║")
                logger.info("╠" + "-" * 98 + "╣")
                logger.info(f"║ 系统类别: {classified_result:<88} ║")
                logger.info("╠" + "=" * 98 + "╣")
                logger.info("║" + " " * 30 + f"【分类完成 - 请求ID: {request_id}】" + " " * 30 + "║")
                logger.info("╚" + "=" * 98 + "╝")
                logger.info("")
                return classified_result
            else:
                logger.warning("║" + " " * 10 + f"【分类失败 - API调用错误】错误: {response.get('error', '未知错误')}，返回默认值'其他'" + " " * 20 + "║")
                logger.info("╚" + "=" * 98 + "╝")
                logger.info("")
                return "其他"
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error("║" + " " * 10 + f"【分类失败 - 异常】异常: {str(e)}" + " " * 50 + "║")
            logger.error("╠" + "-" * 98 + "╣")
            logger.error("║" + " " * 10 + "【错误详情】" + " " * 70 + "║")
            logger.error("╠" + "-" * 98 + "╣")
            for line in error_detail.split('\n'):
                logger.error(f"║ {line[:96]:<96} ║")
            logger.error("╚" + "=" * 98 + "╝")
            logger.error("")
            return "其他"
    
    async def extract_key_information(self, text: str) -> Dict[str, Any]:
        """使用Qwen提取关键信息"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info("【大模型交互 - 关键信息提取】")
        logger.info(f"输入文本长度: {len(text)}")
        logger.info(f"输入文本内容: {text[:500]}{'...' if len(text) > 500 else ''}")
        logger.info("-" * 80)
        
        try:
            prompt = f"""
            从以下文本中提取关键信息：
            
            文本：
            {text}
            
            请提取以下信息并以JSON格式返回：
            {{
                "system": "系统名称",
                "component": "部件名称",
                "location": "位置信息",
                "action": "执行动作",
                "keywords": ["关键词1", "关键词2"]
            }}
            """
            
            response = self.generate_text(prompt)
            if response["success"]:
                json_result = self.parse_json_response(response["text"])
                if json_result["success"]:
                    result = json_result["data"]
                    logger.info("【提取结果】")
                    logger.info(f"提取的关键信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    logger.info("=" * 80)
                    return result
                else:
                    logger.warning(f"【提取失败 - JSON解析错误】错误: {json_result.get('error', '未知错误')}")
                    logger.info("=" * 80)
                    return {
                        "system": "",
                        "component": "",
                        "location": "",
                        "action": "",
                        "keywords": []
                    }
            else:
                logger.error(f"【提取失败 - API调用错误】错误: {response.get('error', '未知错误')}")
                logger.info("=" * 80)
                return {
                    "system": "",
                    "component": "",
                    "location": "",
                    "action": "",
                    "keywords": []
                }
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"【提取失败 - 异常】异常: {str(e)}")
            logger.error(f"错误详情: {error_detail}")
            logger.info("=" * 80)
            return {
                "system": "",
                "component": "",
                "location": "",
                "action": "",
                "keywords": []
            }
    
    async def compare_defect_workcard(
        self,
        defect_description: str,
        workcard_description: str
    ) -> Dict[str, Any]:
        """使用Qwen比较缺陷描述与工卡描述"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info("【大模型交互 - 缺陷工卡对比】")
        logger.info(f"缺陷描述长度: {len(defect_description)}")
        logger.info(f"缺陷描述内容: {defect_description[:300]}{'...' if len(defect_description) > 300 else ''}")
        logger.info(f"工卡描述长度: {len(workcard_description)}")
        logger.info(f"工卡描述内容: {workcard_description[:300]}{'...' if len(workcard_description) > 300 else ''}")
        logger.info("-" * 80)
        
        try:
            prompt = f"""
            比较以下缺陷描述与工卡描述的相关性：
            
            缺陷描述：
            {defect_description}
            
            工卡描述：
            {workcard_description}
            
            请分析并返回JSON格式的结果：
            {{
                "relevance_score": 0.0-1.0,
                "is_related": true/false,
                "similarity_reasons": ["原因1", "原因2"],
                "differences": ["差异1", "差异2"],
                "recommendation": "推荐或不推荐"
            }}
            """
            
            response = self.generate_text(prompt)
            if response["success"]:
                json_result = self.parse_json_response(response["text"])
                if json_result["success"]:
                    result = json_result["data"]
                    logger.info("【对比结果】")
                    logger.info(f"相关性评分: {result.get('relevance_score', 0.0)}")
                    logger.info(f"是否相关: {result.get('is_related', False)}")
                    logger.info(f"相似原因: {result.get('similarity_reasons', [])}")
                    logger.info(f"差异: {result.get('differences', [])}")
                    logger.info(f"推荐: {result.get('recommendation', '')}")
                    logger.info(f"完整结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    logger.info("=" * 80)
                    return result
                else:
                    result = {
                        "relevance_score": 0.0,
                        "is_related": False,
                        "similarity_reasons": [],
                        "differences": [f"JSON解析失败: {json_result['error']}"],
                        "recommendation": "不推荐"
                    }
                    logger.warning(f"【对比失败 - JSON解析错误】错误: {json_result.get('error', '未知错误')}")
                    logger.info("=" * 80)
                    return result
            else:
                result = {
                    "relevance_score": 0.0,
                    "is_related": False,
                    "similarity_reasons": [],
                    "differences": [f"Qwen调用失败: {response['error']}"],
                    "recommendation": "不推荐"
                }
                logger.error(f"【对比失败 - API调用错误】错误: {response.get('error', '未知错误')}")
                logger.info("=" * 80)
                return result
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"【对比失败 - 异常】异常: {str(e)}")
            logger.error(f"错误详情: {error_detail}")
            logger.info("=" * 80)
            return {
                "relevance_score": 0.0,
                "is_related": False,
                "similarity_reasons": [],
                "differences": [f"比较失败: {str(e)}"],
                "recommendation": "不推荐"
            }
    
    def batch_validate_workcards(self, workcards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量验证工卡数据"""
        import asyncio
        
        async def _batch_validate():
            tasks = [self.validate_workcard_data(workcard) for workcard in workcards]
            return await asyncio.gather(*tasks)
        
        return asyncio.run(_batch_validate())


# 全局单例
_qwen_service = None


def get_qwen_service() -> QwenService:
    """获取Qwen服务单例"""
    global _qwen_service
    if _qwen_service is None:
        _qwen_service = QwenService()
    return _qwen_service




