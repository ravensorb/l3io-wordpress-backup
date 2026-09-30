"""AD-21 — Archives stream; nothing buffers a whole Archive.

The rule: every port that moves Archive bytes exposes a chunked or file-object
interface, never ``bytes``, and peak RSS is bounded by a constant independent
of Archive size — asserted against a fixture an order of magnitude larger than
that bound.

No such port exists yet. What this file establishes now is the **instrument**,
because an RSS assertion that cannot tell a streaming copy from a whole-file
read is worse than no assertion: it reports success over everything. So the
measurement is calibrated in both directions — a chunked copy stays under the
bound, and a deliberate whole-file read breaches it.

``test_the_real_streaming_bound_is_still_owed`` fails the moment the first
port module appears, so this placeholder cannot outlive the thing it is
standing in for.
"""

from __future__ import annotations

import resource
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PORTS = PROJECT_ROOT / "src" / "l3io" / "wp" / "backup" / "ports"

MIB = 1024 * 1024
FIXTURE_BYTES = 64 * MIB
CHUNK_BYTES = 256 * 1024

#: The bound a chunked copy must stay under, independent of fixture size.
RSS_BOUND_BYTES = 24 * MIB
#: What a whole-file read must exceed, or the instrument is not measuring.
RSS_TEETH_BYTES = 48 * MIB


def test_the_ports_directory_exists_and_has_modules() -> None:
    """Scope assertion for everything below that reads PORTS.

    PORTS is built from separate quoted path segments --
    ``SRC / "l3io" / "wp" / "backup" / "ports"`` -- which a search-and-replace over
    ``l3io/wp`` cannot reach. A namespace move would leave this pointing at a
    directory that does not exist, and a check over an absent directory finds
    nothing to complain about and passes.

    py-wpconfigr hit exactly this during the distribution rename: their equivalent
    constant silently pointed nowhere, ten parametrised tests collapsed to an empty
    set, and pytest SKIPPED them. The suite stayed green and the collected-test
    count was the only signal.
    """
    assert PORTS.is_dir(), f"AD-21 scope missing: {PORTS} does not exist"
    assert list(PORTS.glob("*.py")), f"AD-21 scope empty: no modules under {PORTS}"


def _peak_rss_bytes() -> int:
    """Peak RSS of this process. ``ru_maxrss`` is KiB on Linux, bytes on macOS."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if peak > (1 << 32) else peak * 1024


def _fixture(path: Path) -> Path:
    block = b"\xa5" * MIB
    with path.open("wb") as handle:
        for _ in range(FIXTURE_BYTES // MIB):
            handle.write(block)
    return path


def test_a_chunked_copy_stays_under_the_bound(tmp_path: Path) -> None:
    source = _fixture(tmp_path / "fixture.bin")
    before = _peak_rss_bytes()

    with source.open("rb") as src, (tmp_path / "copy.bin").open("wb") as dst:
        shutil.copyfileobj(src, dst, CHUNK_BYTES)

    growth = _peak_rss_bytes() - before
    assert growth < RSS_BOUND_BYTES, (
        f"AD-21 — a {FIXTURE_BYTES // MIB} MiB chunked copy grew peak RSS by "
        f"{growth // MIB} MiB, over the {RSS_BOUND_BYTES // MIB} MiB bound."
    )


def test_the_instrument_detects_a_whole_file_read(tmp_path: Path) -> None:
    """The teeth. Without this, the bound above could pass on a broken meter."""
    source = _fixture(tmp_path / "fixture.bin")
    before = _peak_rss_bytes()

    buffered = source.read_bytes()
    assert len(buffered) == FIXTURE_BYTES

    growth = _peak_rss_bytes() - before
    del buffered
    assert growth > RSS_TEETH_BYTES, (
        f"reading {FIXTURE_BYTES // MIB} MiB into memory grew peak RSS by only "
        f"{growth // MIB} MiB — the RSS measurement is not measuring, so the "
        f"bound in this file proves nothing."
    )


def test_the_real_streaming_bound_is_still_owed() -> None:
    """Tripwire. AD-21 binds the byte-moving ports, not ``shutil``.

    Delete this test when the first port lands, and replace this file with one
    that drives the ArchiveStore/tar ports against a fixture Archive an order
    of magnitude larger than the bound.
    """
    modules = sorted(p.name for p in PORTS.glob("*.py") if p.name != "__init__.py")
    assert modules == [], (
        f"AD-21 — ports now exist ({modules}) but this file still only measures "
        f"shutil. Write the RSS bound against the byte-moving ports."
    )
