"""create import batch tables

Revision ID: 005
Revises: 004
Create Date: 2025-11-10 16:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'import_batches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('defect_list_id', sa.Integer(), nullable=True),
        sa.Column('aircraft_number', sa.String(length=50), nullable=False),
        sa.Column('workcard_number', sa.String(length=100), nullable=False),
        sa.Column('maintenance_level', sa.String(length=100), nullable=False),
        sa.Column('aircraft_type', sa.String(length=100), nullable=False),
        sa.Column('customer', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['defect_list_id'], ['defect_lists.id'], ondelete="SET NULL")
    )
    op.create_index('ix_import_batches_id', 'import_batches', ['id'], unique=False)

    op.create_table(
        'import_batch_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('defect_record_id', sa.Integer(), nullable=True),
        sa.Column('defect_number', sa.String(length=100), nullable=False),
        sa.Column('description_cn', sa.Text(), nullable=True),
        sa.Column('description_en', sa.Text(), nullable=True),
        sa.Column('workcard_number', sa.String(length=100), nullable=False),
        sa.Column('selected_workcard_id', sa.Integer(), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batches.id'], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(['defect_record_id'], ['defect_records.id'], ondelete="SET NULL")
    )
    op.create_index('ix_import_batch_items_id', 'import_batch_items', ['id'], unique=False)
    op.create_index('ix_import_batch_items_batch_id', 'import_batch_items', ['batch_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_import_batch_items_batch_id', table_name='import_batch_items')
    op.drop_index('ix_import_batch_items_id', table_name='import_batch_items')
    op.drop_table('import_batch_items')
    op.drop_index('ix_import_batches_id', table_name='import_batches')
    op.drop_table('import_batches')


