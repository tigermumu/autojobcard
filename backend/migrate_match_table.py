import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "aircraft_workcard.db")
if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

print(f"Connecting to database: {os.path.abspath(db_path)}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column(table, column, type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type}")
        print(f"Successfully added column '{column}' to table '{table}'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"Column '{column}' already exists in table '{table}'.")
        else:
            print(f"Error adding column '{column}': {e}")

add_column("defect_match_local", "action", "VARCHAR(200)")
add_column("defect_match_local", "cabin_layout", "VARCHAR(100)")

conn.commit()
conn.close()
print("Migration completed.")
