from alembic import op
import sqlalchemy as sa


revision = "b7c3a9d2e4f1"
down_revision = "f2a9c8b7d6e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "global_keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("global_keywords", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_global_keywords_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_global_keywords_keyword"), ["keyword"], unique=False)
        batch_op.create_index(batch_op.f("ix_global_keywords_enabled"), ["enabled"], unique=False)

    op.execute(
        """
        INSERT INTO global_keywords (keyword, enabled, created_at, updated_at)
        SELECT DISTINCT keyword, enabled, created_at, updated_at
        FROM keyword_dict_item
        WHERE dimension = 'global'
        """
    )
    op.execute("DELETE FROM keyword_dict_item WHERE dimension = 'global'")


def downgrade() -> None:
    op.drop_table("global_keywords")
