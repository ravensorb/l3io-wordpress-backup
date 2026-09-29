"""The version is single-sourced, and the two ways to ask agree.

PyPA's single-source discussion lists three options and states no preference, but
makes one explicit recommendation: test that ``import_name.__version__`` and
``importlib.metadata.version("dist-name")`` report the same value.
https://packaging.python.org/en/latest/discussions/single-source-version/

This repo carried TWO hand-maintained literals -- ``pyproject.toml`` and
``src/l3io/wp/backup/__init__.py`` -- with nothing comparing them. They agreed by
luck, so a ``v1.0.0`` tag would have passed the version gate and proved nothing.
``pyproject.toml`` is now ``dynamic = ["version"]`` with
``[tool.hatch.version] path`` pointing at the module, so there is one literal and
no second value to drift from.

These tests are the backstop for that arrangement being *removed*: the realistic
regression is someone replacing ``dynamic`` with a literal again, which hatchling
accepts without complaint. Verified by doing exactly that -- two of these tests
fail on it.

**What these tests do NOT prove, stated plainly.** Now that there is one literal,
changing it changes both the attribute and the metadata together, so they cannot
disagree: an attempt to drift them by editing the module produced a matching
wheel and all tests passed. That is single-sourcing working, not a gap -- but it
means ``test_attribute_and_metadata_agree`` is a regression guard for the
arrangement, not a live invariant with a reachable violation. The reachable
violations are the ones in the two structural tests.
"""

from __future__ import annotations

import pathlib
import tomllib
from importlib.metadata import version as dist_version

import pytest

from l3io.wp import backup

DIST = "l3io-wp-backup"
PYPROJECT = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_attribute_and_metadata_agree() -> None:
    """The PyPA-recommended assertion.

    Compares the module attribute (a literal) against installed distribution
    metadata (what the build backend resolved). Only these two together exercise
    both mechanisms; comparing the literal to itself would pass vacuously.
    """
    assert backup.__version__ == dist_version(DIST)


def test_pyproject_declares_version_dynamic() -> None:
    """There is no second literal to drift from.

    Asserted structurally rather than by comparing two values: if a literal comes
    back, single-sourcing has been undone, and a comparison test would then start
    passing again as soon as the two happened to match.
    """
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data["project"]
    assert "version" in project.get("dynamic", []), (
        "pyproject.toml must declare version dynamic; a static `version = ...` "
        "reintroduces the second literal this test exists to prevent"
    )
    assert "version" not in project, (
        "pyproject.toml carries a static version AND dynamic; hatchling rejects "
        "this at build time, but fail here with a clearer reason"
    )


def test_hatch_version_points_at_a_file_that_defines_version() -> None:
    """The configured path exists and actually holds the literal.

    Reachability, recorded honestly: a *wrong* path is caught by hatchling itself
    at build time with `OSError: Error getting the version from source regex`, so
    this test never sees that case in a normal run -- verified by pointing the
    path at a nonexistent file. What it does catch is `[tool.hatch.version]` being
    deleted entirely, which is half of the realistic regression below.
    """
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    hatch_version = data.get("tool", {}).get("hatch", {}).get("version")
    assert hatch_version is not None, (
        "[tool.hatch.version] is missing; with `dynamic = [\"version\"]` the build "
        "has no version source, and without dynamic there is a second literal again"
    )
    rel = hatch_version["path"]
    src = PYPROJECT.parent / rel
    assert src.is_file(), f"[tool.hatch.version] path does not exist: {rel}"
    text = src.read_text(encoding="utf-8")
    assert "__version__" in text, f"{rel} defines no __version__ for hatchling to read"


@pytest.mark.parametrize("bad", ["", "v1.0.0", "1.0", "latest"])
def test_version_is_pep440_ish(bad: str) -> None:
    """The real version is not one of the shapes that quietly break a publish."""
    assert backup.__version__ != bad
