import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.schemas.import_batch import ImportBatchCreate
from pydantic import ValidationError

# simulate frontend payload
# items have defect_record_id as null, similarity_score as 0 (int)
data = {
    "metadata": {
        "aircraft_number": "B-1234",
        "workcard_number": "WO-123",
        "maintenance_level": "A-Check",
        "aircraft_type": "B777",
        "customer": "AirChina"
    },
    "items": [
        {
            "defect_record_id": None,
            "defect_number": "D-001",
            "description_cn": "Desc",
            "description_en": "Desc EN",
            "workcard_number": "WC-001",
            "issued_workcard_number": "NR/000",
            "selected_workcard_id": None,
            "similarity_score": 0
        }
    ]
}

print("Testing validation...")
try:
    model = ImportBatchCreate(**data)
    print("Validation Success")
    print(model.dict())
except ValidationError as e:
    print("Validation Failed")
    print(e)
except Exception as e:
    print(f"Other Error: {e}")
