import asyncio
import os
import signal
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


class ProcessTimeoutError(TimeoutError):
    """Raised when a process does not finish within its permitted time."""


class ProcessExecutionError(RuntimeError):
    """Raised when a process cannot be started."""


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


async def run_process(
    command: Sequence[str],
    *,
    workspace: Path,
    timeout_seconds: float,
    input_text: str | None = None,
    env: Mapping[str, str] | None = None,
    inherit_environment: bool = True,
    max_output_bytes: int | None = None,
) -> ProcessResult:
    if not command:
        raise ValueError("command must not be empty")
    if timeout_seconds <= 0:
        raise ValueError("timeout must be positive")

    process_environment: dict[str, str] | None
    if env is None:
        process_environment = None if inherit_environment else {}
    else:
        process_environment = {**os.environ, **env} if inherit_environment else dict(env)
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace,
            start_new_session=True,
            env=process_environment,
        )
    except (OSError, ValueError):
        raise ProcessExecutionError("process could not be started") from None

    input_bytes = None if input_text is None else input_text.encode()
    communication = asyncio.create_task(
        process.communicate(input_bytes)
        if max_output_bytes is None
        else _bounded_communication(process, input_bytes, max_output_bytes)
    )
    try:
        stdout, stderr = await asyncio.wait_for(asyncio.shield(communication), timeout_seconds)
    except TimeoutError as exc:
        await _stop_process_group(process)
        await _reap_communication(communication)
        raise ProcessTimeoutError("process timed out") from exc
    except BaseException:
        await _stop_process_group(process)
        await _reap_communication(communication)
        raise

    return ProcessResult(
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
    )


async def _bounded_communication(
    process: asyncio.subprocess.Process, data: bytes | None, maximum: int
) -> tuple[bytes, bytes]:
    used = 0

    async def read(stream: asyncio.StreamReader | None) -> bytes:
        nonlocal used
        assert stream is not None
        chunks = bytearray()
        while chunk := await stream.read(16384):
            used += len(chunk)
            if used > maximum:
                raise ProcessExecutionError("process output limit exceeded")
            chunks.extend(chunk)
        return bytes(chunks)

    async def write() -> None:
        assert process.stdin is not None
        try:
            if data is not None:
                process.stdin.write(data)
                await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            process.stdin.close()

    writer = asyncio.create_task(write())
    readers = [asyncio.create_task(read(process.stdout)), asyncio.create_task(read(process.stderr))]
    try:
        stdout, stderr = await asyncio.gather(*readers)
        await writer
        await process.wait()
        return stdout, stderr
    finally:
        for task in [writer, *readers]:
            if not task.done():
                task.cancel()
        await asyncio.gather(writer, *readers, return_exceptions=True)


async def _stop_process_group(process: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

    if process.returncode is None:
        try:
            await asyncio.wait_for(asyncio.shield(process.wait()), timeout=0.3)
        except TimeoutError:
            pass
    else:
        await asyncio.sleep(0.05)

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    await process.wait()


async def _reap_communication(communication: asyncio.Task[tuple[bytes, bytes]]) -> None:
    try:
        await asyncio.wait_for(asyncio.shield(communication), timeout=0.5)
    except TimeoutError:
        communication.cancel()
        await asyncio.gather(communication, return_exceptions=True)
