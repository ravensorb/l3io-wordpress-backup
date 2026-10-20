# Proposed Epic 2 stories — gap pass, 2026-10-20

Written by the E002 gap pass of `/l3io-plan` step 03. Each entry below is too large to keep
any existing E002 story coherent. **No story file or state node exists for them**; the
orchestrator creates those. Layout and provenance follow
`_bmad-output/planning-artifacts/elaboration-brief.md`. Names reuse what E002–E004 already
established; the contracts these stories implement are defined in the E002 stories they
depend on (marked "Added 2026-10-20" there).

---

## P1 — Give restore the database, file and config operations it needs

- **Epic / sprint:** E002, sprint S02 (needs the ports E002-S02-007 adds and the Run machinery of S02).
- **Classification:** complex — it binds the only destructive operations the product performs (drop database, clear a Site Root, rewrite `wp-config.php`) to their real effects.
- **depends_on:** E002-S01-001, E002-S01-003, E002-S02-004, E002-S02-007.
- **Implements:** FR-7, FR-9 (the operations), AD-18 items 2–4, AD-28, AD-29; ADR-0015.

As an operator,
I want restore's destructive operations performed only through the family packages that already do them safely,
So that a restore can never drop, clear or rewrite more than the plan says.

**Acceptance Criteria:**

**Given** the restore halves of `DatabaseQuery`/`DatabaseCommand`, `SiteFilesQuery`/`SiteFilesCommand` and `ConfigQuery`/`ConfigCommand` (E002-S02-007)
**When** a composition root binds the real adapters
**Then** every database operation goes through `l3io-wordpress-database` v0.1.0 and this package issues no SQL
**And** existence is answered only by the administrator (AD-29)
**And** `wp-config.php` is written only through `adapters/config_writer`, which delegates the write and its verification to `l3io-wordpress-config` and keeps the file's mode (AD-18.4)

## Business acceptance criteria

### Outcome

Epic 3 can restore without editing an Epic 2 module: `adapters/database.py` implements every restore-half method E002-S02-007 declares, `adapters/site_files.py` implements emptiness, clearing and extraction, and `adapters/config_writer.py` is the one caller of `l3io.wp.config.WpConfigFile` in the package. A reviewer can tell it happened by running the adapter contract tests against the CI MySQL/MariaDB service and a temp Site Root, and by grepping `src/` for `WpConfigFile(` (one hit, in `adapters/config_writer.py`; `adapters/database.py`'s read-only use of database's `WpConfigFile` is a different class) and for SQL DDL (none).

Spec: _bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/prd.md#52-restore
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-18--a-killed-run-must-be-recoverable
Spec: _bmad-output/planning-artifacts/epics.md#epic-list

### Non-goals

- Deciding *when* any of these runs, the staging name, the journal and the cutover order — Epic 3 (stories 3.1–3.5) through `core/restore` and `adapters/{staging,journal}`.
- Relocation's key set (`WP_HOME`, `WP_SITEURL`, new host) — Epic 7 calls this writer.
- Fixing `l3io-wordpress-config`'s mode/fsync behaviour — that package's fix release.

## Technical acceptance criteria

### Interface contracts

- **`adapters/database.py` — the restore halves (ADR-0015; signatures verified at `l3io-wordpress-database` v0.1.0).** `survey_target` → `survey(connection, admin, *, wordpress_user=..., user_host="%", table_prefix=...)` (`inspection.py` L101), copied into `DatabaseTargetState` field by field; `check_ensure`/`ensure_database` → `check_ensure`/`ensure(connection, admin, wordpress, *, user_host="%")` (`provision.py` L287/L308), `EnsureResult` copied into `EnsureOutcome` with the verdict's warning **codes**; `check_load`/`load_dump` → `check_load`/`load(connection, wordpress, source, *, replace=None, identities=...)` (`transfer.py` L834/L865) — `replace` is never passed a value; `check_revoke`/`revoke_grants` → `check_revoke`/`revoke(connection, admin, user, *, user_host="%", confirm=user)` (L590/L604); `check_drop_database`/`drop_database` → `check_drop_database`/`drop_database(connection, admin, *, confirm=location.name)` (L710/L718), returning `OperationResult.changed`. `Connection` is built from `DatabaseLocation` once, in one private helper. The administrator source is `l3io.wp.database.Explicit` built by the composition root from `--admin-username`/`--admin-password` (or the library's `admin=`); its password is registered with the Run's `SecretRegistry` before the first call. `l3io.wp.database` stays a function-scope import (AD-8).
- **Error mapping (AD-14), to E002-S01-001's classes:** database `RefusedError` → `DatabaseRefusedError` (finding codes only); `ProvisioningError` → `ProvisioningFailedError`; `TransferError` → `DumpFailedError`'s load counterpart `LoadFailedError(BackupError)` (added to `domain/errors.py` here); `AuthenticationFailedError`/`AccessDeniedError` → `CredentialsError`; `DatabaseUnreachableError` → `DatabaseUnreachableError`. Always `raise ... from`.
- **`adapters/site_files.py` — `LocalSiteFiles`** (outside the Epic List's named adapter set, on the precedent of `adapters/workspace.py`; no other epic claims it). `is_empty`/`entry_count` via `os.scandir`; `clean(site_root, *, keep)` removes each top-level entry not in `keep` with `shutil.rmtree`/`os.unlink`, never following a symlink (a symlinked directory is unlinked, not descended — `shutil.rmtree` is called only on real directories) and never removing `site_root` itself; refuses (`UnsafeCleanTargetError(RefusedError)`) when `site_root` is `/`, the user's home, or contains no `wp-config.php` and no `wp-includes/` (a guard against a mistyped `--wp-dir`, stated as a heuristic in the docstring); `extract` delegates to E002-S01-003's `extract_archive` unchanged.
- **`adapters/config_writer.py` — the one writer of `wp-config.php` (AD-18.2, AD-18.4; Epic 2's since 2026-10-20).** `WpConfigWriter` implements `ConfigQuery`/`ConfigCommand` over `l3io.wp.config.WpConfigFile`: `set_constants` calls `WpConfigFile(path).set(key, value)` once per key, in the order given, each an atomic, read-back-verified write owned by that package (ADR-0010); it writes no config bytes itself and implements no verification. `ReadBackError`/`ConfigWriteError`/`ConfigValueError` are re-raised as `ConfigWriteFailedError(path, key, reason)` with the original byte-identical. A multi-key call is a sequence of atomic writes, not one transaction; the docstring says so and returns `changed` so the caller can journal per key. **Required behaviour of the write: the file's permission bits are unchanged by it, and the new content is durable (file and directory fsync) before `set` returns.** `l3io-wordpress-config` v0.1.0 does neither (its `_set` writes the temp file with umask permissions and calls no `fsync`; reproduced 2026-10-20). This package does **not** work around it with its own `chmod` (that would leave a window with the widened mode and a second writer); it pins the config release that carries the fix — the `database` extra gains an explicit `l3io-wordpress-config>=<fix release>` lower bound when that release exists. The only caller of `WpConfigFile(` in the package is this module (contract test).

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-18--a-killed-run-must-be-recoverable
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-29--existence-is-answered-by-the-administrator-never-inferred-from-a-failed-login
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-28--a-database-name-in-a-grant-is-escaped-because-it-is-a-pattern
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-14--errors-cross-a-public-boundary-only-as-package-owned-types
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-8--an-optional-dependency-is-an-optional-import

### Error and edge case handling

- A restore-half call with no administrator source bound: `AdminCredentialsRequiredError`, before any connection (E002-S02-007).
- `drop_database` of a database that does not exist: `False`, not an error; database's `LIVE_WORDPRESS_SITE` warning is logged, not swallowed.
- `clean` interrupted part-way (an `OSError` on one entry): stops, raises naming the entry, leaves the remaining entries — never continues past a failure.
- `set_constants` with an unrenderable value: `ConfigWriteFailedError(reason="unrenderable")`, file unchanged; with a key already at the value: `changed` omits it and the file is not rewritten.
- `wp-config.php` read-only or its directory unwritable: `ConfigWriteFailedError`, original intact, no `.l3io-tmp` left behind.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-18--a-killed-run-must-be-recoverable
Spec: _bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/prd.md#71-safety

### Observability requirements

- Each command emits E002-S02-005's `phase_completed`-shaped record under its own name (`database_ensured`, `dump_loaded`, `grants_revoked`, `database_dropped`, `site_root_cleaned`, `config_written`) with location or path, `duration_ms` and the outcome flags; `config_written` names the **keys** written, never values (`DB_PASSWORD` is a key that may be written by relocation). `database_surveyed` carries `observed_by="administrator"`.
- database's own operation events flow through unchanged.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-10--one-logger-one-run-id-bound-at-the-composition-root

### Security considerations

- The administrator password and any `DB_PASSWORD` value passed to `set_constants` are registered with the `SecretRegistry` before use; E002-S02-004's `credential_sentinel` is applied to each adapter's contract test.
- No SQL, `GRANT` or identifier quoting in this package (AD-28 is satisfied by database's escaping); `tests/contracts/test_no_sql_ddl.py` (Epic 3's name, created here because these are the call sites) scans `src/` for DDL keywords in string literals.
- A widened `wp-config.php` mode exposes `DB_PASSWORD` (NFR-3): the mode test below is the release gate for restore.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-7--credentials-reach-a-subprocess-by-file-never-by-argument-or-environment
Spec: _bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/prd.md#72-privacy-and-data-governance

### Testability approach

- `tests/adapters/test_database_restore.py` (`@pytest.mark.integration`, CI MySQL 8.4 / MariaDB 11.4): survey of absent/empty/WordPress databases; ensure creates then reports nothing to do; load into an empty database; load into a non-empty one is refused by database; revoke then drop; drop of an absent database is `False`.
- `tests/adapters/test_site_files.py`: `keep` honoured; a symlink to a directory outside the Site Root is unlinked and its target untouched; `/` and `$HOME` refused; an `OSError` mid-clean stops.
- `tests/adapters/test_config_writer.py`: a `0640` `wp-config.php` is `0640` after `set_constants` — **marked `xfail(strict=True, reason="l3io-wordpress-config v0.1.0 does not preserve mode; fixed in <release>")`**, so it fails loudly the moment the pinned release fixes it and the marker must be removed; the same for an fsync spy on file and directory. Unmarked cases: read-back failure leaves the original byte-identical (a `verify_write` double forced to fail); one key per atomic write; values never in records.
- `tests/contracts/test_single_config_writer.py`: AST scan — `l3io.wp.config` imported only in `adapters/config_writer.py`.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#consistency-conventions

### Existing-library check

`l3io-wordpress-database` v0.1.0 (`survey`, `ensure`, `load`, `revoke`, `drop_database` and their `check_*`) and `l3io-wordpress-config` (`WpConfigFile.set`, ADR-0010 read-back) do every database and config operation; stdlib `os.scandir`/`shutil.rmtree` clear files. No SQL, PHP parsing or atomic-write code is written here.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#stack

---

## P2 — Drive a restore from the command line

- **Epic / sprint:** E002, sprint S02.
- **Classification:** complex — the composition root for the product's most dangerous operation: every restore safety rule meets here, and a wrong binding destroys a site.
- **depends_on:** E002-S01-001, E002-S01-003, E002-S02-004, E002-S02-005, E002-S02-006, E002-S02-007, E002-S02-008, P1, **and E003-S01-001**.
- **Sequencing note for the orchestrator:** this root calls Epic 3's `core/restore.build_restore_plan` and `adapters/restore_runner.execute_restore` (E003-S01-001), so it is the one Epic 2 story that lands **after** story 3.1's pure core and executor (which 3.1 can build and test without a CLI). The story-level graph stays acyclic: E002 sprints 1–2 → E003-S01-001 → P2 → the end-to-end criteria of E003-S01-002…S02-005. Until P2 lands, `wpbackup2 restore` stays accepted-and-explained (exit `USAGE`, E002-S02-006). If the orchestrator prefers, P2 can be keyed into Epic 3's sprint 1 with an Epic List ownership note granting `cli/restore.py` and its one dispatch arm — the alternative E003-S01-001 proposed; this proposal keeps `cli/*` single-owner as decision 1 asks.
- **Implements:** FR-6, FR-7, FR-8, FR-19 (restore path), AD-5, AD-16, AD-17, AD-18.1, AD-19, AD-25, AD-26.

As an operator,
I want `wpbackup2 restore` to resolve what I asked for once and carry it through every phase,
So that the mode I typed is the mode performed and every safety step runs in order.

**Acceptance Criteria:**

**Given** `wpbackup2 restore --wp-dir <Site Root> --archive <Archive>` with any flag combination
**When** it runs
**Then** `(RestoreMode, OverrideSet)` is resolved once from E002-S02-006's table and passed explicitly to every phase
**And** the Site Lock is taken and an incomplete Run Journal is refused before any Site state is read beyond canonicalising the path
**And** the Archive is verified before the Safety Snapshot and before any destructive phase
**And** a target with no `wp-config.php` gets its Site Descriptor from the Archive's config member
**And** a Dry Run binds no-op commands and refuses wherever the real Run would

## Business acceptance criteria

### Outcome

`wpbackup2 restore` (and Epic 6's library root, which reuses the same driver function) runs a restore end to end: flags resolved through the AD-25 table; Site Lock; incomplete-journal refusal (or `--resolve-interrupted-run <run_id>`); `PREFLIGHT`; `VERIFY`; the target surveyed through query ports; the plan built; `SNAPSHOT` (encrypted when configured, otherwise said loudly; skipped only by `--no-safety-snapshot`); the remaining phases executed in `RestorePhase` order; the database report printed; one exit code. A reviewer can tell it happened by running each FR-6 row against a fixture site and reading the `restore_mode_resolved`, `planned_action` and `phase_completed` records — one `run_id`, phases in AD-17 order, the requested Mode in the Safety Snapshot's Manifest `origin`.

Spec: _bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/prd.md#52-restore
Spec: _bmad-output/planning-artifacts/epics.md#story-31-restore-files-and-database-from-an-archive
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-17--restore-phase-order-is-data-not-a-diagram

### Non-goals

- The plan, the per-phase work, the target guard, the snapshot rules, the staging cutover and the journal format — Epic 3 (`core/restore`, `adapters/{restore_runner,staging,journal}`). This root binds them; it decides none of them.
- Relocation flags' behaviour (`--new-*`) — Epic 7; they stay accepted-and-explained.
- AWS administrator credentials (`--admin-credentials-aws-*`) — Epic 5.
- The library entry point's signature — Epic 6, which calls `drive_restore` below.

## Technical acceptance criteria

### Interface contracts

- **`cli/restore.py::run_restore(args) -> int`** (dispatched from `cli/__init__.py::main`) does only argument translation: `FlagCombination` from the `restore mode` group → `resolve_flags` (AD-25); `SnapshotPolicy` from `--no-safety-snapshot`; administrator source from `--admin-username`/`--admin-password`; cipher configuration from the encryption flags plus E002-S02-004's `resolve_passphrase`; then calls **`drive_restore(request: RestoreRequest, *, ctx: RunContext | None) -> RestoreOutcome`**, the function the library root also calls. Frozen `RestoreRequest(site_root: Path, archive: StorageTarget, mode: RestoreMode, overrides: OverrideSet, snapshot: SnapshotPolicy, snapshot_dir: Path | None, resolve_run_id: str | None, admin: CredentialSource | None, cipher: MemberCipher | None, dry_run: bool)` — `mode`, `overrides` and `snapshot` have no defaults (AD-5). No function below `run_restore` receives `args`.
- **`drive_restore` order (each step before the next; nothing destructive before step 7):**
  1. `join_or_open(ctx, adapters=real_adapters(...) | dry_run_adapters(...), site_root=canonical)` — the Site Lock is acquired here (E002-S02-008); log `restore_mode_resolved` with `restore_mode`, `overrides`, `snapshot_policy`.
  2. `RunJournalQuery.incomplete(site_root)` (E003-S02-005): a record → `IncompleteRunError` unless `resolve_run_id` equals its `run_id`, in which case the journal is resolved (moved to `resolved/`, `resolved_by="cli"`) and the Run **stops** with `OK` after reporting — resolving and restoring are never one command.
  3. `PREFLIGHT`: `Preflight.check(plan-independent requirements)` plus database `check_*` queries for the parts the Mode restores.
  4. `VERIFY`: E002-S01-003's `verify_archive`; failure → `VerificationFailedError`; the `ArchiveView` is kept for planning.
  5. **Site Descriptor.** `site_descriptor_from_wp_config(site_root)` when the target has `wp-config.php`; otherwise `site_descriptor_from_archive_config(site_root, <config member extracted into the workspace>)` (E002-S01-001). Neither present → `InvalidSiteDescriptorError`. A files-only v0 Archive with a Mode naming the database is refused by the plan (`ArchiveHasNoDumpError`, AD-23 amended) before step 7.
  6. `TargetState` from `SiteFilesQuery` and `DatabaseQuery.survey_target`; `build_restore_plan(site, mode, overrides, view, target)` (Epic 3) — which applies the FR-7 guard.
  7. `execute_restore(plan, ports, take_snapshot, journal)` (Epic 3), where `take_snapshot(scope)` calls E002-S02-005's `backup(site, scope, file:<snapshot path>, ctx=ctx, cipher=request.cipher, exclusion=INCLUDE_EVERYTHING, origin=ManifestOrigin(SAFETY_SNAPSHOT, mode.value, ctx.run_id))` and, when `request.cipher is None`, writes `safety snapshot is NOT encrypted: <path>` to stderr and logs WARNING `safety_snapshot_unencrypted` with `path` (AD-26, decided 2026-10-20).
  8. Print the plan (Dry Run) or the database report and Snapshot path; return `ExitCode.OK` or raise.
- **`RestorePhase` is driven, not re-listed.** The root iterates nothing itself; it passes the plan to the executor. A contract test fails if `cli/restore.py` names any `RestorePhase` member other than through `plan.phases`.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-16--one-run-context-created-by-the-outermost-composition-root
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-5--restore-mode-is-a-closed-set-resolved-once-carried-as-a-value
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-25--cli-flags-map-to-restore-mode-through-one-total-function
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-26--one-passphrase-resolution-chain-or-no-encryption-at-all
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-3--one-immutable-site-descriptor-parsed-once-at-the-edge
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-23--archive-format-detection-is-explicit-and-one-way
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-4--dry-run-is-adapter-selection-never-a-conditional

### Error and edge case handling

- Lock held by another Run → `LOCKED`; incomplete journal → `REFUSED` naming run, phase, undo and journal path; `--resolve-interrupted-run` with a different ID → `REFUSED` naming the journal's ID.
- Rejected flag combination → `USAGE` before the lock is taken.
- Verification failure → `VERIFICATION_FAILED` before `SNAPSHOT`; Snapshot failure → `REFUSED` (`SnapshotFailedError`) before `CLEAN`.
- A Mode touching the database with no administrator credentials → `CREDENTIALS` (`AdminCredentialsRequiredError`) before any phase after `VERIFY`.
- Target with neither its own nor an Archive `wp-config.php` → `FAILED` (`InvalidSiteDescriptorError`), nothing changed.
- SIGTERM mid-phase → the journal shows the open phase; the lock is released by the `finally` (E002-S02-008).

Spec: _bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/prd.md#52-restore
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-18--a-killed-run-must-be-recoverable

### Observability requirements

- `restore_mode_resolved` once per Run; `planned_action` per action; Epic 3's `phase_completed` per phase; `run_finished` with `exit_code`/`exit_reason`; all under one `run_id`, including the Safety Snapshot's records (joined Run).
- The Snapshot path is printed on stdout and logged at INFO even on failure of a later phase.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-10--one-logger-one-run-id-bound-at-the-composition-root

### Security considerations

- Administrator password and any passphrase registered before first use; `credential_sentinel` (E002-S02-004) applied to a full restore here — the obligation E002-S02-004 placed on "a full restore" is discharged by this story's test, and `test_credential_hygiene.py`'s restore tripwire is satisfied by it.
- The archive-config path (step 5) extracts only `MemberRole.CONFIG` into the `0700` workspace through `extract_archive` (AD-11); it is never copied into the Site Root by this root.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-7--credentials-reach-a-subprocess-by-file-never-by-argument-or-environment
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-11--an-archive-is-untrusted-input

### Testability approach

- `tests/unit/cli/test_restore_root.py` with recording doubles for every port and for Epic 3's plan/execute functions: step order 1→8; no command call before step 7; `args` never passed below `run_restore`; `mode` reaches `build_restore_plan`, the journal header and the Snapshot `origin` unchanged — parametrised over every `FLAG_MAP` key (scope from the table).
- Dry Run equality: for each `RestoreMode`, the plan built with real and dry-run adapter sets is equal (AD-4), and the Dry Run refuses in each refusal case with the real Run's code.
- `tests/integration/test_restore_cli.py` (`@pytest.mark.integration`): one case per FR-6 row against a fixture site; a fresh empty directory as target (descriptor from the Archive); a files-only v0 Archive with `--mode db` refused naming the missing Dump; an unencrypted Snapshot prints the warning line.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-17--restore-phase-order-is-data-not-a-diagram
Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#consistency-conventions

### Existing-library check

stdlib `argparse` for parsing (already in use) and `getpass` (through E002-S02-004's chain); everything else is this package's own Epic 2/3 contracts. No new dependency.

Spec: _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#stack
