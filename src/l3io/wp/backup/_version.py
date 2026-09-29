"""The installed distribution's version, resolved at runtime.

There is no version literal in this package. ``pyproject.toml`` declares the
version ``dynamic`` with ``source = "vcs"``, so the tag is the single source and
``hatch-vcs`` resolves it at build time into the distribution metadata. This
module reads that metadata back, which keeps ``__version__`` importable without
reintroducing a second value that could disagree with the tag.

Deliberately NOT a generated file. A ``_version.py`` written by the build would
be absent from a fresh clone and from an editable install done before the first
build, so anything importing it would fail in exactly the situation a new
contributor hits first.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _dist_version

__all__ = ["__version__"]

#: Sentinel for "running from a tree that was never installed". It is a valid
#: PEP 440 version and sorts BELOW every real release, so a build that somehow
#: escapes with it cannot outrank a published one -- the same reasoning as the
#: 0.1.devN fallback for an untagged tree: wrong in the safe direction.
_UNKNOWN = "0.0.0+unknown"

try:
    __version__: str = _dist_version("l3io-wp-backup")
except PackageNotFoundError:  # pragma: no cover - only when not installed
    __version__ = _UNKNOWN
