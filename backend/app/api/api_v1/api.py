from fastapi import APIRouter
from app.api.api_v1.endpoints import configurations, workcards, defects, matching, index_data, llm_logs, llm_models, workcard_import, import_batches

api_router = APIRouter()

api_router.include_router(
    configurations.router, 
    prefix="/configurations", 
    tags=["configurations"]
)
api_router.include_router(
    workcards.router, 
    prefix="/workcards", 
    tags=["workcards"]
)
api_router.include_router(
    defects.router, 
    prefix="/defects", 
    tags=["defects"]
)
api_router.include_router(
    matching.router, 
    prefix="/matching", 
    tags=["matching"]
)
api_router.include_router(
    index_data.router, 
    prefix="/index-data", 
    tags=["index-data"]
)
api_router.include_router(
    llm_logs.router,
    prefix="/llm",
    tags=["llm-logs"]
)
api_router.include_router(
    llm_models.router,
    prefix="/llm",
    tags=["llm-models"]
)
api_router.include_router(
    workcard_import.router,
    prefix="/workcard-import",
    tags=["workcard-import"]
)
api_router.include_router(
    import_batches.router,
    prefix="/import-batches",
    tags=["import-batches"]
)
