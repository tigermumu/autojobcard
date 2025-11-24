from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1.api import api_router
import logging
import sys

# 配置日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 设置特定模块的日志级别
logging.getLogger("app.services.qwen_service").setLevel(logging.INFO)
logging.getLogger("app.services.workcard_service").setLevel(logging.INFO)
logging.getLogger("app.services.defect_service").setLevel(logging.INFO)
logging.getLogger("app.api.api_v1.endpoints.matching").setLevel(logging.INFO)

app = FastAPI(
    title="飞机方案处理系统",
    description="智能化的飞机工卡数据处理系统",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 设置CORS
# 确保CORS origins是列表格式
cors_origins = settings.BACKEND_CORS_ORIGINS
if isinstance(cors_origins, str):
    import json
    try:
        cors_origins = json.loads(cors_origins)
    except:
        cors_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "飞机方案处理系统 API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
