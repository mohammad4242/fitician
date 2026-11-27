"""Bounded Codex metadata discovery. Never starts an inference turn or a tool."""

import asyncio
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


async def codex_models(
    executable: str, workspace: Path, environment: Mapping[str, str]
) -> tuple[str, ...]:
    process = await asyncio.create_subprocess_exec(
        executable,
        "app-server",
        cwd=workspace,
        env=dict(environment),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        limit=262144,
    )
    writer, reader = process.stdin, process.stdout
    assert writer is not None and reader is not None

    async def send(payload: dict[str, Any]) -> None:
        writer.write(json.dumps(payload).encode() + b"\n")
        await writer.drain()

    async def receive(identifier: int) -> dict[str, Any]:
        for _ in range(20):
            line = await reader.readline()
            if not line:
                raise ValueError("model_catalog_unavailable")
            value = json.loads(line)
            if value.get("id") == identifier:
                result = value.get("result")
                if not isinstance(result, dict):
                    raise ValueError("model_catalog_unavailable")
                return result
        raise ValueError("model_catalog_unavailable")

    try:
        async with asyncio.timeout(8):
            await send(
                {
                    "id": 1,
                    "method": "initialize",
                    "params": {"clientInfo": {"name": "fitician-catalog", "version": "1.0.0"}},
                }
            )
            await receive(1)
            await send({"method": "initialized"})
            await send({"id": 2, "method": "model/list", "params": {"limit": 100}})
            result = await receive(2)
            return tuple(
                dict.fromkeys(
                    m["model"]
                    for m in result.get("data", [])
                    if isinstance(m, dict)
                    and not m.get("hidden", False)
                    and isinstance(m.get("model"), str)
                    and re.fullmatch(r"[A-Za-z0-9._-]{1,150}", m["model"])
                )
            )[:100]
    finally:
        if process.returncode is None:
            process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 2)
        except TimeoutError:
            process.kill()
            await process.wait()
