"""Protocol definitions — the interfaces through which effects are reached.

Every port splits into queries and commands (AD-4), so a Dry Run binds real
queries and no-op commands rather than branching on a flag.
"""

from __future__ import annotations

__all__: list[str] = []
