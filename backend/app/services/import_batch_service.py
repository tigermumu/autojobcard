from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.import_batch import ImportBatch, ImportBatchItem
from app.models.defect import DefectRecord


class ImportBatchService:
    def __init__(self, db: Session):
        self.db = db

    def delete_batch(self, batch_id: int) -> bool:
        batch = (
            self.db.query(ImportBatch)
            .filter(ImportBatch.id == batch_id)
            .first()
        )
        if not batch:
            return False

        # Cascade delete items (if not handled by DB foreign key cascade)
        # Assuming we want to explicitly delete items or rely on cascade
        # For safety, let's just delete the batch and let SQLAlchemy/DB handle cascade if configured,
        # or we might need to delete items first if strict.
        # Given potential SQLite limitations or explicit needs:
        self.db.query(ImportBatchItem).filter(ImportBatchItem.batch_id == batch.id).delete()
        
        self.db.delete(batch)
        self.db.commit()
        return True

    def create_batch(
        self,
        metadata: Dict[str, Any],
        items: List[Dict[str, Any]]
    ) -> ImportBatch:
        batch = ImportBatch(
            defect_list_id=metadata.get("defect_list_id"),
            aircraft_number=metadata["aircraft_number"],
            workcard_number=metadata["workcard_number"],
            maintenance_level=metadata["maintenance_level"],
            aircraft_type=metadata["aircraft_type"],
            customer=metadata["customer"]
        )
        self.db.add(batch)
        self.db.flush()  # obtain batch.id

        for item in items:
            batch_item = ImportBatchItem(
                batch_id=batch.id,
                defect_record_id=item.get("defect_record_id"),
                defect_number=item["defect_number"],
                description_cn=item.get("description_cn"),
                description_en=item.get("description_en"),
                workcard_number=item.get("workcard_number"),  # 候选工卡，可以为空
                selected_workcard_id=item.get("selected_workcard_id"),
                similarity_score=item.get("similarity_score"),
                issued_workcard_number=item.get("issued_workcard_number"),
                # Add new fields
                reference_workcard_number=item.get("reference_workcard_number"),
                reference_workcard_item=item.get("reference_workcard_item"),
                area=item.get("area"),
                zone_number=item.get("zone_number")
            )
            self.db.add(batch_item)

        self.db.commit()
        self.db.refresh(batch)
        return batch

    def list_batches(self) -> List[Dict[str, Any]]:
        query = (
            self.db.query(
                ImportBatch,
                func.count(ImportBatchItem.id).label("item_count")
            )
            .outerjoin(ImportBatchItem, ImportBatchItem.batch_id == ImportBatch.id)
            .group_by(ImportBatch.id)
            .order_by(ImportBatch.created_at.desc())
        )

        results: List[Dict[str, Any]] = []
        for batch, item_count in query.all():
            results.append({
                "id": batch.id,
                "defect_list_id": batch.defect_list_id,
                "aircraft_number": batch.aircraft_number,
                "workcard_number": batch.workcard_number,
                "maintenance_level": batch.maintenance_level,
                "aircraft_type": batch.aircraft_type,
                "customer": batch.customer,
                "created_at": batch.created_at,
                "item_count": item_count or 0
            })
        return results

    def get_batch(self, batch_id: int) -> Optional[Dict[str, Any]]:
        batch = (
            self.db.query(ImportBatch)
            .filter(ImportBatch.id == batch_id)
            .first()
        )
        if not batch:
            return None

        items = (
            self.db.query(ImportBatchItem)
            .filter(ImportBatchItem.batch_id == batch.id)
            .order_by(ImportBatchItem.id.asc())
            .all()
        )

        # 获取所有相关的缺陷记录ID，用于查询已开出的工卡号
        defect_record_ids = [item.defect_record_id for item in items if item.defect_record_id]
        defect_records_map = {}
        if defect_record_ids:
            defect_records = (
                self.db.query(DefectRecord)
                .filter(DefectRecord.id.in_(defect_record_ids))
                .all()
            )
            defect_records_map = {dr.id: dr for dr in defect_records}

        return {
            "id": batch.id,
            "defect_list_id": batch.defect_list_id,
            "aircraft_number": batch.aircraft_number,
            "workcard_number": batch.workcard_number,
            "maintenance_level": batch.maintenance_level,
            "aircraft_type": batch.aircraft_type,
            "customer": batch.customer,
            "created_at": batch.created_at,
            "items": [
                {
                    "id": item.id,
                    "defect_record_id": item.defect_record_id,
                    "defect_number": item.defect_number,
                    "description_cn": item.description_cn or "",
                    "description_en": item.description_en or "",
                    "workcard_number": item.workcard_number,
                    "selected_workcard_id": item.selected_workcard_id,
                    "similarity_score": item.similarity_score,
                    "issued_workcard_number": (
                        defect_records_map[item.defect_record_id].issued_workcard_number
                        if item.defect_record_id and item.defect_record_id in defect_records_map
                        and hasattr(defect_records_map[item.defect_record_id], 'issued_workcard_number')
                        else item.issued_workcard_number
                    ),
                    # Add new fields
                    "reference_workcard_number": item.reference_workcard_number,
                    "reference_workcard_item": item.reference_workcard_item,
                    "area": item.area,
                    "zone_number": item.zone_number
                }
                for item in items
            ]
        }


