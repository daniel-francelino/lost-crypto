"""Operator commands. The first admin cannot be created through the API (nobody can log in
yet), so it is created here, on the machine that runs the backend:

    python -m manage create-user admin --role admin
    docker compose exec api python -m manage create-user admin --role admin
    make create-admin

``trend-study`` runs the trend detector validation (public candles, no credentials):

    python -m manage trend-study BTC/USDT:USDT --since 2020-01-01
"""

import argparse
import asyncio
import getpass
import sys
from datetime import UTC, datetime

from container import Container, build_container
from core.config import get_settings
from core.errors import DomainError
from modules.auth.domain import Role
from modules.backtesting.domain.trend_validation import format_report, validate_candles
from modules.market_data.domain.models import Candle, Timeframe
from modules.market_data.domain.trend import TrendFrame
from modules.risk_management.domain.models import BackupRecord
from modules.risk_management.infrastructure import backup


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


async def _record(container: Container, record: BackupRecord) -> None:
    async with container.trading_stores() as store:
        await store.flags.add_backup_record(record)
        await store.commit()


async def _backup() -> int:
    """pg_dump the database into BACKUP_DIR and record it (book 1 ch. 4, O4)."""
    settings = get_settings()
    container = build_container(settings)
    try:
        record = await backup.backup(
            settings.database_url, settings.backup_dir, settings.backup_keep, container.clock.now()
        )
        await _record(container, record)
    finally:
        await container.engine.dispose()
    print(f"backup {'OK' if record.ok else 'FAILED'}: {record.file} {record.detail or ''}"[:300])
    return 0 if record.ok else 1


async def _restore_check() -> int:
    """Restore the latest backup into a throwaway database and compare row counts."""
    settings = get_settings()
    container = build_container(settings)
    try:
        async with container.trading_stores() as store:
            latest = await store.flags.latest_backup_record("backup")
        if latest is None or not latest.ok:
            print("no successful backup to check; run `python -m manage backup` first")
            return 1
        record = await backup.restore_check(settings.database_url, latest, container.clock.now())
        await _record(container, record)
    finally:
        await container.engine.dispose()
    print(f"restore check {'OK' if record.ok else 'FAILED'}: {record.detail}")
    return 0 if record.ok else 1


async def _trend_study(
    symbol: str, exchange_id: str, since: datetime, frames: list[TrendFrame], simulations: int
) -> int:
    """Fetch 1h candles (paged) and print the study of how well the trend detector works."""
    from modules.exchanges.infrastructure.catalog import build_exchange_registry

    registry = build_exchange_registry(get_settings().enabled_exchange_ids)
    try:
        source = registry.market_data(exchange_id)
        candles: list[Candle] = []
        cursor, now = since, datetime.now(UTC)
        while cursor < now:
            page = await source.fetch_candles(symbol, Timeframe.H1, cursor, 1000)
            if not page:
                break
            candles += [c for c in page if c.close_time <= now]
            cursor = page[-1].open_time + Timeframe.H1.delta
            if len(page) < 2:
                break
        if not candles:
            print("No candles returned for that symbol.", file=sys.stderr)
            return 1
        print(
            f"{len(candles)} hourly candles, {candles[0].open_time:%Y-%m-%d} to "
            f"{candles[-1].open_time:%Y-%m-%d}",
            file=sys.stderr,
        )
        results = validate_candles(candles, frames, null_simulations=simulations)
        print(format_report(symbol, results, since))
        return 0
    finally:
        await registry.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(prog="manage")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="create a user (prompts for the password)")
    create.add_argument("username")
    create.add_argument("--role", choices=[r.value for r in Role], default=Role.ADMIN.value)
    sub.add_parser("backup", help="dump the database into BACKUP_DIR and record it")
    sub.add_parser("restore-check", help="restore the latest backup in a scratch DB and check it")
    study = sub.add_parser("trend-study", help="validate the trend detector on real candles")
    study.add_argument("symbol", help="e.g. BTC/USDT:USDT")
    study.add_argument("--exchange", default="binance-usdm")
    study.add_argument("--since", default="2020-01-01", help="first day, YYYY-MM-DD")
    study.add_argument(
        "--frames", default="1h,4h,1d,1w", help="comma separated: 1h,4h,1d,1w (or week, day...)"
    )
    study.add_argument("--null-simulations", type=int, default=20)
    args = parser.parse_args()
    if args.command == "trend-study":
        return asyncio.run(
            _trend_study(
                args.symbol,
                args.exchange,
                datetime.fromisoformat(args.since).replace(tzinfo=UTC),
                [TrendFrame.parse(f) for f in args.frames.split(",")],
                args.null_simulations,
            )
        )
    if args.command == "backup":
        return asyncio.run(_backup())
    if args.command == "restore-check":
        return asyncio.run(_restore_check())
    return asyncio.run(_create_user(args.username, Role(args.role)))


if __name__ == "__main__":
    raise SystemExit(main())
