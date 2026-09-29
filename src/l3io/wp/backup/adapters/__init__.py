"""Real implementations of the ports: subprocess, filesystem, tar, crypto.

May import ``domain/``, ``ports/`` and ``core/`` (AD-1). An adapter *holds* a
core object and satisfies a Protocol; it never subclasses the core.
"""

from __future__ import annotations

__all__: list[str] = []
