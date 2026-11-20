"""Every call that carries a device token goes through DeviceSession.call(), which refreshes the access token
shortly before it expires and once more if the server still says token_expired or invalid_token.
device_revoked and invalid_refresh are final: the revocation is written to the local DB, logged once at
ERROR, and no further request is made until the device is enrolled again. invalid_refresh also covers a
refresh token reused after rotation, after which the server has revoked every token of the device.
That is why refreshes are serialized: tasks that all see an expired token at once (heartbeat, policy and
events at boot) must share one rotation; a task whose token was already rotated while it waited skips it.
Credentials are re-read from the DB while not active, so a service that is already running picks up a new
enrollment without a restart. The HTTP client is rebuilt whenever the pinned certificate changes.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

from service.core.config import Config
from service.core.local_db import Credentials, LocalDb
from service.core.server_client import ApiError, ServerClient

log = logging.getLogger("ogk.device")

REFRESH_MARGIN = timedelta(seconds=60)
RETRY_CODES = frozenset({"token_expired", "invalid_token"})
REVOKED_CODES = frozenset({"device_revoked", "invalid_refresh"})

STATE_NOT_ENROLLED = "not_enrolled"
STATE_ACTIVE = "active"
STATE_REVOKED = "revoked"

T = TypeVar("T")
ClientFactory = Callable[[Config, str], ServerClient]


class NotEnrolled(Exception):
    pass


class DeviceRevoked(Exception):
    pass


def default_client_factory(config: Config, pin: str) -> ServerClient:
    return ServerClient(config.server_url, config.ca_cert, pin_sha256=pin)


def utcnow() -> datetime:
    return datetime.now(UTC)


class DeviceSession:
    def __init__(
        self,
        config: Config,
        db: LocalDb,
        client_factory: ClientFactory = default_client_factory,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._config = config
        self._db = db
        self._factory = client_factory
        self._clock = clock
        self._creds: Credentials | None = None
        self._client: ServerClient | None = None
        self._pin: str | None = None
        self._refresh_lock = asyncio.Lock()

    @property
    def state(self) -> str:
        if self._creds is None:
            return STATE_NOT_ENROLLED
        return STATE_REVOKED if self._creds.revoked_at is not None else STATE_ACTIVE

    @property
    def device_id(self) -> int | None:
        return None if self._creds is None else self._creds.device_id

    async def _load(self) -> None:
        creds = await asyncio.to_thread(self._db.load)
        if creds is not None and creds.server_url != self._config.server_url:
            log.warning(
                "enrollment is for %s, config points to %s; ignoring it", creds.server_url, self._config.server_url
            )
            creds = None
        self._creds = creds
        if creds is not None and creds.cert_sha256 != self._pin:
            await self._close_client()
            self._client = self._factory(self._config, creds.cert_sha256)
            self._pin = creds.cert_sha256

    async def _ready(self) -> tuple[Credentials, ServerClient]:
        if self.state != STATE_ACTIVE:
            await self._load()
        if self._creds is None:
            raise NotEnrolled("device is not enrolled")
        if self._creds.revoked_at is not None:
            raise DeviceRevoked("device was revoked by the server")
        return self._creds, self._client

    async def _revoke(self, code: str) -> None:
        self._creds = await asyncio.to_thread(self._db.mark_revoked, self._creds, self._clock())
        log.error(
            "device %s revoked by server (%s); API calls stopped. Run 'ogk_service enroll' as Administrator "
            "to enroll again",
            self._creds.device_id,
            code,
        )

    async def refresh(self) -> None:
        seen, _ = await self._ready()
        async with self._refresh_lock:
            creds, client = await self._ready()
            if creds.refresh_token != seen.refresh_token:
                return
            await self._rotate(creds, client)

    async def _rotate(self, creds: Credentials, client: ServerClient) -> None:
        try:
            tokens = await client.refresh(creds.device_id, creds.refresh_token, creds.device_secret)
        except ApiError as exc:
            if exc.code in REVOKED_CODES:
                await self._revoke(exc.code)
                raise DeviceRevoked(exc.code) from None
            raise
        self._creds = await asyncio.to_thread(
            self._db.update_tokens,
            creds,
            tokens["access_token"],
            datetime.fromisoformat(tokens["access_expires_at"].replace("Z", "+00:00")),
            tokens["refresh_token"],
        )
        log.info("access token refreshed, valid until %s", self._creds.access_expires_at.isoformat())

    async def _attempt(self, fn: Callable[[ServerClient, str], Awaitable[T]]) -> T:
        try:
            return await fn(self._client, self._creds.access_token)
        except ApiError as exc:
            if exc.code == "device_revoked":
                await self._revoke(exc.code)
                raise DeviceRevoked(exc.code) from None
            raise

    async def call(self, fn: Callable[[ServerClient, str], Awaitable[T]]) -> T:
        creds, _ = await self._ready()
        if creds.access_expires_at - self._clock() <= REFRESH_MARGIN:
            await self.refresh()
        try:
            return await self._attempt(fn)
        except ApiError as exc:
            if exc.code not in RETRY_CODES:
                raise
        await self.refresh()
        return await self._attempt(fn)

    async def me(self) -> dict[str, Any]:
        return await self.call(lambda client, token: client.device_me(token))

    async def policy(self) -> Any:
        return await self.call(lambda client, token: client.device_policy(token))

    async def heartbeat(self, body: dict[str, Any]) -> Any:
        return await self.call(lambda client, token: client.heartbeat(token, body))

    async def post_events(self, events: list[dict[str, Any]], idempotency_key: str) -> Any:
        return await self.call(lambda client, token: client.post_events(token, events, idempotency_key))

    async def _close_client(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._pin = None

    async def aclose(self) -> None:
        await self._close_client()
