from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "飞机方案处理系统"
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/aircraft_workcard")
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8000",
    ]
    
    # Qwen配置
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen-plus")

    # Gemini配置
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # 默认大模型
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "Qwen")

    # 工卡导入配置
    WORKCARD_IMPORT_BASE_URL: str = os.getenv("WORKCARD_IMPORT_BASE_URL", "http://10.240.2.131:9080")
    WORKCARD_IMPORT_VERIFY_SSL: bool = os.getenv("WORKCARD_IMPORT_VERIFY_SSL", "false").lower() == "true"
    WORKCARD_IMPORT_COOKIES: str = os.getenv("WORKCARD_IMPORT_COOKIES", "")
    WORKCARD_IMPORT_PRINTER: str = os.getenv("WORKCARD_IMPORT_PRINTER", r"\\lx-ps01\\Prt2Q09L非例卡(机上客舱工艺组)")
    WORKCARD_IMPORT_OUTPUT_DIR: str = os.getenv("WORKCARD_IMPORT_OUTPUT_DIR", "storage/import_logs")
    WORKCARD_IMPORT_SAVE_HTML: bool = os.getenv("WORKCARD_IMPORT_SAVE_HTML", "true").lower() == "true"
    
    # 相似度阈值
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "75.0"))
    
    # 算法权重配置
    ALGORITHM_WEIGHTS: dict = {
        "main_area": 0.05,
        "main_component": 0.20,
        "first_level_subcomponent": 0.35,  # 一级子部件权重最高
        "second_level_subcomponent": 0.20,
        "orientation": 0.05,
        "defect_subject": 0.10,
        "defect_description": 0.05
    }
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
