#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Emit the act dry-run legs as TSV: workflow, event, act arguments.

A separate script rather than a Python one-liner inside the Makefile recipe. The
one-liner version failed with `IndentationError: unexpected indent` because make's
tab indentation leaked into the Python source -- leg expansion is logic, and logic
in a recipe is where that goes wrong.

Reads .github/act-dryrun-legs.json, whose completeness against the workflows' own
triggers and choice options is asserted by
tests/contracts/test_act_dryrun_legs.py.
"""

import json
import pathlib
import sys

TABLE = pathlib.Path(__file__).resolve().parents[1] / ".github" / "act-dryrun-legs.json"


def main() -> int:
    if not TABLE.is_file():
        print(f"missing {TABLE}", file=sys.stderr)
        return 2
    data = json.loads(TABLE.read_text(encoding="utf-8"))
    legs = data.get("legs") or []
    if not legs:
        print("the leg table is empty; refusing to report success", file=sys.stderr)
        return 2
    for leg in legs:
        if leg.get("payload"):
            args = f"-e {leg['payload']}"
        else:
            args = " ".join(f"--input {k}={v}" for k, v in (leg.get("inputs") or {}).items())
        print(f"{leg['workflow']}\t{leg['event']}\t{args}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
