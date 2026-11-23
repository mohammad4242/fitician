#!/usr/bin/env python3
"""Recheck the approved target under the host deployment lock before mutation."""

import argparse
import importlib.util
import re
import time
from pathlib import Path
from uuid import UUID


def verify(request: dict, packet: dict, *, now: int) -> None:
    try:
        valid = (
            str(UUID(request["operation_id"])) == request["operation_id"]
            and request["target"] in {"iran", "germany"}
            and re.fullmatch("[a-f0-9]{64}", request["baseline"])
            and type(request["expires"]) is int
            and now < request["expires"] <= now + 1800
            and packet["target_environment"] == "production-" + request["target"]
            and packet["complete"] is True
            and packet["baseline_sha256"] == request["baseline"]
        )
    except (ValueError, TypeError, KeyError):
        valid = False
    if not valid:
        raise ValueError("Panel authorization expired, target changed, or observation incomplete")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--operation-id", required=True)
    p.add_argument("--target", choices=("iran", "germany"), required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--expires", type=int, required=True)
    args = p.parse_args()
    spec = importlib.util.spec_from_file_location(
        "fixed_host_collector", Path(__file__).with_name("debug-server-observation.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify(
        {
            "operation_id": args.operation_id,
            "target": args.target,
            "baseline": args.baseline,
            "expires": args.expires,
        },
        module.observe(args.target),
        now=int(time.time()),
    )
    print("Panel artifact/target authorization guard passed; owner gates remain required")


if __name__ == "__main__":
    main()
