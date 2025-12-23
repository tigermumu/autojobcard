"""merge branches

Revision ID: c345e357ec5e
Revises: 009, 94d9bd9159fc
Create Date: 2025-12-17 15:36:17.923304

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c345e357ec5e'
down_revision = ('009', '94d9bd9159fc')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass