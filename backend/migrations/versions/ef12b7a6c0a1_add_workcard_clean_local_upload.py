"""add workcard_clean_local_upload

Revision ID: ef12b7a6c0a1
Revises: ed180cc8eaa5
Create Date: 2025-12-26

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ef12b7a6c0a1"
down_revision = "ed180cc8eaa5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workcard_clean_local_upload",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("configuration_id", sa.Integer(), nullable=False),
        sa.Column("dict_id", sa.Integer(), nullable=False),
        sa.Column("dict_version", sa.String(length=50), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_cn", sa.Text(), nullable=True),
        sa.Column("workcard_number", sa.String(length=50), nullable=True),
        sa.Column("main_component", sa.String(length=200), nullable=True),
        sa.Column("sub_component", sa.String(length=200), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("orientation", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=200), nullable=True),
        sa.Column("error", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["configuration_id"], ["configurations.id"]),
        sa.ForeignKeyConstraint(["dict_id"], ["keyword_dict.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("workcard_clean_local_upload", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_workcard_clean_local_upload_id"), ["id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_workcard_clean_local_upload_configuration_id"),
            ["configuration_id"],
            unique=False,
        )
        batch_op.create_index(batch_op.f("ix_workcard_clean_local_upload_dict_id"), ["dict_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_workcard_clean_local_upload_workcard_number"),
            ["workcard_number"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_workcard_clean_local_upload_main_component"),
            ["main_component"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_workcard_clean_local_upload_sub_component"),
            ["sub_component"],
            unique=False,
        )
        batch_op.create_index(batch_op.f("ix_workcard_clean_local_upload_location"), ["location"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_workcard_clean_local_upload_orientation"),
            ["orientation"],
            unique=False,
        )
        batch_op.create_index(batch_op.f("ix_workcard_clean_local_upload_status"), ["status"], unique=False)
        batch_op.create_index(
            "idx_workcard_clean_local_upload_cfg_dict",
            ["configuration_id", "dict_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("workcard_clean_local_upload", schema=None) as batch_op:
        batch_op.drop_index("idx_workcard_clean_local_upload_cfg_dict")
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_status"))
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_orientation"))
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_location"))
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_sub_component"))
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_main_component"))
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_workcard_number"))
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_dict_id"))
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_configuration_id"))
        batch_op.drop_index(batch_op.f("ix_workcard_clean_local_upload_id"))

    op.drop_table("workcard_clean_local_upload")








