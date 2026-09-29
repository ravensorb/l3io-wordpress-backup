"""AD-25 — the CLI flag matrix maps to Restore Mode through one total function.

``--cleanfirst`` x ``--force`` x ``--mode`` is twelve reachable states against
six Restore Modes, and nothing said what each means. The rule is that every
reachable combination has an entry in one table in ``domain/`` and there is no
default branch.

The point of this test is where its scope comes from. It is derived from the
**argparse parser's own actions** — its ``store_true`` actions and its actions
carrying ``choices`` — so a flag added to the parser without an entry in the
table fails here, rather than falling into an implicit default that nobody
chose. A hand-kept list of flags would drift from the parser and keep
reporting success over a set that no longer contains what matters.

The restore subparser declares no flags yet, so the derived set is empty and
the table is empty. ``test_the_derivation_sees_a_flag_the_moment_one_exists``
is what keeps that from being a vacuous pass: it plants a flag on a throwaway
parser and asserts the derivation picks it up.
"""

from __future__ import annotations

import argparse
from itertools import product

from l3io.wp.backup.cli.parser import RESTORE_COMMAND, build_parser
from l3io.wp.backup.domain import flag_map

# argparse exposes no public introspection API. `_actions`, `_SubParsersAction`
# and `_StoreTrueAction` are stable across every supported version and are used
# here rather than in the package itself, so the private access stays in the
# test that needs it.


def _restore_subparser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            assert RESTORE_COMMAND in action.choices, (
                f"AD-22 freezes both subcommands; {RESTORE_COMMAND!r} is missing "
                f"from {sorted(action.choices)}"
            )
            subparser = action.choices[RESTORE_COMMAND]
            assert isinstance(subparser, argparse.ArgumentParser)
            return subparser
    raise AssertionError("the CLI parser registers no subcommands at all")


def _mode_selecting_dimensions(
    parser: argparse.ArgumentParser,
) -> dict[str, tuple[object, ...]]:
    """Derive the mode-selecting flags, and their values, from ``parser``."""
    dimensions: dict[str, tuple[object, ...]] = {}
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._HelpAction | argparse._VersionAction):  # noqa: SLF001
            continue
        if isinstance(action, argparse._StoreTrueAction):  # noqa: SLF001
            dimensions[action.dest] = (False, True)
        elif action.choices:
            dimensions[action.dest] = tuple(action.choices)
    return dimensions


def _reachable_combinations(
    dimensions: dict[str, tuple[object, ...]],
) -> set[flag_map.FlagCombination]:
    if not dimensions:
        # No mode-selecting flag exists, so there is no combination to map.
        # This branch is only reachable while the parser declares none, and
        # `test_flag_map_covers_exactly_the_parsers_mode_selecting_flags`
        # fails the moment that stops being true.
        return set()
    names = sorted(dimensions)
    return {
        tuple(sorted(zip(names, values, strict=True)))
        for values in product(*(dimensions[name] for name in names))
    }


def test_flag_map_covers_exactly_the_parsers_mode_selecting_flags() -> None:
    derived = set(_mode_selecting_dimensions(_restore_subparser(build_parser())))
    declared = set(flag_map.COVERED_FLAGS)

    assert derived == declared, (
        "AD-25 — the flag map's scope has drifted from the parser.\n"
        f"  in the parser but unmapped: {sorted(derived - declared)}\n"
        f"  mapped but not in the parser: {sorted(declared - derived)}\n"
        "Add the flag to l3io.wp.backup.domain.flag_map.COVERED_FLAGS and give "
        "every combination it creates an entry in FLAG_MAP."
    )


def test_flag_map_is_total_over_every_reachable_combination() -> None:
    dimensions = _mode_selecting_dimensions(_restore_subparser(build_parser()))
    expected = _reachable_combinations(dimensions)
    actual = set(flag_map.FLAG_MAP)

    assert actual == expected, (
        "AD-25 — the flag map is not total. There is no default branch, so "
        "every reachable combination needs an entry.\n"
        f"  unmapped combinations: {sorted(expected - actual)}\n"
        f"  entries for unreachable combinations: {sorted(actual - expected)}"
    )


def test_the_derivation_sees_a_flag_the_moment_one_exists() -> None:
    """The scope half of the guard.

    An empty derived set is indistinguishable from a broken derivation. Plant
    both flag shapes AD-25 names — a ``store_true`` and a ``choices`` option —
    on a throwaway parser and assert they are picked up.
    """
    planted = argparse.ArgumentParser()
    planted.add_argument("--cleanfirst", action="store_true")
    planted.add_argument("--mode", choices=["files", "db", "all"])

    assert _mode_selecting_dimensions(planted) == {
        "cleanfirst": (False, True),
        "mode": ("files", "db", "all"),
    }
    assert len(_reachable_combinations(_mode_selecting_dimensions(planted))) == 6
