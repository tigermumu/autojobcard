"""fix migration version

Revision ID: 006
Revises: 005
Create Date: 2025-11-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('defect_records', sa.Column('issued_workcard_number', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('defect_records', 'issued_workcard_number')




