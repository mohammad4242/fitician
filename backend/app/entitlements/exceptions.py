from collections.abc import Sequence
from datetime import datetime
from math import ceil

from app.entitlements.catalog import eligible_upgrade_packages
from app.entitlements.enums import AccessPackageCode, EntitlementCode


class EntitlementRequiredError(Exception):
    def __init__(
        self,
        entitlement: EntitlementCode | str,
        eligible_packages: Sequence[AccessPackageCode | str] | None = None,
    ) -> None:
        self.entitlement = EntitlementCode(entitlement)
        self.eligible_packages = tuple(
            AccessPackageCode(package)
            for package in (
                eligible_packages
                if eligible_packages is not None
                else eligible_upgrade_packages(self.entitlement)
            )
        )
        super().__init__(f"Entitlement required: {self.entitlement.value}")


class EntitlementQuotaExceededError(Exception):
    def __init__(
        self,
        entitlement: EntitlementCode | str,
        reset_at: datetime,
        retry_after_seconds: int | None = None,
        *,
        now: datetime | None = None,
    ) -> None:
        self.entitlement = EntitlementCode(entitlement)
        self.reset_at = reset_at
        if retry_after_seconds is None:
            reference = now or datetime.now(reset_at.tzinfo)
            retry_after_seconds = max(1, ceil((reset_at - reference).total_seconds()))
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__(f"Entitlement quota exceeded: {self.entitlement.value}")
