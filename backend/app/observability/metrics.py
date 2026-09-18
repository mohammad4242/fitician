from __future__ import annotations

import re
from collections import defaultdict
from threading import Lock

_UUID_SEGMENT = re.compile(r"^[0-9a-fA-F-]{16,}$")


class MetricsRegistry:
    """A bounded in-process Prometheus text registry.

    Labels are limited to HTTP method, normalized route, and status code so
    user IDs, tokens, and request payloads can never become metric labels.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._http_count: defaultdict[tuple[str, str, int], int] = defaultdict(int)
        self._http_duration: defaultdict[tuple[str, str, int], float] = defaultdict(float)
        self._in_flight = 0
        self._gauges: dict[str, float] = {}
        self._cache_hits: defaultdict[str, int] = defaultdict(int)
        self._cache_misses: defaultdict[str, int] = defaultdict(int)
        self._cache_unavailable: defaultdict[str, int] = defaultdict(int)
        self._rate_limit_allowed: defaultdict[tuple[str, str], int] = defaultdict(int)
        self._rate_limit_blocked: defaultdict[tuple[str, str], int] = defaultdict(int)
        self._rate_limit_unavailable: defaultdict[tuple[str, str], int] = defaultdict(int)
        self._labeled_gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

    def begin_request(self) -> None:
        with self._lock:
            self._in_flight += 1

    def observe_http(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        route = normalize_route(path)
        key = (method.upper(), route, status_code)
        with self._lock:
            self._http_count[key] += 1
            self._http_duration[key] += max(0.0, duration_seconds)
            self._in_flight = max(0, self._in_flight - 1)

    def finish_failed_request(
        self,
        *,
        method: str,
        path: str,
        duration_seconds: float,
    ) -> None:
        self.observe_http(
            method=method,
            path=path,
            status_code=500,
            duration_seconds=duration_seconds,
        )

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def set_labeled_gauge(self, name: str, labels: dict[str, str], value: float) -> None:
        safe_labels = tuple(
            sorted((key[:32], _safe_label(value)) for key, value in labels.items())
        )
        with self._lock:
            self._labeled_gauges[(name, safe_labels)] = value

    def record_cache(self, *, namespace: str, hit: bool, redis_available: bool) -> None:
        safe_namespace = _safe_label(namespace)
        with self._lock:
            if hit:
                self._cache_hits[safe_namespace] += 1
            else:
                self._cache_misses[safe_namespace] += 1
            if not redis_available:
                self._cache_unavailable[safe_namespace] += 1

    def record_rate_limit(
        self,
        *,
        namespace: str,
        operation: str,
        allowed: bool = False,
        available: bool = True,
    ) -> None:
        key = (_safe_label(namespace), _safe_label(operation))
        with self._lock:
            if available:
                target = self._rate_limit_allowed if allowed else self._rate_limit_blocked
                target[key] += 1
            else:
                self._rate_limit_unavailable[key] += 1

    def render(self) -> str:
        with self._lock:
            counts = dict(self._http_count)
            durations = dict(self._http_duration)
            in_flight = self._in_flight
            gauges = dict(self._gauges)
            cache_hits = dict(self._cache_hits)
            cache_misses = dict(self._cache_misses)
            cache_unavailable = dict(self._cache_unavailable)
            rate_limit_allowed = dict(self._rate_limit_allowed)
            rate_limit_blocked = dict(self._rate_limit_blocked)
            rate_limit_unavailable = dict(self._rate_limit_unavailable)
            labeled_gauges = dict(self._labeled_gauges)
        lines = [
            "# TYPE fitician_http_requests_total counter",
            "# TYPE fitician_http_request_duration_seconds counter",
            "# TYPE fitician_http_requests_in_flight gauge",
        ]
        for (method, route, status), count in sorted(counts.items()):
            labels = _labels(method=method, route=route, status=str(status))
            lines.append(f"fitician_http_requests_total{{{labels}}} {count}")
            duration = durations[(method, route, status)]
            lines.append(
                f"fitician_http_request_duration_seconds{{{labels}}} {duration:.6f}"
            )
        lines.append(f"fitician_http_requests_in_flight {in_flight}")
        lines.extend(
            [
                "# TYPE fitician_cache_hits_total counter",
                "# TYPE fitician_cache_misses_total counter",
                "# TYPE fitician_cache_redis_unavailable_total counter",
                "# TYPE fitician_rate_limit_allowed_total counter",
                "# TYPE fitician_rate_limit_blocked_total counter",
                "# TYPE fitician_rate_limit_redis_unavailable_total counter",
            ]
        )
        for namespace, count in sorted(cache_hits.items()):
            label = _labels(namespace=namespace)
            lines.append(f"fitician_cache_hits_total{{{label}}} {count}")
        for namespace, count in sorted(cache_misses.items()):
            label = _labels(namespace=namespace)
            lines.append(f"fitician_cache_misses_total{{{label}}} {count}")
        for namespace, count in sorted(cache_unavailable.items()):
            label = _labels(namespace=namespace)
            lines.append(f"fitician_cache_redis_unavailable_total{{{label}}} {count}")
        for (namespace, operation), count in sorted(rate_limit_allowed.items()):
            label = _labels(namespace=namespace, operation=operation)
            lines.append(f"fitician_rate_limit_allowed_total{{{label}}} {count}")
        for (namespace, operation), count in sorted(rate_limit_blocked.items()):
            label = _labels(namespace=namespace, operation=operation)
            lines.append(f"fitician_rate_limit_blocked_total{{{label}}} {count}")
        for (namespace, operation), count in sorted(rate_limit_unavailable.items()):
            label = _labels(namespace=namespace, operation=operation)
            lines.append(f"fitician_rate_limit_redis_unavailable_total{{{label}}} {count}")
        for metric_key, value in sorted(labeled_gauges.items()):
            metric_name: str = metric_key[0]
            metric_labels: tuple[tuple[str, str], ...] = metric_key[1]
            rendered_labels = _labels(**dict(metric_labels))
            lines.append(f"{metric_name}{{{rendered_labels}}} {value:g}")
        for name, value in sorted(gauges.items()):
            lines.append(f"{name} {value:g}")
        return "\n".join(lines) + "\n"


def normalize_route(path: str) -> str:
    segments = []
    for segment in path.split("/"):
        if not segment:
            continue
        if _UUID_SEGMENT.fullmatch(segment) or segment.isdigit():
            segments.append(":id")
        else:
            segments.append(segment[:80])
    return "/" + "/".join(segments) if segments else "/"


def _labels(**values: str) -> str:
    return ",".join(f'{key}="{_escape(value)}"' for key, value in values.items())


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _safe_label(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.:-]", "_", str(value))
    return normalized[:64] or "unknown"
