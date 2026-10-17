"""Hashed, optional request keys scoped to existing successful generation records."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from re import fullmatch
from typing import Annotated
from uuid import UUID

from fastapi import Header, HTTPException

GenerationRequestKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"),
]

_request: ContextVar[tuple[str | None, UUID | None]] = ContextVar(
    "generation_request", default=(None, None)
)


def key_hash(value: str | None) -> str | None:
    if value is None:
        return None
    if not fullmatch(r"[A-Za-z0-9_-]{16,128}", value):
        raise HTTPException(422, detail={"code": "INVALID_IDEMPOTENCY_KEY"})
    return sha256(value.encode()).hexdigest()


@contextmanager
def generation_request(value: str | None, existing: UUID | None) -> Iterator[None]:
    token = _request.set((value, existing))
    try:
        yield
    finally:
        _request.reset(token)


def current_key_hash() -> str | None:
    return _request.get()[0]


def require_compatible_outcome(resource_id: UUID | None) -> None:
    existing = _request.get()[1]
    if existing is not None and existing != resource_id:
        raise HTTPException(409, detail={"code": "GENERATION_REQUEST_OUTCOME_INELIGIBLE"})
