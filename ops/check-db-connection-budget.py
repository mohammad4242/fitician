#!/usr/bin/env python3
"""Check the configured worst-case PostgreSQL connection budget."""

from __future__ import annotations

import argparse
import json
import os
import sys


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value is not None and value.strip() else default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicas", type=int, default=2)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--backend-pool-size", type=int, default=env_int("DB_POOL_SIZE", 5))
    parser.add_argument(
        "--backend-overflow", type=int, default=env_int("DB_MAX_OVERFLOW", 5)
    )
    parser.add_argument(
        "--worker-pool-size", type=int, default=env_int("WORKER_DB_POOL_SIZE", 2)
    )
    parser.add_argument(
        "--worker-overflow", type=int, default=env_int("WORKER_DB_MAX_OVERFLOW", 1)
    )
    parser.add_argument("--budget", type=int, default=env_int("DB_CONNECTION_BUDGET", 40))
    parser.add_argument("--headroom", type=int, default=env_int("DB_CONNECTION_HEADROOM", 4))
    args = parser.parse_args()
    values = vars(args)
    if any(value < 0 for value in values.values()) or args.replicas < 1:
        parser.error("connection counts must be non-negative and replicas must be positive")

    api_connections = args.replicas * (args.backend_pool_size + args.backend_overflow)
    worker_connections = args.workers * (args.worker_pool_size + args.worker_overflow)
    possible = api_connections + worker_connections
    payload = {
        "replicas": args.replicas,
        "workers": args.workers,
        "api_connections": api_connections,
        "worker_connections": worker_connections,
        "possible_connections": possible,
        "headroom": args.headroom,
        "budget": args.budget,
        "within_budget": possible + args.headroom < args.budget,
    }
    print(json.dumps(payload, sort_keys=True))
    if not payload["within_budget"]:
        print(
            "connection budget exceeded: possible connections plus headroom must stay below budget",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
