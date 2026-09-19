#!/usr/bin/env python3
"""Provider-neutral local HTTP load smoke with percentile output."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Result:
    status: int | None
    duration_ms: float
    error: str | None = None


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return round(ordered[index], 2)


def request_once(url: str, timeout: float, cookie: str | None) -> Result:
    started = time.perf_counter()
    try:
        headers = {"Accept": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        request = Request(url, headers=headers)
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            response.read(1024)
            status = int(response.status)
        return Result(status, (time.perf_counter() - started) * 1000)
    except HTTPError as error:
        return Result(int(error.code), (time.perf_counter() - started) * 1000, "http_error")
    except (OSError, URLError, TimeoutError) as error:
        return Result(None, (time.perf_counter() - started) * 1000, type(error).__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--path", default=os.environ.get("LOAD_PATH", "/livez"))
    parser.add_argument("--cookie", default=os.environ.get("LOAD_COOKIE"))
    parser.add_argument("--requests", type=int, default=int(os.environ.get("LOAD_REQUESTS", "100")))
    parser.add_argument(
        "--concurrency", type=int, default=int(os.environ.get("LOAD_CONCURRENCY", "10"))
    )
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("LOAD_TIMEOUT", "5")))
    parser.add_argument("--expected-status", type=int, default=200)
    parser.add_argument(
        "--max-error-rate", type=float, default=float(os.environ.get("LOAD_MAX_ERROR_RATE", "0.01"))
    )
    parser.add_argument(
        "--max-p95-ms", type=float, default=float(os.environ.get("LOAD_MAX_P95_MS", "750"))
    )
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.timeout <= 0:
        parser.error("requests, concurrency, and timeout must be positive")

    url = f"{args.base_url.rstrip('/')}/{args.path.lstrip('/')}"
    results: list[Result] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(request_once, url, args.timeout, args.cookie)
            for _ in range(args.requests)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    durations = [result.duration_ms for result in results]
    failures = [result for result in results if result.status != args.expected_status]
    summary = {
        "url": url,
        "requests": len(results),
        "concurrency": args.concurrency,
        "expected_status": args.expected_status,
        "status_counts": dict(sorted(Counter(str(result.status) for result in results).items())),
        "error_rate": round(len(failures) / len(results), 4),
        "p50_ms": percentile(durations, 0.50),
        "p95_ms": percentile(durations, 0.95),
        "p99_ms": percentile(durations, 0.99),
        "mean_ms": round(statistics.fmean(durations), 2) if durations else 0.0,
        "error_types": dict(
            sorted(Counter(result.error for result in failures if result.error).items())
        ),
    }
    print(json.dumps(summary, sort_keys=True))
    return int(
        summary["error_rate"] > args.max_error_rate or summary["p95_ms"] > args.max_p95_ms
    )


if __name__ == "__main__":
    raise SystemExit(main())
