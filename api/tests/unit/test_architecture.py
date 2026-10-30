"""Architecture rules from docs/architecture/02-architecture.md."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "lost_crypto"

FORBIDDEN_IN_DOMAIN = {"fastapi", "sqlalchemy", "ccxt", "redis", "pydantic", "celery", "httpx"}
# Pure core modules must stay framework-free as well.
PURE_CORE_FILES = ["clock.py", "ids.py", "errors.py", "money.py"]


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _violations(files: list[Path], forbidden: set[str]) -> list[str]:
    return [
        f"{f.relative_to(SRC)} imports {root}"
        for f in files
        for root in sorted(_imported_roots(f) & forbidden)
    ]


def test_domain_packages_do_not_import_frameworks() -> None:
    files = [p for d in SRC.glob("modules/*/domain") for p in d.rglob("*.py")]
    assert _violations(files, FORBIDDEN_IN_DOMAIN) == []


def test_application_packages_do_not_import_frameworks() -> None:
    files = [p for d in SRC.glob("modules/*/application") for p in d.rglob("*.py")]
    forbidden = FORBIDDEN_IN_DOMAIN - {"pydantic"}  # pydantic allowed for param schemas
    assert _violations(files, forbidden) == []


def test_pure_core_modules_do_not_import_frameworks() -> None:
    files = [SRC / "core" / name for name in PURE_CORE_FILES]
    assert _violations(files, FORBIDDEN_IN_DOMAIN) == []


def test_only_exchange_infrastructure_may_import_ccxt() -> None:
    allowed = SRC / "modules" / "exchanges" / "infrastructure"
    offenders = [
        f for f in SRC.rglob("*.py") if "ccxt" in _imported_roots(f) and allowed not in f.parents
    ]
    assert offenders == []
