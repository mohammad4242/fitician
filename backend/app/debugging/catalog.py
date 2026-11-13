"""The same explicit, schema-validated gateway tools are shared by both runtimes."""

from __future__ import annotations

from typing import Any


def tool_catalog(
    *,
    allow_write: bool,
    supports_tests: bool = True,
    supports_github: bool = True,
    supports_ci: bool = False,
) -> list[dict[str, Any]]:
    def tool(
        name: str, description: str, properties: dict[str, Any], required: list[str]
    ) -> dict[str, Any]:
        return {
            "name": "fitician_" + name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        }

    path = {"type": "string", "minLength": 1, "maxLength": 240}
    tools = [
        tool(
            "read_file",
            "Read a bounded sanitized source excerpt from the exact release worktree.",
            {
                "path": path,
                "start": {"type": "integer", "minimum": 1, "maximum": 100000},
                "count": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            ["path"],
        ),
        tool(
            "search_code",
            "Search tracked source literally, within the selected prefix.",
            {"query": {"type": "string", "minLength": 1, "maxLength": 100}, "prefix": path},
            ["query", "prefix"],
        ),
        tool("diff", "Inspect the sanitized patch in this isolated worktree.", {}, []),
        tool(
            "server_evidence",
            "Read passive server observations scoped to the selected occurrence. "
            "Includes reported release, related diagnostic records, job attempts and recorded "
            "infrastructure signals. No shell, raw logs or credentials. Current observations "
            "do not prove the historical cause or business completion.",
            {},
            [],
        ),
        tool(
            "record_finding",
            "Persist a Persian observation, hypothesis or next check with evidence IDs. "
            "Cannot confirm a cause, resolve an issue or authorize deployment.",
            {
                "classification": {
                    "type": "string",
                    "enum": ["observed_fact", "hypothesis", "next_check"],
                },
                "text": {"type": "string", "minLength": 1, "maxLength": 2000},
                "evidence_ids": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 8,
                    "items": {"type": "string", "format": "uuid"},
                },
            },
            ["classification", "text", "evidence_ids"],
        ),
        tool(
            "run_tests",
            "Run a Python unittest file in the preconfigured networkless container.",
            {"path": path},
            ["path"],
        ),
    ]
    if allow_write:
        tools += [
            tool(
                "write_file",
                "Write isolated source. Release files and secrets are forbidden.",
                {"path": path, "content": {"type": "string", "maxLength": 131072}},
                ["path", "content"],
            ),
            tool(
                "commit",
                "Commit only a focused patch matching successful sandbox test evidence.",
                {"title": {"type": "string", "maxLength": 140}},
                ["title"],
            ),
            tool(
                "create_pr",
                "Publish the tested debug branch and its draft GitHub PR. Cannot merge or deploy.",
                {"title": {"type": "string", "maxLength": 140}},
                ["title"],
            ),
        ]
    if supports_ci:
        tools += [
            tool(
                "observe_server",
                "Queue fixed read-only observations for the explicitly selected production region. "
                "The selected occurrence trace scopes logs. "
                "No raw logs, arbitrary shell or deployment. "
                "Returns a durable job; use ci_status in a later turn for actual evidence.",
                {
                    "target_environment": {
                        "type": "string",
                        "enum": ["production-iran", "production-germany"],
                    }
                },
                ["target_environment"],
            ),
            tool(
                "ci_validate",
                "Queue exact workspace snapshot validation in isolated GitHub Actions. "
                "Returns a durable operation, not a passed test. No local Docker or credentials. "
                "Use ci_status later; queued work survives this model turn and disconnects.",
                {
                    "profile": {
                        "type": "string",
                        "enum": ["backend", "migrations", "frontend", "frontend_build", "agent"],
                    },
                    "tests": {"type": "array", "maxItems": 16, "items": path},
                },
                ["profile", "tests"],
            ),
            tool(
                "ci_status",
                "Read durable CI operations for this exact issue and selected occurrence. "
                "Results identify the tested candidate, policy, artifact and actual test counts.",
                {},
                [],
            ),
        ]
        if allow_write:
            tools.append(
                tool(
                    "ci_publish_pr",
                    "Request a draft PR for the exact successfully CI-tested workspace snapshot. "
                    "Requires an actual validation ID and unchanged patch. Cannot merge or deploy; "
                    "a changed main requires a fresh current-base repair and new tests.",
                    {
                        "validation_id": {"type": "string", "format": "uuid"},
                        "title": {"type": "string", "maxLength": 140},
                    },
                    ["validation_id", "title"],
                )
            )
    unavailable = set()
    if not supports_tests:
        unavailable.update({"fitician_run_tests", "fitician_commit", "fitician_create_pr"})
    if not supports_github:
        unavailable.add("fitician_create_pr")
    return [item for item in tools if item["name"] not in unavailable]
