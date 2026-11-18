"""Policies are downloaded once at service start; periodic sync arrives with the heartbeat in P11.
The cached copy is applied first so the device is never without a policy while the server is unreachable.
run() must not return after the download, because the agent stops when any module task finishes.
"""

import asyncio
import logging

import httpx

from service.core.agent import ModuleContext
from service.core.bus import POLICY, Bus
from service.core.device_session import DeviceRevoked, DeviceSession, NotEnrolled
from service.core.policy_store import PolicyRejected, PolicyStore, SignedPolicy
from service.core.server_client import ApiError

log = logging.getLogger("ogk.policy")


class PolicyLoader:
    def __init__(self, store: PolicyStore, session: DeviceSession | None, bus: Bus) -> None:
        self._store = store
        self._session = session
        self._bus = bus

    def _apply(self, policies: dict[int, SignedPolicy], source: str) -> None:
        for policy in policies.values():
            log.info("policy loaded from %s: child=%s version=%s", source, policy.child_id, policy.version)
        self._bus.publish(POLICY, policies)

    async def load_cached(self) -> dict[int, SignedPolicy]:
        try:
            policies = await asyncio.to_thread(self._store.load)
        except PolicyRejected:
            return {}
        if policies:
            self._apply(policies, "cache")
        return policies

    async def tick(self) -> bool:
        if self._session is None:
            return False
        try:
            body = await self._session.policy()
        except NotEnrolled:
            log.warning("policy not downloaded: device not enrolled")
            return False
        except DeviceRevoked:
            log.warning("policy not downloaded: device is revoked")
            return False
        except (httpx.HTTPError, ApiError) as exc:
            log.warning("policy download failed, keeping cached policies: %s", exc or type(exc).__name__)
            return False
        try:
            policies = await asyncio.to_thread(self._store.save, body)
        except PolicyRejected as exc:
            log.error("policy from server rejected, keeping cached policies: %s", exc)
            return False
        if not policies:
            log.info("policy loaded from server: no child is assigned to this device")
        self._apply(policies, "server")
        return True

    async def run(self) -> None:
        await self.load_cached()
        await self.tick()
        await asyncio.Event().wait()


def create(context: ModuleContext) -> PolicyLoader:
    return PolicyLoader(context.policy_store, context.session, context.bus)
