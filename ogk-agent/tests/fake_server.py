"""In-memory stand-in for the OGK server's device API, served through httpx.MockTransport.
It mirrors the server contract: rotating refresh tokens, token_expired, device_revoked, invalid_refresh.
"""

import json
from datetime import UTC, datetime, timedelta

import httpx

from service.core.server_client import ServerClient

VALID_CODE = "ABCD-EFGH"
PIN = "c" * 64


class FakeServer:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
        self.counter = 0
        self.access: dict[str, datetime] = {}
        self.refresh_token: str | None = None
        self.secret: str | None = None
        self.revoked = False
        self.requests: list[tuple[str, str]] = []
        self.enroll_bodies: list[dict] = []
        self.policy_body: dict = {"policies": []}

    def _tokens(self) -> dict:
        self.counter += 1
        access, refresh = f"access-{self.counter}", f"refresh-{self.counter}"
        expires = self.now + timedelta(minutes=15)
        self.access = {access: expires}
        self.refresh_token = refresh
        return {
            "device_id": 1,
            "access_token": access,
            "access_expires_at": expires.isoformat().replace("+00:00", "Z"),
            "refresh_token": refresh,
            "refresh_expires_at": (self.now + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        }

    def _check_access(self, request: httpx.Request) -> httpx.Response | None:
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if self.revoked:
            return httpx.Response(401, json={"detail": "device_revoked"})
        if token not in self.access:
            return httpx.Response(401, json={"detail": "invalid_token"})
        if self.access[token] <= self.now:
            return httpx.Response(401, json={"detail": "token_expired"})
        return None

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        path = request.url.path
        if path == "/api/enroll":
            body = json.loads(request.content)
            self.enroll_bodies.append(body)
            if body["code"] != VALID_CODE:
                return httpx.Response(400, json={"detail": "invalid_code"})
            self.secret = body["device_secret"]
            return httpx.Response(201, json=self._tokens())
        if path == "/api/device/token/refresh":
            body = json.loads(request.content)
            if body["device_secret"] != self.secret or body["refresh_token"] != self.refresh_token:
                return httpx.Response(401, json={"detail": "invalid_refresh"})
            if self.revoked:
                return httpx.Response(401, json={"detail": "device_revoked"})
            return httpx.Response(200, json=self._tokens())
        if path in ("/api/device/me", "/api/device/policy"):
            denied = self._check_access(request)
            if denied is not None:
                return denied
            if path == "/api/device/policy":
                return httpx.Response(200, json=self.policy_body)
            return httpx.Response(200, json={"id": 1, "name": "PC"})
        return httpx.Response(404, json={"detail": "not_found"})

    def client(self, *_args, **_kwargs) -> ServerClient:
        client = ServerClient("https://server", transport=httpx.MockTransport(self.handle))
        client._pin.seen = PIN
        return client
