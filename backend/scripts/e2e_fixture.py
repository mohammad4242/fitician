"""Create deterministic E2E accounts without exposing a production role endpoint."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

DATABASE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_]+_e2e\Z")


def _database_url() -> str:
    raw_url = os.environ.get("E2E_DATABASE_URL", "").strip()
    if not raw_url:
        raise RuntimeError("E2E_DATABASE_URL is required")
    url = make_url(raw_url)
    database = url.database or ""
    if url.get_backend_name() != "postgresql" or not DATABASE_NAME_PATTERN.fullmatch(database):
        raise RuntimeError("E2E_DATABASE_URL must point to a PostgreSQL database ending in _e2e")
    os.environ["DATABASE_URL"] = raw_url
    return raw_url


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-user")
    prepare.add_argument("--email", required=True)
    prepare.add_argument("--package", default="complete_care")
    prepare.add_argument("--role", choices=("coach", "physician", "doctor"))
    prepare.add_argument("--display-name")
    prepare.add_argument("--admin", action="store_true")
    return parser


def _prepare_user(
    *,
    email: str,
    package: str,
    role_name: str | None,
    display_name: str | None,
    is_admin: bool,
) -> dict[str, Any]:
    # Register every model relationship before querying the database.
    import app.main  # noqa: F401
    from app.auth.models import User
    from app.body_analysis.enums import SpecialistRole
    from app.body_analysis.models import UserSpecialistRole
    from app.database.session import get_engine
    from app.entitlements.enums import AccessPackageCode, GrantSource
    from app.entitlements.service import grant_package
    from app.profile.models import UserProfile

    normalized_email = email.strip().casefold()
    if not normalized_email:
        raise ValueError("email is required")
    database_url = os.environ["DATABASE_URL"]
    with Session(get_engine(database_url)) as db:
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            raise ValueError(f"E2E account is not registered: {normalized_email}")

        if is_admin:
            user.is_admin = True

        role = SpecialistRole(role_name) if role_name is not None else None
        if role is not None:
            existing_role = db.get(UserSpecialistRole, (user.id, role))
            if existing_role is None:
                db.add(UserSpecialistRole(user_id=user.id, role=role))
            if display_name is not None:
                profile = db.get(UserProfile, user.id)
                if profile is None:
                    db.add(UserProfile(user_id=user.id, display_name=display_name))
                else:
                    profile.display_name = display_name

        package_code = AccessPackageCode(package)
        grant_package(
            db,
            user.id,
            package_code,
            source=GrantSource.MANUAL,
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(days=30),
            idempotency_key=f"e2e:{package_code.value}:{user.id}",
            term_weeks=4,
        )
        db.commit()
        return {
            "id": str(user.id),
            "email": user.email,
            "role": role.value if role is not None else None,
            "is_admin": user.is_admin,
        }


def main() -> None:
    args = _parser().parse_args()
    _database_url()
    if args.command != "prepare-user":
        raise RuntimeError(f"Unsupported E2E fixture command: {args.command}")
    result = _prepare_user(
        email=args.email,
        package=args.package,
        role_name=args.role,
        display_name=args.display_name,
        is_admin=args.admin,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
