"""Database backup and restore check (book 1 ch. 4, O4).

``backup`` runs ``pg_dump`` (custom format), records the row counts of the main tables taken
just before the dump, the file's size and SHA-256. ``restore_check`` restores a dump into a
temporary database, checks the schema version and that every main table has at least the
recorded number of rows, then drops the temporary database. A backup only counts once a restore
check of it succeeded. The dump holds the connections' credentials encrypted: without the
master key (CREDENTIAL_MASTER_KEYS) they cannot be opened, so keep both, separately.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from modules.risk_management.domain.models import BackupRecord

CHECKED_TABLES = (
    "bots",
    "orders",
    "fills",
    "audit_events",
    "exchange_connections",
    "backtest_runs",
    "candles",
)
_PREFIX = "lostcrypto-"
_SUFFIX = ".dump"


class BackupError(RuntimeError):
    pass


def libpq_url(database_url: str, database: str | None = None) -> str:
    """``postgresql+asyncpg://…`` as a plain libpq URL for pg_dump / pg_restore."""
    url = make_url(database_url).set(drivername="postgresql")
    if database is not None:
        url = url.set(database=database)
    return url.render_as_string(hide_password=False)


async def _run(*command: str) -> None:
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise BackupError(f"{command[0]} failed: {stderr.decode(errors='replace')[-500:]}")


async def table_counts(database_url: str) -> dict[str, int]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            counts: dict[str, int] = {}
            for table in CHECKED_TABLES:
                exists = await conn.scalar(text("SELECT to_regclass(:t)"), {"t": table})
                if exists is not None:
                    counts[table] = int(await conn.scalar(text(f"SELECT count(*) FROM {table}")))
            version = await conn.scalar(text("SELECT version_num FROM alembic_version"))
            return {**counts, f"alembic:{version}": 0}
    finally:
        await engine.dispose()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _target(directory: str, now: datetime) -> tuple[Path, Path]:
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir, target_dir / f"{_PREFIX}{now.strftime('%Y%m%dT%H%M%SZ')}{_SUFFIX}"


def _exists(file: str) -> bool:
    return Path(file).exists()


def _size(path: Path) -> int:
    return path.stat().st_size


def _prune(directory: Path, keep: int) -> None:
    dumps = sorted(directory.glob(f"{_PREFIX}*{_SUFFIX}"))
    for old in dumps[: max(len(dumps) - keep, 0)]:
        old.unlink()


async def backup(database_url: str, directory: str, keep: int, now: datetime) -> BackupRecord:
    target_dir, target = _target(directory, now)
    try:
        counts = await table_counts(database_url)
        await _run("pg_dump", "--format=custom", f"--file={target}", libpq_url(database_url))
    except Exception as exc:
        return BackupRecord("backup", now, False, str(target), detail=str(exc)[:500])
    _prune(target_dir, keep)
    return BackupRecord(
        "backup",
        now,
        True,
        str(target),
        _size(target),
        _sha256(target),
        json.dumps(counts),
    )


def _compare(recorded: dict[str, Any], restored: dict[str, int]) -> list[str]:
    problems = [
        f"schema version differs ({key})"
        for key in recorded
        if key.startswith("alembic:") and key not in restored
    ]
    for table, count in recorded.items():
        if table.startswith("alembic:"):
            continue
        if restored.get(table, -1) < count:
            problems.append(f"{table}: {restored.get(table)} rows restored, {count} expected")
    return problems


async def restore_check(database_url: str, record: BackupRecord, now: datetime) -> BackupRecord:
    """Restore ``record``'s dump into a throwaway database and compare it with the counts."""
    if record.file is None or not _exists(record.file):
        return BackupRecord("restore_check", now, False, record.file, detail="dump file missing")
    if record.checksum is not None and _sha256(Path(record.file)) != record.checksum:
        return BackupRecord("restore_check", now, False, record.file, detail="checksum mismatch")
    scratch = f"lostcrypto_restore_{uuid4().hex[:8]}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await conn.execute(text(f'CREATE DATABASE "{scratch}"'))
        scratch_url = (
            make_url(database_url).set(database=scratch).render_as_string(hide_password=False)
        )
        await _run(
            "pg_restore",
            "--no-owner",
            "--no-privileges",
            f"--dbname={libpq_url(database_url, scratch)}",
            record.file,
        )
        restored = await table_counts(scratch_url)
        problems = _compare(json.loads(record.detail or "{}"), restored)
    except Exception as exc:
        problems = [str(exc)[:500]]
    finally:
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)'))
        await admin.dispose()
    return BackupRecord(
        "restore_check",
        now,
        not problems,
        record.file,
        detail="; ".join(problems) if problems else "restored and checked",
    )
