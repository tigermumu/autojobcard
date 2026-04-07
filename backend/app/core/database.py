from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

Base = declarative_base()

def _create_engine():
    url = settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    e = create_engine(url, connect_args=connect_args, echo=False)
    if not url.startswith("sqlite"):
        return e
    try:
        with e.connect() as conn:
            conn.execute(text("SELECT name FROM sqlite_master LIMIT 1"))
        return e
    except Exception as ex:
        msg = str(ex).lower()
        if "unsupported file format" not in msg and "file is not a database" not in msg:
            return e
    fallback_url = "sqlite:///./aircraft_workcard_r1.db"
    return create_engine(fallback_url, connect_args=connect_args, echo=False)

engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _get_sqlite_columns(conn, table_name: str) -> set[str]:
    cols = conn.execute(text(f"PRAGMA table_info('{table_name}')")).mappings().all()
    return {c["name"] for c in cols}

def _ensure_sqlite_columns(table_name: str, column_ddls: list[str]):
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    with engine.connect() as conn:
        try:
            existing = _get_sqlite_columns(conn, table_name)
            if not existing:
                return
            alters = []
            for column_name, ddl in column_ddls:
                if column_name not in existing:
                    alters.append(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")
            for ddl in alters:
                conn.execute(text(ddl))
            if alters:
                conn.commit()
        except Exception:
            pass

def _ensure_defect_scheme_columns():
    """Ensure newly added columns exist for SQLite without alembic migrations."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    with engine.connect() as conn:
        try:
            cols = conn.execute(text("PRAGMA table_info('defect_schemes')")).mappings().all()
            existing = {c["name"] for c in cols}
            alters = []
            if "type" not in existing:
                alters.append("ALTER TABLE defect_schemes ADD COLUMN type VARCHAR(50)")
            if "cust" not in existing:
                alters.append("ALTER TABLE defect_schemes ADD COLUMN cust VARCHAR(50)")
            if "comp_name" not in existing:
                alters.append("ALTER TABLE defect_schemes ADD COLUMN comp_name VARCHAR(100)")
            for ddl in alters:
                conn.execute(text(ddl))
            if alters:
                conn.commit()
        except Exception:
            # Best-effort; avoid blocking app startup on schema check
            pass

def _ensure_standard_defect_desc_columns():
    _ensure_sqlite_columns("standard_defect_descriptions", [
        ("comp_pn", "comp_pn VARCHAR(50)"),
        ("standardized_desc", "standardized_desc TEXT"),
        ("type", "type VARCHAR(50)"),
        ("cust", "cust VARCHAR(50)"),
        ("comp_name", "comp_name VARCHAR(100)"),
    ])

def _ensure_single_defect_check_columns():
    column_ddls = [
        ("seq", "seq INTEGER"),
        ("comp_pn", "comp_pn VARCHAR(50)"),
        ("standardized_desc", "standardized_desc TEXT"),
        ("type", "type VARCHAR(50)"),
        ("cust", "cust VARCHAR(50)"),
        ("comp_name", "comp_name VARCHAR(100)"),
        ("loc", "loc VARCHAR(200)"),
        ("inspector", "inspector VARCHAR(50)"),
        ("yes_flag", "yes_flag INTEGER"),
        ("no_flag", "no_flag INTEGER"),
        ("defect_status", "defect_status VARCHAR(200)"),
        ("defect_positions", "defect_positions TEXT"),
        ("defect_quantity", "defect_quantity INTEGER"),
        ("aircraft_no", "aircraft_no VARCHAR(50)"),
        ("sale_wo", "sale_wo VARCHAR(100)"),
        ("plan_year_month", "plan_year_month VARCHAR(20)"),
        ("local_photo_url", "local_photo_url VARCHAR(500)"),
        ("global_photo_url", "global_photo_url VARCHAR(500)"),
        ("defect_desc_preview", "defect_desc_preview TEXT"),
        ("desc_text", "desc_text TEXT"),
        ("loc_text", "loc_text TEXT"),
        ("qty_text", "qty_text VARCHAR(100)"),
    ]
    _ensure_sqlite_columns("single_defect_checks", column_ddls)
    _ensure_sqlite_columns("galley_lav_defect_checks", column_ddls)

def _ensure_custom_defect_desc_columns():
    _ensure_sqlite_columns("custom_defect_descriptions", [
        ("seq", "seq INTEGER"),
        ("comp_pn", "comp_pn VARCHAR(50)"),
        ("standardized_desc", "standardized_desc TEXT"),
        ("type", "type VARCHAR(50)"),
        ("cust", "cust VARCHAR(50)"),
        ("comp_name", "comp_name VARCHAR(100)"),
    ])

def _ensure_batch_defect_check_columns():
    column_ddls = [
        ("seq", "seq INTEGER"),
        ("comp_pn", "comp_pn VARCHAR(50)"),
        ("standardized_desc", "standardized_desc TEXT"),
        ("type", "type VARCHAR(50)"),
        ("cust", "cust VARCHAR(50)"),
        ("comp_name", "comp_name VARCHAR(100)"),
        ("position", "position VARCHAR(200)"),
        ("quantity", "quantity FLOAT"),
        ("yes_flag", "yes_flag INTEGER"),
        ("no_flag", "no_flag INTEGER"),
        ("defect_status", "defect_status VARCHAR(200)"),
        ("defect_positions", "defect_positions TEXT"),
        ("defect_quantity", "defect_quantity INTEGER"),
        ("aircraft_no", "aircraft_no VARCHAR(50)"),
        ("sale_wo", "sale_wo VARCHAR(100)"),
        ("plan_year_month", "plan_year_month VARCHAR(20)"),
        ("local_photo_url", "local_photo_url VARCHAR(500)"),
        ("global_photo_url", "global_photo_url VARCHAR(500)"),
        ("defect_desc_preview", "defect_desc_preview TEXT"),
        ("desc_text", "desc_text TEXT"),
        ("loc_text", "loc_text TEXT"),
        ("qty_text", "qty_text VARCHAR(100)"),
    ]
    _ensure_sqlite_columns("batch_defect_checks", column_ddls)
    _ensure_sqlite_columns("panel_defect_checks", column_ddls)

def _ensure_seat_defect_check_columns():
    column_ddls = [
        ("seq", "seq INTEGER"),
        ("comp_pn", "comp_pn VARCHAR(50)"),
        ("standardized_desc", "standardized_desc TEXT"),
        ("type", "type VARCHAR(50)"),
        ("cust", "cust VARCHAR(50)"),
        ("comp_name", "comp_name VARCHAR(100)"),
        ("loc", "loc VARCHAR(200)"),
        ("inspector", "inspector VARCHAR(50)"),
        ("yes_flag", "yes_flag INTEGER"),
        ("no_flag", "no_flag INTEGER"),
        ("defect_status", "defect_status VARCHAR(200)"),
        ("defect_positions", "defect_positions TEXT"),
        ("defect_quantity", "defect_quantity INTEGER"),
        ("aircraft_no", "aircraft_no VARCHAR(50)"),
        ("sale_wo", "sale_wo VARCHAR(100)"),
        ("plan_year_month", "plan_year_month VARCHAR(20)"),
        ("local_photo_url", "local_photo_url VARCHAR(500)"),
        ("global_photo_url", "global_photo_url VARCHAR(500)"),
        ("custom_positions_input", "custom_positions_input TEXT"),
        ("defect_desc_preview", "defect_desc_preview TEXT"),
        ("desc_text", "desc_text TEXT"),
        ("loc_text", "loc_text TEXT"),
        ("qty_text", "qty_text VARCHAR(100)"),
    ]
    _ensure_sqlite_columns("seat_defect_checks", column_ddls)
    _ensure_sqlite_columns("crew_seat_defect_checks", column_ddls)

# Auto create tables if not exist
def _ensure_tables():
    try:
        from app import models  # noqa
        from app.models import defect_desc  # noqa
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

# Best-effort auto-upgrade for SQLite
_ensure_tables()
_ensure_defect_scheme_columns()
_ensure_standard_defect_desc_columns()
_ensure_single_defect_check_columns()
_ensure_custom_defect_desc_columns()
_ensure_batch_defect_check_columns()
_ensure_seat_defect_check_columns()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
