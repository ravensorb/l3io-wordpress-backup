---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics']
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/prd.md
  - _bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/reviews/TRIAGE-divergence-pairs.md
  - docs/adr/  (13 records)
  - _bmad-output/implementation-artifacts/handoffs/  (shared context + 4 handoffs)
---

# l3io-wp-backup - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for l3io-wp-backup, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**FR-1**: Full Site backup
**FR-2**: Selective Backup Scope
**FR-3**: Archive Manifest and Verification
**FR-4**: Archive encryption at rest
**FR-5**: Exclusions
**FR-6**: Restore with an explicit, honored Restore Mode
**FR-7**: Refuse destructive restore over a non-empty target
**FR-8**: Safety Snapshot before destruction
**FR-9**: Database restore that reports what it did
**FR-10**: Restore is Archive-format aware
**FR-11**: Configuration rewriting
**FR-12**: Serialization-safe content URL rewriting
**FR-13**: Honest failure when WP-CLI is unavailable
**FR-14**: Pluggable Credential Providers
**FR-15**: Credentials never exposed in process arguments or logs
**FR-16**: Local and remote Storage Targets
**FR-17**: Retention Policy and pruning
**FR-18**: Scheduled operation
**FR-19**: Dry Run across every destructive operation
**FR-20**: Structured logging correlated by Run ID
**FR-21**: Meaningful exit codes
**FR-22**: Typed, importable API
**FR-23**: Exception contract
**FR-24**: Declared public surface
**FR-25**: Resolvable, reproducible installation
**FR-26**: Dependency policy
**FR-27**: External tool dependency declaration
**FR-28**: Concurrent Runs against the same Site are prevented
**FR-29**: `wp-config.php` outside the default location
**FR-30**: Optional distributed tracing, inert unless a host configures it

### NonFunctional Requirements

**NFR-1**: Data integrity is the paramount attribute
**NFR-2**: Atomicity of published artifacts
**NFR-3**: Least privilege and secret hygiene
**NFR-4**: Idempotence and safe retry
**NFR-5**: Untrusted archives
**NFR-6**: Observability
**NFR-7**: Performance envelope
**NFR-8**: Testability without a live WordPress

### Additional Requirements

- **29 architecture invariants (AD-1…AD-29)** bind every story. The ones most likely to be
  violated by a plausible implementation: AD-4 (Dry Run is adapter selection, never a
  conditional), AD-5 (no function consuming a Restore Mode may default it), AD-17 (phase
  order is an ordered enum, not a diagram), AD-18 (a killed Run must be recoverable),
  AD-25 (the CLI flag matrix is a total function), AD-27 (PEP 420 namespace, no `__init__.py`
  above the leaf), AD-28 (escape the database name in a GRANT), AD-29 (existence is answered
  by the administrator, never inferred from a failed login).
- **13 ADRs** carry the mechanism decisions: ports-and-adapters (0001), credential transport
  by `--defaults-file` (0003), PyMySQL (0004), WP-CLI delegation (0005), archive format and
  chunked AES-GCM under Argon2id (0006), uv packaging (0007), optional boto3 (0008), Python
  floor (0009), the regex parser's accepted scope (0010), observability (0011), naming (0012),
  CI replayable under act (0013).
- **10 binding decisions** in `reviews/TRIAGE-divergence-pairs.md`, including three that a
  default implementation gets wrong: `--whatIf` keeps its spelling, `--log-level` defaults to
  INFO not CRITICAL, and a v1 Archive is gzipped.
- **Outward compatibility (AD-22)**: the CLI is frozen — both subcommands, all 19 flag
  spellings, `python -m wpbackup2` as a working invocation. The Python API is explicitly NOT
  preserved. `--only-appointed-in-asg` is accepted and fails with an explanation.
- **Archive compatibility (AD-23)**: v0 archives (manifest-less `.tar.gz` with `database.sql`
  and `wp-root/`) are read by default, permanently. Writing is v1 only.
- **Dependencies are finished and consumable**: `l3io-wp-database` (public, rev-pinned) and
  `l3io-wp-config` beneath it. `quote_grant_database` and `quote_identifier` are imported,
  never reimplemented.
- **Stage 1 is complete**: PEP 420 layout under `src/l3io/wp/backup/`, uv packaging at 1.0.0,
  contract gates (`tools/check_purity.py`, `tools/check_mode_defaults.py`, `tests/contracts/`),
  old tree removed, all five CI jobs green locally under act with the working tree intact.

### UX Design Requirements

_Not applicable — this product has no graphical surface. It ships a CLI and an importable Python library; §3.3 of the PRD carries journeys at the lighter scope dial appropriate to that._

### FR Coverage Map

| Requirement | Epic |
|---|---|
| FR-1, FR-2, FR-3, FR-4, FR-5, FR-10 | Epic 2 — Back up a site |
| FR-6, FR-7, FR-8, FR-9, FR-19 | Epic 3 — Restore without destroying it |
| FR-14, FR-15, FR-20, FR-21, FR-27, FR-28 | Epic 4 — Run it unattended |
| FR-22, FR-23, FR-24, FR-30 | Epic 5 — Embed it in Python automation |
| FR-11, FR-12, FR-13, FR-29 | Epic 6 — Move a site to a new URL |
| FR-25, FR-26 | **delivered by Epic 1** (Stage 1) and enforced continuously |
| FR-16, FR-17, FR-18 | **out of scope** — v1.1 (remote storage, retention, scheduling) |
| NFR-1…NFR-8 | cross-cutting; asserted per epic by the contract gates |

## Epic List

| # | Epic | Depends on | Owns exclusively | Stories |
|---|---|---|---|---|
| 2 | **Walking skeleton — back up and prove it** | Epic 1 | `domain/*`, `ports/*`, `cli/parser.py`, `adapters/{tar,subprocess,credentials_transport,lock}` | 8 |
| 3 | **Restore without destroying it** | Epic 2 | `core/restore`, `adapters/{journal,staging}` | 5 |
| 4 | **Archive lifecycle** | Epic 2 | `adapters/crypto`, `domain/archive_format` (v0 classifier), `core/exclusions` | 3 |
| 5 | **Credential providers and readiness** | Epic 2 | `adapters/{credential_providers,preflight}` | 2 |
| 6 | **Embed in Python automation** | Epic 2 | `api/*`, `adapters/tracing` | 4 |
| 7 | **Move a site to a new URL** | Epic 3 | `adapters/{wpcli,config_writer}` | 4 |

```
Epic 1 ──▶ Epic 2 ──┬──▶ Epic 3 ──▶ Epic 7
 (done)  (skeleton) ├──▶ Epic 4
                    ├──▶ Epic 5
                    └──▶ Epic 6
```

**Epics 3, 4, 5 and 6 run in parallel.** Four agents, no shared files.

**Why this shape, and what it costs.** The organising constraint is not story
independence — it is *which files two agents would edit at once*. Under the previous
user-value grouping, `ports/` was touched by five epics and `cli/parser.py` by four, so
parallelism was bounded by merge conflicts rather than by dependencies. Epic 2 exists to
land every shared contract once, behind seams the later epics fill without returning to
them.

That makes Epic 2 a walking skeleton rather than a pure user-value slice, which departs
from the "organise by user value, not technical layers" rule this document was built under.
The departure is deliberate and was requested; the mitigation is that Epic 2 still ships a
working `backup` and `verify` — an operator can use it — so it is a thin vertical slice
rather than a horizontal layer with nothing to demonstrate.

**Two things remain deliberately absent.** *Outward CLI compatibility (AD-22)* is a
constraint on every epic, not a deliverable of one — each epic must preserve the frozen flag
spellings, and each is where a plausible fix would break them. *Supply chain (FR-25, FR-26)*
was delivered by Epic 1 and is enforced continuously by the clean-install gate.

**Sprint split.** Epic 2 is eight stories and gates everything, so it splits: sprint 1 is
the archive path (2.1–2.3), sprint 2 the run machinery (2.4–2.8). Epic 3 carries NFR-1 and
splits at the safety boundary: sprint 1 restore and refusal (3.1–3.2), sprint 2 snapshot,
honest reporting and recoverability (3.3–3.5). Epics 4–7 are single sprints.

---

## Epic 2: Walking skeleton — take a backup and prove it

One operator-visible capability (`backup` and `verify` both working end to end) that necessarily lands every shared contract: the Site Descriptor, the archive format, the `ports/` Protocols, the Run Context, the CLI parser, and the no-op command adapters that make Dry Run structural. **Sequential — it blocks everything else, and that is its job.**

**Owns exclusively:** `domain/*`, `ports/*`, `cli/parser.py`, `adapters/{tar,subprocess,credentials_transport,lock}`

### Story 2.1: Produce an archive of a site's files and database

**Implements:** FR-1


As an operator,
I want one command to capture my whole WordPress site into a single file,
So that I have something to restore from.

**Acceptance Criteria:**

**Given** a Site Root containing a readable `wp-config.php`
**When** a backup runs naming only that directory
**Then** one Archive is produced containing a Dump, the Site Root tree and a Manifest
**And** the Site is byte-identical afterwards — file mtimes, database contents and `wp-config.php` unchanged
**And** the Archive becomes visible at its destination only once complete and verifiable (NFR-2)
**And** no step reads the whole Archive or Dump into memory (AD-21)

### Story 2.2: Choose what the backup covers

**Implements:** FR-2


As an operator,
I want to back up only the files or only the database,
So that I can take a fast partial backup when that is all I need.

**Acceptance Criteria:**

**Given** the documented Backup Scope values `files`, `db` and `all`
**When** each one is passed
**Then** the behaviour matches the name, and no accepted value silently falls through to another
**And** `db` produces a complete Archive containing a Dump and a Manifest, never a loose dump file and no Archive
**And** `files` produces an Archive whose Manifest records that no Dump is present

### Story 2.3: Verify an archive without touching a site

**Implements:** FR-3


As an operator,
I want to check that an archive is still good,
So that I find out before a restore rather than during one.

**Acceptance Criteria:**

**Given** an Archive produced by this tool
**When** verification runs
**Then** it reports pass or fail and makes no write outside its own temporary workspace
**And** a truncated or corrupted Archive fails
**And** a Manifest declaring a Dump that is absent is a verification failure, not a restore-time surprise
**And** verification runs automatically before any destructive restore step

### Story 2.4: Supply credentials without exposing them

**Implements:** FR-15


As an operator,
I want database credentials never to appear where another user or a log reader can see them,
So that backing up a site does not leak the site.

**Acceptance Criteria:**

**Given** any invocation of `mysqldump` or `mysql`
**When** the argument vector is constructed
**Then** it contains no password — asserted against the vector itself, not by reading the call site
**And** credentials travel in a `[client]` option file at mode `0600` in the per-Run workspace, passed as `--defaults-file` before any other option
**And** `--defaults-extra-file` is never used, because it is additive and an ambient `~/.my.cnf` can silently redirect the run to another server
**And** `MYSQL_PWD` is never used
**And** the option file is removed on both the success and the failure path, and its mode and removal are asserted
**And** no credential appears in any log record at any level, asserted against captured structured and stdlib records across a full backup and a full restore
**And** every `repr` and any exception raised to a caller is clean — a traceback is log output under another name

### Story 2.5: Trace a run end to end by one identifier

**Implements:** FR-20


As an operator,
I want every line a run emits to carry the same identifier,
So that I can pull one run out of a week of logs.

**Acceptance Criteria:**

**Given** any run
**When** it emits records
**Then** every record carries the same Run ID, including those emitted around subprocess boundaries
**And** the Run ID is reported at the start and end of the run
**And** logging is configured once at a composition root and never in a library module
**And** `wpconfigr`'s stdlib records are pulled into the same structured stream without that package taking a logging dependency (AD-2, AD-10)
**And** a library caller can bind their own correlation ID and see it on these records
**And** each phase emits `phase`, `duration_ms`, `exit_code` and `bytes` as fields, so `jq` over a log file is sufficient

### Story 2.6: Branch automation on what happened

**Implements:** FR-21


As an operator,
I want the exit code to tell me which kind of failure occurred,
So that my scheduler can retry a transient fault and alert on a real one.

**Acceptance Criteria:**

**Given** any run
**When** it ends
**Then** success exits 0 and every failure path exits non-zero
**And** documented distinct codes separate at minimum usage error, verification failure, missing external dependency, credential failure, lock conflict and operation failure
**And** invoking with no subcommand is an error, not a silent success
**And** no failure path returns a value the process then discards
**And** the code table lives in `domain/` as the source of truth, not scattered across the CLI

### Story 2.7: Rehearse any destructive operation

**Implements:** FR-19


As an operator,
I want to see what a restore would do before it does it,
So that I can check the plan against a production site safely.

**Acceptance Criteria:**

**Given** any operation that can modify a Site or a Storage Target
**When** it runs as a Dry Run
**Then** verification, credential resolution, preflight and planning all execute for real
**And** the actions it would take are reported in order
**And** the Site and every Storage Target are unchanged afterwards
**And** no `if dry_run:` conditional exists anywhere outside a composition root — a Dry Run binds real queries and no-op commands (AD-4)

### Story 2.8: Prevent two runs colliding on one site

**Implements:** FR-28


As an operator,
I want a second run against the same site to refuse,
So that an overrunning nightly job cannot race a manual restore.

**Acceptance Criteria:**

**Given** a run holding the lock for a Site
**When** a second run targets the same Site
**Then** it exits non-zero naming the holder, and changes nothing
**And** the lock is keyed on the canonical absolute Site Root path
**And** the lock is held **outside** the Site Root, so no restore scope can delete the lock it is holding
**And** it is acquired by the outermost composition root before the first phase and released in a `finally`
**And** a lock whose holding process is gone is reclaimable with a logged warning; a live one is an error
**And** it binds CLI and library callers identically

---

## Epic 3: Restore a site without destroying it

The safety work, and the epic where getting it wrong destroys a customer's site.

**Owns exclusively:** `core/restore`, `adapters/{journal,staging}`

### Story 3.1: Restore files and database from an archive

**Implements:** FR-6


As an operator,
I want to put an archive back onto a site,
So that I can recover from a bad change.

**Acceptance Criteria:**

**Given** a declared Restore Mode
**When** the restore runs
**Then** the declared mode governs the whole run and is never re-defaulted by a sub-step
**And** each documented mode is reachable and does exactly what its name says
**And** a mode that does not name file removal removes no files; one that does not name database removal drops nothing
**And** phases execute as a subsequence of the ordered `RestorePhase` enum, so reordering is unrepresentable (AD-17)
**And** a test exists per mode asserting both what it touches and what it does not

### Story 3.2: Refuse to overwrite a non-empty target

**Implements:** FR-7


As an operator,
I want the tool to stop rather than guess when the target already has content,
So that a mistyped path does not delete a live site.

**Acceptance Criteria:**

**Given** a Site Root that is not empty, or an existing database
**When** a restore is attempted without explicit authorization for that specific destruction
**Then** the run exits non-zero, changes nothing, and names the flag that would authorize it
**And** authorization is specific — a flag permitting file replacement does not thereby permit dropping the database
**And** the flag combination maps through one total function with no default branch (AD-25)
**And** `--cleanfirst` without `--force` against a non-empty target refuses

### Story 3.3: Take a safety snapshot before destroying anything

**Implements:** FR-8


As an operator,
I want the tool to capture what is there before it overwrites it,
So that a bad restore is reversible.

**Acceptance Criteria:**

**Given** a destructive restore against an existing Site
**When** the run begins
**Then** a Safety Snapshot Archive is written before the first destructive operation
**And** it is verified after writing, and encrypted when encryption is configured
**And** its scope is derived from the Restore Mode, covering everything that mode may destroy
**And** it is written outside the Site Root and outside any web-served directory, and its path is reported
**And** if it cannot be written and verified, the destructive restore does not proceed
**And** opting out is explicit and recorded in the run's logs

### Story 3.4: Report honestly what the database restore did

**Implements:** FR-9


As an operator,
I want to know whether the database was actually restored,
So that I am not told "done" when nothing happened.

**Acceptance Criteria:**

**Given** a restore covering the database
**When** it completes
**Then** it either restored, or exited non-zero stating why
**And** encountering an existing database is never silently treated as success
**And** it reports which of the database and user it created
**And** every existence check uses administrator credentials — a failed login by the account being provisioned is evidence about the account, never about the database (AD-29)
**And** any `GRANT` escapes `_` and `%` in the database name via the shared function imported from `l3io-wp-database` (AD-28)

### Story 3.5: Survive being killed mid-restore

**Implements:** NFR-1 (AD-18) — the recoverability guarantee FR-9 reports on


As an operator,
I want an interrupted restore to leave my site recoverable,
So that a power cut does not silently produce a half-restored site that still boots.

**Acceptance Criteria:**

**Given** a restore interrupted at any phase
**When** the operator looks at the site
**Then** a durable Run Journal records the phase that was interrupted and what would undo it
**And** a later run refuses to proceed until that journal is resolved, naming the interrupted phase
**And** `wp-config.php` is written to a temporary file and `os.replace`d, so a partial config is never observable
**And** the Dump loads into a staging database, with the live name switched only by that atomic write after the load is checked
**And** an interrupted load therefore leaves the live site on its original database, untouched

---

## Epic 4: Archive lifecycle — exclusions, legacy reads, encryption

Fills three seams the skeleton left open, each behind a port it does not share.

**Owns exclusively:** `adapters/crypto`, `domain/archive_format` (v0 classifier only), `core/exclusions`

### Story 4.1: Exclude paths that should not be in a backup

**Implements:** FR-5


As an operator,
I want caches and logs left out of my archive,
So that backups stay small and restores do not resurrect stale state.

**Acceptance Criteria:**

**Given** a documented default exclusion set
**When** a backup runs
**Then** the set is enumerable at runtime and overridable
**And** an excluded path is absent from the Archive and recorded as excluded in the Manifest
**And** `wp-config.php` is never excluded, by any rule

### Story 4.2: Read an archive written before the rewrite

**Implements:** FR-10


As an operator,
I want my existing `.tar.gz` backups to still restore,
So that the upgrade does not strand everything I already hold.

**Acceptance Criteria:**

**Given** a manifest-less archive containing `database.sql` and `wp-root/`
**When** it is read
**Then** it is detected as v0 and handled by default, with no opt-in flag (AD-23)
**And** its verification reports `STRUCTURAL_ONLY` rather than claiming integrity it cannot compute
**And** format detection happens in one place, by inspection, never inferred from the filename
**And** nothing in the product writes the v0 format

### Story 4.3: Encrypt an archive at rest

**Implements:** FR-4


As an operator,
I want my archive encrypted,
So that a file containing every user record is not readable by whoever finds it.

**Acceptance Criteria:**

**Given** a supplied passphrase
**When** a backup runs with encryption
**Then** the Archive yields no plaintext database or file content to an inspector without the key
**And** the KDF salt and parameters are recorded in the unencrypted Manifest, and the key never is
**And** a wrong passphrase raises a distinct named error, not a generic corruption error (key commitment)
**And** the passphrase never appears in process arguments
**And** the passphrase resolution chain is shared verbatim by the CLI and the library (AD-26)

---

## Epic 5: Credential providers and environment readiness

Deliberately small. Both stories are additive to seams the skeleton already owns, so they parallelize cleanly rather than justifying a bigger epic.

**Owns exclusively:** `adapters/{credential_providers,preflight}`

### Story 5.1: Source credentials from somewhere other than the command line

**Implements:** FR-14


As an operator,
I want credentials to come from my environment or the site's own config,
So that I do not have to put them in a cron line.

**Acceptance Criteria:**

**Given** the declared resolution order — explicit argument, environment, `wp-config.php`
**When** credentials are needed
**Then** resolution is deterministic and documented, and each source is selectable from both the CLI and the library
**And** resolution is an explicit call returning a frozen value, never a property getter performing I/O (AD-9)
**And** no provider silently substitutes one credential for another — absent admin credentials is an error naming what is missing
**And** a library caller can supply their own provider without subclassing an internal type

### Story 5.2: Fail before starting when a required tool is missing

**Implements:** FR-27


As an operator,
I want to be told up front that `wp` or `mysqldump` is absent,
So that I do not discover it halfway through a restore.

**Acceptance Criteria:**

**Given** a plan that requires external binaries
**When** the run begins
**Then** every required tool is checked before the first effect, not at the point of use
**And** a missing tool aborts with nothing changed, names the tool, and states why it was needed
**And** required tools and their minimum versions are documented, and a diagnostic command reports what is present
**And** an absent optional Python dependency raises a package-owned error naming the extra, rather than being folded into binary preflight

---

## Epic 6: Embed it in Python automation

The PRD's stated wager, and what SM-1 measures.

**Owns exclusively:** `api/*`, `adapters/tracing`

### Story 6.1: Drive backup and restore from Python

**Implements:** FR-22


As a DevOps engineer,
I want to import this and call it,
So that I can embed it in a provisioning pipeline without shelling out.

**Acceptance Criteria:**

**Given** the installed distribution
**When** a caller imports it
**Then** backup, restore, verification and pruning are all available without invoking a subprocess or parsing output
**And** the public API is fully annotated and passes `mypy --strict`
**And** every operation available on the CLI is available through the API
**And** constructing a Site Descriptor with invalid or incomplete values fails at construction with a named error, not at use
**And** `py.typed` ships

### Story 6.2: Catch typed failures

**Implements:** FR-23


As a DevOps engineer,
I want failures to arrive as exceptions I can catch by type,
So that I can branch on what went wrong.

**Acceptance Criteria:**

**Given** any documented failure mode
**When** it occurs
**Then** it raises a documented exception type exported from this package, descending from one base
**And** no exception from a dependency or the stdlib crosses the public boundary — each is caught and re-raised with `raise ... from`
**And** exceptions carry structured fields, not only a formatted message
**And** no exception message contains a credential

### Story 6.3: Know what is public and what is not

**Implements:** FR-24


As a DevOps engineer,
I want to know which names I can rely on,
So that a patch release does not break my pipeline.

**Acceptance Criteria:**

**Given** the package
**When** a caller inspects it
**Then** the public surface is enumerable via `__all__` and documented
**And** internal modules are identifiable as internal by layer, regardless of underscore convention
**And** the distribution ships no `__init__.py` at `l3io/` or `l3io/wp/`, asserted in the source tree, the built wheel and an installed tree alongside a sibling on a different `sys.path` entry (AD-27)

### Story 6.4: See spans in a pipeline that already has tracing

**Implements:** FR-30


As a DevOps engineer whose application already runs an OpenTelemetry SDK,
I want this library's work to appear as spans,
So that I see it in the trace I already collect.

**Acceptance Criteria:**

**Given** a host application with a configured SDK
**When** a run executes
**Then** spans appear — one root per Run, one child per phase, never one per file
**And** with no SDK configured the instrumentation is a no-op: no output, no error, no measurable cost
**And** a base install depends on `opentelemetry-api` only; the SDK and exporter are an optional extra
**And** `process.command_args` is recorded only after the same redaction the logs use — one implementation, not two
**And** log records carry flat `trace_id` and `span_id` fields when, and only when, a span is recording
**And** phase fields are emitted as logs whether or not tracing is configured — tracing is never the only way to see what a run did

---

## Epic 7: Move a site to a new URL

The largest greenfield block, and the one capability that most distinguishes this from `mysqldump | tar`. Needs Epic 3's restore path.

**Owns exclusively:** `adapters/{wpcli,config_writer}`

### Story 7.1: Point a restored site at a new host and database

**Implements:** FR-11


As an operator,
I want to restore to a different database or URL,
So that I can stand up staging from a production archive.

**Acceptance Criteria:**

**Given** new values for database host, name, credentials, site URL or home URL
**When** a relocating restore runs
**Then** each supplied value reaches the restored `wp-config.php`, and each omitted one leaves its constant unchanged
**And** every relocation option exposed on the CLI has an observable effect — none is accepted and discarded
**And** the rewritten file remains valid PHP and preserves constants this tool does not manage
**And** the write is verified by reading back the rendered value span, not a canonically re-rendered statement, and not values round-tripped through `get()` (ADR-0010)
**And** a mismatch fails the restore before the atomic replace, leaving the original byte-identical

### Story 7.2: Restore a site whose config lives outside the site root

**Implements:** FR-29


As an operator who keeps `wp-config.php` one level up,
I want that layout to restore correctly,
So that following WordPress's own hardening advice does not break backups.

**Acceptance Criteria:**

**Given** an archive whose config is outside the Site Root
**When** it is restored
**Then** the config is carried as an enumerated `config`-role member, never as a `../` path
**And** its original location is Manifest metadata, not an archive path
**And** extraction still refuses any member that escapes the destination (AD-11)
**And** a v0 archive, having no Manifest, yields `config_path` of `None` and uses the default location rather than inventing one

### Story 7.3: Rewrite content URLs without corrupting serialized data

**Implements:** FR-12


As an operator,
I want the restored site's content to point at the new URL,
So that widgets, menus and theme options still work.

**Acceptance Criteria:**

**Given** a relocation to a new URL
**When** the content rewrite runs
**Then** it is delegated to WP-CLI's `search-replace`, never a SQL `REPLACE`
**And** afterwards no row in `wp_options`, postmeta or `wp_posts.post_content` contains the old site URL
**And** serialized values that contained it remain valid and can be unserialized — byte-length prefixes recomputed
**And** the rewrite is reported: replacements made, tables touched
**And** a Dry Run reports the replacements it would make and makes none
**And** it runs after the config rewrite, because `wp` bootstraps from the config just written (AD-17)

### Story 7.4: Fail before touching anything when WP-CLI is missing

**Implements:** FR-13


As an operator,
I want to be told WP-CLI is absent before the restore starts,
So that I never end up with files restored and content URLs still pointing at production.

**Acceptance Criteria:**

**Given** a requested relocation
**When** WP-CLI is unavailable
**Then** it is detected before the first destructive step, and the run refuses
**And** the failure names WP-CLI, states why it was needed, and points at installation guidance
**And** a non-relocating restore does not require WP-CLI at all
**And** no partial relocation — config rewritten, content not — can result from its absence
