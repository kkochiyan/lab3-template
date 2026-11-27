"""Track which reservations have already affected loyalty."""

import sqlalchemy as sa
from alembic import op

revision = "8b1e2f093ad7"
down_revision = "47cd4455a499"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loyalty_reservation",
        sa.Column("reservation_uid", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["username"], ["loyalty.username"]),
    )


def downgrade() -> None:
    op.drop_table("loyalty_reservation")
