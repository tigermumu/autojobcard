"""rename_single_and_batch_check_tables

Revision ID: f4c9a2b1d8e7
Revises: e3a1c7d9f4b2
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa


revision = "f4c9a2b1d8e7"
down_revision = "e3a1c7d9f4b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "single_defect_checks" in tables and "galley_lav_defect_checks" not in tables:
        op.rename_table("single_defect_checks", "galley_lav_defect_checks")
    elif "single_defect_checks" in tables and "galley_lav_defect_checks" in tables:
        op.execute(sa.text(
            """
            INSERT OR IGNORE INTO galley_lav_defect_checks
            SELECT * FROM single_defect_checks
            """
        ))
        op.drop_table("single_defect_checks")

    tables = set(sa.inspect(bind).get_table_names())
    if "batch_defect_checks" in tables and "panel_defect_checks" not in tables:
        op.rename_table("batch_defect_checks", "panel_defect_checks")
    elif "batch_defect_checks" in tables and "panel_defect_checks" in tables:
        op.execute(sa.text(
            """
            INSERT OR IGNORE INTO panel_defect_checks
            SELECT * FROM batch_defect_checks
            """
        ))
        op.drop_table("batch_defect_checks")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "panel_defect_checks" in tables and "batch_defect_checks" not in tables:
        op.rename_table("panel_defect_checks", "batch_defect_checks")
    elif "panel_defect_checks" in tables and "batch_defect_checks" in tables:
        op.execute(sa.text(
            """
            INSERT OR IGNORE INTO batch_defect_checks
            SELECT * FROM panel_defect_checks
            """
        ))
        op.drop_table("panel_defect_checks")

    tables = set(sa.inspect(bind).get_table_names())
    if "galley_lav_defect_checks" in tables and "single_defect_checks" not in tables:
        op.rename_table("galley_lav_defect_checks", "single_defect_checks")
    elif "galley_lav_defect_checks" in tables and "single_defect_checks" in tables:
        op.execute(sa.text(
            """
            INSERT OR IGNORE INTO single_defect_checks
            SELECT * FROM galley_lav_defect_checks
            """
        ))
        op.drop_table("galley_lav_defect_checks")
