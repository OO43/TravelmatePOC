"""Create PostgreSQL passenger profiles."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_passenger_profiles"
down_revision = "0001_journey_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "passenger_profiles",
        sa.Column("passenger_id", sa.String(length=100), primary_key=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("preferred_name", sa.String(length=100), nullable=False),
        sa.Column("phone_number", sa.String(length=50), nullable=False),
        sa.Column("email_address", sa.String(length=320), nullable=False),
        sa.Column("emergency_contact", sa.String(length=255), nullable=False),
        sa.Column("preferred_language", sa.String(length=100), nullable=False),
        sa.Column("home_location", sa.String(length=255), nullable=False),
        sa.Column("communication_method", sa.String(length=20), nullable=False),
        sa.Column("accessibility_needs", postgresql.JSONB(), nullable=False),
        sa.Column("assistance_preferences", postgresql.JSONB(), nullable=False),
        sa.Column("sharing_preference", sa.String(length=20), nullable=False),
        sa.Column("personalised_suggestions", sa.Boolean(), nullable=False),
        sa.Column("enhanced_supervision", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "communication_method IN ('audio', 'visual', 'combined')",
            name="ck_passenger_profiles_communication_method",
        ),
        sa.CheckConstraint(
            "sharing_preference IN ('needed', 'always', 'never')",
            name="ck_passenger_profiles_sharing_preference",
        ),
    )
    op.create_index(
        "idx_passenger_profiles_email_address",
        "passenger_profiles",
        ["email_address"],
    )


def downgrade():
    op.drop_index("idx_passenger_profiles_email_address", table_name="passenger_profiles")
    op.drop_table("passenger_profiles")
