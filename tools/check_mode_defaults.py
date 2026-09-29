#!/usr/bin/env python3
"""AD-5 — no function consuming a Restore Mode may declare a default for it.

This is the invariant that maps directly to the unconditional-``rmtree`` data
loss: ``restore()`` received ``restore_mode`` and called its sub-steps without
it, so both fell back to an ``ALLCLEAN`` default and the destruction became
unconditional. A default is what made the omission silent.

**What this check covers**

* any parameter of any ``def``/``async def`` whose annotation mentions a
  guarded type and which declares a default — positional-only, positional,
  and keyword-only alike;
* any annotated class attribute mentioning a guarded type with a value, which
  is a constructor-parameter default for a dataclass or an attrs class and so
  is the same defect wearing different syntax.

An annotation "mentions" a guarded type if the name appears anywhere in it, so
``RestoreMode``, ``domain.RestoreMode``, ``RestoreMode | None``,
``Optional[RestoreMode]`` and the string form ``"RestoreMode"`` are all caught.

**What this check does NOT cover, stated so the next reader keeps looking**

* an unannotated parameter that happens to receive a Restore Mode. Nothing
  static can see that; ``mypy --strict`` requiring full annotation on every
  public surface is the guard for it.
* a default supplied by a wrapper — ``functools.partial(f, mode=...)`` or a
  ``**kwargs`` shim — which reintroduces the defect without a syntactic
  default anywhere.
* a module-level constant used as a default at a call site.

**Scope.** The file set is derived by walking the package tree, so a new module
is covered the moment it exists. The guarded *type names* are enumerated —
they are AD-5's own text — and that is the one hand-kept list here. Widening
it is a one-line change; it is written out rather than derived because
deriving it from ``domain/`` would make the guard vacuous while ``domain/`` is
empty, which is exactly now.
"""

from __future__ import annotations

import ast
import os
import sys
from collections.abc import Iterator
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "src" / "l3io" / "wp" / "backup"

#: AD-5's own text: "any parameter annotated RestoreMode (or BackupScope)".
GUARDED_TYPES = frozenset({"RestoreMode", "BackupScope"})


def _mentions_guarded_type(annotation: ast.expr | None) -> str | None:
    """Return the guarded type named anywhere in ``annotation``, if any."""
    if annotation is None:
        return None
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name) and node.id in GUARDED_TYPES:
            return node.id
        if isinstance(node, ast.Attribute) and node.attr in GUARDED_TYPES:
            return node.attr
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                inner = ast.parse(node.value, mode="eval").body
            except SyntaxError:
                continue
            found = _mentions_guarded_type(inner)
            if found is not None:
                return found
    return None


def _defaulted_parameters(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterator[tuple[ast.arg, str]]:
    """Yield each parameter that both declares a default and names a guard."""
    args = node.args
    positional = args.posonlyargs + args.args
    # `defaults` aligns with the TAIL of the positional parameters.
    offset = len(positional) - len(args.defaults)
    for index, parameter in enumerate(positional):
        if index >= offset:
            guarded = _mentions_guarded_type(parameter.annotation)
            if guarded is not None:
                yield parameter, guarded
    for parameter, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        if default is None:
            continue
        guarded = _mentions_guarded_type(parameter.annotation)
        if guarded is not None:
            yield parameter, guarded


def _check(path: Path, tree: ast.Module) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for parameter, guarded in _defaulted_parameters(node):
                yield (
                    f"{path}:{parameter.lineno}: AD-5 defaulted mode: "
                    f"`{node.name}({parameter.arg}: ...{guarded}... = ...)` — "
                    f"a Restore Mode is resolved once and passed explicitly; "
                    f"a default is how it gets silently forgotten"
                )
        elif isinstance(node, ast.ClassDef):
            for statement in node.body:
                if not isinstance(statement, ast.AnnAssign) or statement.value is None:
                    continue
                guarded = _mentions_guarded_type(statement.annotation)
                if guarded is not None:
                    target = ast.unparse(statement.target)
                    yield (
                        f"{path}:{statement.lineno}: AD-5 defaulted mode: "
                        f"`{node.name}.{target}: ...{guarded}... = ...` — a class "
                        f"attribute default is a constructor-parameter default"
                    )


def main() -> int:
    if not PACKAGE_ROOT.is_dir():
        raise SystemExit(
            f"AD-5 scope error: {PACKAGE_ROOT} does not exist. The guard would "
            f"otherwise report success over an empty set."
        )
    files = sorted(PACKAGE_ROOT.rglob("*.py"))
    if not files:
        raise SystemExit(f"AD-5 scope error: no Python modules under {PACKAGE_ROOT}.")

    failures: list[str] = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        failures.extend(_check(path, tree))

    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for failure in failures:
        if in_actions:
            location, _, message = failure.partition(": ")
            file_name, _, line = location.rpartition(":")
            print(f"::error file={file_name},line={line}::{message}")
        print(failure, file=sys.stderr)

    if failures:
        print(
            f"\nAD-5 check FAILED: {len(failures)} defaulted mode parameter(s) "
            f"across {len(files)} module(s).",
            file=sys.stderr,
        )
        return 1
    print(f"AD-5 check passed over {len(files)} module(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
