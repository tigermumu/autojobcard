from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.import_batch import (
    ImportBatchCreate,
    ImportBatchSummary,
    ImportBatchDetail
)
from app.services.import_batch_service import ImportBatchService

router = APIRouter()


@router.post("/", response_model=ImportBatchSummary)
def create_import_batch(
    payload: ImportBatchCreate,
    db: Session = Depends(get_db)
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="待导入的数据项不能为空")

    service = ImportBatchService(db)
    batch = service.create_batch(payload.metadata.dict(), [item.dict() for item in payload.items])
    return {
        "id": batch.id,
        "aircraft_number": batch.aircraft_number,
        "workcard_number": batch.workcard_number,
        "maintenance_level": batch.maintenance_level,
        "aircraft_type": batch.aircraft_type,
        "customer": batch.customer,
        "defect_list_id": batch.defect_list_id,
        "created_at": batch.created_at,
        "item_count": len(batch.items)
    }


@router.get("/", response_model=List[ImportBatchSummary])
def list_import_batches(
    db: Session = Depends(get_db)
):
    service = ImportBatchService(db)
    return service.list_batches()


@router.get("/{batch_id}", response_model=ImportBatchDetail)
def get_import_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):
    service = ImportBatchService(db)
    batch = service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="待导入批次未找到")
    return batch









