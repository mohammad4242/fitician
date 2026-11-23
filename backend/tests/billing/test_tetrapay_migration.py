"""Upgrade/downgrade rehearsal uses only the isolated pytest database."""

from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command


def test_recovery_migration_preserves_historical_fake_transactions(test_settings, monkeypatch):
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[2] / "alembic"))
    config.set_main_option("sqlalchemy.url", test_settings.database_url.replace("%", "%%"))
    # env.py reads Settings; bind it explicitly to this isolated pytest database.
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    engine = create_engine(test_settings.database_url)
    order_id, tx_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO billing_orders
            (id, offer_code, package_code_snapshot, duration_weeks_snapshot, amount_irr_snapshot,
             currency_snapshot, provider, status, idempotency_key)
            VALUES (:id, 'training_4w', 'training', 4, 1000000, 'IRR', 'fake', 'paid', :key)"""),
            {"id": order_id, "key": str(order_id)},
        )
        connection.execute(
            text("""INSERT INTO billing_transactions
            (id, order_id, provider, provider_reference, amount_irr, currency, status)
            VALUES (:id, :order_id, 'fake', :ref, 1000000, 'IRR', 'verified')"""),
            {"id": tx_id, "order_id": order_id, "ref": f"fake-payment:{tx_id}"},
        )
    try:
        with engine.begin() as connection:
            command.downgrade(config, "20261018_175")
            command.upgrade(config, "head")
            row = connection.execute(
                text("""SELECT provider_reference, amount_irr, status,
                    provider_mode, checkout_url, provider_evidence,
                    reconcile_attempts, next_reconcile_at
                    FROM billing_transactions WHERE id = :id"""),
                {"id": tx_id},
            ).one()
            assert tuple(row) == (
                f"fake-payment:{tx_id}",
                1000000,
                "verified",
                None,
                None,
                None,
                0,
                None,
            )
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM billing_orders WHERE id = :id"), {"id": order_id})
        engine.dispose()
