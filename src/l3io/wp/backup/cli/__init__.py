"""The argparse composition root.

Binds adapters, creates the Run Context (AD-16), configures ``structlog``
(AD-10) and translates errors to the exit-code table (FR-21). None of that
exists yet: this stage ships the packaging skeleton and the contract gates
only, so the entry point resolves, reports its version, and refuses anything
else rather than pretending to act.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from l3io.wp.backup.cli.parser import build_parser

__all__ = ["main", "run_from_cli"]


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv`` and dispatch. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action is None:
        parser.print_help(sys.stderr)
        return 2
    parser.error(f"{args.action!r} is not implemented in this build")


def run_from_cli() -> None:
    """Console-script entry point."""
    raise SystemExit(main())
