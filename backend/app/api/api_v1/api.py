from fastapi import APIRouter, Depends

from app.api.api_v1.endpoints import (
    auth,
    defect_schemes,
    import_batches,
    llm_logs,
    llm_models,
    localwash,
    standard_defect_desc,
    users,
    workcard_import,
)
from app.core.permissions import PermissionCodes
from app.core.security import require_any_permission, require_authenticated_user, require_permission

api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)
api_router.include_router(
    defect_schemes.router,
    prefix="/defect-schemes",
    tags=["defect-schemes"],
    dependencies=[Depends(require_permission(PermissionCodes.CHINESE_SCHEME))]
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
    llm_logs.router,
    prefix="/llm",
    tags=["llm-logs"],
    dependencies=[Depends(require_authenticated_user)]
)
api_router.include_router(
    llm_models.router,
    prefix="/llm",
    tags=["llm-models"],
    dependencies=[Depends(require_authenticated_user)]
)
api_router.include_router(
    workcard_import.router,
    prefix="/workcard-import",
    tags=["workcard-import"],
    dependencies=[Depends(require_any_permission(PermissionCodes.ENGLISH_MAIN, PermissionCodes.CHINESE_MAIN))]
)
api_router.include_router(
    import_batches.router,
    prefix="/import-batches",
    tags=["import-batches"],
    dependencies=[Depends(require_any_permission(PermissionCodes.ENGLISH_MAIN, PermissionCodes.CHINESE_MAIN))]
)

# Local wash & match (strictly separated from existing AI pipeline)
api_router.include_router(
    localwash.router,
    prefix="/local",
    tags=["localwash"],
    dependencies=[Depends(require_any_permission(PermissionCodes.CHINESE_KEYWORDS, PermissionCodes.CHINESE_MAIN))]
)
