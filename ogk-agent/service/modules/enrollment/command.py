"""Usage: ogk_service enroll [--code XXXX-XXXX] [--force]
Run from an elevated prompt on the child's PC. Without --code the pairing code is read from the terminal.
The pin is learned here: the first connection is verified against ca.crt from config.json, and the SHA-256
of the certificate seen on that connection becomes the pin for every later request.
The device secret is generated locally and never shown; the server keeps only its hash.
Exit codes: 0 enrolled, 1 refused or failed, 2 bad usage.
"""

import argparse
import asyncio
import secrets
import socket
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from service.core.config import Config, ConfigError, load_config
from service.core.local_db import Credentials, LocalDb
from service.core.server_client import ApiError, ServerClient
from service.platform import get_platform

MESSAGES = {
    "invalid_code": "Pairing code is invalid, expired or already used. Create a new code on the dashboard.",
    "rate_limited": "Too many attempts. Wait a minute and try again.",
}

ClientFactory = Callable[[Config], ServerClient]


def default_client_factory(config: Config) -> ServerClient:
    return ServerClient(config.server_url, config.ca_cert, capture_pin=True)


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ogk_service enroll", description="Pair this PC with a parent account.")
    parser.add_argument("--code", help="8-character pairing code from the dashboard")
    parser.add_argument("--force", action="store_true", help="enroll again even if this PC is already enrolled")
    return parser.parse_args(argv)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def enroll(
    data_dir: Path,
    code: str,
    *,
    force: bool = False,
    client_factory: ClientFactory = default_client_factory,
    out=print,
) -> int:
    platform = get_platform()
    if not platform.is_admin():
        out("enroll must run as Administrator")
        return 1
    try:
        config = load_config(data_dir)
    except ConfigError as exc:
        out(str(exc))
        return 1
    db = LocalDb(data_dir)
    existing = await asyncio.to_thread(db.load)
    if existing is not None and existing.revoked_at is None and not force:
        out(f"This PC is already enrolled as device {existing.device_id}. Use --force to enroll again.")
        return 1

    secret = secrets.token_urlsafe(32)
    body = {
        "code": code,
        "fingerprint": platform.machine_fingerprint(),
        "device_secret": secret,
        "name": socket.gethostname(),
        "accounts": [{"username": u, "sid": s} for u, s in platform.list_windows_accounts()],
    }
    client = client_factory(config)
    try:
        tokens = await client.enroll(body)
        pin = client.peer_cert_sha256
    except ApiError as exc:
        out(MESSAGES.get(exc.code, f"Enrollment failed: {exc}"))
        return 1
    except httpx.HTTPError as exc:
        out(f"Cannot reach server {config.server_url}: {exc or type(exc).__name__}")
        return 1
    finally:
        await client.aclose()
    if not pin:
        out("Enrollment failed: server certificate was not captured")
        return 1

    creds = Credentials(
        device_id=tokens["device_id"],
        server_url=config.server_url,
        cert_sha256=pin,
        device_secret=secret,
        access_token=tokens["access_token"],
        access_expires_at=_parse_time(tokens["access_expires_at"]),
        refresh_token=tokens["refresh_token"],
        enrolled_at=datetime.now(UTC),
    )
    await asyncio.to_thread(db.save, creds)
    out(f"Enrolled as device {creds.device_id} with {len(body['accounts'])} Windows account(s).")
    out(f"Pinned server certificate SHA-256: {pin}")
    out("Assign each Windows account to a child on the dashboard.")
    return 0


def main(argv: list[str], data_dir: Path) -> int:
    args = _parse(argv)
    code = args.code
    if not code:
        if not sys.stdin.isatty():
            print("No pairing code given; use --code")
            return 2
        code = input("Pairing code: ")
    if not code.strip():
        print("Pairing code is empty")
        return 2
    return asyncio.run(enroll(data_dir, code.strip(), force=args.force))
