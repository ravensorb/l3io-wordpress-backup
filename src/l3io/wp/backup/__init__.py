"""``l3io.wp.backup`` — WordPress backup, restore and relocation.

This is the package root of the ``l3io-wordpress-backup`` distribution. ``l3io`` and
``l3io.wp`` are a **PEP 420 native namespace** shared with ``l3io-wordpress-config``
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

# Re-exported from _version, which reads installed distribution metadata. There
# used to be a literal here AND one in pyproject.toml, with nothing comparing
# them; the git tag is now the only source.
from l3io.wp.backup._version import __version__
