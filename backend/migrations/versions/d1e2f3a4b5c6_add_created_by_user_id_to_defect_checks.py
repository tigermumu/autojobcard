"""add created_by_user_id to defect checks

Revision ID: d1e2f3a4b5c6
Revises: b9f1d2e3c4a5
Create Date: 2026-04-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d1e2f3a4b5c6"
down_revision = "c2d4e6f8a1b3"
branch_labels = None
depends_on = None


TABLES = [
    "galley_lav_defect_checks",
    "panel_defect_checks",
    "seat_defect_checks",
    "crew_seat_defect_checks",
]


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _column_names(inspector, table_name: str):
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str):
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in TABLES:
        if not _table_exists(inspector, table_name):
            continue
        columns = _column_names(inspector, table_name)
        if "created_by_user_id" not in columns:
            op.add_column(table_name, sa.Column("created_by_user_id", sa.Integer(), nullable=True))
            inspector = sa.inspect(bind)
        index_name = f"ix_{table_name}_created_by_user_id"
        indexes = _index_names(inspector, table_name)
        if index_name not in indexes:
            op.create_index(index_name, table_name, ["created_by_user_id"])
            inspector = sa.inspect(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in TABLES:
        if not _table_exists(inspector, table_name):
            continue
        index_name = f"ix_{table_name}_created_by_user_id"
        indexes = _index_names(inspector, table_name)
        if index_name in indexes:
            op.drop_index(index_name, table_name=table_name)
            inspector = sa.inspect(bind)
        columns = _column_names(inspector, table_name)
        if "created_by_user_id" in columns:
            op.drop_column(table_name, "created_by_user_id")
            inspector = sa.inspect(bind)
