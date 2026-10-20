"""The `--ignore=tests/classes` in pytest's addopts hides only legacy tests.

An ignored directory is invisible: a rewrite test written there would never
run and never fail. So every module in it must test the legacy `wpbackup2`
package, and the ignore must name no other directory.
"""

from __future__ import annotations

import ast
import pathlib
import shlex
import tomllib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

LEGACY_DIR = PROJECT_ROOT / "tests" / "classes"


def _imported_roots(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_ignore_names_only_the_legacy_directory() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    addopts = shlex.split(pyproject["tool"]["pytest"]["ini_options"]["addopts"])
    ignored = [a.split("=", 1)[1] for a in addopts if a.startswith("--ignore")]
    assert ignored == ["tests/classes"]


def test_every_ignored_module_tests_wpbackup2() -> None:
    modules = sorted(LEGACY_DIR.rglob("test_*.py"))
    assert modules, "tests/classes/ is empty; drop the --ignore from addopts"
    hidden = [m.name for m in modules if "wpbackup2" not in _imported_roots(m)]
    assert not hidden, f"ignored but not legacy, so never run: {hidden}"


# The legacy 0.2.21 tree, and the only paths ruff may skip besides the vendored
# agent tooling. A rewrite path added to extend-exclude is never linted again.
LEGACY_PATHS = {"wpbackup2", "tests/classes", "setup.py", "test.py", "README.md"}
VENDORED_PATHS = {"_bmad", "_bmad-output", ".claude", ".agents", ".bmad"}


def test_ruff_skips_only_legacy_and_vendored_paths() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    excluded = set(pyproject["tool"]["ruff"]["extend-exclude"])
    assert excluded == LEGACY_PATHS | VENDORED_PATHS


def test_legacy_python_paths_are_the_legacy_package() -> None:
    files = [PROJECT_ROOT / p for p in ("setup.py", "test.py")]
    files += sorted((PROJECT_ROOT / "wpbackup2").rglob("*.py"))
    assert all(f.is_file() for f in files)
    assert "l3io" not in set().union(*(_imported_roots(f) for f in files))
