from collections.abc import Iterator
from typing import Annotated, BinaryIO, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.cookies import require_trusted_origin
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import Settings, get_settings
from app.database.session import get_db
from app.exercises.enums import MuscleGroup
from app.nutrition.models import NutritionProfile, NutritionSafetyDecision
from app.profile.enums import ProfileCompletionState
from app.profile.exceptions import (
    AgeNotSupportedError,
    AgeOutOfRangeError,
    InvalidProfilePreferencesError,
    InvalidWorkoutSetupError,
    ProfileAlreadyExistsError,
    ProfileCycleNotFoundError,
    ProfileInvariantError,
    ProfileNotFoundError,
)
from app.profile.models import UserProfile, UserProfilePhoto
from app.profile.photo import (
    ProfilePhotoAccessDeniedError,
    ProfilePhotoNotFoundError,
    ProfilePhotoService,
    ProfilePhotoStorageError,
    ProfilePhotoValidationError,
    profile_photo_url,
)
from app.profile.schemas import (
    ProductModeSelection,
    ProfileCreate,
    ProfilePhotoResponse,
    ProfileResponse,
    ProfileStatusResponse,
    ProfileUpdate,
    SharedProfileResponse,
    SharedProfileUpsert,
    TimezoneResponse,
    TimezoneUpdateRequest,
)
from app.profile.service import (
    ProfileSnapshot,
    create_profile,
    get_profile,
    get_shared_profile,
    profile_completion_state,
    select_product_mode,
    update_profile,
    update_user_timezone,
    upsert_shared_profile,
)
from app.profile.training_compatibility import (
    UnsupportedResistanceTrainingCombinationError,
    resistance_training_day_status,
)
from app.workouts.program_engine.equipment import (
    ordered_available_equipment,
    resolve_available_equipment,
)

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def raise_age_error(error: Exception) -> NoReturn:
    if isinstance(error, AgeNotSupportedError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "AGE_NOT_SUPPORTED",
                "message": "فیتیشن در حال حاضر فقط برای افراد ۱۸ سال و بالاتر ارائه می‌شود.",
            },
        ) from None
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "AGE_OUT_OF_RANGE", "message": "تاریخ تولد واردشده پشتیبانی نمی‌شود."},
    ) from None


def completion_state(db: Session, profile: UserProfile | None) -> ProfileCompletionState:
    if profile is None:
        return profile_completion_state(None)
    nutrition_profile = db.get(NutritionProfile, profile.user_id)
    safety_decision = db.scalar(
        select(NutritionSafetyDecision)
        .where(NutritionSafetyDecision.user_id == profile.user_id)
        .order_by(NutritionSafetyDecision.revision.desc())
        .limit(1)
    )
    return profile_completion_state(profile, nutrition_profile, safety_decision)


@router.post(
    "/mode",
    response_model=ProfileStatusResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def select_mode(
    payload: ProductModeSelection,
    db: DatabaseSession,
    user: CurrentUser,
) -> ProfileStatusResponse:
    profile = select_product_mode(db, user.id, payload.product_mode)
    return ProfileStatusResponse(
        user_id=profile.user_id,
        product_mode=profile.product_mode,
        completion_state=completion_state(db, profile),
    )


@router.get("/status", response_model=ProfileStatusResponse)
def read_status(db: DatabaseSession, user: CurrentUser) -> ProfileStatusResponse:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    return ProfileStatusResponse(
        user_id=user.id,
        product_mode=profile.product_mode if profile is not None else None,
        completion_state=completion_state(db, profile),
    )


@router.put(
    "/timezone",
    response_model=TimezoneResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_timezone(
    payload: TimezoneUpdateRequest,
    db: DatabaseSession,
    user: CurrentUser,
) -> TimezoneResponse:
    try:
        profile = update_user_timezone(db, user.id, payload.timezone)
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND"},
        ) from None
    return TimezoneResponse(timezone=profile.timezone)


def to_response(
    snapshot: ProfileSnapshot,
    photo_url: str | None = None,
) -> ProfileResponse:
    profile = snapshot.profile
    measurement = snapshot.measurement
    assert profile.experience_level is not None
    assert profile.training_days_per_week is not None
    assert profile.training_location is not None
    return ProfileResponse(
        user_id=profile.user_id,
        display_name=profile.display_name,
        birth_date=profile.birth_date,
        sex=profile.sex,
        height_cm=profile.height_cm,
        current_weight_kg=float(measurement.weight_kg),
        weight_measured_at=measurement.measured_at,
        shoulder_circumference_cm=(
            float(measurement.shoulder_circumference_cm)
            if measurement.shoulder_circumference_cm is not None
            else None
        ),
        waist_circumference_cm=(
            float(measurement.waist_circumference_cm)
            if measurement.waist_circumference_cm is not None
            else None
        ),
        hip_circumference_cm=(
            float(measurement.hip_circumference_cm)
            if measurement.hip_circumference_cm is not None
            else None
        ),
        circumferences_measured_at=(
            measurement.measured_at
            if any(
                value is not None
                for value in (
                    measurement.shoulder_circumference_cm,
                    measurement.waist_circumference_cm,
                    measurement.hip_circumference_cm,
                )
            )
            else None
        ),
        fitness_goal=profile.fitness_goal,
        experience_level=profile.experience_level,
        training_age_months=profile.training_age_months,
        training_days_per_week=profile.training_days_per_week,
        training_days_compatibility=resistance_training_day_status(
            profile.experience_level, profile.training_days_per_week
        ),
        preferred_weekdays=(
            tuple(profile.preferred_weekdays) if profile.preferred_weekdays is not None else None
        ),
        priority_muscles=(
            tuple(MuscleGroup(value) for value in profile.priority_muscles)
            if profile.priority_muscles is not None
            else None
        ),
        training_location=profile.training_location,
        home_training_setup=profile.home_training_setup,
        available_equipment=ordered_available_equipment(
            resolve_available_equipment(
                profile.training_location,
                profile.home_training_setup,
                profile.available_equipment,
            )
        ),
        session_duration_minutes=profile.session_duration_minutes,
        training_intensity=profile.training_intensity,
        physical_limitations=profile.physical_limitations,
        training_cautions=sorted(
            (item.caution for item in profile.training_caution_items),
            key=lambda value: value.value,
        ),
        plan_duration_weeks=profile.plan_duration_weeks,
        workout_generation_method=profile.workout_generation_method,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        profile_photo_url=photo_url,
    )


def to_shared_response(
    snapshot: ProfileSnapshot,
    photo_url: str | None = None,
) -> SharedProfileResponse:
    return SharedProfileResponse(
        user_id=snapshot.profile.user_id,
        product_mode=snapshot.profile.product_mode,
        display_name=snapshot.profile.display_name,
        birth_date=snapshot.profile.birth_date,
        sex=snapshot.profile.sex,
        height_cm=snapshot.profile.height_cm,
        current_weight_kg=float(snapshot.measurement.weight_kg),
        weight_measured_at=snapshot.measurement.measured_at,
        fitness_goal=snapshot.profile.fitness_goal,
        profile_photo_url=photo_url,
    )


def _owner_photo_url(db: Session, user_id: UUID) -> str | None:
    photo = db.scalar(select(UserProfilePhoto).where(UserProfilePhoto.user_id == user_id))
    if photo is None:
        return None
    return profile_photo_url(user_id, photo.updated_at, photo.storage_key)


def _photo_response(photo: UserProfilePhoto) -> ProfilePhotoResponse:
    return ProfilePhotoResponse(
        id=photo.id,
        profile_photo_url=profile_photo_url(photo.user_id, photo.updated_at, photo.storage_key),
        mime_type=photo.mime_type,
        byte_size=photo.byte_size,
        width=photo.width,
        height=photo.height,
        updated_at=photo.updated_at,
    )


def _stream_photo(
    row: UserProfilePhoto,
    handle: BinaryIO,
    settings: Settings,
) -> StreamingResponse:
    def stream() -> Iterator[bytes]:
        with handle:
            while chunk := handle.read(settings.profile_photo_read_chunk_bytes):
                yield chunk

    return StreamingResponse(
        stream(),
        media_type=row.mime_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.put(
    "/photo",
    response_model=ProfilePhotoResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def upload_profile_photo(
    db: DatabaseSession,
    user: CurrentUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
) -> ProfilePhotoResponse:
    try:
        photo = ProfilePhotoService(db, settings).save(user.id, file)
    except ProfilePhotoValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": error.code},
        ) from None
    except ProfilePhotoStorageError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE"},
        ) from None
    return _photo_response(photo)


@router.get("/photo")
def read_profile_photo(
    db: DatabaseSession,
    user: CurrentUser,
    settings: AppSettings,
) -> StreamingResponse:
    return _read_profile_photo(db, settings, user.id, user.id)


@router.get("/photo/{owner_id}")
def read_related_profile_photo(
    owner_id: UUID,
    db: DatabaseSession,
    user: CurrentUser,
    settings: AppSettings,
) -> StreamingResponse:
    return _read_profile_photo(db, settings, user.id, owner_id)


def _read_profile_photo(
    db: Session,
    settings: Settings,
    viewer_id: UUID,
    owner_id: UUID,
) -> StreamingResponse:
    try:
        row, handle = ProfilePhotoService(db, settings).open_for(viewer_id, owner_id)
    except ProfilePhotoAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PROFILE_PHOTO_ACCESS_DENIED"},
        ) from None
    except ProfilePhotoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_PHOTO_NOT_FOUND"},
        ) from None
    return _stream_photo(row, handle, settings)


@router.delete(
    "/photo",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trusted_origin)],
)
def delete_profile_photo(
    db: DatabaseSession,
    user: CurrentUser,
    settings: AppSettings,
) -> None:
    try:
        ProfilePhotoService(db, settings).delete(user.id)
    except ProfilePhotoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_PHOTO_NOT_FOUND"},
        ) from None
    except ProfilePhotoStorageError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE"},
        ) from None


@router.put(
    "/shared",
    response_model=SharedProfileResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def save_shared_profile(
    payload: SharedProfileUpsert,
    db: DatabaseSession,
    user: CurrentUser,
) -> SharedProfileResponse:
    try:
        photo_url = _owner_photo_url(db, user.id)
        return to_shared_response(
            upsert_shared_profile(db, user.id, payload),
            photo_url,
        )
    except (AgeNotSupportedError, AgeOutOfRangeError) as error:
        raise_age_error(error)
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PRODUCT_MODE_REQUIRED",
                "message": "ابتدا مسیر فیتیشن را انتخاب کنید.",
            },
        ) from None


@router.get("/shared", response_model=SharedProfileResponse)
def read_shared_profile(db: DatabaseSession, user: CurrentUser) -> SharedProfileResponse:
    try:
        return to_shared_response(get_shared_profile(db, user.id), _owner_photo_url(db, user.id))
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SHARED_PROFILE_NOT_FOUND"},
        ) from None
    except ProfileInvariantError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE"},
        ) from None


@router.post(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create(
    payload: ProfileCreate,
    db: DatabaseSession,
    user: CurrentUser,
) -> ProfileResponse:
    try:
        photo_url = _owner_photo_url(db, user.id)
        return to_response(create_profile(db, user.id, payload), photo_url)
    except (AgeNotSupportedError, AgeOutOfRangeError) as error:
        raise_age_error(error)
    except ProfileAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PROFILE_ALREADY_EXISTS"},
        ) from None
    except UnsupportedResistanceTrainingCombinationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_RESISTANCE_TRAINING_DAYS",
            },
        ) from None
    except ProfileInvariantError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE"},
        ) from None


@router.patch(
    "",
    response_model=ProfileResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update(
    payload: ProfileUpdate,
    db: DatabaseSession,
    user: CurrentUser,
) -> ProfileResponse:
    try:
        photo_url = _owner_photo_url(db, user.id)
        return to_response(update_profile(db, user.id, payload), photo_url)
    except (AgeNotSupportedError, AgeOutOfRangeError) as error:
        raise_age_error(error)
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND"},
        ) from None
    except ProfileCycleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKOUT_CYCLE_NOT_FOUND"},
        ) from None
    except InvalidWorkoutSetupError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "HOME_TRAINING_SETUP_REQUIRED"},
        ) from None
    except InvalidProfilePreferencesError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PREFERRED_WEEKDAYS_INVALID"},
        ) from None
    except UnsupportedResistanceTrainingCombinationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_RESISTANCE_TRAINING_DAYS",
            },
        ) from None
    except ProfileInvariantError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE"},
        ) from None


@router.get("", response_model=ProfileResponse)
def read(db: DatabaseSession, user: CurrentUser) -> ProfileResponse:
    try:
        return to_response(get_profile(db, user.id), _owner_photo_url(db, user.id))
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND"},
        ) from None
    except ProfileInvariantError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE"},
        ) from None
