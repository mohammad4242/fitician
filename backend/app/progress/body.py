from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.profile.models import BodyMeasurement
from app.progress.schemas import BodyPoint, BodySeries, ProgressBodyMeasurements

METRICS = {
    "weight": "weight_kg",
    "waist": "waist_circumference_cm",
    "hip": "hip_circumference_cm",
    "shoulder_width": "shoulder_width_cm",
}


def body_series(
    db: Session, user_id: UUID, start: date, end: date, zone: ZoneInfo
) -> ProgressBodyMeasurements:
    columns: list[Any] = [
        BodyMeasurement.id,
        BodyMeasurement.measured_at,
        BodyMeasurement.observed_fields,
    ]
    for field in METRICS.values():
        metric = getattr(BodyMeasurement, field)
        columns.extend(
            [
                metric,
                func.lag(metric)
                .over(order_by=(BodyMeasurement.measured_at, BodyMeasurement.id))
                .label("previous_" + field),
            ]
        )
    history = select(*columns).where(BodyMeasurement.user_id == user_id).subquery()
    rows = (
        db.execute(
            select(history)
            .where(
                history.c.measured_at >= datetime.combine(start, datetime.min.time(), zone),
                history.c.measured_at
                < datetime.combine(end + timedelta(days=1), datetime.min.time(), zone),
            )
            .order_by(history.c.measured_at, history.c.id)
        )
        .mappings()
        .all()
    )
    series: dict[str, BodySeries] = {}
    for name, field in METRICS.items():
        points = []
        for row in rows:
            value = row[field]
            if value is None:
                continue
            observed = row["observed_fields"]
            if observed is not None:
                if field not in observed:
                    continue
                source = "manual"
            else:
                if value == row["previous_" + field]:
                    continue
                source = "legacy_changed_value"
            points.append(
                BodyPoint(recorded_at=row["measured_at"], value=float(value), source=source)
            )
        series[name] = BodySeries(
            unit="kg" if name == "weight" else "cm",
            points=points,
            start_value=points[0].value if points else None,
            latest_value=points[-1].value if points else None,
            delta=round(points[-1].value - points[0].value, 2) if len(points) > 1 else None,
        )
    return ProgressBodyMeasurements(**series)
