#!/usr/bin/env python3
"""Validate the bounded single-VPS production runtime envelope."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value is not None and value.strip() else default


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value is not None and value.strip() else default


@dataclass(frozen=True)
class ServiceBudget:
    name: str
    memory_mib: int
    cpus: float
    count: int = 1


def normal_budgets(replicas: int) -> tuple[ServiceBudget, ...]:
    return (
        ServiceBudget("db", env_int("POSTGRES_MEMORY_MIB", 320), env_float("POSTGRES_CPUS", 0.35)),
        ServiceBudget("redis", env_int("REDIS_MEMORY_MIB", 192), env_float("REDIS_CPUS", 0.10)),
        ServiceBudget("agent-service", env_int("AGENT_MEMORY_MIB", 448), env_float("AGENT_CPUS", 0.40)),
        ServiceBudget("backend", env_int("BACKEND_MEMORY_MIB", 704), env_float("BACKEND_CPUS", 0.40), replicas),
        ServiceBudget("body-analysis-worker", env_int("BODY_ANALYSIS_WORKER_MEMORY_MIB", 384), env_float("BODY_ANALYSIS_WORKER_CPUS", 0.35)),
        ServiceBudget("food-photo-worker", env_int("FOOD_PHOTO_WORKER_MEMORY_MIB", 192), env_float("FOOD_PHOTO_WORKER_CPUS", 0.20)),
        ServiceBudget("notification-worker", env_int("NOTIFICATION_WORKER_MEMORY_MIB", 96), env_float("NOTIFICATION_WORKER_CPUS", 0.10)),
        ServiceBudget("scheduler", env_int("SCHEDULER_MEMORY_MIB", 128), env_float("SCHEDULER_CPUS", 0.15)),
        ServiceBudget("frontend", env_int("FRONTEND_MEMORY_MIB", 64), env_float("FRONTEND_CPUS", 0.05)),
        ServiceBudget("caddy", env_int("CADDY_MEMORY_MIB", 64), env_float("CADDY_CPUS", 0.10)),
    )


def monitoring_budgets() -> tuple[ServiceBudget, ...]:
    return (
        ServiceBudget("prometheus", 256, 0.40),
        ServiceBudget("redis-exporter", 64, 0.10),
        ServiceBudget("grafana", 192, 0.25),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicas", type=int, default=2)
    parser.add_argument("--host-memory-mib", type=int, default=env_int("VPS_MEMORY_MIB", 4096))
    parser.add_argument("--host-cpus", type=float, default=env_float("VPS_CPUS", 2.0))
    parser.add_argument("--minimum-headroom-mib", type=int, default=env_int("VPS_MINIMUM_HEADROOM_MIB", 750))
    parser.add_argument("--cpu-oversubscription", type=float, default=env_float("VPS_CPU_OVERSUBSCRIPTION", 1.5))
    parser.add_argument("--include-monitoring", action="store_true")
    args = parser.parse_args()
    if args.replicas < 1 or args.host_memory_mib < 1 or args.host_cpus <= 0:
        parser.error("replicas and host capacity must be positive")

    budgets = normal_budgets(args.replicas)
    if args.include_monitoring:
        budgets += monitoring_budgets()
    memory_total = sum(item.memory_mib * item.count for item in budgets)
    cpu_total = sum(item.cpus * item.count for item in budgets)
    headroom = args.host_memory_mib - memory_total
    memory_ok = headroom >= args.minimum_headroom_mib
    cpu_ok = cpu_total <= args.host_cpus * args.cpu_oversubscription
    topology_ok = args.replicas == 2
    payload = {
        "replicas": args.replicas,
        "host_memory_mib": args.host_memory_mib,
        "host_cpus": args.host_cpus,
        "memory_limit_total_mib": memory_total,
        "memory_headroom_mib": headroom,
        "minimum_headroom_mib": args.minimum_headroom_mib,
        "cpu_limit_total": round(cpu_total, 2),
        "cpu_limit_ceiling": round(args.host_cpus * args.cpu_oversubscription, 2),
        "monitoring_included": args.include_monitoring,
        "services": {
            item.name: {
                "count": item.count,
                "memory_mib_each": item.memory_mib,
                "cpus_each": item.cpus,
            }
            for item in budgets
        },
        "within_budget": memory_ok and cpu_ok and topology_ok,
    }
    print(json.dumps(payload, sort_keys=True))
    if not payload["within_budget"]:
        print(
            "runtime capacity exceeded: require exactly two replicas, memory headroom, and bounded CPU oversubscription",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
