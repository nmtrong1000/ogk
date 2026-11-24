"""In-memory stand-in for the OGK server's device API, served through httpx.MockTransport.
It mirrors the server contract: rotating refresh tokens, token_expired, device_revoked, invalid_refresh,
heartbeat versions, pending commands until acknowledged, and idempotent event batches.
offline makes every request fail like a dropped connection;
drop_response stores an event batch and then fails, like a response lost on the way back.
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
        self.versions: dict[int, int] = {}
        self.offline = False
        self.drop_response = False
        self.reject_events = False
        self.heartbeats: list[dict] = []
        self.batch_keys: list[str] = []
        self.events: list[dict] = []
        self.commands: list[dict] = []
        self.acked: list[int] = []

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

    def _events(self, request: httpx.Request) -> httpx.Response:
        if self.reject_events:
            return httpx.Response(422, json={"detail": "invalid_event", "index": 0, "field": "type"})
        key = request.headers["idempotency-key"]
        if key in self.batch_keys:
            return httpx.Response(200, json={"accepted": 0, "duplicate": True})
        events = json.loads(request.content)["events"]
        self.batch_keys.append(key)
        self.events.extend(events)
        if self.drop_response:
            raise httpx.ReadError("response lost", request=request)
        return httpx.Response(200, json={"accepted": len(events), "duplicate": False})

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.offline:
            raise httpx.ConnectError("network down", request=request)
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
        if path in ("/api/device/me", "/api/device/policy", "/api/device/heartbeat", "/api/device/events"):
            denied = self._check_access(request)
            if denied is not None:
                return denied
            if path == "/api/device/policy":
                return httpx.Response(200, json=self.policy_body)
            if path == "/api/device/heartbeat":
                self.heartbeats.append(json.loads(request.content))
                versions = {str(child_id): version for child_id, version in self.versions.items()}
                server_time = self.now.isoformat().replace("+00:00", "Z")
                pending = [c for c in self.commands if c["id"] not in self.acked]
                return httpx.Response(
                    200, json={"policy_versions": versions, "commands": pending, "server_time": server_time}
                )
            if path == "/api/device/events":
                return self._events(request)
            return httpx.Response(200, json={"id": 1, "name": "PC"})
        if path.startswith("/api/device/commands/") and path.endswith("/ack"):
            denied = self._check_access(request)
            if denied is not None:
                return denied
            command_id = int(path.split("/")[4])
            fresh = command_id not in self.acked
            self.acked.append(command_id)
            return httpx.Response(200, json={"acknowledged": fresh})
        return httpx.Response(404, json={"detail": "not_found"})

    def client(self, *_args, **_kwargs) -> ServerClient:
        client = ServerClient("https://server", transport=httpx.MockTransport(self.handle))
        client._pin.seen = PIN
        return client
