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

    def render(self) -> str:
        with self._lock:
            counts = dict(self._http_count)
            durations = dict(self._http_duration)
            in_flight = self._in_flight
            gauges = dict(self._gauges)
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
