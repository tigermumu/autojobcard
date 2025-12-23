"""make_main_fields_nullable

Revision ID: 008
Revises: 72f0b0869944
Create Date: 2025-12-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '72f0b0869944'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make main_area and main_component nullable in index_data table
    with op.batch_alter_table('index_data', schema=None) as batch_op:
        batch_op.alter_column('main_area',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
        batch_op.alter_column('main_component',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)


def downgrade() -> None:
    # Revert main_area and main_component to not nullable
    with op.batch_alter_table('index_data', schema=None) as batch_op:
        batch_op.alter_column('main_component',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
        batch_op.alter_column('main_area',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)

