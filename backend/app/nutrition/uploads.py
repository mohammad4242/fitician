from datetime import date
from uuid import UUID

from app.media.uploads import SingleFileUpload


class LabUploadForm(SingleFileUpload):
    test_date: date | None = None
    laboratory_name: str | None = None
    user_note: str | None = None
    category: str | None = None
    request_id: UUID | None = None
