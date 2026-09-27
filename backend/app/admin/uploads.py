from fastapi import UploadFile
from pydantic import BaseModel


class ExerciseUploadForm(BaseModel):
    payload: str
    media: UploadFile | None = None
    media_male_video: UploadFile | None = None
    media_female_video: UploadFile | None = None
    media_files: list[UploadFile] | None = None


# Same total body allowance as the exercise-gallery ingress rule.
EXERCISE_UPLOAD_MAX_BYTES = 256 * 1024 * 1024
