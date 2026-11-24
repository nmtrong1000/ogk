import asyncio
from datetime import UTC, datetime
from typing import Any

from service.core.agent import ModuleContext


class RequestsModule:
    def __init__(self, context: ModuleContext) -> None:
        self._context = context

    async def submit(self, body: dict[str, Any]) -> dict[str, Any]:
        if self._context.session is None or self._context.screen is None:
            raise RuntimeError("device is not ready")
        child_id = self._context.screen.child_id
        if child_id is None:
            raise RuntimeError("no child is signed in")
        kind = body["type"]
        request_body = {"child_id": child_id, "type": kind}
        if kind == "blocked_domain":
            request_body["domain"] = body["domain"]
        result = await self._context.session.create_request(request_body)
        if self._context.event_queue is not None and self._context.session.device_id is not None:
            await self._context.event_queue.enqueue(
                [
                    {
                        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "device_id": self._context.session.device_id,
                        "child_id": child_id,
                        "type": "unlock_request",
                        "subject": body.get("domain", kind),
                        "duration_sec": 0,
                        "policy_id": self._context.policy_store.versions().get(child_id, 0),
                    }
                ]
            )
        return result

    async def run(self) -> None:
        await asyncio.Event().wait()


def create(context: ModuleContext) -> RequestsModule:
    return RequestsModule(context)
