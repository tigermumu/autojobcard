"""make_subcomponents_nullable

Revision ID: 72f0b0869944
Revises: 007
Create Date: 2025-12-05 09:55:59.423210

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '72f0b0869944'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only modify index_data table to make subcomponents nullable
    # Other changes are skipped as they may cause issues or are not needed
    with op.batch_alter_table('index_data', schema=None) as batch_op:
        batch_op.alter_column('first_level_subcomponent',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
        batch_op.alter_column('second_level_subcomponent',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)


def downgrade() -> None:
    # Revert index_data subcomponents to not nullable
    with op.batch_alter_table('index_data', schema=None) as batch_op:
        batch_op.alter_column('second_level_subcomponent',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
        batch_op.alter_column('first_level_subcomponent',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)