from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import HTTPException, Request, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.types import Message

# Allow multipart headers while keeping the entire request bounded.
MULTIPART_OVERHEAD_BYTES = 64 * 1024


@asynccontextmanager
async def bounded_photo_upload(request: Request, max_bytes: int) -> AsyncIterator[UploadFile]:
    limit = max_bytes + MULTIPART_OVERHEAD_BYTES
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            raise HTTPException(400, detail={"code": "BAD_REQUEST"}) from None
        if declared_size < 0:
            raise HTTPException(400, detail={"code": "BAD_REQUEST"})
        if declared_size > limit:
            raise HTTPException(413, detail={"code": "invalid_file_size"})

    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > limit:
            raise HTTPException(413, detail={"code": "invalid_file_size"})
        content.extend(chunk)

    async def receive() -> Message:
        return {"type": "http.request", "body": bytes(content), "more_body": False}

    # Parse only after authentication and the complete streamed size check.
    bounded_request = Request(request.scope, receive)
    async with bounded_request.form(max_files=1, max_fields=0) as form:
        file = form.get("file")
        if not isinstance(file, StarletteUploadFile):
            raise HTTPException(422, detail={"code": "VALIDATION_ERROR"})
        yield cast(UploadFile, file)
