from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.models import AccessCampaign, AccessCampaignRedemption
from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.service import grant_package


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


def _load_semantic_migration():
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/20260913_148_harden_access_campaign_package_semantics.py"
    )
    spec = spec_from_file_location("access_campaign_semantic_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _load_generalization_migration():
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/20260920_160_generalize_signup_campaigns.py"
    )
    spec = spec_from_file_location("signup_campaign_generalization_migration", path)
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
    assert campaign.kind is AccessCampaignKind.SIGNUP_BONUS
    assert campaign.is_active is False
    check_names = {
        check["name"]
        for check in inspect(db.get_bind()).get_check_constraints("access_campaigns")
    }
    assert {
        "ck_access_campaigns_kind_values",
        "ck_access_campaigns_training_term",
    } <= check_names


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


def test_campaign_semantic_migration_round_trips_constraints(db: Session) -> None:
    migration = _load_semantic_migration()
    generalization = _load_generalization_migration()
    assert migration.revision == "20260913_148"
    assert migration.down_revision == "20260913_146"

    generalization.op = Operations(MigrationContext.configure(db.connection()))
    generalization.downgrade()
    migration.op = Operations(MigrationContext.configure(db.connection()))
    migration.downgrade()
    check_names = {
        check["name"]
        for check in inspect(db.get_bind()).get_check_constraints("access_campaigns")
    }
    assert "ck_access_campaigns_signup_trial_package" not in check_names
    assert "ck_access_campaigns_manual_promotion_package" not in check_names

    migration.op = Operations(MigrationContext.configure(db.connection()))
    migration.upgrade()
    check_names = {
        check["name"]
        for check in inspect(db.get_bind()).get_check_constraints("access_campaigns")
    }
    assert {
        "ck_access_campaigns_signup_trial_package",
        "ck_access_campaigns_manual_promotion_package",
    } <= check_names

    generalization.op = Operations(MigrationContext.configure(db.connection()))
    generalization.upgrade()


def test_generalization_migration_preserves_history_and_round_trips_generic_campaign(
    db: Session,
) -> None:
    migration = _load_generalization_migration()
    assert migration.revision == "20260920_160"
    assert migration.down_revision == "20260918_159"

    owner = User(email="migration-campaign-owner@example.com", password_hash="hash")
    member = User(email="migration-campaign-member@example.com", password_hash="hash")
    db.add_all([owner, member])
    db.flush()
    campaign = AccessCampaign(
        code="migration-generic-bonus",
        name="Migration generic bonus",
        kind=AccessCampaignKind.SIGNUP_BONUS,
        package_code=AccessPackageCode.COMPLETE,
        duration_days=42,
        term_weeks=6,
        is_active=True,
        public_title_fa="عنوان فارسی",
        public_title_en="English title",
        public_message_fa="پیام فارسی",
        public_message_en="English message",
        public_cta_fa="شروع",
        public_cta_en="Start",
        show_on_landing=True,
        show_on_register=True,
        created_by_user_id=owner.id,
    )
    db.add(campaign)
    db.flush()
    grant = grant_package(
        db,
        member.id,
        AccessPackageCode.COMPLETE,
        source=GrantSource.PROMOTION,
        starts_at=campaign.created_at,
        ends_at=campaign.created_at,
        term_weeks=6,
        idempotency_key="migration-generic-bonus:v1",
    )
    db.add(
        AccessCampaignRedemption(
            campaign_id=campaign.id,
            user_id=member.id,
            access_grant_id=grant.id,
            package_code_snapshot=AccessPackageCode.COMPLETE,
            duration_days_snapshot=42,
            term_weeks_snapshot=6,
        )
    )
    db.flush()

    migration.op = Operations(MigrationContext.configure(db.connection()))
    migration.downgrade()
    legacy_state = db.execute(
        text(
            "SELECT kind, is_active FROM access_campaigns "
            "WHERE code = 'migration-generic-bonus'"
        )
    ).one()
    assert legacy_state == ("manual_promotion", False)
    assert db.scalar(
        text("SELECT count(*) FROM access_campaign_redemptions WHERE campaign_id = :id"),
        {"id": campaign.id},
    ) == 1
    assert db.scalar(
        text("SELECT count(*) FROM user_access_grants WHERE id = :id"),
        {"id": grant.id},
    ) == 1

    migration.op = Operations(MigrationContext.configure(db.connection()))
    migration.upgrade()
    columns = {column["name"] for column in inspect(db.get_bind()).get_columns("access_campaigns")}
    assert {
        "public_badge_fa",
        "public_badge_en",
        "public_title_fa",
        "public_title_en",
        "public_message_fa",
        "public_message_en",
        "public_cta_fa",
        "public_cta_en",
        "show_on_landing",
        "show_on_register",
    } <= columns
    launch_state = db.execute(
        text("SELECT kind, is_active FROM access_campaigns WHERE code = 'launch_trial_v1'")
    ).one()
    assert launch_state == ("signup_bonus", False)
    db.execute(
        text(
            "UPDATE access_campaigns SET public_title_fa = :title_fa, "
            "public_title_en = :title_en WHERE code = 'migration-generic-bonus'"
        ),
        {"title_fa": "عنوان تازه", "title_en": "Fresh title"},
    )
    public_state = db.execute(
        text(
            "SELECT public_title_fa, public_title_en FROM access_campaigns "
            "WHERE code = 'migration-generic-bonus'"
        )
    ).one()
    assert public_state == ("عنوان تازه", "Fresh title")
