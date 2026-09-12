## Bootstrap State Mode

Communicate all responses in `{communication_language}`.

Invoked with `bootstrap-state` argument.

Creates sharded state YAML nodes for stories that exist as `.md` artifact files but have no
corresponding state YAML under `{pm_state_root}`. Intended for projects whose stories were
created via `bmad-create-story` (or another workflow) without going through `l3io-pm-plan`
— the artifacts exist and are the source of truth; this mode makes the state tree agree with
them. The mode never overwrites an existing state YAML, so it is additive and safe to run
on a project that already has partial state.

---

### Step BS1 — Pre-flight: find artifact-only stories

Scan the artifact tree for story `.md` files that have no corresponding state YAML:

```bash
find {implementation_artifacts}/epic-*/sprint-*/stories -name 'E*.md' 2>/dev/null | sort
```

For each `.md` found, check whether a state YAML exists anywhere in the state tree:

```bash
find {pm_state_root}/active {pm_state_root}/planned {pm_state_root}/archived \
  -name "{story_key}.yaml" 2>/dev/null | head -1
```

If the `find` prints nothing, the story has an artifact but no state node — collect it as
**artifact-only**.

**If no artifact files exist at all:**
```
Nothing to bootstrap — no story .md files found under {implementation_artifacts}/epic-*/sprint-*/stories/.
If this is a new project, stories will be created when l3io-pm-plan runs.
```
Exit. This is not an error.

**If artifact files exist but all already have state nodes:**
```
Nothing to bootstrap — all {N} story artifact(s) already have state nodes under {pm_state_root}.
Run /l3io-util-doctor check to see the current project health.
```
Exit. This is not an error.

Proceed if at least one artifact-only story was found. Record: `{artifact_only_stories}` = list of
`{story_key}` values.

---

### Step BS2 — Build create manifest

For each artifact-only story key, derive the required nodes.

**Extract path components** from the artifact path
`{implementation_artifacts}/epic-{nnn}/sprint-{nn}/stories/{story_key}.md`:

- `epic_num` = `{nnn}` (three digits; strip leading zeros for arithmetic, re-pad with `printf '%03d'`)
- `sprint_num` = `{nn}` (two digits)
- `epic_key` = `'E{nnn}'`
- `sprint_key` = `'S{nn}'`

**Read frontmatter from the story `.md` file.** Frontmatter is the YAML block between the
first pair of `---` markers. Extract, falling back to defaults when a field is absent:

```bash
uv run --with ruamel.yaml python3 - "{story_md_path}" <<'PY'
import sys
from pathlib import Path
from ruamel.yaml import YAML

yaml = YAML(typ='safe')
text = Path(sys.argv[1]).read_text()
parts = text.split('---', 2)
fm = {}
if len(parts) >= 3:
    try:
        fm = yaml.load(parts[1]) or {}
    except Exception:
        pass
print('title:', fm.get('title', ''))
print('status:', fm.get('status', 'backlog'))
print('classification:', fm.get('classification', 'standard'))
PY
```

Bind per story: `{story_title}`, `{story_status}` (default `backlog`), `{story_classification}`
(default `standard`).

**Determine which nodes need to be created.**

For each story's epic (`epic_key`, `epic_num`), check whether an epic state node already exists:

```bash
find {pm_state_root}/active/epic-{nnn} \
     {pm_state_root}/planned/epic-{nnn} \
     {pm_state_root}/archived/epic-{nnn} \
     -name "epic.yaml" 2>/dev/null | head -1
```

- If found: record `epic_state_dir` = the path to the existing `epic-{nnn}/` directory (e.g.
  `{pm_state_root}/active/epic-{nnn}`). This epic's state already exists — do not create a new
  `epic.yaml`.
- If not found: this epic needs an `epic.yaml`. Determine `status_dir` from the spread of story
  statuses across all artifact-only stories in this epic:
  - Any story has `status: in-progress` or `status: review` → `status_dir = active`, `epic_status = in-progress`
  - All stories are `status: done` → `status_dir = archived`, `epic_status = done`
  - Otherwise → `status_dir = planned`, `epic_status = backlog`

  Record `epic_state_dir` = `{pm_state_root}/{status_dir}/epic-{nnn}`. Add to the epic create list.

For each (epic, sprint) pair, check whether a sprint state node already exists inside
`epic_state_dir`:

```bash
find "{epic_state_dir}/sprint-{nn}" -name "sprint.yaml" 2>/dev/null | head -1
```

- If found: sprint state exists — do not create a new `sprint.yaml`.
- If not found: add to sprint create list.

All artifact-only stories are added to the story create list (by definition — their state YAML
was not found in Step BS1).

---

### Step BS3 — Dry-run report and confirmation

Print the create plan:

```
Bootstrap State — Dry Run
================================================================
Source: {implementation_artifacts}/epic-*/sprint-*/stories/
Target: {pm_state_root}/

  Will create {N} epic node(s), {M} sprint node(s), {K} story node(s).

Epics to create:
  E{nnn}  → {pm_state_root}/{status_dir}/epic-{nnn}/epic.yaml   (status: {epic_status})

Sprints to create:
  S{nn} under E{nnn}  → .../epic-{nnn}/sprint-{nn}/sprint.yaml  (status: in-progress)

Stories to create:
  {story_key}  → .../sprint-{nn}/{story_key}.yaml  (status: {story_status}, classification: {story_classification})
    source: {implementation_artifacts}/epic-{nnn}/sprint-{nn}/stories/{story_key}.md

Epics with existing state (not touched):
  {epic_key}  @ {epic_state_dir}

Sprints with existing state (not touched):
  S{nn} under E{nnn}  @ {epic_state_dir}/sprint-{nn}/
================================================================
```

If the create list is empty for all categories (all state exists), exit with:
```
Nothing to bootstrap — all artifact stories already have matching state nodes.
```

Otherwise ask:
```
Create {N} node(s)? [Y/n]:
```

If `n`: exit without changes.

---

### Step BS4 — Write state YAML files

Write nodes in order: epics first, then sprints, then stories. Use the following Python snippet
for every file write — it uses `ruamel.yaml` (the same library `pm-status.py` uses) for safe
YAML serialization:

```bash
uv run --with ruamel.yaml python3 - <<'PY'
import os, sys
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString as SQ

yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False

def write_node(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if Path(path).exists():
        print(f"SKIP (already exists): {path}", file=sys.stderr)
        return False
    with open(path, 'w') as f:
        yaml.dump(data, f)
    print(f"CREATED: {path}")
    return True

# --- write epic nodes ---
# (repeated for each epic to create)
write_node(
    "{pm_state_root}/{status_dir}/epic-{nnn}/epic.yaml",
    {
        'key': SQ('E{nnn}'),
        'title': '{epic_title_or_placeholder}',
        'goal': '',
        'status': '{epic_status}',
    }
)

# --- write sprint nodes ---
write_node(
    "{pm_state_root}/{status_dir}/epic-{nnn}/sprint-{nn}/sprint.yaml",
    {
        'key': SQ('S{nn}'),
        'epic': SQ('E{nnn}'),
        'title': 'Sprint {nn}',
        'status': '{sprint_status}',
    }
)

# --- write story nodes ---
write_node(
    "{pm_state_root}/{status_dir}/epic-{nnn}/sprint-{nn}/{story_key}.yaml",
    {
        'key': SQ('{story_key}'),
        'epic': SQ('E{nnn}'),
        'sprint': SQ('S{nn}'),
        'title': '{story_title}',
        'status': '{story_status}',
        'classification': '{story_classification}',
    }
)
PY
```

For `{epic_title_or_placeholder}`: read the story's frontmatter `title` field (if one story in
the epic carries an epic-level title, prefer that); otherwise use `'Epic {nnn}'` as a
placeholder — the user can fill in `goal` and `title` in `epic.yaml` directly after bootstrap.

Sprint status inference: if any story in the sprint has `status: in-progress` or
`status: review`, sprint status = `in-progress`; if all are `done`, `in-progress`; otherwise
`backlog`.

**If `uv` is unavailable**, use `python3` in place of `uv run --with ruamel.yaml python3`.

If `ruamel.yaml` is not importable (neither path), fall back to the stdlib `yaml` / `json`
writer and note in the output that round-trip preservation may not apply, but file contents
are still valid.

Any file the write skips as already-existing is listed in a `SKIP (already exists)` line and
not counted as created. The skip-and-continue policy means a partial prior run can be safely
retried without re-running the parts that succeeded.

---

### Step BS5 — Verify

For each epic whose nodes were created or augmented, run:

```bash
uv run {pm_status} verify --state-root {pm_state_root} --epic {epic_key} --scope epic
```

If `uv` is unavailable, use `python3 {pm_status} ...` instead.

Report each result:

```
Verify E{nnn}: OK
Verify E{nnn}: FAIL — {detail}
```

If any verify call fails:
```
BLOCKED: verification failed for {epic_key} — newly created nodes did not pass integrity
check. See detail above. The state files are on disk; nothing was removed. Inspect
{pm_state_root}/{status_dir}/epic-{nnn}/ and correct or delete the malformed nodes, then
re-run /l3io-util-doctor bootstrap-state (existing correct nodes will be skipped).
```

---

### Step BS6 — Summary

```
bootstrap-state complete
================================================================
  Epics created:   {N}
  Sprints created: {N}
  Stories created: {N}
  Skipped (already exist): {N} node(s)
  Verify: {N}/{N} epics passed
================================================================

Next steps:
  - Review newly created epic.yaml files and fill in 'goal' (and 'title' if placeholder was used).
  - Run /l3io-pm-plan to validate readiness and produce an execution plan.
  - Or run /l3io-pm-execute {epic_key} to begin executing directly.
```

---
