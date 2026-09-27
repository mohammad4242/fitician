from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.formparsers import MultiPartException
from starlette.types import Message

MULTIPART_OVERHEAD_BYTES = 64 * 1024


class SingleFileUpload(BaseModel):
    file: UploadFile


def multipart_openapi(model: type[BaseModel]) -> dict[str, Any]:
    return {
        "requestBody": {
            "required": True,
            "content": {"multipart/form-data": {"schema": model.model_json_schema()}},
        },
        "responses": {
            "422": {
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                    }
                },
            }
        },
    }


@asynccontextmanager
async def bounded_upload_form[FormModel: BaseModel](
    request: Request,
    model: type[FormModel],
    *,
    max_bytes: int,
    max_files: int = 1,
    max_fields: int = 0,
    list_fields: tuple[str, ...] = (),
) -> AsyncIterator[FormModel]:
    """Parse only when called by an authorized endpoint; bound actual streamed bytes."""
    limit = max_bytes + MULTIPART_OVERHEAD_BYTES
    declared_size = request.headers.get("content-length")
    if declared_size is not None:
        try:
            length = int(declared_size)
        except ValueError:
            raise HTTPException(400, detail={"code": "BAD_REQUEST"}) from None
        if length < 0:
            raise HTTPException(400, detail={"code": "BAD_REQUEST"})
        if length > limit:
            raise HTTPException(413, detail={"code": "invalid_file_size"})

    stream = request.stream()
    received = 0
    exceeded = False

    async def receive() -> Message:
        nonlocal received, exceeded
        chunk = await anext(stream, b"")
        received += len(chunk)
        if received > limit:
            exceeded = True
            # Starlette closes already-spooled files on MultiPartException.
            raise MultiPartException("Upload request too large")
        return {"type": "http.request", "body": chunk, "more_body": bool(chunk)}

    bounded = Request(request.scope, receive)
    try:
        async with bounded.form(max_files=max_files, max_fields=max_fields) as form:
            values: dict[str, object] = dict(form)
            for name in list_fields:
                if name in form:
                    values[name] = form.getlist(name)
            # Match FastAPI's optional Form/File handling for empty fields.
            for name, field in model.model_fields.items():
                if values.get(name) == "" and not field.is_required():
                    values.pop(name)
            try:
                parsed = model.model_validate(values)
            except ValidationError as error:
                raise RequestValidationError(
                    [{**item, "loc": ("body", *item["loc"])} for item in error.errors()]
                ) from error
            yield parsed
    except StarletteHTTPException:
        if exceeded:
            raise HTTPException(413, detail={"code": "invalid_file_size"}) from None
        raise
