#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Conformance check for the l3io Python-package CI/CD standard.

Checks every sibling package repo, not a hand-kept list: the scope is derived by
globbing for `pyproject.toml` + `.github/workflows/` under the parent directory.
A repo added tomorrow is checked tomorrow, without editing this file -- a
hand-maintained roster is exactly how a guard ends up reporting success over a
set that no longer contains what matters.

Exit 0 = all repos conform. Exit 1 = at least one finding.
"""
from __future__ import annotations
import sys, pathlib, argparse, re
import yaml

def load(p: pathlib.Path):
    with p.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def triggers(doc) -> dict:
    # PyYAML parses a bare `on:` key as boolean True
    return doc.get(True, doc.get("on")) or {}

def jobtext(job) -> str:
    return yaml.safe_dump(job, default_flow_style=False)

def code_only(job) -> str:
    """Job text with shell comments stripped.

    A `run:` block's comments are part of the serialized job, so a naive grep
    finds a rule's own name in the comment that says the rule is being FOLLOWED.
    That produced two false positives on the first run of this checker: a comment
    reading "not pyproject.toml, because this job has no checkout" was reported as
    reading pyproject.toml.
    """
    out = []
    for line in jobtext(job).splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith("\\n#"):
            continue
        out.append(re.sub(r"\\n\s*#[^\\]*", " ", line))
    return "\n".join(out)

def strip_comments(blob: str) -> str:
    """Remove YAML/shell comments from a serialized workflow.

    A `run:` block's comments survive serialization, so a rule that greps the blob
    finds its own subject inside the comment that says the rule is satisfied.
    """
    out = []
    for line in blob.splitlines():
        s = line.lstrip()
        if s.startswith("#"):
            continue
        out.append(re.sub(r"\\n\s*#[^\\]*", " ", line))
    return "\n".join(out)


def needs_closure(jobs: dict, start: str) -> set[str]:
    """Every job transitively reachable through `needs` from `start`."""
    seen: set[str] = set()
    stack = list(jobs.get(start, {}).get("needs") or [])
    while stack:
        n = stack.pop()
        if n in seen or n not in jobs:
            continue
        seen.add(n)
        stack += list(jobs[n].get("needs") or [])
    return seen


# ---------------------------------------------------------------- rules

def check_ci(doc, R):
    on, jobs = triggers(doc), doc.get("jobs", {})
    if "pull_request" not in on:
        R("ci", "no pull_request trigger -- CI never gates a PR")
    push = on.get("push") or {}
    if isinstance(push, dict) and "main" not in (push.get("branches") or []):
        R("ci", f"push trigger is {push.get('branches')}, expected ['main']")
    if "workflow_dispatch" not in on:
        R("ci", "no workflow_dispatch trigger -- cannot be re-run by hand")
    for j in ("static", "test", "verify-install"):
        if j not in jobs:
            R("ci", f"missing required job `{j}`")
    blob = yaml.safe_dump(doc)
    if "verify-install" in jobs and "--no-project" not in blob and "clean" not in blob.lower():
        R("ci", "verify-install present but does not look like a clean-install check")
    return blob

def check_namespace(ci_blob, pub_blob, is_ns, R):
    """AD-27: a namespace package must be guarded at BOTH ends."""
    if not is_ns:
        return
    shadow = r"__init__\.py"
    if not re.search(shadow, ci_blob):
        R("ns", "ci.yml has no AD-27 __init__.py shadow guard -- a namespace break "
                "reaches publish instead of the PR")
    # Do NOT match the word "namespace": it appears in comments, so a file saying
    # "we should check the namespace" and nothing else would pass. That is the
    # comment-stripping hazard this checker warned another repo about, in this
    # checker's own rule -- found by that repo reading it. Require the structural
    # thing a real check must mention outside a comment.
    if "__init__.py" not in strip_comments(pub_blob):
        R("ns", "publish.yml has no structural namespace assertion (no __init__.py "
                "check outside a comment) -- the word alone is not a check")

def check_version_single_source(repo: pathlib.Path, pub_blob: str, R):
    """One version literal per distribution, and an assertion that the two ways agree.

    Reported by py-wordpress-database: this family carried TWO hand-maintained
    literals per repo (pyproject.toml and the module's __version__) with nothing
    comparing them. They agreed by luck, so a tag would have gone green and proved
    nothing -- and a version gate comparing the tag to pyproject.toml alone leaves
    __version__ free to disagree with the value users see.

    PyPA states no preference among its three single-sourcing options but makes one
    explicit recommendation: assert import_name.__version__ equals
    importlib.metadata.version("dist-name").
    https://packaging.python.org/en/latest/discussions/single-source-version/
    """
    pyproject = repo / "pyproject.toml"
    if not pyproject.is_file():
        return
    try:
        import tomllib
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception as e:
        R("ver", f"pyproject.toml unreadable, so version single-sourcing was not checked: {e}")
        return
    project = data.get("project", {})
    static = "version" in project
    dynamic = "version" in (project.get("dynamic") or [])

    # Count literals in the source tree too -- a static pyproject version is only
    # half the problem; the pair is what drifts.
    src_literals = sorted(
        f.relative_to(repo).as_posix()
        for f in repo.glob("src/**/*.py")
        if re.search(r"^__version__\s*=", f.read_text(encoding="utf-8", errors="ignore"), re.M)
    )
    if static and src_literals:
        R("ver", f"TWO version literals: pyproject.toml ({project['version']}) and "
                 f"{', '.join(src_literals)} -- nothing forces them to agree")
    elif static:
        R("ver", "pyproject.toml carries a static version literal; prefer "
                 'dynamic = ["version"] with [tool.hatch.version] so there is one source')
    if dynamic and not data.get("tool", {}).get("hatch", {}).get("version"):
        R("ver", 'pyproject.toml declares dynamic = ["version"] but no [tool.hatch.version] '
                 "source -- the build has no version to read")
    if len(src_literals) > 1:
        R("ver", f"{len(src_literals)} __version__ literals in src/: {', '.join(src_literals)}")

    # The PyPA agreement assertion must exist somewhere that runs.
    if src_literals or dynamic:
        blobs = [pub_blob]
        for d in ("tests", "tools"):
            for f in (repo / d).rglob("*.py") if (repo / d).is_dir() else []:
                blobs.append(f.read_text(encoding="utf-8", errors="ignore"))
        joined = strip_comments("\n".join(blobs))
        if "importlib.metadata" not in joined and "importlib_metadata" not in joined:
            R("ver", "nothing asserts __version__ == importlib.metadata.version(dist) -- "
                     "PyPA's one explicit recommendation for single-sourcing")


def check_publish(doc, R):
    on, jobs = triggers(doc), doc.get("jobs", {})
    push = on.get("push") or {}
    if not (isinstance(push, dict) and any(t.startswith("v") for t in (push.get("tags") or []))):
        R("pub", "no `push: tags: [v*]` trigger")
    if "release" not in on:
        R("pub", "no `release: types: [published]` trigger -- cutting a release does not publish")
    wd = on.get("workflow_dispatch") or {}
    opts = (((wd.get("inputs") or {}).get("target") or {}).get("options")) or []
    for want in ("testpypi", "pypi", "mirror"):
        if want not in opts:
            R("pub", f"workflow_dispatch target option `{want}` missing (has {opts})")

    for j in ("version-gate", "build", "smoke", "publish-pypi", "publish-mirror", "release"):
        if j not in jobs:
            R("pub", f"missing required job `{j}`")

    # --- the secrets-in-if trap
    for name, job in jobs.items():
        cond = str(job.get("if", ""))
        if "secrets." in cond:
            R("pub", f"job `{name}` references `secrets` in its `if:` -- not an available "
                     "context there; it evaluates empty and SILENTLY SKIPS the job")

    # --- mirror must be gated on a preflight boolean, not on vars alone
    pre = next((n for n in jobs if n.endswith("preflight")), None)
    if pre is None:
        R("pub", "no preflight job -- mirror cannot be gated on secret presence, because "
                 "`secrets` is unavailable in a job-level `if:`")
    else:
        if pre != "preflight":
            R("pub", f"preflight job is named `{pre}`; the standard name is `preflight`")
        outs = jobs[pre].get("outputs") or {}
        if not outs:
            R("pub", f"`{pre}` declares no outputs -- nothing for the mirror to gate on")
        if "${VAR:+set}" not in jobtext(jobs[pre]) and ":+set}" not in jobtext(jobs[pre]):
            R("pub", f"`{pre}` does not use ${{VAR:+set}} -- a skip is not diagnosable "
                     "from the log without leaking a value")

    mir = jobs.get("publish-mirror")
    if mir:
        cond = str(mir.get("if", ""))
        if pre and f"needs.{pre}.outputs" not in cond:
            R("pub", "publish-mirror is not gated on the preflight output")
        if "inputs.target" not in cond and "event_name" not in cond:
            R("pub", "publish-mirror has no event/target gate -- a testpypi dry run also "
                     "publishes to the mirror")
        body = jobtext(mir)
        if "check-url" in body and "curl" not in body:
            R("pub", "mirror relies on `uv publish --check-url` for idempotence; it does not "
                     "provide it (the check gets no credentials and falls through to a 409)")
        if "curl" not in body:
            R("pub", "publish-mirror has no idempotence pre-check")
        if "pyproject" in code_only(mir):
            R("pub", "mirror derives identity from pyproject.toml; this job has no checkout")

    rel = jobs.get("release")
    if rel:
        needs = rel.get("needs") or []
        if any("mirror" in n for n in needs):
            R("pub", "release depends on a mirror job -- a red mirror then blocks the release")
        cond = str(rel.get("if", ""))
        c = cond.replace('"', "'")
        # Either form correctly excludes a `release` event: an explicit exclusion,
        # or restricting to push (which is stricter). Checking only for the literal
        # spelling of one of them was a false positive on the first run.
        excluded = ("event_name != 'release'" in c) or ("event_name == 'push'" in c)
        if "release" in str(on) and not excluded:
            R("pub", "release job does not exclude `release` events, but `release:` is a "
                     "trigger -- it will try to create a release that already exists")
        c2 = cond.replace('"', "'")
        # `if: !cancelled()` unquoted is invalid YAML (`!` starts a tag), so the real
        # spellings are ${{ !cancelled() }} or a quoted scalar. Match on the function
        # name with optional whitespace rather than one literal form.
        forced = bool(re.search(r"always\s*\(\s*\)", c2) or
                      re.search(r"!\s*cancelled\s*\(\s*\)", c2))
        guards = re.findall(r"needs\.[A-Za-z0-9_-]+\.result", c2)
        # Fire only when a job that CAN be skipped is actually in the release job's
        # needs closure. The previous spelling fired on every release job, which
        # encoded this repo's dependency graph as universal and was a false positive
        # against a release job that needs only unconditional jobs -- reported by
        # py-wordpress-database, verified by walking the closure.
        conditional = sorted(n for n in needs_closure(jobs, "release") if jobs[n].get("if"))
        if conditional and not forced:
            R("pub", f"release can be skipped: {conditional} in its needs closure carry an "
                     "`if:`, and a skipped dependency skips release. Needs always() or "
                     "!cancelled() to stay evaluated")
        # Independent of topology: a force function WITHOUT per-need result guards is
        # actively harmful. Neither always() NOR !cancelled() filters a FAILED
        # dependency -- any truthy `if:` overrides failure propagation -- so the force
        # function alone cuts a release for a wheel that just failed its checks. Only
        # explicit needs.<job>.result assertions distinguish skipped from failed.
        if forced and not guards:
            R("pub", "release `if:` forces evaluation (always()/!cancelled()) but asserts no "
                     "needs.<job>.result -- a FAILED dependency would still cut a release. "
                     "Neither function filters failure; only result checks do")
    return yaml.safe_dump(doc)

# ---------------------------------------------------------------- driver

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[2]),
                    help="directory holding the package repos (default: this repo's parent)")
    a = ap.parse_args()
    root = pathlib.Path(a.root)

    repos = sorted(p.parent for p in root.glob("*/pyproject.toml")
                   if (p.parent/".github"/"workflows").is_dir())
    if not repos:
        print(f"no package repos found under {root}", file=sys.stderr)
        return 2

    total = 0
    for repo in repos:
        findings: list[tuple[str, str]] = []
        R = lambda area, msg: findings.append((area, msg))
        wf = repo/".github"/"workflows"
        ci_p, pub_p = wf/"ci.yml", wf/"publish.yml"
        ci_blob = pub_blob = ""
        # A parse failure is a finding, not an exception. Letting it raise ended the
        # whole sweep at the first bad file, so repos after it were never examined --
        # the checker stopped covering its own scope, which is the failure it exists
        # to catch in others. Found by feeding it a workflow with invalid YAML.
        if not ci_p.exists():
            R("ci", "no ci.yml")
        else:
            try:
                ci_blob = check_ci(load(ci_p), R)
            except yaml.YAMLError as e:
                R("ci", f"ci.yml is not valid YAML, so nothing in it was checked: "
                        f"{str(e).splitlines()[0]}")
        if not pub_p.exists():
            R("pub", "no publish.yml")
        else:
            try:
                pub_blob = check_publish(load(pub_p), R)
            except yaml.YAMLError as e:
                R("pub", f"publish.yml is not valid YAML, so nothing in it was checked: "
                         f"{str(e).splitlines()[0]}")

        is_ns = (repo/"src"/"l3io").is_dir()
        check_namespace(ci_blob, pub_blob, is_ns, R)
        check_version_single_source(repo, pub_blob, R)

        # tracked-in-git check: a workflow that is not committed never runs
        import subprocess
        for f in sorted(wf.glob("*.yml")):
            r = subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch",
                                str(f.relative_to(repo))],
                               capture_output=True)
            if r.returncode != 0:
                R("git", f"{f.name} is NOT tracked in git -- it can never run on a push")

        mark = "OK" if not findings else f"{len(findings)} finding(s)"
        ns = " [namespace pkg]" if is_ns else ""
        print(f"\n=== {repo.name}{ns} -- {mark}")
        for area, msg in findings:
            print(f"  [{area}] {msg}")
        total += len(findings)

    print(f"\n{'-'*60}\n{len(repos)} repo(s) checked, {total} finding(s)")
    return 1 if total else 0

if __name__ == "__main__":
    raise SystemExit(main())
