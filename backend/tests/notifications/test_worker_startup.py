from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_notification_worker_import_registers_all_sqlalchemy_models() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(backend_root)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import app.notifications.worker\n"
                "from sqlalchemy.orm import configure_mappers\n"
                "configure_mappers()\n"
            ),
        ],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
