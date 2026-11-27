"""Ensure each payment UID identifies one payment."""

from alembic import op

revision = "91ab2e6f43c8"
down_revision = "b3cbeca4f78e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_payment_payment_uid", "payment", ["payment_uid"])


def downgrade() -> None:
    op.drop_constraint("uq_payment_payment_uid", "payment", type_="unique")
