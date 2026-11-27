"""Index the ordered list of reservations for a user."""

from alembic import op

revision = "b5a9f0e916c2"
down_revision = "432b6fca1524"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_reservation_username_id", "reservation", ["username", "id"])


def downgrade() -> None:
    op.drop_index("ix_reservation_username_id", table_name="reservation")
