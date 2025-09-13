"""
initial schema

Revision ID: 0001_init
Revises:
Create Date: 2025-09-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    plan_algorithm = sa.Enum(
        "token_bucket",
        "fixed_window",
        "sliding_window",
        "concurrency",
        name="plan_algorithm",
    )
    subject_type = sa.Enum("api_key", "ip", "user_id", name="subject_type")

    # Tenants
    op.create_table(
        "tenants",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Plans
    op.create_table(
        "plans",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("algorithm", plan_algorithm, nullable=False),
        sa.Column("limit_per_window", sa.Integer(), nullable=True),
        sa.Column("window_seconds", sa.Integer(), nullable=True),
        sa.Column("bucket_capacity", sa.Integer(), nullable=True),
        sa.Column("refill_rate_per_sec", sa.Float(), nullable=True),
        sa.Column("concurrency_limit", sa.Integer(), nullable=True),
        sa.Column("cost_per_call", sa.Integer(), server_default="1", nullable=False),
        sa.Column("burst_factor", sa.Float(), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Api keys
    op.create_table(
        "api_keys",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    # Resource policies
    op.create_table(
        "resource_policies",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource", sa.String(length=300), nullable=False),
        sa.Column("subject_type", subject_type, nullable=False),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("resource_policies")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_table("plans")
    op.drop_table("tenants")
    op.execute("DROP TYPE IF EXISTS plan_algorithm")
    op.execute("DROP TYPE IF EXISTS subject_type")
