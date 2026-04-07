from fastapi import APIRouter
from app.api.api_v1.endpoints import configurations, workcards, defects, matching, index_data, llm_logs, llm_models, workcard_import, import_batches, localwash, defect_list, defect_schemes, standard_defect_desc

api_router = APIRouter()

api_router.include_router(
    defect_schemes.router,
    prefix="/defect-schemes",
    tags=["defect-schemes"]
)
api_router.include_router(
    standard_defect_desc.router,
    prefix="/standard-defect-desc",
    tags=["standard-defect-desc"]
)
api_router.include_router(
    standard_defect_desc.single_router,
    prefix="/single-defect-checks",
    tags=["single-defect-checks"]
)
api_router.include_router(
    standard_defect_desc.batch_router,
    prefix="/batch-defect-checks",
    tags=["batch-defect-checks"]
)
api_router.include_router(
    standard_defect_desc.seat_router,
    prefix="/seat-defect-checks",
    tags=["seat-defect-checks"]
)
api_router.include_router(
    standard_defect_desc.crew_seat_router,
    prefix="/crew-seat-defect-checks",
    tags=["crew-seat-defect-checks"]
)
api_router.include_router(
    standard_defect_desc.custom_router,
    prefix="/custom-defect-desc",
    tags=["custom-defect-desc"]
)

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

# Local wash & match (strictly separated from existing AI pipeline)
api_router.include_router(
    localwash.router,
    prefix="/local",
    tags=["localwash"]
)

# Defect list processing
api_router.include_router(
    defect_list.router,
    prefix="/defect-list",
    tags=["defect-list"]
)
