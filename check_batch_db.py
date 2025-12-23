import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add local directory to sys.path to ensure modules can be imported
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.app.models.import_batch import Base, ImportBatch, ImportBatchItem

# ABSOLUTE PATH TO THE DATABASE
DB_URL = "sqlite:///f:/autojobcard/backend/aircraft_workcard.db"

def check_batches(batch_ids):
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        for batch_id in batch_ids:
            print(f"\n--- Checking Batch {batch_id} ---")
            batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
            if not batch:
                print(f"Batch {batch_id} NOT FOUND")
                continue
            
            print(f"Batch Info: Aircraft={batch.aircraft_number}, DefectList={batch.defect_list_id}")
            
            items = db.query(ImportBatchItem).filter(ImportBatchItem.batch_id == batch_id).all()
            print(f"Item Count: {len(items)}")
            
            if items:
                # Print first item details
                item = items[0]
                print("First Item Details:")
                print(f"  ID: {item.id}")
                print(f"  Defect Number: {item.defect_number}")
                print(f"  Workcard Number (Candidate): '{item.workcard_number}'")
                print(f"  Issued Workcard: '{item.issued_workcard_number}'")
                print(f"  Ref JC Number (txtCRN): '{item.reference_workcard_number}'")
                print(f"  Ref JC Item (refNo): '{item.reference_workcard_item}'")
                print(f"  Area (txtZoneName): '{item.area}'")
                print(f"  Zone (txtZoneTen): '{item.zone_number}'")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_batches([5, 6, 7])
