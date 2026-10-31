"""Operator commands. The first admin cannot be created through the API (nobody can log in
yet), so it is created here, on the machine that runs the backend:

    python -m manage create-user admin --role admin
    docker compose exec api python -m manage create-user admin --role admin
    make create-admin
"""

import argparse
import asyncio
import getpass
import sys

from container import build_container
from core.config import get_settings
from core.errors import DomainError
from modules.auth.domain import Role


async def _create_user(username: str, role: Role) -> int:
    container = build_container(get_settings())
    try:
        password = getpass.getpass("Password (min 12 characters): ")
        if password != getpass.getpass("Repeat the password: "):
            print("The passwords do not match.", file=sys.stderr)
            return 1
        user = await container.auth.create_user(username, password, role, actor="cli")
        print(f"Created {user.role.value} {user.username!r} ({user.id})")
        return 0
    except DomainError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        await container.engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(prog="manage")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="create a user (prompts for the password)")
    create.add_argument("username")
    create.add_argument("--role", choices=[r.value for r in Role], default=Role.ADMIN.value)
    args = parser.parse_args()
    return asyncio.run(_create_user(args.username, Role(args.role)))


if __name__ == "__main__":
    raise SystemExit(main())
