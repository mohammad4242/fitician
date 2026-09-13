from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.access_management.models import AccessCampaign


def _load_migration():
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/20260913_145_create_access_management.py"
    )
    spec = spec_from_file_location("access_management_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_access_management_migration_has_expected_revision_and_tables(db: Session) -> None:
    migration = _load_migration()
    assert migration.revision == "20260913_145"
    assert migration.down_revision == "20260913_144"
    assert {
        "access_campaigns",
        "access_campaign_redemptions",
        "admin_audit_events",
    }.issubset(inspect(db.get_bind()).get_table_names())
    campaign = db.scalar(
        select(AccessCampaign).where(AccessCampaign.code == "launch_trial_v1")
    )
    assert campaign is not None
    assert campaign.package_code.value == "launch_trial"
    assert campaign.duration_days == 30
    assert campaign.term_weeks == 4
    assert campaign.is_active is True


def test_access_management_migration_downgrades_and_upgrades_cleanly(db: Session) -> None:
    migration = _load_migration()
    migration.op = Operations(MigrationContext.configure(db.connection()))
    migration.downgrade()
    assert not {
        "access_campaigns",
        "access_campaign_redemptions",
        "admin_audit_events",
    }.intersection(inspect(db.get_bind()).get_table_names())

    migration.op = Operations(MigrationContext.configure(db.connection()))
    migration.upgrade()
    assert {
        "access_campaigns",
        "access_campaign_redemptions",
        "admin_audit_events",
    }.issubset(inspect(db.get_bind()).get_table_names())
