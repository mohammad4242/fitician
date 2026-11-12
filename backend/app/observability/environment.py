"""Stable diagnostics identity exists even when Sentry is not configured."""

import os
import re


def diagnostics_environment() -> str:
    value = (
        os.environ.get("DIAGNOSTICS_ENVIRONMENT")
        or os.environ.get("SENTRY_ENVIRONMENT")
        or os.environ.get("APP_ENV")
        or "development"
    )
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value):
        raise ValueError("invalid_diagnostics_environment")
    return value
