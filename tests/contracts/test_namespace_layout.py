"""AD-27 — ``l3io`` and ``l3io.wp`` are a PEP 420 *native* namespace.

Three separately released distributions share the ``l3io.wp`` root. If one
ships an ``__init__.py`` at ``l3io/`` or ``l3io/wp/`` it becomes a *regular*
package, shadows the namespace, and makes its siblings unimportable — while
its own tests keep passing, because the breakage only appears when two are
installed together.

So the assertion is made three ways, because each catches a different mistake:

* in the **source tree**, which catches the file being added by hand or by a
  tool that "helpfully" creates package markers;
* in the **built wheel and sdist**, which catches a build-backend
  configuration that synthesises one — the failure the source-tree check
  cannot see;
* at **import time**, which catches an installed layout that is a regular
  package whatever the source says.

``test_namespace_coexistence.py`` carries the fourth and decisive shape — two
distributions on two ``sys.path`` entries — which is the only one of these in
which the failure AD-27 describes is actually observable.
"""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"

#: The namespace levels that must never carry a package marker (AD-27).
NAMESPACE_LEVELS = ("l3io", "l3io/wp")

#: The one ``__init__.py`` this distribution does ship, and the marker beside it.
DISTRIBUTION_ROOT = "l3io/wp/backup"


def test_no_package_marker_at_either_namespace_level_in_the_source_tree() -> None:
    offenders = [
        marker
        for level in NAMESPACE_LEVELS
        if (marker := SRC / level / "__init__.py").exists()
    ]
    assert offenders == [], (
        f"AD-27 — {offenders} shadow the PEP 420 namespace and make "
        f"l3io-wordpress-config and l3io-wp-database unimportable alongside this one."
    )


def test_the_distribution_root_is_a_real_package_in_the_source_tree() -> None:
    """The scope half of the guard: prove the tree is where we think it is."""
    assert (SRC / DISTRIBUTION_ROOT / "__init__.py").is_file()
    assert (SRC / DISTRIBUTION_ROOT / "py.typed").is_file()


def test_the_built_wheel_ships_no_namespace_package_marker(
    built_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = built_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    offenders = sorted(f"{level}/__init__.py" for level in NAMESPACE_LEVELS)
    present = sorted(name for name in offenders if name in names)
    assert present == [], f"AD-27 — the wheel {wheel.name} ships {present}"

    assert f"{DISTRIBUTION_ROOT}/__init__.py" in names, (
        f"AD-27 scope error: the wheel contains no {DISTRIBUTION_ROOT} package, "
        f"so the check above proved nothing. Members: {sorted(names)}"
    )
    assert f"{DISTRIBUTION_ROOT}/py.typed" in names, (
        "py.typed is part of the definition of done and is not in the wheel"
    )


def test_the_built_sdist_ships_no_namespace_package_marker(
    built_distributions: tuple[Path, Path],
) -> None:
    _, sdist = built_distributions
    with tarfile.open(sdist) as archive:
        # Strip the single top-level `name-version/` directory.
        names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}

    offenders = sorted(f"src/{level}/__init__.py" for level in NAMESPACE_LEVELS)
    present = sorted(name for name in offenders if name in names)
    assert present == [], f"AD-27 — the sdist {sdist.name} ships {present}"

    assert f"src/{DISTRIBUTION_ROOT}/__init__.py" in names, (
        f"AD-27 scope error: the sdist contains no src/{DISTRIBUTION_ROOT}."
    )


def test_the_installed_namespace_is_not_a_regular_package() -> None:
    import l3io
    import l3io.wp

    assert l3io.__file__ is None, (
        f"AD-27 — `l3io` resolved to a regular package at {l3io.__file__}"
    )
    assert l3io.wp.__file__ is None, (
        f"AD-27 — `l3io.wp` resolved to a regular package at {l3io.wp.__file__}"
    )
