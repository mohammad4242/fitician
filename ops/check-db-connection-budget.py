#!/usr/bin/env python3
"""Check the configured worst-case PostgreSQL connection budget."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
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
    parser.add_argument("--compose-file")
    parser.add_argument("--env-file")
    args = parser.parse_args()
    values = vars(args)
    if any(value < 0 for value in values.values() if isinstance(value, int)) or args.replicas < 1:
        parser.error("connection counts must be non-negative and replicas must be positive")

    api_connections = args.replicas * (args.backend_pool_size + args.backend_overflow)
    worker_connections = args.workers * (args.worker_pool_size + args.worker_overflow)
    if args.compose_file:
        command = ["docker", "compose"]
        if args.env_file:
            command.extend(("--env-file", args.env_file))
        command.extend(("-f", args.compose_file, "config", "--format", "json"))
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode:
                raise ValueError("Compose render failed")
            services = json.loads(result.stdout)["services"]

            def pool(name: str) -> int:
                environment = services[name]["environment"]
                size = int(environment["DB_POOL_SIZE"])
                overflow = int(environment["DB_MAX_OVERFLOW"])
                if size < 1 or overflow < 0:
                    raise ValueError("Unbounded or invalid database pool")
                return size + overflow

            api_connections = sum(pool(name) for name in ("backend", "backend-2"))
            worker_connections = sum(
                pool(name)
                for name in (
                    "food-photo-worker", "body-analysis-worker", "notification-worker", "scheduler"
                )
            )
            environment = services["backend"]["environment"]
            args.budget = int(environment.get("DB_CONNECTION_BUDGET", args.budget))
            args.headroom = int(environment.get("DB_CONNECTION_HEADROOM", args.headroom))
            if args.budget < 1 or args.headroom < 0:
                raise ValueError("Invalid database budget")
            args.replicas, args.workers = 2, 4
        except (OSError, ValueError, KeyError, TypeError):
            print("Invalid rendered database connection budget", file=sys.stderr)
            return 1
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
