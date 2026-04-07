import os
import sqlite3
import datetime
import sys

ALLOWED_SCHEMA = {
    "defect_schemes": {
        "id", "comp_pn", "defect_catalog", "jc_desc_cn", "jc_desc_en", "key_words_1", "key_words_2",
        "trade", "zone", "loc", "qty", "jc_type", "labor", "manhour", "candidate_history_wo",
        "refer_manual", "type", "cust", "comp_name", "created_at", "updated_at"
    },
    "defect_steps": {
        "id", "scheme_id", "step_number", "step_desc_cn", "step_desc_en", "manhour", "trade", "manpower", "refer_manual"
    },
    "defect_materials": {
        "id", "step_id", "material_seq", "part_number", "amount", "unit", "remark"
    },
    "defect_lists": {
        "id", "aircraft_number", "title", "description", "status", "processing_progress", "cleaning_status",
        "cleaning_progress", "matching_status", "matching_progress", "processing_stage", "last_processed_at",
        "configuration_id", "created_at", "updated_at"
    },
    "defect_records": {
        "id", "defect_number", "title", "description", "system", "component", "location", "severity",
        "is_matched", "is_selected", "selected_workcard_id", "issued_workcard_number", "is_cleaned",
        "cleaned_at", "matched_at", "raw_data", "defect_list_id", "created_at", "updated_at"
    },
    "defect_cleaned_data": {
        "id", "defect_record_id", "main_area", "main_component", "first_level_subcomponent",
        "second_level_subcomponent", "orientation", "defect_subject", "defect_description", "location",
        "quantity", "description_cn", "is_cleaned", "cleaned_at", "cleaning_confidence", "created_at", "updated_at"
    },
    "matching_results": {
        "id", "similarity_score", "is_candidate", "matching_details", "algorithm_version",
        "defect_record_id", "workcard_id", "created_at"
    },
    "candidate_workcards": {
        "id", "defect_record_id", "workcard_id", "similarity_score", "is_selected", "selection_notes",
        "created_at", "updated_at"
    },
    "workcards": {
        "id", "workcard_number", "title", "description", "system", "component", "location", "action",
        "configuration_id", "workcard_type_id", "aircraft_number", "aircraft_type", "msn", "amm_ipc_eff",
        "main_area", "main_component", "first_level_subcomponent", "second_level_subcomponent", "orientation",
        "defect_subject", "defect_description", "location_index", "quantity", "raw_data", "is_cleaned",
        "cleaning_confidence", "cleaning_notes", "created_at", "updated_at"
    },
    "import_batches": {
        "id", "defect_list_id", "aircraft_number", "workcard_number", "maintenance_level",
        "aircraft_type", "customer", "created_at", "updated_at"
    },
    "import_batch_items": {
        "id", "batch_id", "defect_record_id", "defect_number", "description_cn", "description_en",
        "workcard_number", "issued_workcard_number", "selected_workcard_id", "similarity_score",
        "reference_workcard_number", "reference_workcard_item", "area", "zone_number", "loc", "qty",
        "comp_pn", "keywords_1", "keywords_2", "candidate_description_en", "candidate_description_cn",
        "ref_manual", "created_at"
    },
    "standard_defect_descriptions": {
        "id", "seq", "comp_pn", "standardized_desc", "type", "cust", "comp_name"
    },
    "custom_defect_descriptions": {
        "id", "seq", "comp_pn", "standardized_desc", "type", "cust", "comp_name"
    },
    "single_defect_checks": {
        "id", "seq", "comp_pn", "standardized_desc", "type", "cust", "comp_name", "loc", "inspector",
        "yes_flag", "no_flag", "defect_status", "defect_positions", "defect_quantity", "aircraft_no",
        "sale_wo", "plan_year_month", "local_photo_url", "global_photo_url"
    },
    "batch_defect_checks": {
        "id", "seq", "comp_pn", "standardized_desc", "type", "cust", "comp_name", "position", "quantity",
        "yes_flag", "no_flag", "defect_status", "defect_positions", "defect_quantity", "aircraft_no",
        "sale_wo", "plan_year_month", "local_photo_url", "global_photo_url"
    },
}

ALLOWED_EXTRA_TABLES = {"alembic_version"}

p = "aircraft_workcard.db"
if not os.path.exists(p):
    sys.exit(0)

err = None
scope_warn = []
try:
    f = open(p, "rb")
    hdr = f.read(16)
    f.close()
    if hdr != b"SQLite format 3\x00":
        raise RuntimeError("bad header")
    conn = sqlite3.connect(p)
    conn.execute("SELECT name FROM sqlite_master LIMIT 1")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    actual_tables = {r[0] for r in cur.fetchall()}
    allowed_tables = set(ALLOWED_SCHEMA.keys()) | ALLOWED_EXTRA_TABLES
    out_of_scope_tables = sorted(t for t in actual_tables if t not in allowed_tables)
    missing_tables = sorted(t for t in ALLOWED_SCHEMA.keys() if t not in actual_tables)
    if out_of_scope_tables:
        scope_warn.append("Out-of-scope tables: " + ", ".join(out_of_scope_tables))
    if missing_tables:
        scope_warn.append("Missing in-scope tables: " + ", ".join(missing_tables))
    for table, expected_cols in ALLOWED_SCHEMA.items():
        if table not in actual_tables:
            continue
        c2 = conn.cursor()
        c2.execute(f"PRAGMA table_info('{table}')")
        actual_cols = {r[1] for r in c2.fetchall()}
        extra_cols = sorted(c for c in actual_cols if c not in expected_cols)
        missing_cols = sorted(c for c in expected_cols if c not in actual_cols)
        if extra_cols:
            scope_warn.append(f"[{table}] extra columns: " + ", ".join(extra_cols))
        if missing_cols:
            scope_warn.append(f"[{table}] missing columns: " + ", ".join(missing_cols))
    conn.close()
except Exception as e:
    err = e

if err is not None:
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    bad = f"{p}.bad_{ts}"
    try:
        os.replace(p, bad)
        print("    - [WARNING] Invalid SQLite file detected, moved to: " + bad)
    except Exception as move_err:
        print("    - [WARNING] Invalid SQLite file detected but could not move file: " + str(move_err))
elif scope_warn:
    print("    - [WARNING] Database schema scope check warnings:")
    for line in scope_warn:
        print("      * " + line)

