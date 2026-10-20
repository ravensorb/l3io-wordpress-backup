"""ADR-0015 — credentials reach MySQL client tools only through l3io-wp-database.

This package never invokes ``mysqldump``, ``mysql``, ``mariadb-dump`` or
``mariadb`` itself: database's ``dump``/``load`` do, with credentials passed
through a pipe option file. A second transport here would be a second
implementation of AD-7's guarantee, tested against nothing.

The check is on string literals naming a client binary, anywhere in the
package source. It cannot see a name assembled at runtime; review covers that.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = PROJECT_ROOT / "src" / "l3io" / "wp" / "backup"

CLIENTS = {"mysqldump", "mysql", "mariadb-dump", "mariadb", "mysqladmin", "mysqlpump"}


def _literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_the_package_has_source_to_check() -> None:
    """Scope assertion. Without it the test below passes over an empty set."""
    assert any(PACKAGE.rglob("*.py")), f"no Python source under {PACKAGE}"


def test_no_module_names_a_mysql_client_binary() -> None:
    offenders = sorted(
        f"{path.relative_to(PROJECT_ROOT)}: {name!r}"
        for path in PACKAGE.rglob("*.py")
        for literal in _literals(path)
        for name in CLIENTS
        if literal == name or literal.startswith((f"{name} ", f"/usr/bin/{name}"))
    )
    assert not offenders, (
        "call l3io-wp-database's dump/load instead of a client binary "
        f"(ADR-0015): {offenders}"
    )
