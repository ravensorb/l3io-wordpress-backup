## Migrate ADRs Mode

Moves ADRs from the old per-epic home, `{implementation_artifacts}/epic-*/arch/adr-NNNN-*.md`,
to `{project-root}/docs/adr/NNNN-slug.md`, the one ADR home. Health Check 15 detects them. A
project that never migrates keeps working: `adr-reserve` and `spec-align.py adrs` still read
the old home.

### Step MA1 — Plan (read-only)

```bash
{spec_align} migrate-adrs --plan
```

Print a table of `moves`: from, to, epic, and collision. A collision has an empty `to`,
because `docs/adr/` already holds that number. At apply time:
- the `docs/adr/` file keeps its number, since it may be cited outside PM artifacts;
- the epic ADR gets a newly reserved number;
- `ADR-NNNN` mentions are rewritten **only inside that epic's artifact tree**;
- every other mention is listed for a person, and not rewritten.

If `moves` is empty, print `✓ No ADRs in the old home.` and exit.

### Step MA2 — Confirm

Ask: `Move {n} ADR(s) to docs/adr/ and commit? (y/n)`. On `n`, exit with no changes.

### Step MA3 — Apply

```bash
{spec_align} migrate-adrs --apply
```

Print its summary:
- **moved:** from → to;
- **renumbered:** old → new, from `renumbered_to`;
- **rewritten:** the files;
- **commit:** the SHA (a single `docs(adr): migrate epic ADRs to docs/adr` commit);
- **every `review` entry.** Those mentions were not rewritten; ask the user to check each
  one by hand.
