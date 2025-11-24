"""
Gemini AI服务模块
基于Google Gemini模型，为飞机方案处理系统提供与Qwen一致的接口
"""
import logging
import datetime
from typing import Dict, Any, List

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.qwen_service import QwenService


class GeminiService(QwenService):
    """Gemini AI服务 - 复用Qwen服务流程，替换底层模型调用"""

    def __init__(self):
        # 不调用父类 __init__，避免初始化Qwen客户端
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL
        self.provider_name = "Gemini"

    def generate_text(
        self,
        prompt: str,
        system_prompt: str = "你是一个专业的航空维修数据分析助手。",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        重写生成文本方法，使用Google Gemini模型
        """
        logger = logging.getLogger(__name__)

        request_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        logger.info("")
        logger.info("╔" + "=" * 98 + "╗")
        logger.info("║" + " " * 30 + f"【大模型调用开始 - 请求ID: {request_id}】" + " " * 30 + "║")
        logger.info("╠" + "=" * 98 + "╣")
        logger.info(f"║ 模型: {self.model:<90} ║")
        logger.info("║ API Base URL: Google Generative AI ║")
        logger.info(f"║ 提示词长度: {len(prompt)}, 系统提示词长度: {len(system_prompt):<60} ║")
        logger.info(f"║ Temperature: {temperature}, Max Tokens: {max_tokens:<60} ║")
        logger.info(f"║ 时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]:<80} ║")
        logger.info("╠" + "-" * 98 + "╣")
        logger.info("║" + " " * 10 + "【系统提示词】" + " " * 70 + "║")
        logger.info("╠" + "-" * 98 + "╣")
        for line in system_prompt.split('\n'):
            logger.info(f"║ {line[:96]:<96} ║")
        logger.info("╠" + "-" * 98 + "╣")
        logger.info("║" + " " * 10 + "【用户提示词】" + " " * 70 + "║")
        logger.info("╠" + "-" * 98 + "╣")
        for line in prompt.split('\n'):
            logger.info(f"║ {line[:96]:<96} ║")
        logger.info("╠" + "-" * 98 + "╣")
        logger.info("║ 正在发送API请求..." + " " * 80 + "║")

        try:
            # 计算提示词token数（粗略估算：中文1字符≈1token，英文1词≈1token）
            total_prompt_length = len(system_prompt) + len(prompt)
            estimated_tokens = total_prompt_length  # 粗略估算
            
            logger.info("╠" + "-" * 98 + "╣")
            logger.info(f"║ 提示词总长度: {total_prompt_length} 字符 ║")
            logger.info(f"║ 估算token数: ~{estimated_tokens} ║")
            logger.info(f"║ max_output_tokens设置: {max_tokens} ║")
            logger.info(f"║ 可用输出空间: {max_tokens} tokens ║")
            if estimated_tokens + max_tokens > 8000:  # Gemini 2.0 Flash 通常有32K上下文
                logger.warning(f"║ ⚠️ 提示词可能过长，可能影响响应生成 ║")
            logger.info("╠" + "-" * 98 + "╣")
            
            generation_config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(f"{system_prompt}\n\n{prompt}")]
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=[content],
                config=generation_config
            )

            # ========== 调试日志：检查响应结构 ==========
            logger.info("╠" + "-" * 98 + "╣")
            logger.info("║" + " " * 10 + "【调试信息 - 响应结构分析】" + " " * 60 + "║")
            logger.info("╠" + "-" * 98 + "╣")
            
            # 检查response对象类型和属性
            logger.info(f"║ Response类型: {str(type(response)):<88} ║")
            response_attrs = [attr for attr in dir(response) if not attr.startswith('_')]
            logger.info(f"║ Response主要属性数量: {len(response_attrs):<88} ║")
            logger.info(f"║ Response主要属性: {', '.join(response_attrs[:10]):<88} ║")
            
            # 检查response.text
            if hasattr(response, "text"):
                text_value = response.text
                logger.info(f"║ response.text存在: True, 值类型: {str(type(text_value)):<88} ║")
                logger.info(f"║ response.text长度: {len(str(text_value)) if text_value else 0:<88} ║")
                if text_value:
                    logger.info(f"║ response.text前100字符: {str(text_value)[:100]:<88} ║")
                else:
                    logger.warning(f"║ response.text为空或None ║")
            else:
                logger.info(f"║ response.text属性不存在 ║")
            
            # 检查candidates
            candidates = getattr(response, "candidates", []) or []
            logger.info(f"║ candidates数量: {len(candidates):<88} ║")
            
            if not candidates:
                logger.warning(f"║ ⚠️ candidates为空列表！ ║")
            else:
                for i, candidate in enumerate(candidates):
                    logger.info(f"║ --- candidate[{i}] 分析 --- ║")
                    logger.info(f"║ candidate[{i}]类型: {str(type(candidate).__name__):<88} ║")
                    
                    # 检查finish_reason
                    finish_reason = getattr(candidate, "finish_reason", None)
                    logger.info(f"║ candidate[{i}].finish_reason: {finish_reason:<88} ║")
                    if finish_reason and finish_reason != "STOP":
                        logger.warning(f"║ ⚠️ finish_reason不是STOP，可能是: {finish_reason} ║")
                    
                    # 检查safety_ratings
                    safety_ratings = getattr(candidate, "safety_ratings", None)
                    if safety_ratings:
                        logger.warning(f"║ candidate[{i}].safety_ratings存在: {safety_ratings:<88} ║")
                        try:
                            if isinstance(safety_ratings, list):
                                for j, rating in enumerate(safety_ratings):
                                    category = getattr(rating, "category", "unknown")
                                    probability = getattr(rating, "probability", "unknown")
                                    logger.warning(f"║    rating[{j}]: {category} = {probability:<88} ║")
                        except Exception as e:
                            logger.warning(f"║    safety_ratings解析错误: {str(e):<88} ║")
                    
                    # 检查content
                    content = getattr(candidate, "content", None)
                    if content:
                        logger.info(f"║ candidate[{i}].content类型: {str(type(content).__name__):<88} ║")
                        content_attrs = [attr for attr in dir(content) if not attr.startswith('_')]
                        logger.info(f"║ candidate[{i}].content属性: {', '.join(content_attrs[:10]):<88} ║")
                        
                        parts = getattr(content, "parts", []) or []
                        logger.info(f"║ candidate[{i}].content.parts数量: {len(parts):<88} ║")
                        
                        if not parts:
                            logger.warning(f"║ ⚠️ candidate[{i}].content.parts为空！ ║")
                            logger.warning(f"║ ⚠️ finish_reason={finish_reason}，可能因为MAX_TOKENS导致没有生成内容 ║")
                            logger.warning(f"║ ⚠️ 建议：增加max_output_tokens或缩短提示词 ║")
                        else:
                            for j, part in enumerate(parts):
                                logger.info(f"║    part[{j}]类型: {str(type(part).__name__):<88} ║")
                                part_attrs = [attr for attr in dir(part) if not attr.startswith('_')]
                                logger.info(f"║    part[{j}]属性: {', '.join(part_attrs[:5]):<88} ║")
                                
                                if hasattr(part, "text"):
                                    part_text = getattr(part, "text", None)
                                    if part_text:
                                        logger.info(f"║    part[{j}].text长度: {len(str(part_text)):<88} ║")
                                        logger.info(f"║    part[{j}].text前100字符: {str(part_text)[:100]:<88} ║")
                                    else:
                                        logger.warning(f"║    part[{j}].text为空或None ║")
                                else:
                                    logger.info(f"║    part[{j}]没有text属性 ║")
                    else:
                        logger.warning(f"║ ⚠️ candidate[{i}].content不存在或为None ║")
            
            # 检查prompt_feedback
            prompt_feedback = getattr(response, "prompt_feedback", None)
            if prompt_feedback:
                logger.warning(f"║ prompt_feedback存在 ║")
                block_reason = getattr(prompt_feedback, "block_reason", None)
                if block_reason:
                    logger.error(f"║ ⚠️⚠️ 提示词被阻止，原因: {block_reason:<88} ║")
                safety_ratings = getattr(prompt_feedback, "safety_ratings", None)
                if safety_ratings:
                    logger.warning(f"║ prompt_feedback.safety_ratings: {safety_ratings:<88} ║")
                    try:
                        if isinstance(safety_ratings, list):
                            for j, rating in enumerate(safety_ratings):
                                category = getattr(rating, "category", "unknown")
                                probability = getattr(rating, "probability", "unknown")
                                logger.warning(f"║    prompt_rating[{j}]: {category} = {probability:<88} ║")
                    except Exception as e:
                        logger.warning(f"║    prompt_feedback.safety_ratings解析错误: {str(e):<88} ║")
            else:
                logger.info(f"║ prompt_feedback不存在（正常情况） ║")
            
            logger.info("╠" + "-" * 98 + "╣")
            # ========== 调试日志结束 ==========
            
            response_text = ""
            if hasattr(response, "text") and response.text:
                response_text = response.text
                logger.info(f"║ 使用response.text提取文本，长度: {len(response_text):<88} ║")
            else:
                logger.info(f"║ response.text不存在，尝试_extract_text_from_response ║")
                response_text = self._extract_text_from_response(response)
                logger.info(f"║ _extract_text_from_response返回长度: {len(response_text):<88} ║")

            logger.info("╠" + "-" * 98 + "╣")
            logger.info("║" + " " * 10 + f"【大模型API调用成功 - 请求ID: {request_id}】" + " " * 50 + "║")
            logger.info(f"║ 最终返回文本长度: {len(response_text):<88} ║")
            logger.info("╠" + "-" * 98 + "╣")
            logger.info("║" + " " * 10 + "【大模型返回内容 - 完整文本】" + " " * 60 + "║")
            logger.info("╠" + "-" * 98 + "╣")
            # 输出完整文本（分行显示）
            for line in response_text.split('\n'):
                logger.info(f"║ {line[:96]:<96} ║")
            logger.info("╠" + "-" * 98 + "╣")
            logger.info(f"║ 完整文本（单行，用于调试）: {repr(response_text):<88} ║")
            logger.info("╠" + "-" * 98 + "╣")
            logger.info("╠" + "=" * 98 + "╣")
            logger.info("║" + " " * 30 + f"【大模型调用结束 - 请求ID: {request_id}】" + " " * 30 + "║")
            logger.info("╚" + "=" * 98 + "╝")
            logger.info("")

            return {
                "success": True,
                "text": response_text,
                "model": "Gemini",
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
            for line in error_detail.split('\n'):
                logger.error(f"║ {line[:96]:<96} ║")
            logger.error("╠" + "=" * 98 + "╣")
            logger.error("║" + " " * 30 + f"【请求结束 - 请求ID: {request_id}】" + " " * 30 + "║")
            logger.error("╚" + "=" * 98 + "╝")
            logger.error("")
            return {
                "success": False,
                "error": f"Gemini API调用失败: {str(e)}",
                "text": ""
            }

    def _extract_text_from_response(self, response: Any) -> str:
        """从Gemini响应中抽取文本内容"""
        logger = logging.getLogger(__name__)
        try:
            candidates = getattr(response, "candidates", []) or []
            logger.debug(f"_extract_text_from_response: candidates数量 = {len(candidates)}")
            
            if not candidates:
                logger.warning("_extract_text_from_response: candidates为空")
                return ""
            
            for idx, candidate in enumerate(candidates):
                logger.debug(f"_extract_text_from_response: 处理candidate[{idx}]")
                
                content = getattr(candidate, "content", None)
                if not content:
                    logger.debug(f"_extract_text_from_response: candidate[{idx}].content不存在")
                    continue
                
                parts: List[Any] = getattr(content, "parts", []) or []
                logger.debug(f"_extract_text_from_response: candidate[{idx}].content.parts数量 = {len(parts)}")
                
                if not parts:
                    logger.warning(f"_extract_text_from_response: candidate[{idx}].content.parts为空")
                    continue
                
                texts = []
                for part_idx, part in enumerate(parts):
                    if hasattr(part, "text"):
                        part_text = getattr(part, "text", "")
                        if part_text:
                            texts.append(part_text)
                            logger.debug(f"_extract_text_from_response: part[{part_idx}].text长度 = {len(str(part_text))}")
                        else:
                            logger.debug(f"_extract_text_from_response: part[{part_idx}].text为空")
                    else:
                        logger.debug(f"_extract_text_from_response: part[{part_idx}]没有text属性")
                
                if texts:
                    result = "\n".join(texts)
                    logger.info(f"_extract_text_from_response: 成功提取文本，长度 = {len(result)}")
                    return result
                else:
                    logger.warning(f"_extract_text_from_response: candidate[{idx}]没有提取到文本")
            
            logger.warning("_extract_text_from_response: 所有candidates都没有提取到文本")
            return ""
        except Exception as e:
            logger.error(f"_extract_text_from_response: 提取文本时发生异常: {str(e)}", exc_info=True)
            return ""


_gemini_service = None


def get_gemini_service() -> GeminiService:
    """获取Gemini服务单例"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service

