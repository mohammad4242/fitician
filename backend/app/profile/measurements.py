from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.profile.models import BodyMeasurement, UserProfile
from app.user_activity.service import record_activity

METRIC_FIELDS = (
    "weight_kg",
    "waist_circumference_cm",
    "hip_circumference_cm",
    "shoulder_width_cm",
    "shoulder_circumference_cm",
)


class BodyMeasurementInput(BaseModel):
    request_id: UUID
    weight_kg: Decimal | None = Field(default=None, ge=35, le=300, max_digits=5, decimal_places=2)
    waist_circumference_cm: Decimal | None = Field(
        default=None, ge=40, le=250, max_digits=5, decimal_places=2
    )
    hip_circumference_cm: Decimal | None = Field(
        default=None, ge=40, le=250, max_digits=5, decimal_places=2
    )
    shoulder_width_cm: Decimal | None = Field(
        default=None, ge=20, le=80, max_digits=5, decimal_places=2
    )

    @model_validator(mode="after")
    def require_observation(self) -> "BodyMeasurementInput":
        if not any(
            value is not None for key, value in self.model_dump().items() if key != "request_id"
        ):
            raise ValueError("At least one actual measurement is required")
        return self


class BodyMeasurementCreated(BaseModel):
    id: UUID
    recorded_at: datetime
    observed_fields: list[str]


def record_measurement(
    db: Session, user_id: UUID, payload: BodyMeasurementInput
) -> BodyMeasurementCreated:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id).with_for_update())
    if not profile:
        raise HTTPException(409, detail={"code": "PROFILE_REQUIRED"})
    previous = db.scalar(
        select(BodyMeasurement).where(
            BodyMeasurement.user_id == user_id,
            BodyMeasurement.observation_request_id == payload.request_id,
        )
    )
    values = payload.model_dump(exclude_none=True, exclude={"request_id"})
    if previous:
        if sorted(values) != previous.observed_fields or any(
            value != getattr(previous, field) for field, value in values.items()
        ):
            raise HTTPException(409, detail={"code": "MEASUREMENT_REQUEST_CONFLICT"})
        return BodyMeasurementCreated(
            id=previous.id,
            recorded_at=previous.measured_at,
            observed_fields=previous.observed_fields or [],
        )
    latest = db.scalar(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user_id)
        .order_by(BodyMeasurement.measured_at.desc(), BodyMeasurement.id.desc())
        .limit(1)
    )
    if not latest and "weight_kg" not in values:
        raise HTTPException(422, detail={"code": "INITIAL_WEIGHT_REQUIRED"})
    observed = sorted(values)
    snapshot = {field: values.get(field, getattr(latest, field, None)) for field in METRIC_FIELDS}
    row = BodyMeasurement(
        user_id=user_id,
        observation_request_id=payload.request_id,
        measured_at=datetime.now(UTC),
        observed_fields=observed,
        **snapshot,
    )
    db.add(row)
    db.flush()
    record_activity(
        db,
        user_id,
        "body.measurement_recorded",
        resource_type="body_measurement",
        resource_id=str(row.id),
        metadata={"weight_kg": float(row.weight_kg)}
        if "weight_kg" in observed and row.weight_kg is not None
        else {},
        occurred_at=row.measured_at,
        deduplication_key=f"body-measurement:{row.id}",
    )
    db.commit()
    db.refresh(row)
    return BodyMeasurementCreated(id=row.id, recorded_at=row.measured_at, observed_fields=observed)
