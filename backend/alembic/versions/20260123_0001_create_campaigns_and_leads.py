"""create campaigns and leads tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260123_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "running",
                "paused",
                "stopped",
                "completed",
                name="campaign_status",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("dial_ratio", sa.Float(), nullable=False, server_default="3.0"),
        sa.Column("caller_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.String(length=36),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "calling",
                "connected",
                "completed",
                "failed",
                "dnc",
                name="lead_status",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("outcome", sa.String(length=100), nullable=True),
        sa.Column("fail_reason", sa.String(length=100), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "call_history", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.UniqueConstraint("campaign_id", "phone_number", name="uq_leads_campaign_phone"),
    )

    op.create_index("ix_leads_campaign_id", "leads", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_campaign_id", table_name="leads")
    op.drop_table("leads")
    op.drop_table("campaigns")
    op.execute("DROP TYPE IF EXISTS lead_status")
    op.execute("DROP TYPE IF EXISTS campaign_status")
