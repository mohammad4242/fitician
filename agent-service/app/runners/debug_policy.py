"""Version-bound native-tool restrictions for externally orchestrated turns.

Unknown CLI versions fail closed. Generation runners retain their existing policy.
"""

import re

from ..schemas import AgentName

# Verified installed CLI contracts; expanding this requires a runner security test.
_VERSIONS = {
    AgentName.CODEX: frozenset({"0.151.0"}),
    AgentName.CLAUDE: frozenset({"2.1.220"}),
    # Per-request settings + hook denial; finish only formats schema output.
    AgentName.ANTIGRAVITY: frozenset({"1.5.14"}),
}


def supports_external_tools(agent: AgentName, version: str | None) -> bool:
    versions = re.findall(r"(?<![0-9])([0-9]+\.[0-9]+\.[0-9]+)(?![0-9])", version or "")
    return len(versions) == 1 and versions[0] in _VERSIONS[agent]
