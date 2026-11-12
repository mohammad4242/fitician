"""Worker-to-laptop durable calls. The web process never runs model-produced commands."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from .connectors import _authorize_run, enqueue_call
from .models import DebugConnector, DebugConnectorCall, DebugRun
from .service import append_event


async def call_connector(
    engine: Engine | Connection,
    run_id: UUID,
    lease: UUID,
    key: str,
    tool: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    with Session(engine) as db:
        run = db.scalar(select(DebugRun).where(DebugRun.id == run_id).with_for_update())
        if run is None or run.lease_token != lease:
            raise ValueError("run_lease_lost")
        _authorize_run(db, run)
        connector_id = run.config_snapshot.get("connector_id")
        connector = db.get(DebugConnector, UUID(connector_id)) if connector_id else None
        if connector is None:
            raise ValueError("local_connector_not_configured")
        row = enqueue_call(db, run, connector, key, tool, arguments)
        identifier = row.id
        append_event(
            db,
            run,
            "tool_queued",
            {"tool": tool, "call_id": str(row.id), "connector_id": str(connector.id)},
        )
        db.commit()
    while True:
        await asyncio.sleep(0.5)
        with Session(engine) as db:
            run = db.get(DebugRun, run_id)
            if run is None or run.lease_token != lease:
                raise ValueError("run_lease_lost")
            _authorize_run(db, run)
            latest_call = db.get(DebugConnectorCall, identifier)
            if latest_call and latest_call.state == "completed":
                result = latest_call.result or {}
                if result.get("error_code"):
                    raise ValueError("connector_execution_failed")
                return result
