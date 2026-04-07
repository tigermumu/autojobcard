from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    res = db.execute(text('SELECT id, title FROM defect_lists ORDER BY id DESC LIMIT 50')).fetchall()
    print("Defect Lists (ID: Title):")
    for r in res:
        print(f"{r[0]}: {r[1]}")
finally:
    db.close()
