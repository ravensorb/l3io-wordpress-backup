"""Invariants over the workflow files themselves, derived from the files on disk.

Each of these was a real defect in this repo, found by a sibling session reporting
it in theirs. They are tests rather than prose because a rule that lives only in a
comment gets violated by the next person to add a job -- and the whole point of
these two is that the violation is *silent*.

The scope is discovered by walking ``.github/workflows/``. It is never a list of
job names: a hand-kept roster is how a guard ends up reporting success over a set
that no longer contains what matters.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

WORKFLOWS = sorted(
    (pathlib.Path(__file__).resolve().parents[2] / ".github/workflows").glob("*.yml")
)


def _jobs(path: pathlib.Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("jobs") or {}


def test_there_are_workflows_to_check() -> None:
    """Scope assertion. Without it every test below passes over an empty set."""
    assert WORKFLOWS, "no workflow files found; the tests below would pass vacuously"


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_every_checkout_fetches_full_history(wf: pathlib.Path) -> None:
    """``actions/checkout`` defaults to depth 1 and fetches no tags.

    The version is read from git, so a shallow checkout makes setuptools-scm find
    no tags and fall back to ``0.1.dev1`` -- and the job passes GREEN with a
    misversioned artifact. There is no error anywhere, which is what makes it
    worth a test.

    Applied to every checkout rather than only the jobs that build, because a
    dynamic version means ``uv run`` builds the package: all three of this repo's
    lint-only jobs build one. Which jobs build is a fact that changes.
    """
    offenders = []
    for name, job in _jobs(wf).items():
        for i, step in enumerate(job.get("steps") or []):
            if "actions/checkout" in str(step.get("uses", "")):
                depth = (step.get("with") or {}).get("fetch-depth")
                if str(depth) != "0":
                    offenders.append(f"{name}[step {i}] fetch-depth={depth!r}")
    assert not offenders, (
        f"{wf.name}: checkout without fetch-depth: 0 -> "
        f"a shallow clone silently versions the build 0.1.dev1: {offenders}"
    )


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_no_unguarded_wheel_glob(wf: pathlib.Path) -> None:
    """``ls dist/*.whl`` assumes a set of size one and never checks it.

    With two wheels it expands to two paths and the consumer gets a nonsense
    argument; with none the glob does not expand and the literal ``dist/*.whl`` is
    passed. Neither fails where the mistake is. Comments mentioning the pattern are
    excluded, or this test would flag the comment explaining why it is banned.
    """
    offenders = []
    for name, job in _jobs(wf).items():
        for i, step in enumerate(job.get("steps") or []):
            run = str(step.get("run", ""))
            code = "\n".join(
                line for line in run.splitlines() if not line.lstrip().startswith("#")
            )
            if "ls dist/*.whl" in code:
                offenders.append(f"{name}[step {i}]")
    assert not offenders, (
        f"{wf.name}: unguarded `ls dist/*.whl` -> resolve it once and assert the "
        f"set has exactly one member: {offenders}"
    )
