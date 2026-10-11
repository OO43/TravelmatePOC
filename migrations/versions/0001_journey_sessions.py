"""Create PostgreSQL journey sessions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_journey_sessions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "journey_sessions",
        sa.Column("session_id", sa.String(), primary_key=True),
        sa.Column("passenger_id", sa.String(), nullable=False),
        sa.Column("journey_id", sa.String(), nullable=False),
        sa.Column("vehicle_id", sa.String(), nullable=False),
        sa.Column("declared_ui_options", postgresql.JSONB(), nullable=False),
        sa.Column("support_categories", postgresql.JSONB(), nullable=False),
        sa.Column("consent_to_support_sharing", sa.Boolean(), nullable=False),
        sa.Column("consent_enhanced_supervision", sa.Boolean(), nullable=False),
        sa.Column("stop_request", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'completed')", name="ck_journey_sessions_status"),
    )
    op.create_index("idx_journey_sessions_vehicle_status", "journey_sessions",
                    ["vehicle_id", "status", sa.text("created_at DESC")])


def downgrade():
    op.drop_index("idx_journey_sessions_vehicle_status", table_name="journey_sessions")
    op.drop_table("journey_sessions")
