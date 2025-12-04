"""Redis客户端工具"""
import redis
import json
from typing import Optional, Dict, Any
from app.core.config import settings

# 全局Redis客户端实例
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """获取Redis客户端实例（单例模式）"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,  # 自动解码为字符串
            socket_connect_timeout=5,
            socket_timeout=5
        )
    return _redis_client

def set_matching_progress(task_id: str, progress: Dict[str, Any], expire_seconds: int = 3600):
    """设置匹配进度"""
    client = get_redis_client()
    key = f"matching_progress:{task_id}"
    client.setex(key, expire_seconds, json.dumps(progress, ensure_ascii=False))

def get_matching_progress(task_id: str) -> Optional[Dict[str, Any]]:
    """获取匹配进度"""
    client = get_redis_client()
    key = f"matching_progress:{task_id}"
    progress_json = client.get(key)
    if progress_json:
        return json.loads(progress_json)
    return None

def delete_matching_progress(task_id: str):
    """删除匹配进度"""
    client = get_redis_client()
    key = f"matching_progress:{task_id}"
    client.delete(key)





