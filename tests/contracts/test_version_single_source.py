"""The git tag is the version, and the arrangement that makes that true is intact.

There is no version literal in this distribution -- not in ``pyproject.toml``, not
in the source. ``hatch-vcs`` resolves the tag at build time and
``l3io.wp.backup._version`` reads it back out of installed metadata.

That makes the PyPA agreement test (``__version__`` vs
``importlib.metadata.version``) close to vacuous here: with one source they cannot
disagree. So these tests assert the **arrangement** instead, because the realistic
regression is someone reintroducing a literal -- which hatchling accepts without
complaint.

Every assertion below was attack-tested with a planted violation.
"""

from __future__ import annotations

import pathlib
import re
import tomllib

import pytest

from l3io.wp import backup

ROOT = pathlib.Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
DATA = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_version_is_dynamic_with_no_literal() -> None:
    project = DATA["project"]
    assert "version" in project.get("dynamic", []), (
        'pyproject.toml must declare `dynamic = ["version"]`'
    )
    assert "version" not in project, (
        "pyproject.toml carries a static version literal; the tag is the source"
    )


def test_version_source_is_vcs() -> None:
    assert DATA["tool"]["hatch"]["version"]["source"] == "vcs", (
        'hatch version source must be "vcs"; a `path` source reads a literal again'
    )


def test_local_scheme_is_disabled() -> None:
    """A +g<sha> local segment is rejected outright by PyPI and most indexes."""
    raw = DATA["tool"]["hatch"]["version"]["raw-options"]
    assert raw.get("local_scheme") == "no-local-version"


def test_describe_command_matches_only_three_component_tags() -> None:
    """The least obvious line in pyproject, and the likeliest to be cut as noise.

    Without ``--match v[0-9]*.[0-9]*.[0-9]*`` a two-component tag such as ``v1.0``
    is read as the basis and setuptools-scm guesses the next MINOR -- ``1.1.devN``,
    which sorts ABOVE ``1.0.0`` in PEP 440 and would permanently outrank the real
    release. A sibling repo had exactly that tag from 2018. This repo has no tags,
    so the guard protects against the first two-component tag anyone pushes.
    """
    cmd = DATA["tool"]["hatch"]["version"]["raw-options"]["git_describe_command"]
    assert "--match" in cmd, "git_describe_command must restrict the tag pattern"
    assert re.search(r"--match\s+v\[0-9\]\*\.\[0-9\]\*\.\[0-9\]\*", cmd), (
        f"--match must pin three components; got: {cmd}"
    )


def test_no_version_literal_anywhere_in_src() -> None:
    """A literal is allowed ONLY in a module that reads importlib.metadata.

    The rule has to carve that out or it flags ``_version.py``'s own
    ``0.0.0+unknown`` sentinel and gets switched off for crying wolf -- a sibling
    session's first audit did exactly that and reported all three repos as
    carrying literals.
    """
    offenders = []
    for f in sorted((ROOT / "src").rglob("*.py")):
        text = f.read_text(encoding="utf-8")
        if not re.search(r'^\s*__version__(\s*:\s*str)?\s*=\s*["\']', text, re.M):
            continue
        if "importlib.metadata" in text:
            continue  # reads metadata; the literal is a fallback sentinel
        offenders.append(f.relative_to(ROOT).as_posix())
    assert not offenders, (
        f"version literal outside a metadata-reading module: {offenders}"
    )


def test_version_module_exposes_a_pep440_version() -> None:
    assert isinstance(backup.__version__, str)
    assert backup.__version__
    assert not backup.__version__.startswith("v"), "a v prefix is a tag, not a version"


@pytest.mark.parametrize("sentinel", ["0.0.0+unknown"])
def test_sentinel_sorts_below_every_release(sentinel: str) -> None:
    """Documents why the fallback is that value and not something friendlier."""
    from packaging.version import Version

    assert Version(sentinel) < Version("0.1.dev0")
