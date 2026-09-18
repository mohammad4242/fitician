#!/usr/bin/env python3
"""Run a stable, complete subset of collected backend pytest node IDs."""

from __future__ import annotations

import argparse
import hashlib
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def partition_nodeids(nodeids: Sequence[str], *, total: int, index: int) -> tuple[str, ...]:
    if total < 1:
        raise ValueError("total must be positive")
    if index < 0 or index >= total:
        raise ValueError("index must be within shard bounds")
    return tuple(nodeid for position, nodeid in enumerate(nodeids) if position % total == index)


def collection_manifest(nodeids: Sequence[str]) -> str:
    normalized = tuple(re.sub(r"\[[^\]]*\]", "[]", nodeid) for nodeid in nodeids)
    digest = hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest()
    return f"{len(normalized)}\n{digest}\n"


def validate_or_write_manifest(path: Path, nodeids: Sequence[str]) -> None:
    expected = collection_manifest(nodeids)
    if path.exists():
        if path.read_text(encoding="utf-8") != expected:
            raise ValueError("pytest collection manifest differs between backend shards")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(expected, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    import pytest

    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        partition_nodeids((), total=args.total, index=args.index)
    except ValueError as error:
        parser.error(str(error))

    class ShardPlugin:
        @staticmethod
        def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
            nodeids = tuple(item.nodeid for item in items)
            if args.manifest is not None:
                try:
                    validate_or_write_manifest(args.manifest, nodeids)
                except ValueError as error:
                    raise pytest.UsageError(str(error)) from error
            selected = [
                item for position, item in enumerate(items) if position % args.total == args.index
            ]
            deselected = [
                item for position, item in enumerate(items) if position % args.total != args.index
            ]
            if not selected:
                raise pytest.UsageError("selected backend test shard is empty")
            items[:] = selected
            config.hook.pytest_deselected(items=deselected)
            print(
                f"backend shard {args.index + 1}/{args.total}: {len(selected)} tests",
                flush=True,
            )

    return int(pytest.main(["-q"], plugins=[ShardPlugin()]))


if __name__ == "__main__":
    raise SystemExit(main())
