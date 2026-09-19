from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("module_name", "relative_path", "heartbeat_call"),
    (
        ("app.notifications.worker", "app/notifications/worker.py", "threaded_heartbeat("),
        (
            "app.nutrition.food_photo_worker",
            "app/nutrition/food_photo_worker.py",
            "async_heartbeat(",
        ),
        ("app.body_analysis.worker", "app/body_analysis/worker.py", "async_heartbeat("),
    ),
)
def test_worker_starts_heartbeat_before_registering_all_models(
    module_name: str,
    relative_path: str,
    heartbeat_call: str,
) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(backend_root)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                f"import {module_name}\n"
                "import sys\n"
                "assert 'app.main' not in sys.modules\n"
            ),
        ],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    source = (backend_root / relative_path).read_text(encoding="utf-8")
    worker_start = source.index("run_worker(")
    heartbeat_start = source.index(heartbeat_call, worker_start)
    model_registration = source.index('import_module("app.main")', worker_start)
    assert heartbeat_start < model_registration
