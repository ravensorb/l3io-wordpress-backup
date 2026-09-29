"""The argparse parser — the single source of truth for the CLI surface.

AD-22 freezes that surface: both subcommands, all nineteen flag spellings
(including the camelCase ``--whatIf``), and ``python -m wpbackup2`` as a
working invocation. This module is deliberately incomplete at this stage: the
packaging skeleton and its contract gates land first, so that AD-25's gate is
proven to fire *before* there is a flag for it to catch.

AD-25's contract test derives its scope from this parser rather than from a
hand-kept list, so a flag added here without an entry in
``l3io.wp.backup.domain.flag_map`` fails CI.
"""

from __future__ import annotations

import argparse

from l3io.wp.backup import __version__

__all__ = ["BACKUP_COMMAND", "RESTORE_COMMAND", "build_parser"]

BACKUP_COMMAND = "backup"
RESTORE_COMMAND = "restore"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser with both frozen subcommands registered."""
    parser = argparse.ArgumentParser(
        prog="wpbackup2",
        description="Backup/restore your WordPress content and database.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="action", help="Action being requested")
    subparsers.add_parser(BACKUP_COMMAND, help="Perform a WordPress backup")
    subparsers.add_parser(RESTORE_COMMAND, help="Perform a WordPress restore")
    return parser
