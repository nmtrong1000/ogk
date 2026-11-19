"""Development-only IPC routes. Release builds pass --exclude-module service.devtools (installer/build.ps1),
and core/agent.py imports this package only when OGK_DEV=1, so none of this exists on a child's PC.
Sample events come from docs/test_vectors.json, which is only present in a source checkout.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiohttp import web

from service.core.agent import ModuleContext
from service.core.events import EventInvalid, format_ts

VECTORS_FILE = Path(__file__).resolve().parents[3] / "docs" / "test_vectors.json"
MAX_INJECT = 1000


def sample_events() -> dict[str, dict[str, Any]]:
    vectors = json.loads(VECTORS_FILE.read_text(encoding="utf-8"))
    return {case["name"]: case["event"] for case in vectors["events"]["valid"]}


def _error(code: str, status: int = 400) -> web.Response:
    return web.json_response({"error": code}, status=status)


async def _json(request: web.Request) -> dict[str, Any] | None:
    try:
        body = await request.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _from_vector(context: ModuleContext, body: dict[str, Any], device_id: int) -> list[dict[str, Any]] | None:
    sample = sample_events().get(body.get("vector"))
    count = body.get("count", 1)
    if sample is None or isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_INJECT:
        return None
    child_id = body.get("child_id")
    if child_id is None:
        child_id = next(iter(sorted(context.policy_store.versions())), sample["child_id"])
    effective = context.policy_store.rules_for(child_id) if isinstance(child_id, int) else None
    event = {
        **sample,
        "ts": format_ts(datetime.now(UTC)),
        "device_id": device_id,
        "child_id": child_id,
        "policy_id": sample["policy_id"] if effective is None else effective.version,
    }
    return [dict(event) for _ in range(count)]


def routes(context: ModuleContext) -> list[web.AbstractRouteDef]:
    async def inject_events(request: web.Request) -> web.Response:
        body = await _json(request)
        if body is None:
            return _error("bad_request")
        device_id = context.session.device_id if context.session is not None else None
        if device_id is None:
            return _error("not_enrolled", 409)
        if "vector" in body:
            events = _from_vector(context, body, device_id)
        elif isinstance(body.get("events"), list) and len(body["events"]) <= MAX_INJECT:
            events = [{**e, "device_id": device_id} if isinstance(e, dict) else e for e in body["events"]]
        else:
            events = None
        if not events:
            return _error("bad_request")
        try:
            queued = await context.event_queue.enqueue(events)
        except EventInvalid as exc:
            return web.json_response({"error": "invalid_event", "field": exc.field}, status=400)
        return web.json_response({"queued": queued, "pending": await context.event_queue.pending()})

    async def simulate_offline(request: web.Request) -> web.Response:
        body = await _json(request)
        days = None if body is None else body.get("days")
        if isinstance(days, bool) or not isinstance(days, (int, float)) or days < 0:
            return _error("bad_request")
        mode = await asyncio.to_thread(context.offline.simulate, days)
        return web.json_response(
            {"offline_seconds": round(context.offline.clock.offline_seconds()), "policy_mode": mode}
        )

    return [web.post("/ipc/dev/events", inject_events), web.post("/ipc/dev/offline", simulate_offline)]
