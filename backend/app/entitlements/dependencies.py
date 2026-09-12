from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database.session import get_db
from app.entitlements.enums import EntitlementCode
from app.entitlements.service import AccessSnapshot, require_entitlement, resolve_access_snapshot

DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_access_snapshot(db: DatabaseSession, user: CurrentUser) -> AccessSnapshot:
    return resolve_access_snapshot(db, user.id)


CurrentAccessSnapshot = Annotated[AccessSnapshot, Depends(get_current_access_snapshot)]


def entitlement_dependency(entitlement: EntitlementCode | str) -> Callable[..., AccessSnapshot]:
    required = EntitlementCode(entitlement)

    def dependency(db: DatabaseSession, user: CurrentUser) -> AccessSnapshot:
        return require_entitlement(db, user.id, required)

    return dependency
