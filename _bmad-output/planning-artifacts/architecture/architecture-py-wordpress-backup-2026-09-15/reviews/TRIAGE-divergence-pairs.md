# Divergence-pair triage — 2026-09-17

The spine's Deferred section required this before the first work touching the
restore path. The rewrite is that work, so it is done here.

Sources: `review-adversarial-divergence.md` (D-1…D-14, first pass, against a
15-AD spine) and `review-adversarial-divergence-delta.md` (E-1…E-18, second pass,
against a 24-AD spine). The spine now carries **29** ADs, so several pairs were
closed by invariants written after the review that found them.

**Disposition counts: 12 closed · 10 decided here · 6 deferred with a condition · 4 won't-fix.**

## Closed by an AD written after the review

| Pair | Closed by |
|---|---|
| D-1 Manifest inside the envelope it decrypts | AD-6 three-layer format, ADR-0006 |
| D-2 Safety Snapshot forks the Run | AD-16 Run Context |
| D-3 restore order exists only in a diagram | AD-17 `RestorePhase` enum |
| D-4 "plausible results" lets adapters disagree | AD-4 queries/commands split |
| D-5 FR-29 out-of-root config vs containment | AD-6 enumerated member roles |
| D-11 `wpconfigr` cannot carry the Run ID | AD-10 stream-not-dependency |
| D-12 two owners of provisioning | spine Deferred: one implementation, in `l3io-wp-database` |
| E-1 twelve CLI states, no mapping function | AD-25 total flag map |
| E-2 AD-7 named the corrected-away flag | AD-7 rewritten to `--defaults-file` |
| E-3 v0 Archive has no Manifest, four ADs read two ways | AD-23 normalized `ArchiveView` |
| E-4 detection in `domain/` needs `tarfile`, which AD-1 forbids | AD-23 `ArchiveProbe` port + pure classifier |
| E-5 Snapshot must be encrypted, no way to configure it | AD-26 passphrase chain |

E-13 (FR-10 opt-in vs AD-23 permanent) is also closed — the PRD's FR-10 was
rewritten to make v0 reads a default guarantee.

## Decided here — fold into the build, no new AD needed

1. **E-7 — `--whatIf` is not "fixed".** AD-22 freezes flag spellings and permits
   *behaviour* fixes. Renaming it to `--what-if` is a spelling change and is
   forbidden; adding `--what-if` as an **alias** is permitted. Dry Run must not be
   silently disabled by a rename that looks like a defect fix.
2. **E-8 — a Dry Run emits spans, and they say so.** Spans are recorded with
   `dry_run=true` as an attribute (FR-30 already lists it). A no-op command adapter
   records the span it *would* have produced, never one asserting an effect
   occurred.
3. **E-12 — the CLI's `--mode` vocabulary is not the domain's.** AD-25's table is
   the only translation point; `{files, db, all}` are CLI tokens, `BackupScope` and
   `RestoreMode` are domain types, and FR-6's per-mode test enumerates the domain
   set, not the CLI set.
4. **E-14 — the default log level must let `jq` work.** AD-24 promises a log file
   and `jq` as the operator's route; the preserved CLI defaults `--log-level` to
   `CRITICAL`, which emits nothing. Defaulting to `INFO` is a *behaviour* fix
   permitted by AD-22, and is required for AD-24's claim to be true. Structured
   output stays opt-in; human-readable remains the TTY default.
5. **E-15 — "a Run Context is active" means within the process.** Scope is the
   `contextvars` context, which is also what carries the Run ID (AD-10), so the two
   cannot disagree.
6. **E-16 — a v1 Archive is gzipped.** The preserved `--archive` help says
   `.tar.gz` and AD-22 freezes it, so the container is a gzipped tar. AD-6's "tar
   container" is the member layout, not the compression.
7. **E-17 — a v0 restore has no `config_path`, and must not invent one.** v0 has no
   Manifest, so `ArchiveView.config_path` is `None` and the config is taken from the
   Site Root's default location. AD-3 forbids re-deriving it; `None` is the honest
   answer and the restore says so.
8. **E-18 — the supported range is a set, not an interval.** v0 has no version, so
   AD-6's fixture-derived range is the **set of fixtures that exist**, with v0 a
   named member rather than a bound.
9. **E-6 — redaction has one implementation and the guard checks both sinks.**
   Already required by AD-7's five assertions and AD-24's single redaction path;
   recorded here so the pair is not re-raised.
10. **D-6 — the Site Descriptor is one type.** AD-3 already says so; the two named
    types in the old code collapse into it, and any Glossary field without a source
    is absent rather than defaulted.

## Deferred, each with the condition that reopens it

| Pair | Why it can wait | Reopens when |
|---|---|---|
| E-9 exit codes for new failure modes | The code table is FR-21's and belongs with the CLI, which is built after the core | the CLI epic starts — it needs writing, not discovering |
| E-10 Run Journal directory | AD-18 says "the Safety Snapshot's directory"; AD-12 deletes the workspace in `finally`. They do not conflict only because the Snapshot lives outside the workspace | the journal is implemented — state the path explicitly then |
| E-11 Snapshot in the ArchiveStore or beside it | Retention is v1.1; until then nothing can prune it | FR-17 is built |
| D-7 exit-code table ownership | Same as E-9 | the CLI epic |
| D-13 Storage Target addressing | v1.0 accepts a scheme-qualified string; the grammar's expansion is v1.1 | FR-16 is built |
| D-14 Clock port under Dry Run vs structlog timestamps | Cosmetic until a test asserts on a timestamp | a test asserts on a timestamp |

## Won't fix, with the reason

- **D-8 — AD-13's preflight covers binaries, not optional Python dependencies.**
  Correct as written. AD-8 makes an absent extra raise a named error at the point of
  use; folding it into binary preflight would mean importing the extra to check it,
  which defeats the optionality.
- **D-9 / D-10 — the Snapshot destination and the Site Lock's home.** Both were
  answered after that review: AD-12 puts the Snapshot outside the Site Root and any
  web-served directory, AD-19 keys the lock on the canonical Site Root path and
  holds it outside the tree.
