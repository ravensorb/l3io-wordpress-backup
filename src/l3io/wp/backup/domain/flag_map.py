"""AD-25 — the flag combination to ``(RestoreMode, OverrideSet)`` mapping.

The mapping is **total**: every reachable combination of the restore
subcommand's mode-selecting flags has an entry and there is no default branch.
``OverrideSet`` is a distinct type from ``RestoreMode``, so ``--force`` is
structurally incapable of selecting a Mode — it can only waive the FR-7
non-empty-target refusal.

Nothing is mapped yet because the restore subparser declares no flags yet.
``COVERED_FLAGS`` is checked against the parser's own actions by
``tests/contracts/test_flag_map.py``, so the first flag added without an entry
here fails CI rather than falling into an implicit default.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, TypeAlias

__all__ = ["COVERED_FLAGS", "FLAG_MAP", "FlagCombination"]

#: One reachable flag combination, as ``(dest, value)`` pairs sorted by ``dest``.
FlagCombination: TypeAlias = tuple[tuple[str, object], ...]

#: The ``dest`` names of the restore flags this table maps. Asserted equal to
#: the set derived from the parser itself.
COVERED_FLAGS: Final[frozenset[str]] = frozenset()

#: The total mapping. Empty only while ``COVERED_FLAGS`` is empty.
FLAG_MAP: Final[Mapping[FlagCombination, object]] = MappingProxyType({})
