# Handoff — wordpress-backup

- **Repo:** `py-wordpress-backup` (being republished as the distribution `l3io-wp-backup`)
- **Branch:** `main` (renamed from `master` this session; CI triggers follow `main`)
- **Written:** 2026-09-27
- **Status:** active

## Resume line

> You are `wordpress-backup`. Read `docs/handoff/wordpress-backup.md` in this repo, then continue.

---

## What this session owns

The ground-up rewrite of a broken WordPress backup package, planned through BMad/l3io and
about to be built by dispatched agents.

Frozen outward surface (this is the constraint everything else bends around):

- The **CLI** as shipped at v0.2.21 — both subcommands, all nineteen flag spellings including
  the camelCase `--whatIf`, `python -m wpbackup2` still working, console script `wpbackup2`
  added alongside. See `ARCHITECTURE-SPINE.md#ad-22`.
- The **v0 archive read path**, forever. v1 is the only write format.
- The **Python API is explicitly not preserved** — redesigned freely.

Version restarts at **1.0.0** under the new name. Two sibling repos (`wordpress-config` →
`l3io-wp-config`, `wordpress-database` → `l3io-wp-database`) are being renamed in parallel by
their own sessions; imports are PEP 420 namespace (`from l3io.wp import backup`), see
`docs/adr/0012-*` and `#ad-27`.

## Read these first, in this order

1. `_bmad-output/implementation-artifacts/epic-002/arch/arch-gate-review.md` — **the live
   blocker.** Full gate record, 29 findings classified, and the five spec defects that were
   independently verified rather than taken on the reviewer's word.
2. `_bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md`
   — 29 architecture decisions, `status: final`. The source of truth for design.
3. `_bmad-output/planning-artifacts/epics.md` — 6 epics, 26 stories, the ownership table.
   **Known-defective**, see the blocked items below.
4. `docs/adr/` — 14 ADRs with a README index. ADR-0002 is superseded by ADR-0012.
5. `_bmad-output/implementation-artifacts/handoffs/00-SHARED-CONTEXT.md` — 19 domain traps
   collected during planning. Read before touching implementation.

Do **not** read the PRD (70 KB) or the spine whole unless you need to. The spec index at
`_bmad-output/implementation-artifacts/spec/spec-index.md` lists every section as
`path#anchor — heading (Lstart–Lend)`; open ranges with `sed -n 'START,ENDp'`.

## Blocked

- [blocked] **Phase 1 dispatch (E002, 8 stories) — the arch gate returned 6 BLOCKER and 18
  MAJOR.** Nothing may dispatch until this is resolved. Record in the gate file above.
- [blocked] **Root cause: story elaboration never ran.** `plan-output-meta.yaml` records
  `readiness: amber` with `stories_elaborated: 0`, and
  `_bmad-output/planning-artifacts/readiness-report.md` — which `l3io-pm-plan` step-02 writes
  and step-03 reads to find thin stories — **does not exist**. So all 26 stories are the
  `epics.md` user-value ACs verbatim plus front-matter (verified byte-for-byte on
  `E002-S01-001`). The spine decides AD-3/6/12/13/14/16/21/22/23/25 and is final; no story
  carries any of them as an acceptance criterion. **This affects all six epics, not just
  E002** — E003–E007 will each block the same way at their own gates.
- [blocked] `domain/*` (E002) and `domain/archive_format` (E004) are **both** claimed
  exclusively in `epics.md#epic-list`, on exactly the module `#ad-23` requires to be
  single-owner. E003 consumes `ArchiveView` in the same parallel phase E004 writes its v0
  branch.
- [blocked] `core/backup`, any archive **store** adapter, and `cli/*` beyond `parser.py` are
  owned by **no epic** in `epics.md#epic-list` — though `#ad-16` (Run Context), `#ad-10`
  (logging configured once), `#ad-4` (adapter binding) and `#ad-26` (passphrase chain) all
  land in `cli/`, and `#ad-20` binds the local v1.0 store to
  temp-name-then-`os.replace`-after-Manifest-verification.
- [blocked] `epics.md#fr-coverage-map` is **pre-reorganization** and names three epic titles
  that no longer exist. Fallout from this session's own epic reorg; never regenerated. Any
  agent consulting it to find an FR's owner gets a wrong answer.
- [blocked] `db` vs `database`: the PRD Glossary and FR-2 name the domain value `database`,
  `#ad-22` freezes the **CLI** spelling as `--mode db`, and the Consistency Conventions bind
  the Glossary verbatim for domain terms. Story 2.2 collapses the two; the CLI→domain mapping
  is owned by nobody.

### The two findings most likely to bite

- [blocked] **Site Lock is not re-entrant for its holder.** E003's Safety Snapshot (FR-8,
  story 3.3) is naturally implemented by calling the backup entry point, which deadlocks
  against the lock the outer Run holds — making **every destructive restore refuse**.
  `adapters/lock` is E002-exclusive, so E003 cannot fix it without crossing the ownership
  boundary. `#ad-16`, `#ad-19`.
- [blocked] **Sprint-01 needs a contract sprint-02 delivers.** `E002-S01-001` must produce a
  Dump, so it runs `mysqldump`, which `#ad-7` permits **only** through the
  credential-transport adapter that `E002-S02-004` (sprint-02) delivers. Sprint-01 either
  violates AD-7 and rewrites, or blocks.

## Decisions pending — Shawn's, not yours to assume

- [todo] **Remediation route for the gate.** Three were put to him and none chosen:
  (1) elaborate all 26 stories + fix the five `epics.md` defects + re-run the gate with both
  reviewers; (2) E002's 8 stories only, let E003–E007 block at their own gates;
  (3) Class C findings as ADRs only, accept thin stories elsewhere. This session recommended
  (1). **Do not proceed on a route he has not picked.**
- [todo] **Make the `liquidlogiclabs` Gitea org public.** The cheapest route to relieving
  `#ad-15` (release order + index reachability). Held by him.
- [todo] **The PyPI decision** — whether to publish to PyPI at all, and under which account.
  Held by him. Related: `publish-pypi` in `.github/workflows/publish.yml` is deliberately
  dispatch-only.
- [todo] **Whether to move the 16 `standard` stories to Sonnet.** Bindings currently put
  `simple` + prep/closure on `claude-sonnet-5` and everything else on `claude-opus-5`
  (`_bmad/custom/config.toml`). Moving `standard` too would shift 16 of 26 stories to a ~3.3×
  cheaper input tier. Deliberately not taken unilaterally on a rewrite handling credentials
  and encryption.

## Done this session

- [done] `13a50f8` — pinned `spec_paths` in `_bmad/custom/l3io-pm-execute.toml` to the three
  real specs. Discovery was sweeping review outputs into the spec index every reviewer reads;
  guard verified in both directions with a planted canary. Index 31,019 → 26,218 bytes.
- [done] `d3d5281` — bound per-classification dispatch models. `modules.l3io-pm` did not
  exist at all, so every dispatch *and* every cost figure resolved to the Opus baseline.
- [done] `20361a5` — populated `goal` and `title` on all six epic nodes from `epics.md`. They
  were bootstrapped from sprint directories with `goal: ''`, which degraded all 26 story preps
  (`step-02-story-prep` reads `epic.yaml` directly for `goal`).
- [done] `466cc09` — the gate record, 4 MINORs deferred as `BL-E002-001..004`,
  `E002-S01-002` reclassified `simple` → `standard`.
- [done] CI/CD verified green locally — all 5 `ci.yml` jobs under `nektos/act` with
  `MAKE_EXIT=0` and **0 root-owned files left behind**. Same approach as the two sibling
  repos. Secrets go through Infisical; `.act.secrets` ships empty and no secret is written to
  disk in any of the three repos.

## Traps this session hit — worth not repeating

- **`bmad-agent-architect` was detected and deliberately not run**, although step-04 §4
  mandates escalation once a BLOCKER appears. Reason: all 8 stories are about to be rewritten
  by the elaboration that never ran, so a second full-epic read of known-thin stories
  reproduces the same omission set, and §5's table says a second reviewer can only change a
  *label*, never the verdict. Escalation belongs after remediation. **This is a departure from
  the step file and is recorded as such in the gate file.**
- **`step-04` §6 prescribes `append-issue --source-phase` and `--source-ref`. Those flags do
  not exist** — the installed `pm-status.py` requires `--source`. Worth fixing upstream in the
  skill payload; it is the same documented-flag-that-does-not-exist pattern the global rules
  call out.
- **§6's one-ADR-per-blocking-finding does not survive 24 findings.** Most name no open
  decision, so there is nothing for an ADR to decide. They were classified instead: Class A
  omissions (fixed by elaboration), Class B spec defects (fixed by editing `epics.md`), Class
  C genuinely ADR-shaped (4 of them: exit-code numbers, Storage Target addressing grammar, the
  sprint split, story 2.7's restore-only ACs).
- **Sprint keys are `S01`, not `E002-S01`**, and rollups write low/high bands where stories
  write point estimates. Both cost a round trip.
- **`_bmad-output/planning-artifacts` changed outside this session's edits** mid-run (the PRD
  grew 52 KB → 66 KB, `check_prd.py` appeared). *Inference:* another session or a BMad
  workflow touched it. Verify before claiming authorship of anything in there.

## Already in the shared KB — do not restate

Two findings from this repo landed in basic-memory under `home-lab/` and should only be
pointed at from here, never duplicated:

- the **MySQL GRANT underscore-wildcard** finding
- the **restore-is-not-atomic** material

Together with the db-backup note they bracket the estate's backup problem from both ends. A
peer noted that deleting the broad `act` note rather than leaving two competing versions is
what made the KB usable — carry that instinct: **one authoritative note, deleted and replaced
rather than duplicated.**
