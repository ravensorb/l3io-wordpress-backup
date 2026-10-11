---
title: wpbackup2 — WordPress Backup and Relocation for Automation
status: final
created: 2026-09-12
updated: 2026-09-14
---

# PRD: wpbackup2 — WordPress Backup and Relocation for Automation
*Working title — confirm.*

## 0. Document Purpose

This PRD is for the maintainer, contributors, and the downstream BMad workflows (UX, architecture, epics and stories) that will build from it. It is **forward-looking**: it describes the product wpbackup2 is meant to become, informed by — but not limited to — the 909 lines of package source that exist today at v0.2.21 (1,265 including the test suite). The architectural review at `_bmad-output/implementation-artifacts/arch-review-2026-09-12.md` is an input, not an appendix; where that review found a defect that represents a missing *capability* (credential handling, restore-mode semantics, dependency resolvability), the capability appears here as a requirement rather than as a bug.

Structure: vocabulary is anchored in the Glossary (§4) and used verbatim throughout; features are grouped with functional requirements nested and numbered globally (FR-1…FR-30) so downstream artifacts have stable references — numbers are assigned on creation, so FR-28 and FR-29 sit where they were inserted rather than in sequence; inferences are tagged inline as `[ASSUMPTION]` and indexed in §16. Technical mechanism, rejected alternatives, and the competitive matrix live in `addendum.md` alongside this file — they inform architecture, they are not product requirements.

Several of the structural claims this section makes about itself are enforced by `check_prd.py` next to this file rather than by a reader's diligence: the FR and SM ranges, contiguous numbering with no gaps, every requirement placed in a release phase, every `Q-n` mentioned anywhere having an entry in §15, and §16's open-assumption count matching the tags left in the body. What it does **not** check: whether a §-pointer leads somewhere relevant, whether a question's entry actually resolves it, or whether requirements shared between Release A and v1.0 belong in both. Run it after editing; read the rest yourself.

No UX document exists yet, and the product has no graphical surface.

## 1. Vision

Self-hosted WordPress operators have two credible options for backup, and both make them choose. The plugin ecosystem — UpdraftPlus, Duplicator, All-in-One WP Migration — is excellent and WordPress-admin-first, but its command-line story is uneven and added after the fact: UpdraftPlus puts WP-CLI control behind its Premium tier, while All-in-One WP Migration ships a free CLI and paywalls remote storage instead. In every case the CLI follows the admin screen rather than leading. At the other end, an operator writes their own `mysqldump | restic` script, which gives them encryption and remote storage but treats WordPress as an opaque directory: nothing understands `wp-config.php`, nothing can put a site back on a different host, and every operator writes the same script again.

**wpbackup2 is a WordPress backup and relocation tool built for automation first.** It takes a complete, verifiable, encrypted archive of a site — database and files — and puts that archive back on the same host or a different one, rewriting the configuration and the content URLs so the restored site actually works. It ships as a command-line tool for operators and as a typed Python library for the people who embed it in provisioning pipelines, lifecycle hooks and scheduled jobs. Both are supported contracts.

The wager is specific: **the underserved position is not "another backup tool", it is an idiomatic Python API for WordPress backup and relocation.** WP-CLI is the mature substrate for the database work and for the one genuinely hard problem in this space — rewriting URLs without corrupting PHP-serialized data — and wpbackup2 delegates to it rather than reimplementing it. What wpbackup2 adds is everything around that: the archive format, integrity and encryption, credential sourcing that does not put passwords in `argv`, relocation as a first-class operation, and a programmatic surface that a DevOps engineer can import without shelling out and parsing strings.

Because this is a backup tool, one quality attribute outranks the rest and is stated here rather than buried in §7: **a restore must never leave a site worse off than not running it.** Every destructive capability is opt-in, reversible where it can be, and refused where it cannot be made safe.

## 2. Why Now

Timing is load-bearing, in a way that is unusual for a version 0.2 utility.

**The published package does not install.** Two of three runtime dependencies — `chesney` and `wpconfigr` — return HTTP 404 from PyPI. `pip install wpbackup2` cannot resolve, there is no lockfile pinning what once worked, and the test suite therefore cannot run in a clean environment. Every user acquired before that point is on a version they can no longer reinstall or reproduce.

The two causes differ. `chesney` is gone and its feature is cut (§13.1). The configuration reader is not gone: upstream renamed and republished it as `wpconfigger` in 2022 after hitting this same install failure, and a fork of the pre-rename code sits in the sibling repository `py-wpconfigr` — 343 lines, no runtime dependencies of its own. This project publishes that fork as **`l3io-wp-config`** with corrected authorship and a credit to the MIT original (ADR-0012), rather than claiming a name whose history belongs to someone else. The product is offline for want of a release, not for want of code.

That makes the timing argument narrower but not weaker. Publishing `wpconfigr` restores resolvability cheaply; what it does not do on its own is prevent a recurrence, pin what resolved, or address the dependencies inherited further down the graph (§9). A public launch is the moment those are worth doing together, because each one is nearly free while `pyproject.toml` is already open and expensive to retrofit afterward.

## 3. Target User

### 3.1 Jobs To Be Done

`[ASSUMPTION]` This entire section — the operator profile, the site scale, and the incidental detail in the §3.3 journeys — is inferred from the shape of the existing CLI and its AWS hooks, not from user research, interviews or telemetry. No such research exists. Names and numbers are illustrative and should be read as a hypothesis to be tested, not as findings. See §16.

- **Sleep through the night.** I run WordPress sites I am responsible for, and I need to know a recoverable copy exists without thinking about it.
- **Undo a bad afternoon.** A plugin update, a botched edit, or a compromise happened. I want the site back as it was an hour ago, and I want to know the restore worked before I find out from a user.
- **Move a site without a day of work.** Production to staging, one host to another, one URL to another — including the content URLs, not just the config file.
- **Automate it in the language my tooling is already written in.** My provisioning is Python. I want to `import` this and get typed objects and exceptions, not build a command string and parse stdout.
- **Not hand a database to the wrong person.** The archive contains every user record on the site. I need it encrypted at rest and I need credentials that never appear in `ps` output or a log file.
- **Prove the backup is good.** A backup I have not verified is a hope, not a backup.

### 3.2 Non-Users (v1)

- **Managed-WordPress customers** (WP Engine, Kinsta, WordPress.com) — no filesystem or database access, and the host already does this.
- **Operators who want a graphical interface.** There is no admin screen and none is planned; the plugin ecosystem serves this well.
- **Non-WordPress PHP applications.** The product is WordPress-specific by design — `wp-config.php`, the WordPress directory layout, and WordPress's serialized-options problem are the whole point.
- **Operators needing WordPress multisite in v1.** Deferred explicitly; see §13.2.

### 3.3 Key User Journeys

Written at the lighter scope dial: this is a CLI and library with a single operator role, so journeys are short scenes rather than screen flows.

- **UJ-1. Dana's nightly job runs and she never sees it.** Dana runs six client WordPress sites on a single VPS. A systemd timer invokes wpbackup2 at 03:00 per Site; each run writes an encrypted Archive with a Manifest to S3, prunes anything older than the Retention Policy, and exits 0. Dana sees nothing. **Climax:** the only signal she gets is the absence of an alert, because a non-zero exit is what her monitoring watches. **Edge case:** the database is mid-migration and `mysqldump` fails — the run exits non-zero, no partial Archive is published to the Storage Target, and last night's Archive is left untouched.

- **UJ-2. Marcus restores after a plugin update takes the site down.** Marcus, a freelancer, updates a plugin at 16:40 and the site white-screens. He runs a restore against last night's Archive, same host, same URL. wpbackup2 verifies the Manifest, takes a Safety Snapshot of the current state, restores the files and the database, and reports the Run ID. **Climax:** the site loads and he checks the snapshot path is still on disk in case he needs to come back. **Edge case:** he initially forgets the Restore Mode flag; wpbackup2 refuses to overwrite the non-empty Site Root and tells him precisely which flag would authorize it, rather than proceeding.

- **UJ-3. Priya clones production to staging on a different URL.** Priya needs `staging.example.com` to match production. She restores production's Archive into a fresh Site Root with relocation flags for the new URL and database. wpbackup2 rewrites `wp-config.php`, then delegates a serialization-safe search-replace to WP-CLI across the database. **Climax:** she loads the staging site and the widgets, menus and theme options are intact — the thing that breaks when a naive SQL `REPLACE` corrupts serialized data. **Edge case:** WP-CLI is not installed on the staging box; wpbackup2 detects this *before* touching anything, refuses the relocation, and says what to install — it does not perform a partial relocation that leaves content URLs pointing at production.

- **UJ-4. Sam embeds it in a provisioning pipeline.** Sam, an SRE, is writing a Python service that spins up review environments. He imports `wpbackup2`, constructs a Site Descriptor and a Credential Provider that reads from his secret store, and calls restore. He catches a typed exception on failure. **Climax:** no subprocess, no string parsing, no parsing of exit codes — the failure arrives as an exception with structured fields he logs against his own trace ID.

- **UJ-5. Dana finds out the Archive is bad before it matters.** Dana verifies a month-old Archive as a routine check. The Manifest checksum does not match. **Climax:** she learns this from a Verification command that touched nothing, rather than from a restore that had already deleted the live Site Root.

## 4. Glossary

Downstream workflows and readers use these terms exactly. FRs, UJs and SMs use them verbatim; synonyms are a discipline violation.

- **Site** — a single self-hosted WordPress installation: one Site Root plus one database. Cardinality: one Site has exactly one Site Root and one database.
- **Site Root** — the filesystem directory containing the WordPress installation. Contains `wp-config.php` in the default layout.
- **Site Descriptor** — the resolved set of values identifying a Site: Site Root, site URL, site home URL, database host, database name, and a Credential Provider. Produced either by reading `wp-config.php` or by explicit construction.
- **Archive** — a single portable file containing a Dump, the Site Root contents, and a Manifest. The unit of backup and the unit of restore.
- **Manifest** — metadata embedded in an Archive: format version, creation time, source Site Descriptor (credentials excluded), per-member checksums, Dump checksum, and encryption parameters. Enables Verification.
- **Dump** — the logical database export contained in an Archive.
- **Verification** — checking an Archive against its Manifest without writing to any Site. A read-only operation.
- **Backup Scope** — which parts of a Site a backup covers: `files`, `database`, or `all`.
- **Restore Mode** — the declared behavior of a restore: which parts are restored, and whether existing files and database contents are removed first. Every destructive element is named explicitly.
- **Relocation** — restoring a Site to a different URL, database, or host, including rewriting `wp-config.php` constants *and* the database content URLs.
- **Safety Snapshot** — an Archive of the target Site taken automatically immediately before a destructive restore, so the restore is reversible.
- **Credential Provider** — a pluggable source of database credentials: explicit values, environment variables, `wp-config.php`, or an external secret store such as AWS Secrets Manager.
- **Storage Target** — where an Archive is written or read: a local path or a remote target (S3-compatible object storage, SFTP, rsync).
- **Retention Policy** — a rule determining which Archives at a Storage Target are kept and which are pruned.
- **Run** — a single invocation of a backup, restore, verification or prune operation, identified by a Run ID that appears on every log record the invocation emits.
- **Dry Run** — a Run that performs all inspection, validation and planning but makes no change to any Site or Storage Target.
- **WP-CLI** — the external `wp` command-line tool. wpbackup2 delegates serialization-safe database URL rewriting to it.

## 5. Features

### 5.1 Backup

**Description:** Produces a single Archive from a Site. The operator names a Site Root; wpbackup2 resolves a Site Descriptor from `wp-config.php`, exports the database, collects the Site Root contents, computes a Manifest, optionally encrypts, and writes to a Storage Target. Backup is never destructive to the Site. Realizes UJ-1.

**Functional Requirements:**

#### FR-1: Full Site backup

An operator can produce one Archive containing both the Dump and the Site Root contents from a single invocation naming only the Site Root. Realizes UJ-1.

**Consequences (testable):**
- An Archive produced from a Site contains a Dump, the Site Root file tree, and a Manifest.
- The Site is unmodified after a backup Run — file mtimes, database contents and `wp-config.php` are byte-identical.
- Credentials are resolved from `wp-config.php` when no Credential Provider is given explicitly.

#### FR-2: Selective Backup Scope

An operator can restrict a backup to a Backup Scope of `files`, `database`, or `all`. Realizes UJ-1.

**Consequences (testable):**
- Each of the three documented Backup Scope values is accepted and produces the behavior it names — no accepted value silently falls through to a different scope.
- `database` scope produces a complete, well-formed Archive containing a Dump and a Manifest and no Site Root members. It does not leave a loose dump file and no Archive.
- `files` scope produces an Archive whose Manifest records that no Dump is present, and a restore of that Archive does not claim to have restored a database.

#### FR-3: Archive Manifest and Verification

An operator can verify an Archive against its Manifest without writing to any Site. Verification also runs automatically before any restore. Realizes UJ-5, UJ-2.

**Consequences (testable):**
- Every Archive embeds a Manifest containing a format version, creation timestamp, per-member checksums and a Dump checksum.
- A Verification command reports pass or fail and makes no filesystem or database write outside its own temporary working area.
- A corrupted or truncated Archive fails Verification, and a restore of it aborts **before** any destructive step.
- A missing Dump inside an Archive whose Manifest declares one is a Verification failure, not a restore-time surprise.

#### FR-4: Archive encryption at rest

An operator can produce an encrypted Archive using a supplied passphrase or key, and restore from one by supplying the same. Realizes UJ-1.

**Consequences (testable):**
- With encryption requested, the resulting Archive yields no plaintext database content or file content to an inspector without the key.
- Encryption parameters sufficient to decrypt (algorithm, KDF parameters, salt — never the key) are recorded in the Manifest.
- Restoring an encrypted Archive without a key fails with a distinct, named error, not a generic corruption error.
- An operator can encrypt without the passphrase appearing in process arguments.

#### FR-5: Exclusions

An operator can exclude paths within the Site Root from a backup, and a documented default exclusion set covers caches and logs. Realizes UJ-1.

**Consequences (testable):**
- The default exclusion set is documented, enumerable at runtime, and overridable.
- An excluded path is absent from the Archive and recorded as excluded in the Manifest.
- Exclusions never apply to `wp-config.php`.

**Notes:** `[NOTE FOR PM]` The default exclusion set is a judgment call with real consequences — excluding an object-cache directory is obviously right, excluding `wp-content/uploads` never is. Worth an explicit review of the default list before implementation.

### 5.2 Restore

**Description:** Puts an Archive back onto a Site. This is the product's most dangerous operation and carries the most safety machinery: Verification first, Safety Snapshot second, then the restore itself, with every destructive element requiring explicit authorization. Realizes UJ-2.

**Functional Requirements:**

#### FR-6: Restore with an explicit, honored Restore Mode

An operator can declare a Restore Mode, and the declared mode governs the entire Run. Realizes UJ-2, UJ-3.

**The Restore Mode set.** A mode is the composition of two independent choices, and both are named in the mode:

| Mode | Restores files | Restores database | Clears Site Root first | Drops database first |
|---|:--:|:--:|:--:|:--:|
| `files` | ● | | | |
| `files-clean` | ● | | ● | |
| `database` | | ● | | |
| `database-clean` | | ● | | ● |
| `all` | ● | ● | | |
| `all-clean` | ● | ● | ● | ● |

`all` is the default. `all-clean` is reachable only by authorizing both destructions separately — §7.1 forbids a single option that authorizes all destruction at once, which is precisely what today's `--force`→`ALLCLEAN` mapping does (arch review B-3, M-17).

**Consequences (testable):**
- Every mode in the table above is reachable by name, and produces exactly the behavior its row describes. No mode is unreachable, and no mode silently substitutes another.
- A mode that does not name file removal does not remove files; a mode that does not name database removal does not drop or clear the database.
- The mode requested is the mode performed: the value parsed from the CLI reaches the restore operation unmodified, and is recorded in the Run's logs and in the Safety Snapshot's Manifest. (Today it is discarded — arch review B-3.)
- Mode names round-trip: every accepted CLI value maps to exactly one API enum member and back, asserted mechanically against the table rather than a hand-kept list. (Today `--mode db` upper-cases to `DB` and never matches `DATABASE` — arch review M-1.)
- A test exists per row asserting both what that mode does and what it does not touch.

#### FR-7: Refuse destructive restore over a non-empty target

A restore that would overwrite or delete existing content refuses to proceed unless the operator has explicitly authorized that specific destruction. Realizes UJ-2.

**Consequences (testable):**
- Restoring into a non-empty Site Root without explicit authorization exits non-zero, changes nothing, and names the flag that would authorize it.
- Restoring over an existing database without explicit authorization exits non-zero and changes nothing.
- The authorization is specific: a flag authorizing file replacement does not thereby authorize dropping the database.

#### FR-8: Safety Snapshot before destruction

Before any destructive restore step, wpbackup2 captures a Safety Snapshot of the current state of the target Site. Realizes UJ-2.

**Consequences (testable):**
- A destructive restore against an existing Site produces a Safety Snapshot Archive before the first destructive operation.
- The Safety Snapshot path is reported to the operator and is not deleted by the Run that created it.
- If the Safety Snapshot cannot be taken, the destructive restore does not proceed.
- An operator can opt out of the Safety Snapshot explicitly, and doing so is recorded in the Run's logs.

#### FR-9: Database restore that reports what it did

A restore of the database either completes, or fails loudly. It never reports success without having restored. Realizes UJ-2.

**Consequences (testable):**
- When a database restore is skipped for any reason, the Run exits non-zero and the reason is stated.
- Encountering an existing database is not silently treated as success.
- The restore ensures the target database and user exist before loading the Dump, and reports which of those it created.

#### FR-10: Restore is Archive-format aware

A restore refuses an Archive whose Manifest format version it does not support. Realizes UJ-5.

**Consequences (testable):**
- An Archive with a newer major format version is refused with a message naming the version and the supported range.
- An Archive written before v1.0 — a manifest-less `.tar.gz` carrying `database.sql` and `wp-root/` — is detected and restored **by default, permanently**, not behind a legacy opt-in. Having no checksums, its Verification reports `STRUCTURAL_ONLY` rather than claiming an integrity guarantee it cannot make.
- An Archive matching no known shape is refused, naming what was found.

### 5.3 Relocation

**Description:** Restores a Site to a different URL, database or host. This is the capability that distinguishes wpbackup2 from a tar-and-dump script, and the one place where a naive implementation silently corrupts data. Rewriting `wp-config.php` constants is necessary but not sufficient: WordPress stores PHP-serialized values in `wp_options` and postmeta whose byte-length prefixes must be recomputed when embedded URLs change. wpbackup2 delegates that rewrite to WP-CLI's `search-replace`, chosen because it is already present in the target environment and shelling out to it carries no PHP-parser ownership cost — not because it is canonical. `addendum.md` §B holds the evidence, C.1 the alternatives weighed. This section also owns locating the configuration file in the first place, since a Site whose `wp-config.php` is not where it is assumed to be defeats every requirement below. Realizes UJ-3.

**Functional Requirements:**

#### FR-11: Configuration rewriting

An operator can specify a new database host, database name, database credentials, site URL and site home URL, and wpbackup2 writes those into the restored `wp-config.php`. Realizes UJ-3.

**Consequences (testable):**
- Each relocation value supplied by the operator reaches the restored `wp-config.php`; each value not supplied leaves the corresponding constant unchanged.
- Every relocation option exposed on the CLI has an observable effect — no option is accepted and then discarded.
- The rewritten `wp-config.php` remains valid PHP and preserves constants wpbackup2 does not manage.
- The database **port** is a relocation value alongside host, name and credentials. The existing code already writes it; the requirement makes it a declared capability rather than an accident.
- Values round-trip with their PHP types intact: a constant written as a boolean, integer or `null` is not returned as the string `"true"`, `"1"` or `"null"`. This behavior lives in `wpconfigr`, so the test suite asserts it against the dependency rather than assuming it.

#### FR-29: `wp-config.php` outside the default location

wpbackup2 locates and operates on a Site's `wp-config.php` when it is not at the Site Root. Realizes UJ-3.

**Consequences (testable):**
- A Site whose `wp-config.php` sits one level above the Site Root — WordPress's own documented convention — is backed up, restored and relocated correctly.
- The configuration path can be stated explicitly by the operator, and the stated path is used rather than being re-derived.
- A Site whose `wp-config.php` cannot be located fails before any destructive step, naming the paths that were searched.

**Notes:** Carried in from the existing README's TODO list, where it has sat unaddressed; today `WpSite` accepts either a Site Root or a full `wp-config.php` path interchangeably, which is the seam this requirement makes explicit rather than incidental.

#### FR-12: Serialization-safe content URL rewriting

When relocating to a new URL, wpbackup2 rewrites URLs in the database content without corrupting PHP-serialized values, by delegating to WP-CLI. Realizes UJ-3.

**Consequences (testable):**
- After a relocation to a new URL, no row in `wp_options` or postmeta contains the old site URL.
- Serialized values containing the old URL remain valid and unserialize cleanly after the rewrite — length prefixes are correct.
- The rewrite is reported: number of replacements, tables touched.
- A Dry Run reports the replacements it would make and makes none.

#### FR-13: Honest failure when WP-CLI is unavailable

If WP-CLI is required for a requested Relocation and is not available, wpbackup2 detects this before making any change and refuses. Realizes UJ-3.

**Consequences (testable):**
- WP-CLI availability is checked before the first destructive step of a relocating restore, not at the point of use.
- The failure names WP-CLI, states why it is needed, and points at installation guidance.
- A non-relocating restore does not require WP-CLI.
- A partial relocation — config rewritten, content URLs not — never results from a WP-CLI absence.

**Feature-specific NFRs:**
- The WP-CLI invocation must pass credentials without exposing them in process arguments (see FR-15).

### 5.4 Credentials and Secrets

**Description:** Database credentials reach `mysqldump`, `mysql` and WP-CLI without ever appearing where another user on the machine, or a log reader, can see them. Credentials come from a Credential Provider, which is pluggable — explicit values, environment, `wp-config.php`, or an external secret store. Realizes UJ-1, UJ-4.

**Functional Requirements:**

#### FR-14: Pluggable Credential Providers

An operator can source database credentials from explicit values, environment variables, `wp-config.php`, or an external secret store; a library caller can supply a custom provider. Realizes UJ-4.

**Consequences (testable):**
- Each built-in provider resolves credentials and is selectable from both the CLI and the library.
- AWS Secrets Manager is supported as a provider, and its dependencies are optional — a base install pulls no AWS libraries, **including transitively**. This requires `boto3` to become an optional extra in the sibling `wpdatabase2` package, where it is currently a hard runtime dependency; that change is a named Release A precondition with an owner (§13.2), not an assumption.
- A library caller can implement and pass a provider without subclassing internal types.
- Provider resolution order is documented and deterministic.

#### FR-15: Credentials never exposed in process arguments or logs

No credential ever appears in a subprocess argument vector or in any log record at any level. Realizes UJ-1, UJ-4.

**Consequences (testable):**
- No invocation of `mysqldump`, `mysql` or `wp` includes a password in `argv`; a test asserts this by inspecting the constructed argument vector.
- No log record at any level, including debug, contains a credential value; a test asserts this against captured log output for a full backup and a full restore.
- Where a command line is logged for diagnosis, credential-bearing elements are redacted with a visible marker.
- Any temporary file carrying credentials is created with owner-only permissions and removed on both success and failure.
- There is no implicit fallback to administrative credentials. Today `WpSite` silently defaults the admin credential to the site credential; where an operation genuinely needs elevated rights (database or user creation, FR-9), the operator supplies them explicitly and their absence is a refusal with a named cause, not a silent substitution.

### 5.5 Archive Storage and Lifecycle

**Description:** Archives are written to and read from Storage Targets — local or remote — and pruned according to a Retention Policy. Getting the Archive off the machine is part of the product, because an Archive on the same disk as the Site is not a backup. Realizes UJ-1.

**Functional Requirements:**

#### FR-16: Local and remote Storage Targets

An operator can write an Archive to, and restore one from, a local path or a remote Storage Target. Realizes UJ-1.

**Consequences (testable):**
- Each supported target is usable for both write and read. Which targets ship is decided by demand at v1.1 rather than guessed now (Q-2); the recorded default is to delegate to `rclone` rather than own three protocol integrations.
- A Storage Target is addressable as a single string in both the CLI and the library.
- Remote target credentials are handled under the same rules as FR-15.
- A failed upload does not leave a partial Archive visible at the target as if it were complete.

#### FR-17: Retention Policy and pruning

An operator can declare a Retention Policy for a Storage Target, and wpbackup2 prunes Archives that fall outside it. Realizes UJ-1.

**Consequences (testable):**
- Retention is expressible by count and by age.
- Pruning never removes the most recent Archive that passes Verification.
- A Dry Run lists exactly which Archives would be pruned and removes none.
- Pruning is reported: what was removed, what was kept, and why.

#### FR-18: Scheduled operation

An operator can run wpbackup2 on a schedule without writing an orchestration script. Realizes UJ-1.

**Consequences (testable):**
- A scheduled configuration can express: which Sites, which Backup Scope, which Storage Target, which Retention Policy.
- A failed scheduled Run exits non-zero and does not publish a partial Archive.
- Concurrent-Run prevention is **not** part of this requirement; it is FR-28, and ships in v1.0 whether or not a scheduler ever does.

**Notes:** `[NOTE FOR PM]` This is the weakest-fit capability in the selected set, and the review should be deliberate. `cron` and `systemd` timers already do scheduling well, operators already have opinions about them, and owning a scheduler means owning process supervision, missed-run semantics and time zones. The genuinely product-shaped part is the *declarative site configuration* (which sites, which policy) — that could ship without a scheduler, invoked by the operator's own timer. Cut to v1.1 in §13.2, and the concurrency guarantee that mattered was extracted into FR-28 so it ships in v1.0 regardless.

### 5.6 Safety, Observability and Exit Behavior

**Description:** Cross-cutting behavior that makes the product usable in automation: a real Dry Run, structured logs correlated by Run ID, exit codes that mean something, and a guarantee that two Runs never touch one Site at once. Realizes UJ-1, UJ-4.

**Functional Requirements:**

#### FR-19: Dry Run across every destructive operation

An operator can request a Dry Run of any operation, and the Dry Run performs all validation and planning while making no change. Realizes UJ-1, UJ-3.

**Consequences (testable):**
- Every operation that can modify a Site or a Storage Target supports a Dry Run.
- A Dry Run performs Verification, credential resolution, WP-CLI availability checks and relocation planning — the checks, not just the writes, are exercised.
- A Dry Run reports the actions it would take, in order.
- After a Dry Run, the Site and every Storage Target are unchanged.

#### FR-20: Structured logging correlated by Run ID

Every log record carries a Run ID, and log output is machine-parseable. Realizes UJ-1, UJ-4.

**Consequences (testable):**
- Every record emitted by a Run carries the same Run ID, including records emitted around subprocess boundaries.
- A structured output format is selectable, and human-readable output is the default for interactive use.
- The Run ID is reported to the operator at the start and end of a Run.
- A library caller can bind their own correlation ID and see it on wpbackup2's records.
- Operator-selectable verbosity is part of the CLI contract, consistent across `wpbackup2`, `wpconfigr` and `wpdatabase2`, and raising it never causes a credential to appear (NFR-3, FR-15).

#### FR-30: Optional distributed tracing, inert unless a host configures it

A library caller whose application already runs an OpenTelemetry SDK sees wpbackup2's work as spans in their existing pipeline, with no configuration on wpbackup2's part. An operator running the CLI is never asked to configure anything. Realizes UJ-4.

**Consequences (testable):**
- A base install depends on `opentelemetry-api` only, never the SDK. With no SDK configured the instrumentation is a no-op: no output, no error, no measurable cost.
- Spans follow the restore and backup phases — one root span per Run, one child per phase — never one per file.
- A span attribute carrying a command line is redacted by the same code path that redacts logs (FR-15). There is exactly one redaction implementation.
- Log records carry `trace_id` and `span_id` as flat fields when, and only when, a span is recording.
- Every phase emits `phase`, `duration_ms`, `exit_code` and `bytes` as structured log fields **whether or not tracing is configured** — tracing is never the only way to see what a Run did.
- The SDK and any exporter are an optional extra; installing the base package pulls neither.

#### FR-28: Concurrent Runs against the same Site are prevented

Two Runs cannot operate on the same Site at once. Realizes UJ-1.

**Consequences (testable):**
- A Run acquires a lock identified by the Site before its first read of Site state, and releases it on success, on failure, and on signal.
- A second Run against a locked Site exits non-zero without touching the Site, and names the holding Run's ID and start time.
- A stale lock — one whose holding process no longer exists — is detected and reclaimed rather than requiring manual removal.
- Locking is independent of how the Run was started: the guarantee holds for a `cron` entry, a `systemd` timer, a shell, and a library caller alike.

**Notes:** Extracted from FR-18 because UJ-1, the flagship journey, is an unattended 03:00 timer, and the tool it describes does `rmtree` and database drops. A v1.0 whose intended use is scheduled invocation cannot make concurrency safety contingent on shipping a scheduler.

#### FR-21: Meaningful exit codes

The process exit code communicates the outcome. Realizes UJ-1.

**Consequences (testable):**
- A successful Run exits 0; every failure path exits non-zero.
- Invoking with no operation is an error, not a silent success.
- Documented, distinct exit codes separate at minimum: usage error, Verification failure, missing external dependency, credential failure, and operation failure.
- No failure path returns a value that the process then discards.

### 5.7 Python API

**Description:** The importable surface is a supported product, not an implementation detail exposed by accident. It is typed, its exceptions are part of the contract, and it does not require callers to build command strings. Realizes UJ-4.

**Functional Requirements:**

#### FR-22: Typed, importable API

A Python caller can perform backup, restore, verification and pruning through imported objects without invoking a subprocess or parsing output. Realizes UJ-4.

**Consequences (testable):**
- The public API is fully type-annotated and passes a strict type check.
- Every operation available on the CLI is available through the API.
- The API accepts and returns domain objects; it does not require the caller to construct CLI argument lists.
- Constructing a Site Descriptor with invalid or incomplete values fails at construction with a named error, not at use.

#### FR-23: Exception contract

Failures reach a library caller as typed exceptions carrying structured detail. Realizes UJ-4.

**Consequences (testable):**
- Every documented failure mode maps to a documented exception type exported from the package.
- Exceptions carry structured fields, not only a formatted message.
- No exception message contains a credential.
- The package does not raise a dependency's exception types across its own public boundary.
- Every exception type exported from the package has at least one reachable raise site, asserted mechanically. An exported type that nothing raises is either wired up or removed — today `WpBackupNotFoundError` is public API that no code path can produce.

#### FR-24: Declared public surface

The package declares what is public and what is internal. Realizes UJ-4.

**Consequences (testable):**
- The public surface is enumerable and documented.
- Internal modules are identifiable as internal by naming or export convention.
- Changes to internal modules do not require a major version bump; changes to the public surface do (see §10).

### 5.8 Distribution and Supply Chain

**Description:** The package installs, from a locked and reproducible dependency set, on every supported Python version. The review's finding that the published version is uninstallable is not a bug to fix once; resolvability is a standing requirement with a mechanical check. Realizes every journey, in the sense that none of them are possible otherwise.

**Functional Requirements:**

#### FR-25: Resolvable, reproducible installation

`pip install wpbackup2` succeeds from a clean environment on every supported Python version, and a committed lockfile makes a development install reproducible.

**Consequences (testable):**
- A clean-environment install from the published artifact succeeds in CI, on every supported Python version, on every release.
- A lockfile is committed and CI installs frozen from it.
- Every runtime dependency resolves from its declared index at release time; a dependency that cannot resolve fails the release, not the user.
- Optional capabilities (AWS, remote targets) are optional extras and their absence does not break a base install.
- Installing the package puts a `wpbackup2` command on `PATH` via a declared console entry point, and CI asserts it runs. Every journey in §3.3 assumes this; today the package declares none, so operators must invoke `python -m`.

#### FR-26: Dependency policy

Runtime dependencies are bounded, maintained, and recorded.

**Consequences (testable):**
- Every runtime dependency has an upper bound that excludes an unreviewed major version.
- A dependency inventory records, per dependency, its license and why it is present.
- No pre-1.0 runtime dependency is carried without a recorded decision and a named exit plan.
- No runtime dependency in the graph, direct or transitive, is an abandoned or superseded distribution. Specifically: the transitive dependency on `mysql-connector` (2.2.9, last released 2019-04-01 — the superseded Oracle-uploaded name) is replaced by the maintained `mysql-connector-python`, or by another actively maintained driver.
- A mechanical check fails the build when a declared runtime dependency is unresolvable, unbounded, or has had no release within a documented staleness window.

#### FR-27: External tool dependency declaration

Dependence on external binaries — `mysqldump`, `mysql`, `wp` — is declared, detected and reported.

**Consequences (testable):**
- Required external tools are documented with minimum versions.
- Absence of a required external tool is detected before any destructive step and reported by name.
- A diagnostic command reports which external tools are present and their versions.

## 6. Cross-Cutting Non-Functional Requirements

- **NFR-1 · Data integrity is the paramount attribute.** No operation may leave a Site in a state worse than not having run it. Where that cannot be guaranteed, the operation refuses rather than proceeds. This outranks every other quality attribute in this section and every convenience consideration in §5.
- **NFR-2 · Atomicity of published artifacts.** An Archive is visible at a Storage Target only once complete and verifiable. Partial Archives are never presented as usable.
- **NFR-3 · Least privilege and secret hygiene.** Credentials live in memory, in owner-only temporary files, or in the environment of a child process — never in `argv`, never in logs, never in an Archive's Manifest.
- **NFR-4 · Idempotence and safe retry.** A failed Run leaves no state that makes a subsequent Run unsafe. Temporary working areas are per-Run and cleaned on both success and failure.
- **NFR-5 · Untrusted archives.** An Archive is treated as untrusted input. Extraction cannot write outside the destination, whatever member paths it declares.
- **NFR-6 · Observability.** Every Run is traceable end to end by its Run ID, across subprocess boundaries, without enabling a debug mode that would expose secrets.
- **NFR-7 · Performance envelope.** Backup and restore are bounded by `mysqldump`, the filesystem and the network. Against a baseline of a bare `mysqldump` plus `tar` of the same Site, a wpbackup2 Run completes in no more than 1.5× the baseline wall-clock, measured on the integration fixture set. Archives are streamed, never buffered whole in memory: peak resident memory does not scale with Archive size. Both are asserted in the test suite, not merely documented.
- **NFR-8 · Testability without a live WordPress.** Every FR consequence in §5.1–§5.8 is verifiable against fixtures with no running WordPress and no live MySQL, *except* those on an explicitly enumerated integration list; that list lives in the test strategy and is itself asserted to be complete, so a new consequence cannot quietly join it. The suite runs in CI on every supported Python version, and a test that asserts nothing is a failing test — the current suite's assertion-free cases (arch review M-9, M-10, M-11) are treated as absent coverage, not as existing coverage.

## 7. Constraints and Guardrails

### 7.1 Safety

- Every destructive operation is opt-in by an explicit, specific authorization. A general "force" that authorizes all destruction at once is not acceptable.
- Every destructive operation is preceded by a Safety Snapshot unless the operator explicitly opted out, and that opt-out is logged.
- Dry Run is available for every destructive operation and exercises the same validation path as the real Run.
- Refusing is always an acceptable outcome. A refusal that protects a Site is a success, and exits non-zero so automation notices.

### 7.2 Privacy and Data Governance

- An Archive contains the complete WordPress database, including user accounts, email addresses, comment authors and any personal data the site holds. It is a sensitive artifact and the product treats it as one.
- Encryption at rest is available for every Archive, at every Storage Target (FR-4).
- A Manifest never contains credentials, and records source Site identity at the minimum useful detail.
- Data residency of remote Storage Targets is the operator's choice and responsibility; wpbackup2 does not relocate data between regions on its own initiative.
- `[NOTE FOR PM]` Operators subject to GDPR will ask about retention of personal data inside Archives and about the right to erasure propagating into backups. The product's honest answer is that Retention Policy (FR-17) is the control surface. Worth stating explicitly in the documentation rather than leaving readers to infer it.

### 7.3 Cost

- The product is free and open source under MIT. No paid tier is contemplated.
- The dominant operator-side cost is object storage, controlled by Retention Policy (FR-17), exclusions (FR-5) and compression.
- Maintenance cost is a first-class constraint: it is the reason relocation delegates to WP-CLI (FR-12) rather than owning a serialization-safe rewriter, and the reason the dependency policy (FR-26) is a requirement rather than a convention.

## 8. Public Surface and Compatibility

Two supported contracts, and they are versioned together.

- **The command-line interface.** Command names, option names, accepted values, exit-code meanings and the structured log schema.
- **The Python API.** The names exported from the package: domain objects, operation entry points, exception types, and the Credential Provider extension point.

Not part of either contract: internal module layout, private helpers, log message wording, and the exact composition of the default exclusion set.

**Across the v1.0 rewrite these two contracts are not equal.** The CLI is preserved: both subcommands, every existing flag spelling, and `python -m wpbackup2` as a working invocation. The **Python API is deliberately not preserved** — it is redesigned, and v1.0 is the major version that says so. The asymmetry is justified by who can actually be affected: the package has been uninstallable since its dependencies left the index, so no one can have written new code against the API recently, whereas archives on disk are untouched by that and are what operators hold. From v1.0 onward both contracts are governed by §10 equally.

**The Archive format is a third contract, versioned independently** by the Manifest's format version (FR-10). An Archive written by one version must be restorable by later versions within the same Archive format major version; when that major version changes, a documented migration or read-compatibility path exists. This matters more than the other two: operators hold Archives for months, and an Archive they cannot restore is the product's central failure.

The guarantee is bounded by what is tested. Read-compatibility is only claimed for format versions covered by a fixture Archive committed to the repository and exercised on every release; a version with no such fixture carries no promise, and the supported range is derived from the fixture set rather than declared by hand. A cross-major migration path is committed to only when a v2 format is contemplated — promising one in advance for a format that has had exactly one version would be untested prose.

## 9. Runtime Targets and Dependency Policy

- **Python versions.** Supported versions are those with upstream security support; the supported range is declared in package metadata and enforced in CI across every version in it. The current README's claim of Python 3.6 is not a target.
- **External tools.** `mysqldump` and `mysql` are required. `wp` (WP-CLI) is required only for Relocation (FR-13). Minimum versions are declared and detected (FR-27).
- **Database engines.** MySQL and MariaDB, at versions supported upstream. Parity between them is a **tested** claim, not a stated one: the integration suite runs against both from v1.0, so a divergence fails CI rather than reaching an operator. This roughly doubles integration runtime and is accepted deliberately — MariaDB is the default engine across much of the self-hosted market this product targets, and an untested parity claim there would be the most consequential kind of unenforced prose.
- **Dependency selection.** Runtime dependencies are permissively licensed, and otherwise governed by FR-26. Optional capabilities ship as extras.
- **The two unresolvable dependencies.** `chesney` is gone and is removed with the feature that needed it (§13.1). The `wp-config.php` reader ships as `l3io-wp-config` (ADR-0012), zero runtime dependencies, published before anything that depends on it. The standing requirement is that no runtime dependency can disappear from under a release without CI noticing (FR-25).
- **Inherited dependencies.** `l3io-wp-backup` reaches `boto3` and a MySQL driver transitively through `l3io-wp-database`, published from a sibling repository. Requirements stated here — optional AWS (FR-14), bounded and maintained dependencies (FR-26) — apply to the dependency graph as a user resolves it, not only to this package's direct declarations, and satisfying them requires coordinated changes in that sibling package.

## 10. Versioning and Deprecation Policy

- Semantic versioning across all three contracts in §8.
- A breaking change to the CLI or the Python API requires a major version. Adding a command, option or exported name is a minor version.
- **These guarantees begin at v1.0.** Before v1.0 the CLI and Python API are explicitly unstable: surface is removed without a deprecation cycle, and the changelog is the only notice. This is what makes the §13.1 ASG cut and the Release A churn affordable (Q-1).
- From v1.0, deprecation precedes removal: a deprecated CLI option or API name continues to function for at least one minor release, emits a warning naming its replacement, and is listed in the changelog.
- Exit-code meanings are part of the CLI contract; reassigning one is a breaking change.
- The Archive format's compatibility guarantee is stated in §8 and is stronger than the API's.

## 11. Operational Requirements

- **Release gates.** Two conditions gate every release and are not success metrics (§14): a clean-environment install from the published artifact succeeds on every supported Python version, and the documented integration suite — same-URL restore, and relocation once v1.0.1 ships — passes in full. A restored Site is functionally equivalent to its source: content present, serialized options unserializing cleanly, no residual source URLs.
- **Recovery objective.** The product's contribution to an operator's RPO is the backup interval they schedule; its contribution to RTO is restore duration, dominated by archive transfer and `mysql` load time. wpbackup2 commits to not adding avoidable delay and to reporting progress on long operations. No absolute RTO or RPO figure is committed: the product does not control archive size, network or host, so a number here would be unfalsifiable. NFR-7's 1.5×-baseline bound is the commitment that *is* testable, and it is the one the suite asserts.
- **Architecture decisions.** Two of the arch review's recommended ADRs have no home in this document because they are implementation choices rather than product requirements — the archive container format and the subprocess invocation strategy. They pass to `bmad-architecture` rather than being dropped here.
- **Failure visibility.** Automation learns about failure through exit codes (FR-21) and structured logs (FR-20). The product does not own alerting.
- **Diagnostics.** A single command reports environment readiness: Python version, external tool presence and versions, optional extras installed, and Storage Target reachability (FR-27).
- **Runbook.** Documentation states what a failed restore leaves behind at each stage, where the Safety Snapshot is, and how to recover from it — the question an operator asks at the worst possible moment.
- **Support expectation.** Public OSS: issues triaged, no response-time commitment. Security reports have a documented private channel.
- **The pipeline is reproducible on a laptop.** Every mechanical gate this document relies on — lint, types, tests, the import and AST contracts, the clean-environment install of the built artifact — runs locally under `nektos/act` with the same workflow files CI uses. A maintainer can reproduce a CI failure without pushing a commit. Steps that genuinely cannot run locally (publishing, anything needing OIDC) are structurally skipped rather than failing, and the skip is visible in the run output.

## 12. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| A restore destroys a live site and the backup turns out to be bad | Catastrophic and unrecoverable — the failure the product exists to prevent | Verification before any destructive step (FR-3), Safety Snapshot (FR-8), explicit per-destruction authorization (FR-7) |
| A runtime dependency disappears from its index again | Product offline; has already happened once | Locked, bounded dependencies with a resolvability check on every release (FR-25, FR-26); minimize the runtime dependency surface. Mitigated structurally by the fact that the two WordPress-specific dependencies (`wpconfigr`, `wpdatabase2`) are self-owned — the residual exposure is third-party and transitive |
| WP-CLI changes `search-replace` behavior or invocation | Relocation breaks | Version detection (FR-27); relocation confined behind one seam; integration test pinned across supported WP-CLI versions |
| Relocation silently corrupts serialized data | Site appears restored but widgets, menus and options are broken — discovered late | Delegate to WP-CLI rather than reimplement (FR-12); assert that values unserialize after the rewrite |
| An encrypted Archive is unrecoverable because the key is lost | Total data loss, caused by a feature meant to protect | Documentation states plainly that the key is the operator's responsibility; encryption parameters recorded in the Manifest so a held key always suffices |
| Scope selected here exceeds sustainable maintenance for a small OSS project | Half-finished capabilities, worse than absent ones | Phased MVP (§13); WP-CLI delegation over ownership; scheduling deferred to v1.1 (FR-18) |
| Positioned as novel when a near-identical predecessor exists | Credibility damage in an ecosystem where trust is the whole product | State the lineage and the delta plainly in the README and in §1 |

## 13. Non-Goals and Scope

### 13.1 Non-Goals (explicit)

- **Not a WordPress plugin, and no graphical interface.** No admin screen, now or planned.
- **Not a general-purpose backup tool.** WordPress-specific by design. Backing up arbitrary directories or non-WordPress databases is out of scope permanently.
- **Not a reimplementation of WP-CLI.** Serialization-safe search-replace, in particular, is delegated and will stay delegated (FR-12).
- **Not a hosting or monitoring product.** No alerting, no dashboard, no hosted service.
- **Not an EC2 auto-scaling orchestrator.** The `--only-appointed-in-asg` capability is **cut**. It served one deployment shape, was the sole reason for a dependency that no longer exists, and generalizes poorly. Operators needing single-instance execution should use their orchestrator's own primitives. No deprecation cycle is owed: the package does not currently install, so there is no reachable user, and §10 removes pre-1.0 surface without ceremony (Q-1).
- **Not a WordPress core, theme or plugin updater.**
- **Not novel.** `cariad/py-wordpress-backup` did substantially this first and is credited; `wpconfigr`, still relied on directly, is likewise a fork of `cariad/py-wpconfigr`. The delta wpbackup2 claims is the supported Python API, relocation done safely, and the archive lifecycle around it — not the idea.

### 13.2 Release Phasing

Three adversarial reviews converged on one finding: the previous single-v1.0 cut put all but four requirements into one release — a release built by one maintainer, on a package that does not currently install. The phasing below separates the thing that is urgent from the thing that is large, and orders the rest against the §1 wager.

**v1.0 is a rewrite, not an increment.** The arch review found nearly every existing behavior defective — `restore_mode` discarded, `--mode db` never matching, database restore silently skipped, `--cleanfirst` and `--new-site-home-url` inert, failure paths exiting 0 — and roughly half the v1.0 requirements describe capabilities with no implementation at all (Manifest, Verification, Safety Snapshot, content-URL rewriting, Dry Run, typed API). What survives is the CLI's overall shape, the domain concepts, and `wpconfigr` as a dependency. The implementation underneath does not.

#### Release A — resolvability only

No new product behavior. This exists because §2's urgency is entirely about the package not installing, and that problem should not wait behind a rewrite.

- Publish **`l3io-wp-config`** to PyPI — the fork with corrected authorship and project URL, and a README credit to the MIT original (ADR-0012) — **owner: Sanderson**
- Release **`l3io-wp-database`** with the abandoned `mysql-connector` (2.2.9, last released 2019) replaced by the maintained driver of ADR-0004 — **owner: Sanderson**
- Final pointer releases of `wpbackup2` and `wpdatabase2`, each depending only on its `l3io-wp-*` replacement and warning on import. PyPI has no redirect mechanism; this is the migration path, and it repairs `pip install wpbackup2`, which fails today with `ResolutionImpossible`
- Register `wpbackup`, `wpdatabase` and `wpconfigr` as thin pointer packages — the names a stranger searches, and the names this project's own history references
- Remove `chesney` together with the `--only-appointed-in-asg` capability (§13.1)
- Lockfile, and CI that installs from the built artifact in a clean environment on every supported Python version (FR-25, FR-27)
- Correct the README's credit link, which currently points at `cariad/py-wordpress-database` rather than at `cariad/py-wordpress-backup`, the actual predecessor (§13.1, §12)

The two cross-repository items above — publishing `wpconfigr`, and replacing `wpdatabase2`'s MySQL driver — are this PRD's answer to Q-9 and Q-10. They are not deferred to an unowned document: they are preconditions of a specific release with a named owner, and that owner controls all three repositories.

**Release gate:** `pip install wpbackup2` resolves and imports in a clean environment on every supported Python version. Nothing else in this document is a precondition of Release A.

#### v1.0 — "it installs, it cannot hurt you, and you can import it"

- Full and selective backup to a local Storage Target (FR-1, FR-2, FR-5)
- Manifest, Verification, and Verification before restore (FR-3, FR-10)
- Restore with an enumerated, honored Restore Mode (FR-6)
- Refusal over non-empty targets, Safety Snapshot, honest database restore (FR-7, FR-8, FR-9)
- `wp-config.php` outside the Site Root (FR-29)
- Credential hygiene — never in `argv`, never in logs, never in a Manifest — with explicit, environment and `wp-config.php` sourcing (FR-15)
- Dry Run across every destructive operation (FR-19)
- Meaningful exit codes (FR-21) and concurrent-Run prevention (FR-28)
- Archive encryption at rest (FR-4)
- Typed Python API and exception contract (FR-22, FR-23) — shipped, but explicitly not yet a stable contract; see below
- Dependency policy enforced mechanically, carried forward from Release A (FR-25, FR-26, FR-27)

**Two placements here carry reasoning worth stating.**

*The API ships in v1.0; the promise about it does not.* §1 stakes the product on the claim that the underserved position is an idiomatic Python library, and a v1.0 shipping only a CLI would postpone that wager rather than test it — so FR-22 and FR-23 stay. But a reviewer's objection stands: locking a versioned contract before the domain model has survived one real release is the most expensive commitment in the document, and the codebase it would be locking is a rewrite (above), not a proven shape. So FR-24 — the declared, stability-guaranteed public surface — moves to v1.1. In v1.0 the API is documented, typed and usable, and explicitly carries no stability guarantee; §10's pre-1.0 clause governs it. SM-1 still measures the wager, because the wager is about whether people import it, not about whether its signature is frozen.

*Encryption moves forward, because the previous cut created a hole.* FR-8 ships Safety Snapshots always-on, and they are deliberately not deleted by the Run that created them. With FR-4 in v1.1 and FR-17's Retention Policy also in v1.1, a v1.0 restore would have written an unencrypted, complete copy of the site's database — every user record on it — to local disk, with nothing in the product that ever removed it. That is a privacy defect manufactured by the release plan rather than by any requirement, and it is the kind a backup tool least survives. FR-4 therefore ships in v1.0. Snapshot lifetime is still unbounded until FR-17 lands, which is noted in §11 as a documented v1.0 limitation rather than silently accepted.

#### v1.0.1 — relocation

- Configuration rewriting and serialization-safe content URL rewriting via WP-CLI, with honest failure when `wp` is absent (FR-11, FR-12, FR-13)
- Structured logging correlated by Run ID (FR-20), and the optional tracing surface that shares its correlation processor (FR-30)

Relocation is the single largest greenfield block in the product and the one capability that most distinguishes it from `mysqldump | tar`. Separating it lets v1.0 ship, and lets relocation get the integration-test attention it needs without holding the safety work hostage.

#### v1.1

- Declared public surface and stability guarantees (FR-24)
- Remote Storage Targets (FR-16)
- Retention Policy and pruning (FR-17)
- Scheduled operation (FR-18), minus the concurrent-Run prevention that ships in v1.0
- Pluggable Credential Provider contract, including AWS Secrets Manager (FR-14) — v1.0 ships fixed sourcing; the documented extension point follows once the shape has survived a release

**Out of scope for v1.x:**

- WordPress multisite — real demand, real complexity, needs its own requirements work
- Incremental or differential backup — full archives only (Q-5)
- Site-to-site push/pull over HTTP, as WP Migrate DB Pro does
- Backup of anything outside the Site Root and its database

## 14. Success Metrics

Release gates are not success metrics. A green suite and a clean install are preconditions for shipping rather than evidence the product succeeded, so they live in §11 as gates. Nor is a metric that having no users would satisfy — SM-2 and SM-4 require evidence of use before they count. What is Primary here is what would read differently if the §1 wager were wrong.

**Primary**

- **SM-1 · The library is used as a library.** Adoption through the Python API rather than only the CLI: public repositories declaring `wpbackup2` as a dependency and importing it, and issues phrased in API terms rather than CLI terms. **Target: by v1.0 + 12 months, at least three independent public repositories demonstrably import the API surface.** Below that, the library positioning is retired, FR-24 is abandoned rather than shipped, FR-22 and FR-23 are demoted from public surface to internal detail, and the CLI becomes the sole contract. This is the metric that tests the wager, and it carries a date and a consequence because a wager without either is a wish. Validates FR-22, FR-23, FR-24.
- **SM-2 · No unauthorized destruction.** Zero reported incidents of a Run destroying data the operator had not explicitly authorized — weighted by adoption, so that zero incidents against zero users counts as no evidence rather than as success. Treated as release-blocking severity when one is reported. Validates FR-7, FR-8, FR-28, NFR-1.
- **SM-3 · Restores that are trusted enough to run unattended.** Operators schedule wpbackup2 and leave it — evidenced by issues that mention `cron` or `systemd`, and by restore-after-incident reports arriving with a Run ID rather than a narrative. The product's whole claim is automation-first; nobody automates a tool they check on. Validates FR-6, FR-9, FR-20, FR-28.

**Secondary**

- **SM-4 · Relocation is exercised without corruption.** Relocation is used, and relocation-corruption reports remain at zero. Meaningful only once v1.0.1 ships. Validates FR-12, FR-13.
- **SM-5 · Failures are diagnosable without the maintainer.** Issues arrive with a Run ID and structured log excerpt rather than "it didn't work". Validates FR-20, FR-21.

**Counter-metrics (do not optimize)**

- **SM-C1 · Restore speed.** Must not be optimized at the expense of Verification or the Safety Snapshot. A slower restore that cannot destroy a site is the correct trade. Counterbalances the §11 restore-suite release gate, whose green-ness is easier to reach by doing less.
- **SM-C2 · Feature count and surface breadth.** Growth in capabilities is not a success signal for a small OSS project; it is a maintenance liability. Counterbalances the §13.2 deferral list — the deferrals are not a backlog to burn down on principle.
- **SM-C3 · Dependency count.** Convenience dependencies are not free. Counterbalances FR-16 and FR-4, whose implementations will each want to add one.

## 15. Open Questions

**None of the eleven are open.** Two were Release A blockers (Q-6, Q-9/Q-10) and are now named preconditions with an owner in §13.2. Two blocked v1.0 (Q-3, Q-11) and are answered below. The rest were closed by the release phasing or by making an unfalsifiable statement testable. Each entry below carries its disposition and the section that now owns the decision.

1. **Q-1 — Does anyone depend on `--only-appointed-in-asg`?** *Closed.* §10 states that pre-1.0 surface is removed without a deprecation cycle, and the package cannot currently be installed, so there is no reachable user to deprecate for. The cut stands, with the reasoning now on the page rather than in a question.
2. **Q-2 — Which remote Storage Targets actually matter?** *Closed by phasing.* FR-16 is v1.1; the first operator to ask for a specific target answers it. The recorded default if nobody asks — delegate to `rclone` — sits with FR-16; one dependency instead of three is what SM-C3 prices correctly.
3. **Q-3 — Is MariaDB parity a requirement or an expectation?** *Answered: a requirement.* Both engines run in the integration matrix from v1.0, at the runtime cost §9 states and accepts. A parity claim that CI does not check is exactly the sort of prose that reads as authoritative and is not.
4. **Q-4 — Are absolute performance or RTO/RPO targets needed for v1?** *Closed: no.* NFR-7 carries a testable bound instead, and §11 states why no absolute figure is committed — the product controls neither archive size, nor network, nor host.
5. **Q-5 — Is full-archive-only acceptable indefinitely?** *Closed by phasing.* Not indefinitely, but for v1.x. Revisit when an operator reports a Site whose full Archive no longer fits their backup window — that report is the signal, and it has not arrived.
6. **Q-6 — Under what name does the configuration reader publish?** *Answered: `l3io-wp-config` (ADR-0012).* Publishing the fork as `wpconfigr` would misattribute — its metadata still credits the original author and points at their repository — and would likely fail to upload at all, since PyPI permanently burns filenames and the fork is still version 1.4. Upstream's own successor, `wpconfigger`, was weighed and not chosen: one release, one maintainer, and no ability to fix the parser ourselves.
7. **Q-7 — Does the project keep the name `wpbackup2`?** *Answered: no (ADR-0012).* All three packages move to the `l3io-wp-*` family under the `l3io.wp` namespace. `wpbackup2` read as version two of a package nobody can install, and sat beside the actively-maintained `WPBackupTool`. `wpbackup2` and `wpdatabase2` each get one final pointer release depending on their replacement, which is the only migration path PyPI offers and which also repairs `pip install wpbackup2` for everyone currently hitting `ResolutionImpossible`.
8. **Q-8 — Closed.** Encryption ships in v1.0 (§13.2). Deferring it while always-on Safety Snapshots also shipped in v1.0 would have written unencrypted, never-pruned copies of the full database to local disk as a side effect of the product's own safety feature. Snapshot *lifetime* stays unbounded until FR-17 lands, which §11 records as a documented v1.0 limitation.
9. **Q-9 / Q-10 — Cross-package obligations, and who owns them.** *Answered.* `wpconfigr` publication and `wpdatabase2`'s MySQL-driver replacement are named Release A preconditions owned by Sanderson (§13.2). The PRD stays scoped to `wpbackup2`; what it no longer does is make a cross-repository change a precondition of its own release while filing the ownership question under "deferred".
10. **Q-11 — Is the FR-6 Restore Mode table the right set?** *Answered: yes, as derived.* Six modes across the two axes the existing `WpRestoreMode` flag already encodes, keeping every combination operators can express today, minus the single all-authorizing `--force`→`ALLCLEAN` mapping that §7.1 forbids. Nothing reachable today becomes unreachable.

## 16. Assumptions Index

Every inference this document rests on: the assumptions now confirmed and stated as decisions, the one still tagged in the body, and the inferences taken from the codebase that were never tagged.

**Confirmed and now stated as decisions** — the tag is gone from the body:

- **§13.1 / Q-1** — No current user depends on the ASG capability being cut. Confirmed; §13.1 carries the reasoning.
- **§6 / NFR-7 and §11 / Q-4** — No absolute throughput or RTO/RPO target for v1. Confirmed, and replaced with a bound the suite actually asserts.
- **§13.2 / Q-5** — Full-archive-only is acceptable for the target site sizes. Confirmed for v1.x, with a named revisit signal.
- **§5.5 / FR-16 / Q-2** — S3, SFTP and rsync cover the operator base. Superseded: the capability is v1.1 and the target set is now demand-driven, so the assumption no longer needs to hold.
- **§5.4 / FR-14 / Q-9** — `boto3` can become an optional extra in `wpdatabase2`. Confirmed and made concrete: a Release A precondition with a named owner, not an aspiration.
- **§9 / Q-3** — MariaDB parity with MySQL. Confirmed and *promoted*: parity is now enforced by the integration matrix rather than assumed, which is the only disposition that makes the §9 claim true.

**Still open, and tagged in the body:**

- **§3** — The entire target-user section is inferred from the shape of the existing CLI and its AWS hooks, not from research. Now tagged at the head of §3 itself, rather than only in this index. Names, site counts and timings in §3.3 are illustrative. This is the one assumption the document still carries, and it is the one that research — not a decision — would close.

**Inferences drawn from the codebase rather than from stated intent:**

- Site scale is "a handful to a few dozen sites per operator" rather than fleet scale — inferred from the absence of any multi-site orchestration in the existing code.
- MIT licensing continues — taken from the existing `setup.py` and `LICENSE`.
