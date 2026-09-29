"""``l3io.wp.backup`` — WordPress backup, restore and relocation.

This is the package root of the ``l3io-wp-backup`` distribution. ``l3io`` and
``l3io.wp`` are a **PEP 420 native namespace** shared with ``l3io-wp-config``
and ``l3io-wp-database``; neither carries an ``__init__.py`` (AD-27), and
``tests/contracts/test_namespace_layout.py`` asserts that, in the source tree
and in the built wheel.

The public surface is declared by ``__all__`` (spine, Consistency
Conventions). It is deliberately minimal at this stage: the packaging skeleton
and its contract gates land before any behaviour, so that every gate is proven
to fire before there is anything for it to catch.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "1.0.0"
