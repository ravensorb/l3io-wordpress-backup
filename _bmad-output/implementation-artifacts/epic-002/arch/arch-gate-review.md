# Arch gate review — E002 "Walking skeleton — take a backup and prove it"

- **Date:** 2026-09-27
- **Work type:** CODE
- **Reviewers detected:** `l3io-arch-review`, `bmad-agent-architect`
- **Reviewers run:** `l3io-arch-review` (alone, per step-04 §4 — escalation to
  `bmad-agent-architect` is pending a decision on remediation shape, see *Root cause* below)
- **Scope:** 8 story files across `epic-002/sprint-01` and `epic-002/sprint-02` (derived count
  of `{story_file_paths}`)
- **Spec alignment:** ON. Stories carried **no `Spec:` pointers** (`spec-align.py sections`
  returned `(no resolvable pointers)`), so the reviewer picked sections from the index itself.
- **Verdict:** **BLOCKED** — 6 BLOCKER, 18 MAJOR (all single-source, all blocking per §5),
  4 MINOR auto-deferred.

---

## Root cause — a skipped planning step, not 24 independent design defects

`plan-output-meta.yaml` records:

```yaml
readiness: amber
stories_elaborated: 0
```

Readiness graded **amber** — meaning `l3io-pm-plan` step-02 *did* find technical-AC gaps —
and **zero stories were elaborated**. `_bmad-output/planning-artifacts/readiness-report.md`,
which step-02 writes and step-03 reads to find thin stories, **does not exist**.

So all 26 stories in this project are the user-value acceptance criteria from `epics.md`
verbatim, plus front-matter. Verified byte-for-byte on `E002-S01-001`.

That is the common cause of most findings below. The spine *already makes* these decisions —
AD-3, AD-6, AD-12, AD-13, AD-14, AD-16, AD-21, AD-22/AD-25, AD-23 are all decided and
`status: final`. What is missing is the acceptance criterion carrying each decision into the
work a dev agent will actually do. That is precisely what story elaboration adds, and it
never ran.

**This matters for the remedy.** step-04 §6 prescribes one reserved ADR number and one
resolution subagent *per blocking finding*. Applied literally that is 24 ADRs — but most of
these findings name no open decision, so there is nothing for an ADR to decide. They are
findings of *omission from the stories*, and the instrument for that is elaboration.

Findings are therefore classified below. Only Class C is ADR-shaped.

---

## Class B — spec defects in `epics.md`. Independently verified, not reviewer-reported only.

Each of these was checked against the file before being recorded here. They are **not** fixed
by elaboration; they are wrong in the spec.

### AG-1 (BLOCKER, `l3io-arch-review`) — `domain/*` vs `domain/archive_format` ownership contradiction

`epics.md#epic-list` gives Epic 2 `domain/*` exclusively **and** Epic 4
`domain/archive_format` (v0 classifier). `domain/archive_format` is inside `domain/*`, so the
exclusive-ownership claim contradicts itself — on exactly the module
`ARCHITECTURE-SPINE.md#ad-23` requires to be single-owner ("no module outside
`domain/archive_format` branches on version"). E003 consumes `ArchiveView` in the same
parallel phase in which E004 writes its v0 branch.

**Verified:** ownership table read directly; both rows present as described.

### AG-2 (BLOCKER, `l3io-arch-review`) — `core/backup`, `adapters/store` and `cli/*` beyond `parser.py` are owned by no epic

`epics.md#epic-list` claims `core/*` only as `core/restore` (E003) and `core/exclusions`
(E004). `core/backup` — which the spine's capability map (L416, L438) makes the home of FR-1
and FR-2 — appears nowhere. Neither does any archive store, although `ports/ArchiveStore`
carries NFR-2 and `#ad-20` binds the **local** store shipping in v1.0 to
temp-name-then-`os.replace`-after-Manifest-verification. E002 owns `cli/parser.py` only, so
the rest of `cli/` — where AD-16 (Run Context), AD-10 (logging configured once), AD-4
(adapter binding) and AD-26 (passphrase chain, "shared **verbatim** by both composition
roots") all land — is unowned.

**Verified:** ownership table read directly; no `core/backup`, no store adapter, no `cli/*`.

### AG-3 (MAJOR, `l3io-arch-review`) — the FR Coverage Map is stale and names epics that no longer exist

`epics.md#fr-coverage-map` still reflects the **pre-reorganization** epic structure. It maps
FR-14/15/20/21/27/28 to "Epic 4 — Run it unattended", FR-22/23/24/30 to "Epic 5 — Embed it in
Python automation", FR-11/12/13/29 to "Epic 6 — Move a site to a new URL". After the epic
reorganization, Epic 5 is *Credential providers*, Epic 6 is *Embed in Python automation* and
Epic 7 is *Move a site to a new URL*. "Epic 4 — Run it unattended" does not exist at all.

An agent consulting the coverage map to decide which epic owns an FR gets a wrong answer.

**Verified:** map read directly; titles compared against the Epic List and the epic headings.
**Attribution:** this is fallout from the epic reorganization in this session. The map was
never regenerated.

### AG-4 (MAJOR, `l3io-arch-review`) — `db` vs `database`: the domain term and the frozen CLI value are collapsed

`prd.md#4-glossary` L86 and `prd.md#fr-2` both name the Backup Scope values `files`,
**`database`**, `all` — `database` three times in FR-2. `ARCHITECTURE-SPINE.md#ad-22` freezes
the **CLI** spelling as `--mode db`. The Consistency Conventions make "the PRD §4 Glossary
verbatim" binding for domain terms. `E002-S01-002` uses `db` as the domain value, collapsing
the two and leaving the CLI→domain mapping owned by nobody. It also drops FR-2's "**and no
Site Root members**" clause.

**Verified:** all three sources read directly.

### AG-5 (MINOR→recorded here, `l3io-arch-review`) — Epic 2's title is inconsistent *within* `epics.md`

The `## Epic 2` heading reads "take a backup and prove it"; the Epic List table row reads
"back up and prove it". State nodes were corrected to the heading form in commit `20361a5`;
the table was not.

---

## Class A — contract decisions with no acceptance criterion in any story

These name no open decision. The spine decides each one and is `status: final`; the story
does not carry it. **Remedy: story elaboration**, which is the step that was skipped.

| ID | Sev | Decision with no AC | Spine section |
|---|---|---|---|
| AG-6  | BLOCKER | Archive format contract — `manifest.json` as first tar member never encrypted, format version + KDF salt/params + member index + checksums, enumerated member roles, checksums over bytes **as stored**, supported range derived from committed CI fixtures never a hand-kept list | `#ad-6` L97–110 |
| AG-7  | BLOCKER | Normalized `ArchiveView` — `ArchiveProbe` port, pure classifier in `domain/`, `integrity: VERIFIED \| STRUCTURAL_ONLY` | `#ad-23` L257–266 |
| AG-8  | BLOCKER | Site Descriptor — frozen value object, built once at the boundary, `host:port` split during construction, **no setters**, nothing below the composition root reopens `wp-config.php` | `#ad-3` L77–82 |
| AG-9  | BLOCKER | Site Lock **re-entrancy for its holder** — without it the Safety Snapshot (FR-8, E003 story 3.3) deadlocks and **every** destructive restore refuses | `#ad-16` L206–211, `#ad-19` L229–234 |
| AG-10 | BLOCKER | Frozen CLI surface conformance (19 flag spellings incl. `--whatIf`, `python -m wpbackup2`, console script, `--only-appointed-in-asg` accepted-and-explained) + AD-25's **total** flag→`(RestoreMode, OverrideSet)` table with parser-derived test scope | `#ad-22` L247–256, `#ad-25` L281–287 |
| AG-11 | BLOCKER | Run Context — created exactly once, carries Run ID + workspace + logger + Site Lock + clock + bound adapters; an entry point that receives one **joins** it; creating one while another is active is **an error** | `#ad-16` L206–211 |
| AG-12 | MAJOR | AD-4 mechanism, not just its prohibition — **every port splits into queries and commands**, plan-equality test across adapter sets, CI grep gate on `dry_run`/`what_if` outside a composition root | `#ad-4` L83–89 |
| AG-13 | MAJOR | AD-21 as a contract — no port moving Archive bytes accepts or returns `bytes`; peak RSS bounded by a constant, asserted in CI against an oversized fixture | `#ad-21` L241–246, NFR-7 |
| AG-14 | MAJOR | AD-7 covers the **in-process driver** (PyMySQL) too, and there is **exactly one** redaction implementation (FR-30) which E006's tracing story must reuse; Site Descriptor `repr` named specifically | `#ad-7` L111–134, `prd.md#fr-30` |
| AG-15 | MAJOR | FR-20 consequences — selectable structured output, human-readable default on a TTY, `--log-level` defaulting to **INFO not CRITICAL**, cross-package verbosity consistency; `merge_contextvars` **first** in the processor chain; UTC ISO-8601 with explicit offset on every record | `prd.md#fr-20`, `#ad-10` L151 |
| AG-16 | MAJOR | Lock released **on signal** (a bare `finally` does not run on SIGTERM) and refusal naming the holder's **Run ID and start time**; record carries PID + start time | `prd.md#fr-28`, `#ad-19` L233 |
| AG-17 | MAJOR | Verification result must carry `integrity`, not binary pass/fail — a v0 Archive verifies as pass + `STRUCTURAL_ONLY`; consumed by E003's pre-destruction gate and E004's v0 read in the same phase | `#ad-6` L106, `#ad-23` L262 |
| AG-18 | MAJOR | AD-12 per-Run private workspace — `mkdtemp`, owner-only, removed in `finally` on both paths, core never learns a path it did not receive. Fix for a live defect (hardcoded `/tmp`, fixed `database.sql`, dump left behind) | `#ad-12` L160–166 |
| AG-19 | MAJOR | AD-14 exception hierarchy — one base per package, structured fields, `raise … from`, no dependency or stdlib type across a public boundary, no credential in any message. E006 owns only `api/*`, so it **cannot** define this | `#ad-14` L173–178 |
| AG-20 | MAJOR | AD-13 preflight **port** (presence + version, driven by what the plan requires). E005 owns the preflight *adapter*; `ports/*` is E002-exclusive | `#ad-13` L167–172 |
| AG-21 | MAJOR | AD-20 atomic visibility mechanism as an AC — temp name, verify Manifest, `os.replace` — rather than story 2.1's prose "becomes visible … only once complete and verifiable" | `#ad-20` L235–240 |
| AG-22 | MINOR | FR-1's third consequence dropped: credentials resolved from `wp-config.php` when no Credential Provider is given. Default path for the epic's flagship command; assigned to no other story | `prd.md#fr-1` L108 |
| AG-23 | MINOR | Story 2.5 says `wpconfigr`; post-rename this is `l3io-wp-config` / `l3io.wp.config` (ADR-0012, AD-27) | `#ad-2`, `#ad-27` |
| AG-24 | MINOR | `E002-S01-002` classified `simple`, but it writes a Glossary-bound `domain/` enum, resolves AG-4's naming conflict and touches a frozen CLI accepted-value set four epics consume. Reclassify `standard` | — |
| AG-25 | MINOR | README CLI usage generated from `--help` and checked in CI (the current README documents three flags that do not exist) belongs with the epic that freezes the CLI | Conventions L341 |

---

## Class C — genuinely open decisions. ADR-shaped.

No spec section decides these. They are the findings step-04 §6's ADR flow is actually for.

### AG-26 (MAJOR, spec-gap) — exit-code numeric values are assigned by no spec and no story

`prd.md#8` makes "exit-code meanings" part of the frozen CLI contract and the capability map
calls the table "part of the §8 CLI contract", but no section fixes the numbers.
`E002-S02-006` lists six categories "**at minimum**" — an open scope on an append-only frozen
table. E003 needs codes for the FR-7 non-empty-target refusal and the AD-18 incomplete-journal
refusal, E005 for preflight, E007 for WP-CLI absence: four parallel epics each inventing a
number in a `domain/` module E002 owns exclusively.

**Decision needed:** fix the six numbers, reserve a documented block per later epic, and
derive the coverage test's scope from the enum rather than a hand-kept list.

### AG-27 (MAJOR, spec-gap) — Storage Target addressing grammar

`ARCHITECTURE-SPINE.md#deferred` L446 states the **addressing grammar is not deferred**:
"v1.0's local store must already accept a scheme-qualified target string, because §10 makes
accepted values a breaking surface and a v1.0 that takes bare paths cannot add schemes without
a major bump." No story lands it, `ports/ArchiveStore` is E002-exclusive, and FR-16/FR-17 are
out of v1.0 scope so no later epic will.

**Decision needed:** the grammar itself — `file://…` accepted, bare path accepted as `file:`,
unknown scheme a named error — and where it lives in `domain/`.

### AG-28 (MAJOR) — sprint-01 needs a contract sprint-02 delivers

`E002-S01-001` (sprint-01) must produce a Dump, so it invokes `mysqldump`, which `#ad-7` says
may happen **only** through the credential-transport adapter delivered by `E002-S02-004`
(sprint-02). It also needs the AD-12 per-Run workspace that story 2.4 references and no
sprint-01 story owns. Sprint-01 therefore either violates AD-7 in the interim and rewrites in
sprint-02, or blocks.

**Decision needed:** the sprint split. Proposed — move `E002-S02-004` and the Run
Context/workspace work into sprint-01, leaving sprint-02 as logging, exit codes, dry run and
lock.

### AG-29 (MAJOR) — two E002 stories have acceptance criteria only E003 can demonstrate

`E002-S01-003`'s final AC is "verification runs automatically before any destructive restore
step". `E002-S02-007` is written entirely about restore ("I want to see what a **restore**
would do", "the Site and every Storage Target are unchanged afterwards"), and the stale
coverage map even assigns FR-19 to Epic 3. E002 ships `backup` and `verify` only, so these ACs
are unverifiable at E002 closure and would be silently deferred past the very gate that exists
to settle contracts before four epics fan out.

**Decision needed:** whether to restate story 2.7 against the *backup* path (no-op
`ArchiveStore` command adapter, dry-run backup leaves the Storage Target unchanged,
plan-equality across adapter sets) and move the restore clause to E003.

---

## Consolidation (§5)

Only one reviewer ran, so every finding is single-source by construction. Per the §5 table
that changes a **label**, never a verdict: a single-source MAJOR still blocks.

| | count |
|---|---|
| BLOCKER | 6 |
| MAJOR (flagged, single-source) | 18 |
| **Blocking total** | **24** |
| MINOR (auto-deferred to issues) | 4 |

`bmad-agent-architect` was detected and has **not** been run. §4 mandates escalation once a
BLOCKER or MAJOR appears. It is deliberately deferred rather than skipped: all 8 stories are
about to be rewritten by the elaboration that never ran, and a second full-epic read of the
known-thin stories would produce the same omission set. Escalation belongs *after*
remediation, on the elaborated stories — which is also what §6's "re-validate only what
changed" implies.

## Independently verified before recording

Not taken on the reviewer's word:

- `plan-output-meta.yaml`: `readiness: amber`, `stories_elaborated: 0`; no `readiness-report.md`
- `E002-S01-001.md` is `epics.md` §Story 2.1 verbatim plus front-matter
- AG-1: both ownership rows present and contradictory
- AG-2: no `core/backup`, no store adapter, no `cli/*` in the ownership table
- AG-3: coverage map names three epic titles that no longer exist
- AG-4: Glossary L86 + FR-2 say `database`; AD-22 freezes `--mode db`; Conventions bind the Glossary
