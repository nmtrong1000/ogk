import argparse
import asyncio
import getpass
import sys

from app.core.crypto import generate_key
from app.core.db import get_engine, get_sessionmaker
from app.core.errors import AppError
from app.modules.auth import service
from app.modules.auth.models import ROLE_ADMIN

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-admin", help="Create an admin account")
    create.add_argument("email")
    commands.add_parser("gen-data-key", help="Generate a new AES-GCM key for OGK_DATA_KEY")
    args = parser.parse_args(argv)

    if args.command == "gen-data-key":
        print(generate_key())
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
