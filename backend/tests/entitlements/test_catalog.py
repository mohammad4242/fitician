from app.entitlements.catalog import QUOTA_POLICIES, PACKAGE_CATALOG, package_definition
from app.entitlements.enums import (
    AccessPackageCode,
    AccessPackageKind,
    EntitlementCode,
)


def test_catalog_matches_the_product_matrix() -> None:
    assert package_definition(AccessPackageCode.FREE).entitlements == frozenset()
    assert package_definition(AccessPackageCode.TRAINING).entitlements == frozenset(
        {
            EntitlementCode.TRAINING_PLAN_GENERATE,
            EntitlementCode.TRAINING_CYCLE_MANAGE,
            EntitlementCode.BODY_ANALYSIS_RUN,
        }
    )
    assert package_definition(AccessPackageCode.TRAINING_COACH).entitlements == frozenset(
        {
            EntitlementCode.TRAINING_PLAN_GENERATE,
            EntitlementCode.TRAINING_CYCLE_MANAGE,
            EntitlementCode.TRAINING_COACH_REVIEW,
            EntitlementCode.BODY_ANALYSIS_RUN,
        }
    )
    assert package_definition(AccessPackageCode.NUTRITION).entitlements == frozenset(
        {
            EntitlementCode.NUTRITION_PLAN_GENERATE,
            EntitlementCode.NUTRITION_PLAN_MANAGE,
            EntitlementCode.NUTRITION_FOOD_PHOTO_ANALYZE,
            EntitlementCode.BODY_ANALYSIS_RUN,
        }
    )
    assert package_definition(AccessPackageCode.NUTRITION_PHYSICIAN).entitlements == frozenset(
        {
            EntitlementCode.NUTRITION_PLAN_GENERATE,
            EntitlementCode.NUTRITION_PLAN_MANAGE,
            EntitlementCode.NUTRITION_FOOD_PHOTO_ANALYZE,
            EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
            EntitlementCode.NUTRITION_LABS_MANAGE,
            EntitlementCode.NUTRITION_SUPPLEMENTS_MANAGE,
            EntitlementCode.BODY_ANALYSIS_RUN,
        }
    )
    assert package_definition(AccessPackageCode.COMPLETE).entitlements == frozenset(
        package_definition(AccessPackageCode.TRAINING).entitlements
        | package_definition(AccessPackageCode.NUTRITION).entitlements
    )
    assert EntitlementCode.TRAINING_COACH_REVIEW not in package_definition(
        AccessPackageCode.COMPLETE
    ).entitlements
    assert EntitlementCode.NUTRITION_PHYSICIAN_REVIEW not in package_definition(
        AccessPackageCode.COMPLETE
    ).entitlements
    assert package_definition(AccessPackageCode.COMPLETE_CARE).entitlements == frozenset(
        package_definition(AccessPackageCode.TRAINING_COACH).entitlements
        | package_definition(AccessPackageCode.NUTRITION_PHYSICIAN).entitlements
    )
    assert package_definition(AccessPackageCode.LAUNCH_TRIAL).entitlements == package_definition(
        AccessPackageCode.COMPLETE_CARE
    ).entitlements


def test_catalog_has_stable_kinds_and_purchase_flags() -> None:
    assert package_definition(AccessPackageCode.FREE).kind is AccessPackageKind.FREE
    assert not package_definition(AccessPackageCode.FREE).is_purchasable
    assert package_definition(AccessPackageCode.LAUNCH_TRIAL).kind is AccessPackageKind.TRIAL
    assert not package_definition(AccessPackageCode.LAUNCH_TRIAL).is_purchasable
    assert package_definition(AccessPackageCode.TRAINING).kind is AccessPackageKind.SUBSCRIPTION
    assert package_definition(AccessPackageCode.TRAINING).is_purchasable
    assert set(PACKAGE_CATALOG) == set(AccessPackageCode)


def test_catalog_exposes_only_decided_quota_policies() -> None:
    assert set(QUOTA_POLICIES) == {
        EntitlementCode.BODY_ANALYSIS_RUN,
        EntitlementCode.TRAINING_COACH_REVIEW,
        EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
    }
    assert QUOTA_POLICIES[EntitlementCode.BODY_ANALYSIS_RUN].limit == 1
    assert QUOTA_POLICIES[EntitlementCode.BODY_ANALYSIS_RUN].window_days == 7
    assert QUOTA_POLICIES[EntitlementCode.TRAINING_COACH_REVIEW].window_days == 28
    assert QUOTA_POLICIES[EntitlementCode.NUTRITION_PHYSICIAN_REVIEW].window_days == 28


def test_package_definitions_are_immutable() -> None:
    definition = package_definition(AccessPackageCode.TRAINING)
    try:
        definition.code = AccessPackageCode.FREE  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("package definitions must be immutable")
