#!/usr/bin/env python3
"""Idempotent Fitician Sentry configuration. Credentials and DSNs never go to stdout."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

PROJECTS = {
    "fitician-backend": "python-fastapi",
    "fitician-agent": "python-fastapi",
    "fitician-web": "javascript-react",
    "fitician-mobile": "react-native",
}
Request = Callable[..., Any]


class SentryError(RuntimeError):
    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"sentry_http_{status}")


class SentrySetup:
    def __init__(self, request: Request, organization: str, team: str) -> None:
        if not all(re.fullmatch(r"[a-z0-9_-]{1,100}", value) for value in (organization, team)):
            raise ValueError("invalid_organization_or_team")
        self.request = request
        self.organization = organization
        self.team = team

    def configure(self, *, apply: bool) -> list[dict[str, Any]]:
        organization = self.request("GET", f"/api/0/organizations/{self.organization}/")
        if organization.get("slug") != self.organization:
            raise ValueError("sentry_organization_mismatch")
        result = []
        for slug, platform in PROJECTS.items():
            path = f"/api/0/projects/{self.organization}/{slug}/"
            try:
                project = self.request("GET", path)
            except SentryError as error:
                if error.status != 404:
                    raise
                if not apply:
                    result.append({"slug": slug, "state": "missing"})
                    continue
                project = self.request(
                    "POST",
                    f"/api/0/teams/{self.organization}/{self.team}/projects/",
                    {
                        "name": slug,
                        "slug": slug,
                        "platform": platform,
                        "default_rules": False,
                    },
                )
            if project.get("isPublic"):
                raise ValueError("public_project_requires_operator_review")
            if apply:
                options = {
                    "dataScrubber": True,
                    "dataScrubberDefaults": True,
                    "scrubIPAddresses": True,
                    "sensitiveFields": [
                        "authorization",
                        "cookie",
                        "password",
                        "token",
                        "email",
                        "phone",
                        "prompt",
                        "completion",
                        "medical",
                        "image",
                        "request_body",
                        "response_body",
                    ],
                    "safeFields": [],
                    "storeCrashReports": 0,
                    "scrapeJavaScript": False,
                    "verifySSL": True,
                    "resolveAge": 0,
                    "defaultEnvironment": "production-germany"
                    if slug == "fitician-agent"
                    else "production-iran",
                }
                updated = self.request("PUT", path, options)
                for name in (
                    "dataScrubber",
                    "dataScrubberDefaults",
                    "scrubIPAddresses",
                    "verifySSL",
                ):
                    if updated.get(name) is not True:
                        raise ValueError("privacy_configuration_not_verified")
                if (
                    updated.get("storeCrashReports") != 0
                    or updated.get("scrapeJavaScript") is not False
                ):
                    raise ValueError("private_artifact_policy_not_verified")
            keys = self.request("GET", path + "keys/")
            active = [key for key in keys if key.get("isActive")]
            if not active:
                raise ValueError("active_client_key_missing")
            dsn = active[0].get("dsn", {}).get("public")
            parsed = urllib.parse.urlsplit(dsn or "")
            if parsed.scheme != "https" or parsed.password or not parsed.hostname:
                raise ValueError("public_https_dsn_required")
            result.append(
                {
                    "slug": slug,
                    "platform": platform,
                    "project_id": str(project["id"]),
                    "dsn": dsn,
                    "state": "configured" if apply else "existing",
                }
            )
        return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def private_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--team", required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-email-file", type=Path)
    parser.add_argument("--region", choices=["global", "us", "de"], default="global")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.credentials.stat().st_mode & 0o077:
        raise SystemExit("Credential file must have mode 0600")
    raw = args.credentials.read_text().strip()
    token = json.loads(raw).get("access_token") if raw.startswith("{") else raw
    if not isinstance(token, str) or not token:
        raise SystemExit("Credential is missing")
    hosts = {"global": "sentry.io", "us": "us.sentry.io", "de": "de.sentry.io"}
    opener = urllib.request.build_opener(NoRedirect)

    def request(method: str, path: str, body: object = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        query = urllib.request.Request(
            f"https://{'sentry.io' if path == '/api/0/' else hosts[args.region]}{path}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            with opener.open(query, timeout=20) as response:
                payload = response.read(1_048_577)
                if len(payload) > 1_048_576:
                    raise ValueError("sentry_response_too_large")
                return json.loads(payload)
        except urllib.error.HTTPError as error:
            raise SentryError(error.code) from None

    if args.expected_email_file:
        identity = request("GET", "/api/0/")
        if (identity.get("user") or {}).get(
            "email"
        ) != args.expected_email_file.read_text().strip():
            raise SystemExit("Intended Sentry account does not match; no resources changed")
    projects = SentrySetup(request, args.organization, args.team).configure(apply=args.apply)
    private_json(args.output, {"organization": args.organization, "projects": projects})
    print(
        json.dumps(
            {
                "organization": args.organization,
                "projects": [{key: item[key] for key in ("slug", "state")} for item in projects],
                "private_configuration_written": True,
            }
        )
    )


if __name__ == "__main__":
    main()
