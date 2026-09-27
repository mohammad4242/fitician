import asyncio
from tempfile import SpooledTemporaryFile

import pytest
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette import formparsers
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Message

from app.admin.uploads import ExerciseUploadForm
from app.media.uploads import MULTIPART_OVERHEAD_BYTES, SingleFileUpload, bounded_upload_form
from app.nutrition.uploads import LabUploadForm


def _part(name: str, content: bytes, filename: str | None = None) -> bytes:
    disposition = f'Content-Disposition: form-data; name="{name}"'
    if filename is not None:
        disposition += f'; filename="{filename}"'
    return b"--test\r\n" + disposition.encode() + b"\r\n\r\n" + content + b"\r\n"


def _request(chunks: list[bytes], length: str | None = None) -> Request:
    pending = iter(chunks)
    headers = [(b"content-type", b"multipart/form-data; boundary=test")]
    if length is not None:
        headers.append((b"content-length", length.encode()))

    async def receive() -> Message:
        chunk = next(pending, b"")
        return {"type": "http.request", "body": chunk, "more_body": bool(chunk)}

    return Request({"type": "http", "headers": headers, "app": object()}, receive)


@pytest.mark.parametrize("length", [None, "1"])
def test_stream_limit_cannot_be_bypassed_and_closes_partial_files(
    monkeypatch: pytest.MonkeyPatch, length: str | None
) -> None:
    handles: list[SpooledTemporaryFile[bytes]] = []

    def spool(*, max_size: int) -> SpooledTemporaryFile[bytes]:
        handle = SpooledTemporaryFile[bytes](max_size=max_size)
        handles.append(handle)
        return handle

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", spool)
    first = _part("file", b"small", "test.bin").removesuffix(b"\r\n")
    request = _request([first, b"x" * (1024 + MULTIPART_OVERHEAD_BYTES)], length)

    async def attempt() -> None:
        async with bounded_upload_form(request, SingleFileUpload, max_bytes=1024):
            pytest.fail("Oversized upload reached the handler")

    with pytest.raises(HTTPException) as error:
        asyncio.run(attempt())
    assert error.value.status_code == 413
    assert len(handles) == 1
    assert all(handle.closed for handle in handles)


@pytest.mark.parametrize("length,status", [("-1", 400), ("invalid", 400), ("1000000", 413)])
def test_invalid_declared_length_is_rejected_without_reading(length: str, status: int) -> None:
    request = _request([], length)

    async def attempt() -> None:
        async with bounded_upload_form(request, SingleFileUpload, max_bytes=1024):
            pytest.fail("Invalid content length accepted")

    with pytest.raises(HTTPException) as error:
        asyncio.run(attempt())
    assert error.value.status_code == status
    assert not request._stream_consumed


def test_single_file_upload_rejects_extra_file_parts() -> None:
    body = _part("file", b"one", "one.bin") + _part("unused", b"two", "two.bin")

    async def attempt() -> None:
        async with bounded_upload_form(
            _request([body + b"--test--\r\n"]), SingleFileUpload, max_bytes=1024
        ):
            pytest.fail("Extra file accepted")

    with pytest.raises(StarletteHTTPException) as error:
        asyncio.run(attempt())
    assert error.value.status_code == 400


def test_legitimate_gallery_preserves_fields_and_closes_files() -> None:
    body = (
        _part("payload", b'{"slug":"test"}')
        + _part("media_files", b"one", "one.bin")
        + _part("media_files", b"two", "two.bin")
        + b"--test--\r\n"
    )

    async def attempt() -> None:
        async with bounded_upload_form(
            _request([body[:80], body[80:]]),
            ExerciseUploadForm,
            max_bytes=1024,
            max_files=2,
            max_fields=1,
            list_fields=("media_files",),
        ) as form:
            assert form.payload == '{"slug":"test"}'
            assert form.media is None
            assert form.media_files is not None
            assert [await file.read() for file in form.media_files] == [b"one", b"two"]
        assert all(file.file.closed for file in form.media_files)

    asyncio.run(attempt())


@pytest.mark.parametrize("test_date,valid", [(b"2026-09-01", True), (b"invalid", False)])
def test_lab_metadata_retains_validation(test_date: bytes, valid: bool) -> None:
    body = (
        _part("file", b"document", "test.pdf")
        + _part("test_date", test_date)
        + _part("laboratory_name", b"")
        + b"--test--\r\n"
    )

    async def attempt() -> None:
        async with bounded_upload_form(
            _request([body]), LabUploadForm, max_bytes=1024, max_fields=5
        ) as form:
            assert str(form.test_date) == "2026-09-01"
            assert form.laboratory_name is None
            assert await form.file.read() == b"document"

    if valid:
        asyncio.run(attempt())
    else:
        with pytest.raises(RequestValidationError) as error:
            asyncio.run(attempt())
        assert error.value.errors()[0]["loc"] == ("body", "test_date")
