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


# release.yml moves floating `v<major>` / `v<major>.<minor>` tags onto every
# release commit. A bare `v*` push filter starts a publish on each of them.
FLOATING = ["v1", "v1.0", "v12", "v12.3"]
RELEASES = ["v1.0.0", "v1.2.3", "v12.0.10", "v1.0.0rc1"]


def _starts_a_run(tag: str, patterns: list[str]) -> bool:
    """GitHub's tag filter: the last matching pattern wins, ``!`` negates."""
    from fnmatch import fnmatchcase

    hit = False
    for pattern in patterns:
        if fnmatchcase(tag, pattern.removeprefix("!")):
            hit = not pattern.startswith("!")
    return hit


def _tag_patterns(wf: pathlib.Path) -> list[str]:
    doc = yaml.safe_load(wf.read_text(encoding="utf-8"))
    # PyYAML parses a bare `on:` key as boolean True.
    on = doc.get(True, doc.get("on")) or {}
    push = (on.get("push") or {}) if isinstance(on, dict) else {}
    return list(push.get("tags") or [])


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_no_floating_tag_starts_a_workflow(wf: pathlib.Path) -> None:
    patterns = _tag_patterns(wf)
    started = [t for t in FLOATING if _starts_a_run(t, patterns)]
    assert not started, f"{wf.name} runs on floating tag(s) {started}: {patterns}"


def test_a_release_tag_still_starts_publish() -> None:
    patterns = _tag_patterns(WORKFLOWS[0].parent / "publish.yml")
    assert patterns, "publish.yml has no tag trigger -- the check above is vacuous"
    assert all(_starts_a_run(t, patterns) for t in RELEASES), patterns


def test_release_notes_never_start_from_a_floating_tag() -> None:
    """Config's v0.1.0 shipped "no changes": the builder took the floating v0.1.

    The notes builder must be told its lower bound, and that bound must come from
    a step that matches only three-component tags.
    """
    jobs = _jobs(WORKFLOWS[0].parent / "publish.yml")
    steps = (jobs.get("release") or {}).get("steps") or []
    assert steps, "publish.yml has no release job -- the check below is vacuous"
    builder = next(
        s
        for s in steps
        if "git-action-release-changelog-builder" in str(s.get("uses", ""))
    )
    from_tag = str((builder.get("with") or {}).get("from-tag", ""))
    assert "steps.previous.outputs.tag" in from_tag, f"from-tag is {from_tag!r}"
    previous = next((s for s in steps if s.get("id") == "previous"), None)
    assert previous is not None, "no step with id 'previous' computes the lower bound"
    assert "--match 'v[0-9]*.[0-9]*.[0-9]*'" in str(previous.get("run", ""))
    assert steps.index(previous) < steps.index(builder)
