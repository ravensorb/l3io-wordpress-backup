# Step 02: Readiness Check

Communicate all responses in `{communication_language}`.

Run after step-01-classify-work. Validates every story in scope before planning proceeds.
Bind `{readiness}` to the gate result before loading the next step.

---

## 0. Pre-scan: artifact-only story detection

Before reading state, check whether the artifact tree holds story `.md` files that have
no corresponding state YAML. Runs for every `{work_type}`.

```bash
find {implementation_artifacts}/epic-*/sprint-*/stories -name 'E*.md' 2>/dev/null | sort
```

For each `.md` file found at path
`{implementation_artifacts}/epic-{nnn}/sprint-{nn}/stories/{story_key}.md`:

Check whether a state YAML exists for that key anywhere in the state tree:

```bash
find {pm_state_root}/active {pm_state_root}/planned {pm_state_root}/archived \
  -name "{story_key}.yaml" 2>/dev/null | head -1
```

If the `find` prints nothing, the story has an artifact but no state node — collect it as
an **artifact-only** story.

If **any artifact-only stories are found**, halt immediately with `{readiness}` = `red`:

```
🔴 Readiness check FAILED — {count} story artifact(s) have no state node.

These stories exist as .md files in the artifact tree but have no corresponding
state YAML under {pm_state_root}/. l3io-pm-plan reads state only, so these stories
are invisible to planning, estimation, and execution.

Artifact-only stories:
{list each: {implementation_artifacts}/epic-{nnn}/sprint-{nn}/stories/{story_key}.md}

Fix: run /l3io-util-doctor bootstrap-state to create state nodes from your artifact
files. This is a one-time step for projects whose stories were created outside l3io-pm
(e.g. via bmad-create-story without going through l3io-pm-plan).
```

BLOCKED: artifact-only stories detected — run `/l3io-util-doctor bootstrap-state` first.

If no artifact-only stories are found (or no `.md` files exist at all), continue to §1.

---

## 1. Collect stories in scope

Read all stories from:
- All epics under `{pm_state_root}/active/` with `status: in-progress`
- All epics under `{pm_state_root}/planned/` with `status: backlog`

For each epic, list its sprint directories and each sprint's story `.yaml` files (excluding
`sprint.yaml`) to enumerate stories — or use `python3 {pm_status} show --state-root {pm_state_root} --epic {epic_key}` for a quick status roll-up.

For each story, record: `key`, `classification`, `status`, `estimate` (present/absent),
`depends_on`, and whether it is assigned to a sprint.

## 2. Run validation checks

For each story, evaluate the following checks:

| Check | Green | Amber | Red |
|-------|-------|-------|-----|
| Classification | `classification` is `simple`, `standard`, or `complex` | — | Missing or unrecognized value |
| Technical ACs | If `{work_type}` is CODE or MIXED: story file exists with non-empty "Acceptance Criteria" section containing technical details (interfaces, data model, error handling) | Story has only functional ACs (no technical details) | No AC section at all |
| Estimate block | `estimate` block present with at least `man_hours` or `man_hours_low` | — | Estimate block absent |
| `depends_on` validity | All referenced keys exist in scope and are not `done` | — | Any key missing from any state file, or a cycle detected |
| Sprint assignment | Story is assigned to a named sprint in its epic | — | Orphaned story (not in any sprint) |

Technical ACs check only applies when `{work_type}` is CODE or MIXED. For DOCS and CONFIG, skip this check for all stories.

## 3. BMad readiness integration

If `.claude/commands/bmad-check-implementation-readiness.md` or `~/.claude/commands/bmad-check-implementation-readiness.md` exists:

For each CODE or MIXED story, invoke `bmad-check-implementation-readiness` with the story file path. Fold its "not ready" findings into the gate:
- Fewer than half the stories flagged as not ready → amber
- Half or more flagged → red

## 4. Compute gate result

- Any Red finding on any story → `{readiness}` = `red`
- Any Amber finding, no Red → `{readiness}` = `amber`
- All Green → `{readiness}` = `green`

## 5. Write readiness-report.md

Write `{planning_artifacts}/readiness-report.md`:

```markdown
# Readiness Report

Generated: {timestamp}
Gate result: {readiness}
Stories checked: {total_story_count}

## Findings

| Story | Check | Result | Detail |
|-------|-------|--------|--------|
| E001-S01-001 | Technical ACs | 🟡 Amber | Functional ACs only — no interface specs |
| E002-S01-003 | Estimate | 🔴 Red | Missing estimate block |
| E001-S02-001 | depends_on | 🟢 Green | — |

## Summary

- Green: {count}
- Amber: {count}
- Red: {count}
```

## 6. Apply gate outcome

**`{readiness}` = red:**
```
🔴 Readiness check FAILED — {count} blocking issue(s) found.
See {planning_artifacts}/readiness-report.md for details.
Resolve all Red findings before running /l3io-pm-plan again.
```
BLOCKED: readiness gate — red. Do not load the next step.

**`{readiness}` = amber:**
```
🟡 Readiness check passed with warnings — {count} non-blocking issue(s).
Estimates for affected stories will be marked low-confidence.
See {planning_artifacts}/readiness-report.md for details.
Continuing with plan...
```

**`{readiness}` = green:**
```
✅ Readiness check passed — all {count} stories ready.
```

## 7. Output status line

```
Step 02 complete — readiness: {readiness}, stories: {total_story_count}, gaps: {amber_count} amber / {red_count} red
```
