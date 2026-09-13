from app.billing.catalog import PAID_OFFER_CATALOG, offer_definition
from app.billing.enums import BillingOfferCode
from app.entitlements.enums import AccessPackageCode

EXPECTED_CODES = {
    "training_4w",
    "training_6w",
    "training_8w",
    "training_coach_4w",
    "training_coach_6w",
    "training_coach_8w",
    "nutrition_4w",
    "nutrition_6w",
    "nutrition_8w",
    "nutrition_physician_4w",
    "nutrition_physician_6w",
    "nutrition_physician_8w",
    "complete_4w",
    "complete_6w",
    "complete_8w",
    "complete_care_4w",
    "complete_care_6w",
    "complete_care_8w",
}


def test_paid_catalog_contains_exactly_the_eighteen_stable_offers() -> None:
    assert len(PAID_OFFER_CATALOG) == 18
    assert {code.value for code in PAID_OFFER_CATALOG} == EXPECTED_CODES
    assert {definition.code.value for definition in PAID_OFFER_CATALOG.values()} == EXPECTED_CODES


def test_offer_definitions_only_use_four_six_or_eight_weeks() -> None:
    assert {definition.duration_weeks for definition in PAID_OFFER_CATALOG.values()} == {4, 6, 8}
    assert all(
        definition.package_code
        not in {AccessPackageCode.FREE, AccessPackageCode.LAUNCH_TRIAL}
        for definition in PAID_OFFER_CATALOG.values()
    )


def test_offer_lookup_rejects_non_purchasable_package_codes() -> None:
    assert offer_definition(BillingOfferCode.TRAINING_4W).package_code is AccessPackageCode.TRAINING
