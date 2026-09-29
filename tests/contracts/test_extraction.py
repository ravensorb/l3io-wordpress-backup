"""AD-11 — an Archive is untrusted input.

The rule: one extraction function in ``adapters/``, used by every restore
path, passing ``filter='data'`` explicitly wherever the interpreter supports
it and refusing outright where it does not. Containment is re-checked after
member-path rewriting.

That adapter does not exist yet, so this file cannot test it. What it can and
does test today is the **mechanism AD-11 mandates**, on every Python in the CI
matrix: that ``filter='data'`` actually refuses a traversing member here, and
that the refusal is not an artefact of the fixture being harmless — the same
archive is shown to escape without the filter.

``test_the_real_containment_test_is_still_owed`` fails the moment the first
adapter module appears, so this placeholder cannot outlive the thing it is
standing in for.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = PROJECT_ROOT / "src" / "l3io" / "wp" / "backup" / "adapters"

ESCAPING_MEMBER = "../escape.txt"
PAYLOAD = b"this must never be written outside the destination\n"


def _archive_with_a_traversing_member(path: Path) -> Path:
    with tarfile.open(path, "w") as archive:
        info = tarfile.TarInfo(ESCAPING_MEMBER)
        info.size = len(PAYLOAD)
        archive.addfile(info, io.BytesIO(PAYLOAD))
    return path


def test_the_interpreter_provides_the_data_filter() -> None:
    """AD-11's preferred path, asserted per interpreter rather than assumed.

    ``filter=`` is only patch-level-dependent on 3.11 via backport, which is
    why AD-11 guards it with ``hasattr`` instead of passing it unconditionally.
    If this ever fails on a matrix leg, that leg must take the refusal path —
    it is not licence to fall back to ``fully_trusted``.
    """
    assert hasattr(tarfile, "data_filter")


def test_the_data_filter_refuses_a_traversing_member(tmp_path: Path) -> None:
    archive_path = _archive_with_a_traversing_member(tmp_path / "evil.tar")
    destination = tmp_path / "destination"
    destination.mkdir()

    with tarfile.open(archive_path) as archive, pytest.raises(tarfile.FilterError):
        archive.extractall(destination, filter="data")

    assert not (tmp_path / "escape.txt").exists()


def test_the_fixture_really_does_escape_without_the_filter(tmp_path: Path) -> None:
    """The teeth of the test above: prove the archive is genuinely hostile."""
    archive_path = _archive_with_a_traversing_member(tmp_path / "evil.tar")
    destination = tmp_path / "destination"
    destination.mkdir()

    with tarfile.open(archive_path) as archive:
        # Deliberately unsafe: this is what AD-11 forbids, called here only
        # to prove the fixture above is genuinely hostile.
        archive.extractall(destination, filter="fully_trusted")  # noqa: S202

    escaped = tmp_path / "escape.txt"
    assert escaped.is_file(), (
        "the fixture did not traverse, so the refusal above proved nothing"
    )
    assert escaped.read_bytes() == PAYLOAD


def test_the_real_containment_test_is_still_owed() -> None:
    """Tripwire. AD-11 binds the adapter, not the stdlib.

    Delete this test when the extraction adapter lands, and replace this file
    with one that drives that adapter: containment re-checked after member-path
    rewriting, against the enumerated member roles of AD-6.
    """
    modules = sorted(p.name for p in ADAPTERS.glob("*.py") if p.name != "__init__.py")
    assert modules == [], (
        f"AD-11 — adapters now exist ({modules}) but this file still only tests "
        f"the stdlib. Write the containment test against the extraction adapter."
    )
