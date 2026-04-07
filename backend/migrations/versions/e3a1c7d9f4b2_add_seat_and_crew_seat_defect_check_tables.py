"""add_seat_and_crew_seat_defect_check_tables

Revision ID: e3a1c7d9f4b2
Revises: d9a0b1c2d3e4
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa


revision = "e3a1c7d9f4b2"
down_revision = "d9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "seat_defect_checks" not in existing_tables:
        op.create_table(
            "seat_defect_checks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("seq", sa.Integer(), nullable=True),
            sa.Column("comp_pn", sa.String(length=50), nullable=True),
            sa.Column("standardized_desc", sa.Text(), nullable=True),
            sa.Column("type", sa.String(length=50), nullable=True),
            sa.Column("cust", sa.String(length=50), nullable=True),
            sa.Column("comp_name", sa.String(length=100), nullable=True),
            sa.Column("loc", sa.String(length=200), nullable=True),
            sa.Column("inspector", sa.String(length=50), nullable=True),
            sa.Column("yes_flag", sa.Integer(), nullable=True),
            sa.Column("no_flag", sa.Integer(), nullable=True),
            sa.Column("defect_status", sa.String(length=200), nullable=True),
            sa.Column("defect_positions", sa.Text(), nullable=True),
            sa.Column("defect_quantity", sa.Integer(), nullable=True),
            sa.Column("aircraft_no", sa.String(length=50), nullable=True),
            sa.Column("sale_wo", sa.String(length=100), nullable=True),
            sa.Column("plan_year_month", sa.String(length=20), nullable=True),
            sa.Column("local_photo_url", sa.String(length=500), nullable=True),
            sa.Column("global_photo_url", sa.String(length=500), nullable=True),
            sa.Column("custom_positions_input", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    seat_indexes = {idx["name"] for idx in sa.inspect(bind).get_indexes("seat_defect_checks")} if "seat_defect_checks" in set(sa.inspect(bind).get_table_names()) else set()
    seat_idx_name = op.f("ix_seat_defect_checks_id")
    if seat_idx_name not in seat_indexes:
        op.create_index(seat_idx_name, "seat_defect_checks", ["id"], unique=False)

    if "crew_seat_defect_checks" not in existing_tables:
        op.create_table(
            "crew_seat_defect_checks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("seq", sa.Integer(), nullable=True),
            sa.Column("comp_pn", sa.String(length=50), nullable=True),
            sa.Column("standardized_desc", sa.Text(), nullable=True),
            sa.Column("type", sa.String(length=50), nullable=True),
            sa.Column("cust", sa.String(length=50), nullable=True),
            sa.Column("comp_name", sa.String(length=100), nullable=True),
            sa.Column("loc", sa.String(length=200), nullable=True),
            sa.Column("inspector", sa.String(length=50), nullable=True),
            sa.Column("yes_flag", sa.Integer(), nullable=True),
            sa.Column("no_flag", sa.Integer(), nullable=True),
            sa.Column("defect_status", sa.String(length=200), nullable=True),
            sa.Column("defect_positions", sa.Text(), nullable=True),
            sa.Column("defect_quantity", sa.Integer(), nullable=True),
            sa.Column("aircraft_no", sa.String(length=50), nullable=True),
            sa.Column("sale_wo", sa.String(length=100), nullable=True),
            sa.Column("plan_year_month", sa.String(length=20), nullable=True),
            sa.Column("local_photo_url", sa.String(length=500), nullable=True),
            sa.Column("global_photo_url", sa.String(length=500), nullable=True),
            sa.Column("custom_positions_input", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    crew_indexes = {idx["name"] for idx in sa.inspect(bind).get_indexes("crew_seat_defect_checks")} if "crew_seat_defect_checks" in set(sa.inspect(bind).get_table_names()) else set()
    crew_idx_name = op.f("ix_crew_seat_defect_checks_id")
    if crew_idx_name not in crew_indexes:
        op.create_index(crew_idx_name, "crew_seat_defect_checks", ["id"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "crew_seat_defect_checks" in tables:
        crew_indexes = {idx["name"] for idx in inspector.get_indexes("crew_seat_defect_checks")}
        crew_idx_name = op.f("ix_crew_seat_defect_checks_id")
        if crew_idx_name in crew_indexes:
            op.drop_index(crew_idx_name, table_name="crew_seat_defect_checks")
        op.drop_table("crew_seat_defect_checks")

    if "seat_defect_checks" in tables:
        seat_indexes = {idx["name"] for idx in inspector.get_indexes("seat_defect_checks")}
        seat_idx_name = op.f("ix_seat_defect_checks_id")
        if seat_idx_name in seat_indexes:
            op.drop_index(seat_idx_name, table_name="seat_defect_checks")
        op.drop_table("seat_defect_checks")
