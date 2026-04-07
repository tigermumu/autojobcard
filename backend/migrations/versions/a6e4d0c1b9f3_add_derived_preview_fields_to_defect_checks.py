"""add_derived_preview_fields_to_defect_checks

Revision ID: a6e4d0c1b9f3
Revises: f4c9a2b1d8e7
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa
import re


revision = "a6e4d0c1b9f3"
down_revision = "f4c9a2b1d8e7"
branch_labels = None
depends_on = None


SEAT_PREVIEW_ORDER = ["L", "A", "B", "C", "D", "E", "M", "F", "G", "H", "I", "J", "K", "R"]


def _norm_str(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return value


def _split_positions(raw):
    text = _norm_str(raw)
    if not text:
        return []
    return [item.strip() for item in re.split(r"[;；,，|｜、\n\r\t ]+", text) if item.strip()]


def _dedupe_keep_order(values):
    seen = set()
    result = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _sort_seat_preview_positions(values):
    index_map = {value: idx for idx, value in enumerate(SEAT_PREVIEW_ORDER)}
    uniq = _dedupe_keep_order(values)
    ranked = sorted([value for value in uniq if value in index_map], key=lambda value: index_map[value])
    others = [value for value in uniq if value not in index_map]
    return ranked + others


def _qty_to_text(value):
    if value is None:
        return None
    try:
        qty = int(value)
    except Exception:
        return None
    if qty <= 0:
        return None
    return f"{qty} EA"


def _build_derived_preview_fields(module_kind, is_defect, standardized_desc, defect_status, defect_positions, defect_quantity, loc=None, position=None):
    if not is_defect:
        return {
            "defect_desc_preview": None,
            "desc_text": None,
            "loc_text": None,
            "qty_text": None,
        }

    base_desc = _norm_str(standardized_desc) or ""
    status_text = _norm_str(defect_status) or ""
    desc_text = f"{base_desc}{status_text}" or None
    positions = _split_positions(defect_positions)
    qty_text = _qty_to_text(defect_quantity)

    if module_kind == "seat":
        seat_loc = _norm_str(loc) or ""
        loc_text = f"{seat_loc}{''.join(_sort_seat_preview_positions(positions))}" or None
    elif module_kind == "crew-seat":
        loc_text = " ".join(_dedupe_keep_order(positions)) or None
    elif module_kind == "batch":
        loc_text = " ".join(_dedupe_keep_order(positions)) or _norm_str(position)
    else:
        loc_text = " ".join(_dedupe_keep_order(positions)) or _norm_str(loc)

    preview = None
    if desc_text or loc_text or qty_text:
        preview = f"{desc_text or ''}，LOC：{loc_text or ''}，QTY：{qty_text or ''}"

    return {
        "defect_desc_preview": preview,
        "desc_text": desc_text,
        "loc_text": loc_text,
        "qty_text": qty_text,
    }


def _table_exists(inspector, table_name):
    return table_name in set(inspector.get_table_names())


def _column_names(inspector, table_name):
    return {column["name"] for column in inspector.get_columns(table_name)}


def _ensure_columns():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_columns = {
        "galley_lav_defect_checks": [
            sa.Column("defect_desc_preview", sa.Text(), nullable=True),
            sa.Column("desc_text", sa.Text(), nullable=True),
            sa.Column("loc_text", sa.Text(), nullable=True),
            sa.Column("qty_text", sa.String(length=100), nullable=True),
        ],
        "panel_defect_checks": [
            sa.Column("defect_desc_preview", sa.Text(), nullable=True),
            sa.Column("desc_text", sa.Text(), nullable=True),
            sa.Column("loc_text", sa.Text(), nullable=True),
            sa.Column("qty_text", sa.String(length=100), nullable=True),
        ],
        "seat_defect_checks": [
            sa.Column("defect_desc_preview", sa.Text(), nullable=True),
            sa.Column("desc_text", sa.Text(), nullable=True),
            sa.Column("loc_text", sa.Text(), nullable=True),
            sa.Column("qty_text", sa.String(length=100), nullable=True),
        ],
        "crew_seat_defect_checks": [
            sa.Column("defect_desc_preview", sa.Text(), nullable=True),
            sa.Column("desc_text", sa.Text(), nullable=True),
            sa.Column("loc_text", sa.Text(), nullable=True),
            sa.Column("qty_text", sa.String(length=100), nullable=True),
        ],
    }

    for table_name, columns in table_columns.items():
        if not _table_exists(inspector, table_name):
            continue
        existing = _column_names(inspector, table_name)
        for column in columns:
            if column.name not in existing:
                op.add_column(table_name, column)
        inspector = sa.inspect(bind)


def _backfill_table(table_name, module_kind, select_sql):
    bind = op.get_bind()
    rows = bind.execute(sa.text(select_sql)).mappings().all()
    update_sql = sa.text(
        f"""
        UPDATE {table_name}
        SET defect_desc_preview = :defect_desc_preview,
            desc_text = :desc_text,
            loc_text = :loc_text,
            qty_text = :qty_text
        WHERE id = :id
        """
    )
    for row in rows:
        yes_flag = row.get("yes_flag")
        no_flag = row.get("no_flag")
        has_legacy_detail = any([
            _norm_str(row.get("defect_status")),
            _norm_str(row.get("defect_positions")),
            _norm_str(row.get("position")),
            row.get("defect_quantity") is not None,
            row.get("quantity") is not None,
        ])
        is_defect = yes_flag == 1 or (yes_flag != 1 and no_flag != 1 and has_legacy_detail)
        derived = _build_derived_preview_fields(
            module_kind,
            is_defect=is_defect,
            standardized_desc=row.get("standardized_desc"),
            defect_status=row.get("defect_status"),
            defect_positions=row.get("defect_positions"),
            defect_quantity=row.get("defect_quantity") if row.get("defect_quantity") is not None else row.get("quantity"),
            loc=row.get("loc"),
            position=row.get("position"),
        )
        bind.execute(update_sql, {"id": row["id"], **derived})


def upgrade() -> None:
    _ensure_columns()
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "galley_lav_defect_checks"):
        _backfill_table(
            "galley_lav_defect_checks",
            "single",
            """
            SELECT id, yes_flag, no_flag, standardized_desc, defect_status, defect_positions, defect_quantity, loc,
                   NULL AS position, NULL AS quantity
            FROM galley_lav_defect_checks
            """,
        )

    if _table_exists(inspector, "panel_defect_checks"):
        _backfill_table(
            "panel_defect_checks",
            "batch",
            """
            SELECT id, yes_flag, no_flag, standardized_desc, defect_status, defect_positions, defect_quantity,
                   NULL AS loc, position, quantity
            FROM panel_defect_checks
            """,
        )

    if _table_exists(inspector, "seat_defect_checks"):
        _backfill_table(
            "seat_defect_checks",
            "seat",
            """
            SELECT id, yes_flag, no_flag, standardized_desc, defect_status, defect_positions, defect_quantity, loc,
                   NULL AS position, NULL AS quantity
            FROM seat_defect_checks
            """,
        )

    if _table_exists(inspector, "crew_seat_defect_checks"):
        _backfill_table(
            "crew_seat_defect_checks",
            "crew-seat",
            """
            SELECT id, yes_flag, no_flag, standardized_desc, defect_status, defect_positions, defect_quantity, loc,
                   NULL AS position, NULL AS quantity
            FROM crew_seat_defect_checks
            """,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    targets = [
        "galley_lav_defect_checks",
        "panel_defect_checks",
        "seat_defect_checks",
        "crew_seat_defect_checks",
    ]
    columns = ["qty_text", "loc_text", "desc_text", "defect_desc_preview"]

    for table_name in targets:
        if not _table_exists(inspector, table_name):
            continue
        existing = _column_names(inspector, table_name)
        for column_name in columns:
            if column_name in existing:
                op.drop_column(table_name, column_name)
                existing.remove(column_name)
        inspector = sa.inspect(bind)
