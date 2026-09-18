from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from enum import Enum
from typing import cast
from uuid import UUID

_NAMESPACE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _json_default(value: object) -> object:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return cast(object, model_dump(mode="json"))
    if isinstance(value, (datetime, date, UUID, Enum)):
        return str(value.value if isinstance(value, Enum) else value)
    raise TypeError(f"Unsupported cache key value: {type(value).__name__}")


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        default=_json_default,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _validate_namespace(namespace: str) -> str:
    if not _NAMESPACE_PATTERN.fullmatch(namespace):
        raise ValueError("Invalid cache namespace")
    return namespace


def generation_key(namespace: str) -> str:
    return f"fitician:cache:v1:{_validate_namespace(namespace)}:generation"


def cache_key(namespace: str, identity: object, *, generation: int) -> str:
    _validate_namespace(namespace)
    identity_hash = hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()
    return f"fitician:cache:v1:{namespace}:g{generation}:{identity_hash}"
