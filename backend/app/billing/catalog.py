from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from app.billing.enums import BillingOfferCode
from app.entitlements.enums import AccessPackageCode


@dataclass(frozen=True, slots=True)
class BillingOfferDefinition:
    code: BillingOfferCode
    package_code: AccessPackageCode
    duration_weeks: int


def _offer(
    code: BillingOfferCode,
    package_code: AccessPackageCode,
    duration_weeks: int,
) -> tuple[BillingOfferCode, BillingOfferDefinition]:
    return code, BillingOfferDefinition(
        code=code,
        package_code=package_code,
        duration_weeks=duration_weeks,
    )


PAID_OFFER_CATALOG: Final = MappingProxyType(
    dict(
        (
            _offer(BillingOfferCode.TRAINING_4W, AccessPackageCode.TRAINING, 4),
            _offer(BillingOfferCode.TRAINING_6W, AccessPackageCode.TRAINING, 6),
            _offer(BillingOfferCode.TRAINING_8W, AccessPackageCode.TRAINING, 8),
            _offer(BillingOfferCode.TRAINING_COACH_4W, AccessPackageCode.TRAINING_COACH, 4),
            _offer(BillingOfferCode.TRAINING_COACH_6W, AccessPackageCode.TRAINING_COACH, 6),
            _offer(BillingOfferCode.TRAINING_COACH_8W, AccessPackageCode.TRAINING_COACH, 8),
            _offer(BillingOfferCode.NUTRITION_4W, AccessPackageCode.NUTRITION, 4),
            _offer(BillingOfferCode.NUTRITION_6W, AccessPackageCode.NUTRITION, 6),
            _offer(BillingOfferCode.NUTRITION_8W, AccessPackageCode.NUTRITION, 8),
            _offer(
                BillingOfferCode.NUTRITION_PHYSICIAN_4W,
                AccessPackageCode.NUTRITION_PHYSICIAN,
                4,
            ),
            _offer(
                BillingOfferCode.NUTRITION_PHYSICIAN_6W,
                AccessPackageCode.NUTRITION_PHYSICIAN,
                6,
            ),
            _offer(
                BillingOfferCode.NUTRITION_PHYSICIAN_8W,
                AccessPackageCode.NUTRITION_PHYSICIAN,
                8,
            ),
            _offer(BillingOfferCode.COMPLETE_4W, AccessPackageCode.COMPLETE, 4),
            _offer(BillingOfferCode.COMPLETE_6W, AccessPackageCode.COMPLETE, 6),
            _offer(BillingOfferCode.COMPLETE_8W, AccessPackageCode.COMPLETE, 8),
            _offer(BillingOfferCode.COMPLETE_CARE_4W, AccessPackageCode.COMPLETE_CARE, 4),
            _offer(BillingOfferCode.COMPLETE_CARE_6W, AccessPackageCode.COMPLETE_CARE, 6),
            _offer(BillingOfferCode.COMPLETE_CARE_8W, AccessPackageCode.COMPLETE_CARE, 8),
        )
    )
)

BILLING_OFFER_CATALOG = PAID_OFFER_CATALOG


def offer_definition(code: BillingOfferCode | str) -> BillingOfferDefinition:
    return PAID_OFFER_CATALOG[BillingOfferCode(code)]
