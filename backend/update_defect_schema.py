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

def rename_column(table, old_col, new_col):
    try:
        cursor.execute(f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}")
        print(f"Successfully renamed column '{old_col}' to '{new_col}' in table '{table}'.")
        return True
    except sqlite3.OperationalError as e:
        if "no such column" in str(e).lower():
            print(f"Column '{old_col}' not found in table '{table}', skipping rename.")
        elif "duplicate column name" in str(e).lower():
             print(f"Target column '{new_col}' already exists in table '{table}', skipping rename.")
        else:
            print(f"Error renaming column '{old_col}': {e}")
        return False

# defect_schemes
add_column("defect_schemes", "candidate_history_wo", "VARCHAR(100)")
add_column("defect_schemes", "refer_manual", "VARCHAR(100)")

# defect_steps
# Try to rename first
if not rename_column("defect_steps", "step_desc", "step_desc_cn"):
    # If rename failed (e.g. old column missing), try adding new one
    add_column("defect_steps", "step_desc_cn", "TEXT")

add_column("defect_steps", "trade", "VARCHAR(50)")
add_column("defect_steps", "manpower", "VARCHAR(50)")
add_column("defect_steps", "refer_manual", "VARCHAR(100)")

# defect_materials
add_column("defect_materials", "material_seq", "INTEGER")
add_column("defect_materials", "unit", "VARCHAR(20)")
add_column("defect_materials", "remark", "VARCHAR(200)")

conn.commit()
conn.close()
print("Schema update completed.")
