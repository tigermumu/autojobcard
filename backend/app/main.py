from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.api_v1.api import api_router
import logging
import sys
import os
from pathlib import Path

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
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
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

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

frontend_dist_dir = Path(os.getenv("FRONTEND_DIST_DIR", "/app/frontend_dist"))
frontend_index = frontend_dist_dir / "index.html"

@app.get("/")
async def root():
    if frontend_index.exists():
        return FileResponse(str(frontend_index))
    return {"message": "飞机方案处理系统 API"}

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if not frontend_index.exists():
        return {"detail": "Not Found"}
    if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path == "api" or full_path == "uploads":
        return {"detail": "Not Found"}
    requested = (frontend_dist_dir / full_path).resolve()
    if not str(requested).startswith(str(frontend_dist_dir.resolve())):
        return FileResponse(str(frontend_index))
    if requested.exists() and requested.is_file():
        return FileResponse(str(requested))
    return FileResponse(str(frontend_index))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
