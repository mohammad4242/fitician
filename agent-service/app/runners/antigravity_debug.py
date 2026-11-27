"""Request-scoped AGY policy. The only local tool is schema output formatting."""

import json
import shlex
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Standalone: hooks do not inherit application imports or access account files.
_HANDLER = """import json, sys
try:
    data = sys.stdin.buffer.read(1048577)
    payload = json.loads(data) if len(data) <= 1048576 else {}
    name = payload.get("toolCall", {}).get("name")
except Exception:
    name = None
print(json.dumps({"decision": "allow" if name == "finish" else "deny",
                  "reason": "Only output formatting is local; use laptop repository tools"}))
"""


@contextmanager
def native_policy(workspace: Path) -> Iterator[str]:
    native = workspace / ".agents"
    handler = workspace / ".fitician-native-hook.py"
    if native.exists() or native.is_symlink() or handler.exists() or handler.is_symlink():
        raise ValueError("native_tool_isolation_unavailable")
    native.mkdir(mode=0o700)
    hooks = native / "hooks.json"
    try:
        with handler.open("x") as stream:
            handler.chmod(0o600)
            stream.write(_HANDLER)
        with hooks.open("x") as stream:
            hooks.chmod(0o600)
            json.dump(
                {
                    "fitician-debug-native-deny": {
                        "PreToolUse": [
                            {
                                "matcher": "*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": shlex.join([sys.executable, str(handler)]),
                                        "timeout": 5,
                                    }
                                ],
                            }
                        ]
                    }
                },
                stream,
            )
        yield json.dumps(
            {
                "agentMode": "",
                "toolPermission": "strict",
                "showThinking": False,
                "permissions": {
                    "deny": [
                        "command(*)",
                        "read_file(*)",
                        "write_file(*)",
                        "read_url(*)",
                        "execute_url(*)",
                        "mcp(*)",
                    ]
                },
            }
        )
    finally:
        hooks.unlink(missing_ok=True)
        handler.unlink(missing_ok=True)
        native.rmdir()
