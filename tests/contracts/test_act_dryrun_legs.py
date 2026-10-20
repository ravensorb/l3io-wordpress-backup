"""The act dry-run leg table is COMPLETE against what the workflows declare.

A dry run only validates the jobs the **event reaches**, and a job that is skipped
never has its ``uses:`` refs resolved. Measured in this repo: with a nonexistent
action ref planted in publish.yml's ``release`` job, ``workflow_dispatch
target=testpypi`` exits **0** and reports success, while a tag-push payload exits
**1** and names the bad ref. So one leg per workflow is not a gate -- it is a false
green, and it was false at exactly the job where a bad ref actually lived.

These tests derive the required legs from the **workflow files themselves** and
compare them against ``.github/act-dryrun-legs.json``. That is the point of the
table being data rather than a list inside the Makefile recipe: a recipe plus a
test hardcoding the expected legs would drift from the workflows, and the drift
would be silent.

No Docker needed, so completeness is checked in ``make check``; only the dry run
itself is slow.
"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
WF_DIR = ROOT / ".github" / "workflows"
TABLE = ROOT / ".github" / "act-dryrun-legs.json"


def _table() -> dict:
    return json.loads(TABLE.read_text(encoding="utf-8"))


def _triggers(path: pathlib.Path) -> dict:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc.get(True, doc.get("on")) or {}


def _covered() -> set[tuple[str, str]]:
    return {(leg["workflow"], leg["event"]) for leg in _table()["legs"]}


def test_the_table_exists_and_has_legs() -> None:
    """Scope assertion. Every test below would pass over an empty table."""
    assert TABLE.is_file(), f"{TABLE} is missing"
    assert _table()["legs"], "the leg table is empty; the tests below prove nothing"


def test_there_are_workflows_to_compare_against() -> None:
    """The OTHER half of the scope, and it was missing.

    Two tests below are parametrised over ``WF_DIR.glob("*.yml")``. pytest treats
    an empty parametrisation as a **SKIP**, not a failure, so with no workflow
    files they vanish and the suite stays green -- and
    ``test_every_workflow_is_either_covered_or_explicitly_excluded`` also passes,
    because the unclassified set is empty too.

    Demonstrated by moving the workflow files aside: 39 passed became 28 passed
    with 4 skipped and, before this assertion existed here, nothing red. Eleven
    tests disappeared and the count was the only signal. Reported by
    py-wpconfigr, who lost ten the same way.
    """
    assert WF_DIR.is_dir(), f"{WF_DIR} does not exist"
    assert list(WF_DIR.glob("*.yml")), (
        "no workflow files, so the parametrised tests below would SKIP rather than "
        "fail and the coverage tests would pass over an empty set"
    )


def test_every_workflow_is_either_covered_or_explicitly_excluded() -> None:
    """A workflow added later must be classified, not silently unvalidated."""
    table = _table()
    excluded = set(table.get("excluded", {}))
    covered = {w for w, _ in _covered()}
    on_disk = {p.name for p in WF_DIR.glob("*.yml")}
    unclassified = on_disk - covered - excluded
    assert not unclassified, (
        f"workflows neither covered by a leg nor excluded with a reason: "
        f"{sorted(unclassified)}"
    )


def test_every_exclusion_states_a_reason() -> None:
    for name, reason in _table().get("excluded", {}).items():
        assert isinstance(reason, str)
        assert len(reason) > 30, (
            f"{name} is excluded without a substantive reason; an unexplained "
            f"exclusion is how a workflow stops being checked and nobody notices"
        )


@pytest.mark.parametrize("wf", sorted(p.name for p in WF_DIR.glob("*.yml")))
def test_every_declared_trigger_has_a_leg(wf: str) -> None:
    """Each event a workflow declares must be replayed by at least one leg."""
    if wf in _table().get("excluded", {}):
        pytest.skip(f"{wf} is excluded with a stated reason")
    covered = _covered()
    for event in _triggers(WF_DIR / wf):
        assert (wf, event) in covered, (
            f"{wf} declares `on: {event}:` but no leg replays it -- the jobs that "
            f"event reaches are never dry-run, so their action refs are never resolved"
        )


@pytest.mark.parametrize("wf", sorted(p.name for p in WF_DIR.glob("*.yml")))
def test_every_choice_option_has_a_leg(wf: str) -> None:
    """A choice input gates jobs, so each option reaches a different job set."""
    if wf in _table().get("excluded", {}):
        pytest.skip(f"{wf} is excluded with a stated reason")
    wd = _triggers(WF_DIR / wf).get("workflow_dispatch") or {}
    for name, spec in (wd.get("inputs") or {}).items():
        options = spec.get("options") or []
        seen = {
            leg.get("inputs", {}).get(name)
            for leg in _table()["legs"]
            if leg["workflow"] == wf and leg["event"] == "workflow_dispatch"
        }
        missing = [o for o in options if o not in seen]
        assert not missing, (
            f"{wf} input `{name}` has options {options} with no leg for {missing}; "
            f"each option gates a different job set"
        )


def test_every_named_payload_file_exists() -> None:
    """act falls back to a synthesised default event when the file is absent.

    That is the failure worth a test: the leg still runs and still reports
    success, against the wrong event.
    """
    for leg in _table()["legs"]:
        payload = leg.get("payload")
        if payload:
            assert (ROOT / payload).is_file(), (
                f"{leg['workflow']} leg names {payload}, which does not exist -- act "
                f"would synthesise a default event and validate the wrong job set"
            )
