#!/usr/bin/env python3
"""Dry-run-first retention for unused immutable Fitician images; never prune volumes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}")


def cleanup_candidates(images, referenced, protected_shas, repositories, now, minimum_age_hours):
    if len(protected_shas) < 2 or any(not SHA.fullmatch(s) for s in protected_shas):
        raise ValueError("Explicit current and rollback SHAs are required")
    if minimum_age_hours < 24:
        raise ValueError("Minimum image retention is 24 hours")
    selected, seen = [], set()
    for image in images:
        identity = image["Id"]
        if identity in seen:
            continue
        seen.add(identity)
        tags = image.get("RepoTags") or []
        if identity in referenced or not tags:
            continue
        refs = [tag.rsplit(":", 1) for tag in tags]
        if any(
            len(ref) != 2 or ref[0] not in repositories or not SHA.fullmatch(ref[1]) for ref in refs
        ):
            continue
        if any(ref[1] in protected_shas for ref in refs):
            continue
        created = datetime.fromisoformat(image["Created"].replace("Z", "+00:00"))
        if (now - created).total_seconds() < minimum_age_hours * 3600:
            continue
        selected.append(image)
    return selected


def recent_image_shas(images, repositories):
    protected = set()
    for repository in repositories:
        count = 0
        for image in sorted(images, key=lambda i: i["Created"], reverse=True):
            tags = [
                t.rsplit(":", 1)[1]
                for t in (image.get("RepoTags") or [])
                if t.startswith(repository + ":") and SHA.fullmatch(t.rsplit(":", 1)[1])
            ]
            if not tags:
                continue
            protected.update(tags)
            count += 1
            if count == 2:
                break
    return protected


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True)


def container_images():
    ids = docker("ps", "-aq").split()
    return {c["Image"] for c in json.loads(docker("inspect", *ids))} if ids else set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protected-file", type=Path, required=True)
    parser.add_argument("--repository", action="append", required=True)
    parser.add_argument("--minimum-age-hours", type=int, default=24)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--cleanup-build-cache", action="store_true")
    args = parser.parse_args()
    protected_bytes = args.protected_file.read_bytes()
    protected = set(protected_bytes.decode().split())
    repositories = set(args.repository)
    if any(
        not re.fullmatch(r"[a-z0-9._/-]+/fitician-(backend|frontend|agent)", r)
        for r in repositories
    ):
        parser.error("Only explicit Fitician repositories are allowed")
    ids = sorted(set(docker("image", "ls", "-aq", "--no-trunc").split()))
    images = json.loads(docker("image", "inspect", *ids)) if ids else []
    protected.update(recent_image_shas(images, repositories))
    candidates = cleanup_candidates(
        images,
        container_images(),
        protected,
        repositories,
        datetime.now(UTC),
        args.minimum_age_hours,
    )
    print(
        json.dumps(
            {
                "apply": args.apply,
                "protectedShas": sorted(protected),
                "unusedImageTags": [t for i in candidates for t in i["RepoTags"]],
            },
            indent=2,
        ),
        flush=True,
    )
    if not args.apply:
        return
    for image in candidates:
        if args.protected_file.read_bytes() != protected_bytes:
            raise RuntimeError("Rollback protection changed; stopping cleanup")
        current = json.loads(docker("image", "inspect", image["Id"]))[0]
        if image["Id"] in container_images() or set(current.get("RepoTags") or []) != set(
            image["RepoTags"]
        ):
            raise RuntimeError("Container/image references changed; stopping cleanup")
        # No force: Docker also refuses removal of any image acquired by a container.
        subprocess.run(["docker", "image", "rm", *image["RepoTags"]], check=True)
    if args.cleanup_build_cache:
        subprocess.run(
            ["docker", "builder", "prune", "--force", "--filter", "until=168h"], check=True
        )


if __name__ == "__main__":
    main()
