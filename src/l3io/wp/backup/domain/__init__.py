"""Pure value objects, closed enumerations and plan types.

Imports stdlib only (AD-1). Purity beyond import-linter's reach — ``open()``,
clock reads and RNG reads — is enforced by ``tools/check_purity.py``.
"""

from __future__ import annotations

__all__: list[str] = []
