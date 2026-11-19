"""Certificate pinning runs inside the connection, right after the TLS handshake and before any HTTP bytes are
sent, so a request carrying a device token never reaches a server whose certificate is not the pinned one.
httpx has no hook at that point, so PinnedTransport swaps its httpcore pool (the private _pool attribute)
for one built on a network backend that checks the leaf certificate. test_pinning.py breaks if httpx changes this.
The CA check still applies; the pin is an extra condition on top of it.
With capture_pin, no pin is enforced and the SHA-256 of the certificate seen is kept in peer_cert_sha256;
enrollment uses this to learn the pin over a CA-verified connection.
trust_env is off so an environment proxy cannot replace the pinned transport.
The pinned pool is built directly on httpcore, whose default keeps idle connections forever. Uvicorn closes
them after 5 seconds, and on Windows the closed socket is not noticed before reuse, so every request after
a pause failed; idle connections are therefore dropped after KEEPALIVE_SECONDS, below the server's 5.
"""

import hashlib
import hmac
import ssl
from pathlib import Path
from typing import Any

import httpcore
import httpx


class CertificatePinError(httpx.ConnectError):
    pass


class ApiError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(f"server returned {status} {code}")
        self.status = status
        self.code = code


def make_ssl_context(ca_cert: Path) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=str(ca_cert))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def cert_sha256(der: bytes) -> str:
    return hashlib.sha256(der).hexdigest()


class _PinState:
    def __init__(self, pin: str | None) -> None:
        self.pin = pin.lower() if pin else None
        self.seen: str | None = None

    def check(self, stream: httpcore.AsyncNetworkStream) -> None:
        ssl_object = stream.get_extra_info("ssl_object")
        der = ssl_object.getpeercert(binary_form=True) if ssl_object else None
        if not der:
            raise CertificatePinError("server presented no certificate")
        self.seen = cert_sha256(der)
        if self.pin is not None and not hmac.compare_digest(self.seen, self.pin):
            raise CertificatePinError(f"server certificate {self.seen} does not match pinned {self.pin}")


class _PinnedStream(httpcore.AsyncNetworkStream):
    def __init__(self, inner: httpcore.AsyncNetworkStream, state: _PinState) -> None:
        self._inner = inner
        self._state = state

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return await self._inner.read(max_bytes, timeout)

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        await self._inner.write(buffer, timeout)

    async def aclose(self) -> None:
        await self._inner.aclose()

    async def start_tls(
        self, ssl_context: ssl.SSLContext, server_hostname: str | None = None, timeout: float | None = None
    ) -> httpcore.AsyncNetworkStream:
        tls = await self._inner.start_tls(ssl_context, server_hostname, timeout)
        try:
            self._state.check(tls)
        except CertificatePinError:
            await tls.aclose()
            raise
        return tls

    def get_extra_info(self, info: str) -> Any:
        return self._inner.get_extra_info(info)


class _PinnedBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, state: _PinState) -> None:
        self._inner = httpcore.AnyIOBackend()
        self._state = state

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        stream = await self._inner.connect_tcp(host, port, timeout, local_address, socket_options)
        return _PinnedStream(stream, self._state)

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):
        raise CertificatePinError("unix sockets are not supported")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


KEEPALIVE_SECONDS = 4.0


class PinnedTransport(httpx.AsyncHTTPTransport):
    def __init__(self, context: ssl.SSLContext, state: _PinState) -> None:
        super().__init__(verify=context)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=context, keepalive_expiry=KEEPALIVE_SECONDS, network_backend=_PinnedBackend(state)
        )


def _error_code(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    return detail if isinstance(detail, str) else f"http_{response.status_code}"


class ServerClient:
    def __init__(
        self,
        base_url: str,
        ca_cert: Path | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
        pin_sha256: str | None = None,
        capture_pin: bool = False,
    ) -> None:
        self._pin = _PinState(pin_sha256)
        verify: ssl.SSLContext | bool = make_ssl_context(ca_cert) if ca_cert else True
        if transport is None and (pin_sha256 or capture_pin):
            if not isinstance(verify, ssl.SSLContext):
                raise ValueError("certificate pinning needs a CA certificate")
            transport = PinnedTransport(verify, self._pin)
        self._client = httpx.AsyncClient(
            base_url=base_url, verify=verify, transport=transport, timeout=timeout, trust_env=False
        )

    @property
    def peer_cert_sha256(self) -> str | None:
        return self._pin.seen

    async def _json(self, method: str, path: str, **kwargs) -> Any:
        response = await self._client.request(method, path, **kwargs)
        if response.is_error:
            raise ApiError(response.status_code, _error_code(response))
        return response.json()

    async def health(self) -> Any:
        response = await self._client.get("/api/health")
        response.raise_for_status()
        return response.json()

    async def enroll(self, body: dict[str, Any]) -> dict[str, Any]:
        return await self._json("POST", "/api/enroll", json=body)

    async def refresh(self, device_id: int, refresh_token: str, device_secret: str) -> dict[str, Any]:
        body = {"device_id": device_id, "refresh_token": refresh_token, "device_secret": device_secret}
        return await self._json("POST", "/api/device/token/refresh", json=body)

    async def device_me(self, access_token: str) -> dict[str, Any]:
        return await self._json("GET", "/api/device/me", headers={"Authorization": f"Bearer {access_token}"})

    async def device_policy(self, access_token: str) -> Any:
        return await self._json("GET", "/api/device/policy", headers={"Authorization": f"Bearer {access_token}"})

    async def heartbeat(self, access_token: str, body: dict[str, Any]) -> Any:
        return await self._json(
            "POST", "/api/device/heartbeat", json=body, headers={"Authorization": f"Bearer {access_token}"}
        )

    async def post_events(self, access_token: str, events: list[dict[str, Any]], idempotency_key: str) -> Any:
        headers = {"Authorization": f"Bearer {access_token}", "Idempotency-Key": idempotency_key}
        return await self._json("POST", "/api/device/events", json={"events": events}, headers=headers)

    async def aclose(self) -> None:
        await self._client.aclose()
