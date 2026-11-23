"""The health check carries no secret, but once the device is enrolled it still uses the pinned certificate
so a changed server certificate shows up as unreachable instead of healthy.
The development tools are imported only when OGK_DEV=1; release builds exclude the service.devtools package,
so there the import fails and no development route exists even if the variable is set.
The device check logs only when its outcome changes, so a long outage or revocation does not flood the log.
"""

import asyncio
import importlib
import logging
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

import httpx
from aiohttp import web

from service.core.alerts import AlertBoard
from service.core.app_state import AppState
from service.core.bus import SERVER_TIME, SESSION, TRAY_HEARTBEAT, Bus
from service.core.clock import SyncClock
from service.core.commands import CommandState
from service.core.config import DEFAULT_POLICY_FILE, Config, bundled_data_dir, load_config
from service.core.device_session import DeviceRevoked, DeviceSession, NotEnrolled
from service.core.enforcement import Enforcement
from service.core.event_queue import EventQueue
from service.core.ipc_server import IpcServer
from service.core.local_db import LocalDb
from service.core.offline import OfflineGuard
from service.core.policy_store import PolicyStore, load_default_policy
from service.core.screen_state import ScreenState
from service.core.server_client import ApiError, CertificatePinError, ServerClient
from service.core.trusted_clock import TrustedClock
from service.core.web_state import WebState
from service.platform import get_platform

log = logging.getLogger("ogk.agent")

DEV_ENV = "OGK_DEV"
DEVTOOLS_MODULE = "service.devtools"


@dataclass(frozen=True)
class ModuleContext:
    bus: Bus
    enforcement: Enforcement
    platform: ModuleType
    data_dir: Path
    policy_store: PolicyStore
    session: DeviceSession | None = None
    config: Config | None = None
    event_queue: EventQueue | None = None
    offline: OfflineGuard | None = None
    db: LocalDb | None = None
    clock: TrustedClock | None = None
    alerts: AlertBoard | None = None
    screen: ScreenState | None = None
    apps: AppState | None = None
    web_state: WebState | None = None
    commands: CommandState | None = None


class Module(Protocol):
    async def run(self) -> None: ...


ModuleFactory = Callable[[ModuleContext], Module]


class Agent:
    def __init__(
        self,
        config: Config,
        client: ServerClient,
        data_dir: Path,
        session: DeviceSession | None = None,
        *,
        bus: Bus | None = None,
        enforcement: Enforcement | None = None,
        policy_store: PolicyStore | None = None,
        offline: OfflineGuard | None = None,
        screen: ScreenState | None = None,
        apps: AppState | None = None,
        web_state: WebState | None = None,
        modules: Sequence[Module] = (),
        extra_routes: Sequence[web.AbstractRouteDef] = (),
    ) -> None:
        self._config = config
        self._client = client
        self._session = session
        self._device_outcome: str | None = None
        self._bus = bus or Bus()
        self._enforcement = enforcement or Enforcement()
        self._policy_store = policy_store
        self._offline = offline
        self._web_state = web_state or WebState()
        self._modules = list(modules)
        self._ipc = IpcServer(
            data_dir,
            config.ipc_port,
            self.status,
            lambda ping: self._bus.publish(TRAY_HEARTBEAT, ping),
            extra_routes,
            None if screen is None else screen.snapshot,
            None if apps is None else apps.snapshot,
            self._web_state.snapshot,
        )
        self._started = time.monotonic()
        self._server_reachable: bool | None = None

    def status(self) -> dict[str, Any]:
        return {
            "uptime": round(time.monotonic() - self._started, 1),
            "server_reachable": self._server_reachable,
            "enrollment": None if self._session is None else self._session.state,
            "enforcement": self._enforcement.snapshot(),
            "policies": {} if self._policy_store is None else self._policy_store.versions(),
            "policy_mode": None if self._policy_store is None else self._policy_store.mode,
            "offline_seconds": None if self._offline is None else round(self._offline.clock.offline_seconds()),
        }

    async def run(self, stop_event: asyncio.Event) -> None:
        log.info("agent started, server %s", self._config.server_url)
        self._started = time.monotonic()
        tasks: list[asyncio.Task] = []
        stop_task = asyncio.create_task(stop_event.wait(), name="stop")
        try:
            await self._ipc.start()
            tasks.append(asyncio.create_task(self._health_loop(), name="health"))
            if self._session is not None:
                tasks.append(asyncio.create_task(self._device_loop(), name="device"))
            for module in self._modules:
                tasks.append(asyncio.create_task(module.run(), name=type(module).__name__))
            await asyncio.wait([stop_task, *tasks], return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in [stop_task, *tasks]:
                task.cancel()
            await asyncio.gather(stop_task, *tasks, return_exceptions=True)
            await self._ipc.stop()
            await self._client.aclose()
            if self._session is not None:
                await self._session.aclose()
        for task in tasks:
            if not task.cancelled() and task.exception() is not None:
                raise task.exception()
        log.info("agent stopped")

    async def check_health(self) -> bool:
        try:
            body = await self._client.health()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("server unreachable: %s", exc or type(exc).__name__)
            self._server_reachable = False
            return False
        log.info("server ok: %s", body)
        self._server_reachable = True
        return True

    def _device_log(self, outcome: str, level: int, message: str, *args: Any) -> None:
        if outcome != self._device_outcome:
            log.log(level, message, *args)
        self._device_outcome = outcome

    async def check_device(self) -> bool:
        try:
            info = await self._session.me()
        except NotEnrolled:
            self._device_log(
                "not_enrolled", logging.WARNING, "device not enrolled; run 'ogk_service enroll' as Administrator"
            )
            return False
        except DeviceRevoked:
            self._device_log("revoked", logging.ERROR, "device is revoked; API calls stopped")
            return False
        except CertificatePinError as exc:
            self._device_log("pin", logging.ERROR, "refusing to connect: %s", exc)
            return False
        except (httpx.HTTPError, ApiError) as exc:
            self._device_log("error", logging.WARNING, "device check failed: %s", exc or type(exc).__name__)
            return False
        self._device_log("ok", logging.INFO, "device %s authenticated as %s", info["id"], info["name"])
        return True

    async def _device_loop(self) -> None:
        while True:
            await self.check_device()
            await asyncio.sleep(self._config.health_interval)

    async def _health_loop(self) -> None:
        while True:
            await self.check_health()
            await asyncio.sleep(self._config.health_interval)


def dev_routes(context: ModuleContext) -> list[web.AbstractRouteDef]:
    if os.environ.get(DEV_ENV) != "1":
        return []
    try:
        devtools = importlib.import_module(DEVTOOLS_MODULE)
    except ImportError:
        log.warning("%s=1 but this build has no development tools", DEV_ENV)
        return []
    log.warning("development tools enabled on IPC")
    return devtools.routes(context)


async def run_agent(data_dir: Path, stop_event: asyncio.Event, modules: Sequence[ModuleFactory] = ()) -> None:
    config = load_config(data_dir)
    db = LocalDb(data_dir)
    creds = await asyncio.to_thread(db.load)
    pin = creds.cert_sha256 if creds is not None and creds.server_url == config.server_url else None
    client = ServerClient(config.server_url, config.ca_cert, pin_sha256=pin)
    bus = Bus()
    enforcement = Enforcement()
    platform = get_platform()
    session = DeviceSession(config, db)
    default_policy = load_default_policy(bundled_data_dir() / DEFAULT_POLICY_FILE)
    policy_store = PolicyStore(db, config.policy_public_key, default_policy)
    offline = OfflineGuard(SyncClock(db), policy_store, bus, config.offline_limit_days)
    await asyncio.to_thread(offline.start)
    clock = TrustedClock(db)
    bus.subscribe(SERVER_TIME, lambda at: clock.offline() if at is None else clock.online(at))
    screen = ScreenState()
    apps = AppState()
    web_state = WebState()
    commands = CommandState(db)
    context = ModuleContext(
        bus,
        enforcement,
        platform,
        data_dir,
        policy_store,
        session,
        config=config,
        event_queue=EventQueue(db, session),
        offline=offline,
        db=db,
        clock=clock,
        alerts=AlertBoard(),
        screen=screen,
        apps=apps,
        web_state=web_state,
        commands=commands,
    )
    instances = [factory(context) for factory in modules]
    platform.set_session_listener(lambda event: bus.publish(SESSION, event))
    agent = Agent(
        config,
        client,
        data_dir,
        session,
        bus=bus,
        enforcement=enforcement,
        policy_store=policy_store,
        offline=offline,
        screen=screen,
        apps=apps,
        web_state=web_state,
        modules=instances,
        extra_routes=dev_routes(context),
    )
    await agent.run(stop_event)
