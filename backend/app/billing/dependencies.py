from typing import Annotated

from fastapi import Depends, Request

from app.auth.cookies import require_trusted_origin
from app.auth.dependencies import AuthenticatedPrincipal, CurrentAuthentication
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
