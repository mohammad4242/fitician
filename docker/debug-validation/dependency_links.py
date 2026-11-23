"""Keep packages read-only while permitting bounded per-run tool caches."""

from pathlib import Path


def link_dependencies(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for entry in source.iterdir():
        if entry.name.startswith(".") and entry.name != ".bin":
            continue
        destination = target / entry.name
        if entry.name.startswith("@"):
            destination.mkdir(exist_ok=True)
            for package in entry.iterdir():
                (destination / package.name).symlink_to(
                    package, target_is_directory=package.is_dir()
                )
        else:
            destination.symlink_to(entry, target_is_directory=entry.is_dir())
