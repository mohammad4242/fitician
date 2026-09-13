from typing import Annotated, cast

from fastapi import Depends, Request

from app.auth.cookies import require_trusted_origin
from app.auth.dependencies import AuthenticatedPrincipal, CurrentAuthentication
from app.billing.enums import PaymentProviderCode
from app.billing.exceptions import BillingProviderUnavailableError
from app.billing.providers.base import PaymentProvider
from app.config import Settings, get_settings

AppSettings = Annotated[Settings, Depends(get_settings)]


def require_billing_write(
    request: Request,
    authentication: CurrentAuthentication,
    settings: AppSettings,
) -> AuthenticatedPrincipal:
    if not authentication.via_bearer:
        require_trusted_origin(request, settings)
    return authentication


BillingWriteAuthentication = Annotated[
    AuthenticatedPrincipal,
    Depends(require_billing_write),
]


def resolve_provider(request: Request, provider: PaymentProviderCode) -> PaymentProvider:
    providers = cast(
        dict[PaymentProviderCode, PaymentProvider],
        getattr(request.app.state, "billing_providers", {}),
    )
    selected = providers.get(provider)
    if selected is None:
        raise BillingProviderUnavailableError(provider.value)
    return selected
