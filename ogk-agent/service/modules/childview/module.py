"""The code travels in the URL fragment, which the browser never sends to the server and the dashboard removes
from history before it exchanges the code; the server also accepts each code once and only for 60 seconds.
"""

import asyncio
import logging
import secrets
from typing import Any

import httpx

from service.core.agent import ModuleContext

START_PATH = "/child-view/start"
log = logging.getLogger("ogk.childview")


class ChildViewModule:
    def __init__(self, context: ModuleContext) -> None:
        self._context = context

    async def issue_child_view_link(self) -> dict[str, Any]:
        session, screen, config = self._context.session, self._context.screen, self._context.config
        if session is None or screen is None or config is None:
            raise RuntimeError("device is not ready")
        child_id = screen.child_id
        if child_id is None:
            raise LookupError("no child is signed in")
        code = secrets.token_urlsafe(32)
        try:
            result = await session.create_child_view_code(child_id, code)
        except httpx.TransportError as exc:
            log.warning("child-view code request lost its connection; retrying on a fresh connection: %s", exc)
            code = secrets.token_urlsafe(32)
            result = await session.create_child_view_code_fresh(child_id, code)
        return {
            "url": f"{config.server_url.rstrip('/')}{START_PATH}#code={code}",
            "expires_at": result.get("expires_at") if isinstance(result, dict) else None,
        }

    async def run(self) -> None:
        await asyncio.Event().wait()


def create(context: ModuleContext) -> ChildViewModule:
    return ChildViewModule(context)
