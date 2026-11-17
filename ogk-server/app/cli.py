"""Lệnh quản trị chạy trên máy chủ: python -m app.cli create-admin <email>"""

import argparse
import asyncio
import getpass
import sys

from app.core.db import get_engine, get_sessionmaker
from app.core.errors import AppError
from app.modules.auth import service
from app.modules.auth.models import ROLE_ADMIN

MESSAGES = {
    "invalid_email": "Email không hợp lệ",
    "password_too_short": f"Mật khẩu phải có ít nhất {service.MIN_PASSWORD_LENGTH} ký tự",
    "password_too_long": f"Mật khẩu dài tối đa {service.MAX_PASSWORD_LENGTH} ký tự",
    "email_taken": "Email đã có tài khoản",
}


async def create_admin(email: str, password: str) -> None:
    try:
        async with get_sessionmaker()() as db:
            account = await service.create_account(db, email, password, role=ROLE_ADMIN)
            print(f"Đã tạo admin {account.email} (id {account.id})")
    finally:
        await get_engine().dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-admin", help="Tạo tài khoản admin")
    create.add_argument("email")
    args = parser.parse_args(argv)

    password = getpass.getpass("Mật khẩu: ")
    if getpass.getpass("Nhập lại mật khẩu: ") != password:
        print("Hai lần nhập mật khẩu không khớp", file=sys.stderr)
        return 1
    try:
        asyncio.run(create_admin(args.email, password))
    except AppError as exc:
        print(MESSAGES.get(exc.code, exc.code), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
