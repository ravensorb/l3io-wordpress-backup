"""AD-27 — the namespace must merge across separately installed distributions.

AD-27's enforcement clause requires a **stub sibling**: a throwaway
distribution claiming the same ``l3io.wp`` root, proving coexistence today
rather than waiting for ``l3io-wordpress-config`` and ``l3io-wp-database`` to be
installable beside this one.

**Why this file exists separately from ``test_namespace_layout.py``, and why it
uses two path entries.** Measured while building this skeleton: with an
``__init__.py`` planted at ``l3io/wp/`` in *this* distribution's wheel, and
both wheels installed into one ``site-packages``, the sibling **still
imported** — because both distributions unpack into the same directory, so the
regular package's single ``__path__`` entry happens to contain the sibling's
subdirectory too. The breakage appears only when the two distributions occupy
**different ``sys.path`` entries** — an editable install beside a wheel, a
``--target`` directory, a second site directory. A coexistence check that only
covered "two wheels in one interpreter" would therefore report success over a
set that cannot contain the failure.

So this check places the two distributions on two path entries, and
``test_the_check_would_catch_the_violation`` plants the marker to prove the
arrangement has teeth.

Everything happens against the **built wheel's real members** in a subprocess
with an explicit ``sys.path``; no installer, no network, no venv.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

STUB_MODULE = "l3io/wp/stub/__init__.py"
STUB_MARKER = "stub sibling imported"

PROBE = """
import l3io
import l3io.wp
from l3io.wp import backup, stub

assert l3io.__file__ is None, f"l3io is a regular package at {l3io.__file__}"
assert l3io.wp.__file__ is None, f"l3io.wp is a regular package at {l3io.wp.__file__}"
print("OK", backup.__version__, stub.MARKER)
for entry in l3io.wp.__path__:
    print("PATH", entry)
"""


def _unpack_distribution_tree(wheel: Path, destination: Path) -> Path:
    """Unpack the wheel's importable members, as an installer would place them."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if ".dist-info/" in name or ".data/" in name:
                continue
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    return destination


def _stub_sibling_tree(destination: Path) -> Path:
    """The throwaway sibling distribution AD-27's enforcement clause calls for."""
    module = destination / STUB_MODULE
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text(f'MARKER = "{STUB_MARKER}"\n', encoding="utf-8")
    return destination


def _import_both(entries: list[Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", PROBE],
        env={"PYTHONPATH": ":".join(str(entry) for entry in entries)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_two_distributions_on_two_path_entries_both_import(
    built_distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    wheel, _ = built_distributions
    ours = _unpack_distribution_tree(wheel, tmp_path / "site-ours")
    theirs = _stub_sibling_tree(tmp_path / "site-theirs")

    result = _import_both([ours, theirs])

    assert result.returncode == 0, (
        f"AD-27 — this distribution does not coexist with a sibling claiming the "
        f"same namespace.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.stdout.startswith("OK "), result.stdout

    # Both entries must be merged into the namespace, not just one. Naming them
    # rather than counting: the interpreter running the tests carries its own
    # editable entry, so a count would pass for the wrong reason.
    merged = {
        line.removeprefix("PATH ")
        for line in result.stdout.splitlines()
        if line.startswith("PATH ")
    }
    for expected in (ours / "l3io" / "wp", theirs / "l3io" / "wp"):
        assert str(expected) in merged, (
            f"AD-27 — {expected} was not merged into l3io.wp.__path__: {merged}"
        )


def test_the_check_would_catch_the_violation(
    built_distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    """The teeth. Plant the package marker AD-27 forbids and require a failure."""
    wheel, _ = built_distributions
    ours = _unpack_distribution_tree(wheel, tmp_path / "site-ours")
    theirs = _stub_sibling_tree(tmp_path / "site-theirs")

    (ours / "l3io" / "wp" / "__init__.py").write_text("", encoding="utf-8")

    result = _import_both([ours, theirs])

    assert result.returncode != 0, (
        "AD-27 — an `__init__.py` at l3io/wp/ did not break the sibling, so the "
        "test above proves nothing about the invariant."
    )
    assert "stub" in result.stderr, (
        f"the failure was not the sibling becoming unimportable: {result.stderr}"
    )
