#!/usr/bin/env python3
"""AD-1 — ``domain/`` and ``core/`` are pure.

import-linter carries the *module* prohibitions and the inward-facing layer
rule (see ``[tool.importlinter]`` in ``pyproject.toml``). It cannot see
builtins, so ``open()``, a clock read reached through a re-export such as
``from time import time``, and RNG reads are outside its reach entirely. This
AST check carries those, and repeats the module bans so the two guards fail
independently rather than one silently covering for the other.

**What this check covers**

* a module import from the forbidden list below, in any spelling —
  including ``from l3io.wp.backup import adapters``, where the forbidden
  layer is the imported *member* rather than the module;
* ``from pathlib import Path`` — ``PurePath`` and friends stay allowed, since
  they carry no I/O methods and a pure layer may legitimately name a path type;
* a call to an I/O builtin — ``open``, ``input``, ``print``, ``breakpoint``,
  ``exec``, ``eval``, ``compile``;
* a clock read or an RNG read, resolved through the file's own import aliases,
  so ``from time import time as now; now()`` is caught as readily as
  ``time.time()``.

**What this check does NOT cover, stated so the next reader keeps looking**

* an effect reached through an object handed in at runtime — a callable
  argument that happens to be ``open`` cannot be seen statically;
* ``getattr(time, "time")()`` and other dynamic attribute lookups;
* an effect inside a dependency that a pure module imports. The module bans
  are the guard for that, and they are a list; import-linter's
  ``include_external_packages`` covers the declared third-party set.

**Scope** is derived from the tree: every ``*.py`` under the pure layer
directories, found by walking them. The two layer names come from AD-1's own
text. If either directory is missing the check fails rather than reporting
success over an empty set.
"""

from __future__ import annotations

import ast
import os
import sys
from collections.abc import Iterator
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "src" / "l3io" / "wp" / "backup"

#: AD-1: "modules under core/ and domain/ import no I/O module".
PURE_LAYERS = ("domain", "core")

#: The layers a pure module may never import (AD-1, inward-facing rule).
FORBIDDEN_LAYERS = frozenset({"ports", "adapters", "cli", "api"})

#: Top-level modules a pure layer may not import, in any spelling. AD-1 names
#: subprocess, socket, shutil, tarfile and boto3; the rest are their obvious
#: siblings, listed so the guard does not depend on which I/O module a future
#: author happens to reach for.
FORBIDDEN_MODULES = frozenset(
    {
        "asyncio",
        "boto3",
        "botocore",
        "bz2",
        "cryptography",
        "ctypes",
        "dbm",
        "fileinput",
        "ftplib",
        "gzip",
        "http",
        "httpx",
        "io",
        "lzma",
        "mmap",
        "multiprocessing",
        "opentelemetry",
        "os",
        "pickle",
        "pymysql",
        "requests",
        "select",
        "selectors",
        "shelve",
        "shutil",
        "signal",
        "smtplib",
        "socket",
        "socketserver",
        "sqlite3",
        "ssl",
        "structlog",
        "subprocess",
        "tarfile",
        "tempfile",
        "threading",
        "urllib",
        "webbrowser",
        "zipfile",
    }
)

#: Sibling distributions in the same namespace. A pure layer reaching one of
#: these has left the layer, whatever the module is called.
FORBIDDEN_PREFIXES = ("l3io.wp.config", "l3io.wp.database")

#: Names importable from an otherwise-allowed module that are not pure.
FORBIDDEN_MEMBERS = {
    "pathlib": frozenset({"Path", "PosixPath", "WindowsPath"}),
}

FORBIDDEN_BUILTINS = frozenset(
    {"open", "input", "print", "breakpoint", "exec", "eval", "compile"}
)

#: Fully qualified callables that read the clock (AD-1) — the clock is a port.
CLOCK_CALLS = frozenset(
    {
        "datetime.date.fromtimestamp",
        "datetime.date.today",
        "datetime.datetime.fromtimestamp",
        "datetime.datetime.now",
        "datetime.datetime.today",
        "datetime.datetime.utcnow",
        "time.asctime",
        "time.ctime",
        "time.gmtime",
        "time.localtime",
        "time.monotonic",
        "time.monotonic_ns",
        "time.perf_counter",
        "time.perf_counter_ns",
        "time.process_time",
        "time.sleep",
        "time.strftime",
        "time.time",
        "time.time_ns",
    }
)

#: Fully qualified callables that read a source of randomness (AD-1).
RNG_CALLS = frozenset({"os.urandom", "uuid.uuid1", "uuid.uuid4"})

#: Whole modules whose every call is a randomness read.
RNG_MODULES = ("random.", "secrets.")


class Violation:
    """One failure, with the location that produced it."""

    def __init__(self, path: Path, line: int, rule: str, detail: str) -> None:
        self.path = path
        self.line = line
        self.rule = rule
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.detail}"


def _dotted(node: ast.AST) -> str | None:
    """Render a ``Name``/``Attribute`` chain as a dotted string."""
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _aliases(tree: ast.Module) -> dict[str, str]:
    """Map each locally bound import name to the fully qualified origin."""
    table: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                table[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                table[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return table


def _resolve(dotted: str, aliases: dict[str, str]) -> str:
    head, _, tail = dotted.partition(".")
    origin = aliases.get(head)
    if origin is None:
        return dotted
    return f"{origin}.{tail}" if tail else origin


def _check_imports(path: Path, tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield from _judge_module(path, node.lineno, alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                # A relative import inside the pure layer; the layer rule below
                # cannot see it, so resolve it against the package path.
                parts = path.relative_to(PACKAGE_ROOT).parts[:-1]
                base = ".".join(parts[: len(parts) - node.level + 1])
                module = f"{base}.{node.module}" if node.module else base
            else:
                module = node.module or ""
            yield from _judge_module(path, node.lineno, module)
            for alias in node.names:
                # `from l3io.wp.backup import adapters` names the layer as a
                # MEMBER, not as the module, so judging `module` alone misses
                # it entirely. Judge the member path too.
                yield from _judge_module(path, node.lineno, f"{module}.{alias.name}")
                banned = FORBIDDEN_MEMBERS.get(module, frozenset())
                if alias.name in banned:
                    yield Violation(
                        path,
                        node.lineno,
                        "AD-1 forbidden import",
                        f"`from {module} import {alias.name}` performs I/O",
                    )


def _judge_module(path: Path, line: int, module: str) -> Iterator[Violation]:
    if not module:
        return
    top = module.split(".")[0]
    if top in FORBIDDEN_MODULES:
        yield Violation(path, line, "AD-1 forbidden import", f"imports `{module}`")
    if module.startswith(FORBIDDEN_PREFIXES):
        yield Violation(path, line, "AD-1 forbidden import", f"imports `{module}`")
    tail = module.removeprefix("l3io.wp.backup.")
    if tail.split(".")[0] in FORBIDDEN_LAYERS:
        yield Violation(
            path,
            line,
            "AD-1 inward-facing import",
            f"a pure layer may not import `{module}`",
        )


def _check_calls(path: Path, tree: ast.Module) -> Iterator[Violation]:
    aliases = _aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted(node.func)
        if dotted is None:
            continue
        if "." not in dotted and dotted not in aliases and dotted in FORBIDDEN_BUILTINS:
            yield Violation(
                path, node.lineno, "AD-1 impure builtin", f"calls `{dotted}()`"
            )
            continue
        resolved = _resolve(dotted, aliases)
        if resolved in CLOCK_CALLS:
            yield Violation(
                path,
                node.lineno,
                "AD-1 clock read",
                f"calls `{resolved}()` — the clock is a port",
            )
        elif resolved in RNG_CALLS or resolved.startswith(RNG_MODULES):
            yield Violation(
                path,
                node.lineno,
                "AD-1 randomness read",
                f"calls `{resolved}()` — randomness is a port",
            )


def _pure_files() -> list[Path]:
    """Every ``*.py`` under the pure layers, derived from the tree itself."""
    files: list[Path] = []
    for layer in PURE_LAYERS:
        directory = PACKAGE_ROOT / layer
        if not directory.is_dir():
            raise SystemExit(
                f"AD-1 scope error: {directory} does not exist. The guard would "
                f"otherwise report success over an empty set."
            )
        files.extend(sorted(directory.rglob("*.py")))
    return files


def main() -> int:
    violations: list[Violation] = []
    files = _pure_files()
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(_check_imports(path, tree))
        violations.extend(_check_calls(path, tree))

    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for violation in violations:
        if in_actions:
            print(
                f"::error file={violation.path},line={violation.line}::"
                f"{violation.rule}: {violation.detail}"
            )
        print(violation, file=sys.stderr)

    if violations:
        print(
            f"\nAD-1 purity check FAILED: {len(violations)} violation(s) "
            f"across {len(files)} pure module(s).",
            file=sys.stderr,
        )
        return 1
    print(f"AD-1 purity check passed over {len(files)} pure module(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
