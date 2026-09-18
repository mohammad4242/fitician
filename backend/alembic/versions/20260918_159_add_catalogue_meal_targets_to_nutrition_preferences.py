"""add catalogue meal targets to nutrition preferences"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260918_159"
down_revision: str | Sequence[str] | None = "20260918_158"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "nutrition_food_items",
        sa.Column("catalogue_meal_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_nutrition_food_items_catalogue_meal_id",
        "nutrition_food_items",
        "nutrition_catalogue_meals",
        ["catalogue_meal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_nutrition_food_items_catalogue_meal_id",
        "nutrition_food_items",
        ["catalogue_meal_id"],
    )
    op.drop_constraint(
        "uq_nutrition_food_items_user_kind_name",
        "nutrition_food_items",
        type_="unique",
    )
    op.create_check_constraint(
        "ck_nutrition_food_items_single_catalogue_target",
        "nutrition_food_items",
        "catalogue_food_id IS NULL OR catalogue_meal_id IS NULL",
    )
    # Older rows may have resolved two different aliases to the same food. Keep
    # every historical snapshot row, but leave all except the stable first row
    # unresolved so the new canonical uniqueness rule can be created safely.
    op.execute(
        """
        UPDATE nutrition_food_items AS item
        SET catalogue_food_id = NULL
        WHERE item.catalogue_food_id IS NOT NULL
          AND item.id NOT IN (
              SELECT min(kept.id)
              FROM nutrition_food_items AS kept
              WHERE kept.catalogue_food_id IS NOT NULL
              GROUP BY kept.user_id, kept.kind, kept.catalogue_food_id
          )
        """
    )
    op.create_index(
        "uq_nutrition_food_items_user_kind_food",
        "nutrition_food_items",
        ["user_id", "kind", "catalogue_food_id"],
        unique=True,
        postgresql_where=sa.text("catalogue_food_id IS NOT NULL"),
    )
    op.create_index(
        "uq_nutrition_food_items_user_kind_meal",
        "nutrition_food_items",
        ["user_id", "kind", "catalogue_meal_id"],
        unique=True,
        postgresql_where=sa.text("catalogue_meal_id IS NOT NULL"),
    )
    op.create_index(
        "uq_nutrition_food_items_user_kind_legacy_name",
        "nutrition_food_items",
        ["user_id", "kind", "normalized_name"],
        unique=True,
        postgresql_where=sa.text(
            "catalogue_food_id IS NULL AND catalogue_meal_id IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_nutrition_food_items_user_kind_legacy_name",
        table_name="nutrition_food_items",
    )
    op.drop_index(
        "uq_nutrition_food_items_user_kind_meal",
        table_name="nutrition_food_items",
    )
    op.drop_index(
        "uq_nutrition_food_items_user_kind_food",
        table_name="nutrition_food_items",
    )
    op.drop_constraint(
        "ck_nutrition_food_items_single_catalogue_target",
        "nutrition_food_items",
        type_="check",
    )
    op.create_unique_constraint(
        "uq_nutrition_food_items_user_kind_name",
        "nutrition_food_items",
        ["user_id", "kind", "normalized_name"],
    )
    op.drop_index(
        "ix_nutrition_food_items_catalogue_meal_id",
        table_name="nutrition_food_items",
    )
    op.drop_constraint(
        "fk_nutrition_food_items_catalogue_meal_id",
        "nutrition_food_items",
        type_="foreignkey",
    )
    op.drop_column("nutrition_food_items", "catalogue_meal_id")
