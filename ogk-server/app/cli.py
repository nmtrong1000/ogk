"""seed-dev fills an empty development DB with sample accounts, children, policies, a sample device, events
and alerts (see app/seed.py). It needs OGK_SEED_PASSWORD, which becomes the password of every seed account.
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

from app.core.config import ConfigError, get_settings
from app.core.crypto import generate_key
from app.core.db import get_engine, get_sessionmaker, utcnow
from app.core.errors import AppError
from app.core.signing import generate_key_pair
from app.modules.auth import service
from app.modules.auth.models import ROLE_ADMIN
from app.seed import seed

MESSAGES = {
    "invalid_email": "Invalid email",
    "password_too_short": f"Password must be at least {service.MIN_PASSWORD_LENGTH} characters",
    "password_too_long": f"Password must be at most {service.MAX_PASSWORD_LENGTH} characters",
    "email_taken": "Email is already registered",
}


async def create_admin(email: str, password: str) -> None:
    try:
        async with get_sessionmaker()() as db:
            account = await service.create_account(db, email, password, role=ROLE_ADMIN)
            print(f"Created admin {account.email} (id {account.id})")
    finally:
        await get_engine().dispose()


async def seed_dev(password: str, pairing_code: bool) -> None:
    try:
        async with get_sessionmaker()() as db:
            report = await seed(db, password, utcnow(), pairing_code)
    finally:
        await get_engine().dispose()
    if not report.created:
        print("Seed data already present; nothing created")
    else:
        print(f"Accounts (password from OGK_SEED_PASSWORD): {', '.join(report.accounts)}")
        for email, names in report.children.items():
            print(f"Children of {email}: {', '.join(names)}")
        for name in report.devices:
            print(f"Sample device (cannot connect): {name}")
        print(f"Sample events: {report.events}")
    if report.pairing_code:
        print(f"Pairing code for the first parent, valid 10 minutes: {report.pairing_code}")


def run_seed(pairing_code: bool) -> int:
    try:
        password = get_settings().seed_password
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 1
    if password is None or not password.get_secret_value():
        print("Set OGK_SEED_PASSWORD to the password for the seed accounts", file=sys.stderr)
        return 1
    try:
        asyncio.run(seed_dev(password.get_secret_value(), pairing_code))
    except AppError as exc:
        print(MESSAGES.get(exc.code, exc.code), file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-admin", help="Create an admin account")
    create.add_argument("email")
    commands.add_parser("gen-data-key", help="Generate a new AES-GCM key for OGK_DATA_KEY")
    policy_key = commands.add_parser("gen-policy-key", help="Generate the Ed25519 key pair that signs policies")
    policy_key.add_argument("--out", type=Path, default=Path("certs/out"))
    seed_cmd = commands.add_parser("seed-dev", help="Fill a development DB with sample data")
    seed_cmd.add_argument("--pairing-code", action="store_true", help="also print a pairing code for the first parent")
    args = parser.parse_args(argv)

    if args.command == "seed-dev":
        return run_seed(args.pairing_code)

    if args.command == "gen-data-key":
        print(generate_key())
        return 0

    if args.command == "gen-policy-key":
        try:
            private_path, public_path = generate_key_pair(args.out)
        except FileExistsError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"Private key: {private_path} (set OGK_POLICY_SIGNING_KEY to this path)")
        print(f"Public key: {public_path} (give to the agent installer)")
        return 0

    password = getpass.getpass("Password: ")
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match", file=sys.stderr)
        return 1
    try:
        asyncio.run(create_admin(args.email, password))
    except AppError as exc:
        print(MESSAGES.get(exc.code, exc.code), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
