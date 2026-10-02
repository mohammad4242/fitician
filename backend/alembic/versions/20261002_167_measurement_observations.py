"""Canonical shoulder width and explicit observation provenance."""

import sqlalchemy as sa

from alembic import op

revision = "20261002_167"
down_revision = "20261002_166"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "body_measurements", sa.Column("observation_request_id", sa.Uuid(), nullable=True)
    )
    op.create_unique_constraint(
        "uq_body_measurement_request", "body_measurements", ["user_id", "observation_request_id"]
    )
    op.add_column(
        "body_measurements", sa.Column("shoulder_width_cm", sa.Numeric(5, 2), nullable=True)
    )
    op.add_column("body_measurements", sa.Column("observed_fields", sa.JSON(), nullable=True))
    op.create_check_constraint(
        "ck_body_measurements_shoulder_width_range",
        "body_measurements",
        "shoulder_width_cm IS NULL OR shoulder_width_cm BETWEEN 20 AND 80",
    )
    # Legacy rows stay unclassified; copied values are never labelled fresh observations.


def downgrade() -> None:
    op.drop_constraint("uq_body_measurement_request", "body_measurements", type_="unique")
    op.drop_column("body_measurements", "observation_request_id")
    op.drop_constraint(
        "ck_body_measurements_shoulder_width_range", "body_measurements", type_="check"
    )
    op.drop_column("body_measurements", "observed_fields")
    op.drop_column("body_measurements", "shoulder_width_cm")
