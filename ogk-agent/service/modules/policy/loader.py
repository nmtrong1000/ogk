"""Policies are downloaded at service start and again whenever the sync module publishes POLICY_STALE after a
heartbeat shows a newer version. The cached copy is applied first so the device is never without a policy
while the server is unreachable. run() must never return, because the agent stops when any module task finishes.
"""

import asyncio
import logging

import httpx

from service.core.agent import ModuleContext
from service.core.bus import POLICY, POLICY_STALE, Bus
from service.core.device_session import DeviceRevoked, DeviceSession, NotEnrolled
from service.core.policy_store import PolicyRejected, PolicyStore, SignedPolicy
from service.core.server_client import ApiError

log = logging.getLogger("ogk.policy")


class PolicyLoader:
    def __init__(self, store: PolicyStore, session: DeviceSession | None, bus: Bus) -> None:
        self._store = store
        self._session = session
        self._bus = bus
        self._stale = asyncio.Event()
        bus.subscribe(POLICY_STALE, lambda _payload: self._stale.set())

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
        while True:
            await self._stale.wait()
            self._stale.clear()
            await self.tick()


def create(context: ModuleContext) -> PolicyLoader:
    return PolicyLoader(context.policy_store, context.session, context.bus)
