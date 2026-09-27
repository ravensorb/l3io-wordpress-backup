# Handoff 3 — `py-wordpress-backup` becomes `l3io-wp-backup`

**Read `00-SHARED-CONTEXT.md` in this folder first.**

**Repository:** `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-backup`

**Decisions taken by the maintainer, 2026-09-17 — build to these:**

- **Version starts at `1.0.0`.** New distribution name, no prior releases under it.
- **Default branch is `main`** (renamed from `master` server-side; local tracking updated).
- **This is a full new package on the new architecture, not an incremental port.**
  Nothing in the old tree is preserved for its own sake. §13.2's release phasing still
  governs *shipping* order; it does not license shipping a subset of the architecture.
- **Dispatched work.** Stages are sequenced below; complete one and report before the next.
**Release position:** THIRD and last.

## Read this before you start

This repository already contains the PRD, the architecture spine, 13 ADRs, and a
complete CI/CD setup that runs locally under act. **Those are done. Do not
regenerate them.** Your job is the code.

**This is a rewrite, not a refactor.** The architecture review found nearly every
existing behaviour defective: `restore_mode` discarded at two call sites making
`shutil.rmtree` unconditional; the database restore silently skipped while
reporting success; passwords in `argv` and in debug logs; `extractall` without
containment; `--mode db` never matching; `--cleanfirst` and `--new-site-home-url`
inert; failure paths exiting 0. Roughly half the v1.0 requirements describe
capabilities with no implementation at all. What survives is the CLI's shape, the
domain concepts, and the dependency on the config reader.

## Non-negotiable outward compatibility

- **The CLI is frozen (AD-22).** Both subcommands, all 19 flag spellings
  including the camelCase `--whatIf`, and `python -m wpbackup2` as a working
  invocation. New flags may be added; none may be renamed or removed.
  `--only-appointed-in-asg` is the single forced exception — it required
  `chesney`, which no longer exists on any index. **Accept the flag and fail with
  an explanation**, never argparse's `unrecognized argument`.
- **Defects are fixed, intent is preserved.** `--mode db` performs a database
  backup; `--cleanfirst` selects the clean Restore Mode; `--force` overrides the
  non-empty-target refusal; failures exit non-zero. Each is a named changelog
  entry.
- **v0 archives restore forever (AD-23).** Pre-rewrite archives are a
  manifest-less `.tar.gz` with members `database.sql` and `wp-root/`. They are
  detected and restored **by default, permanently** — not behind a legacy opt-in.
  Verification reports `STRUCTURAL_ONLY` rather than claiming integrity it cannot
  check. Nothing writes v0.
- **The Python API is explicitly NOT preserved.** It is redesigned freely.

## Your dependency is finished — consume it, do not re-derive it

`l3io-wp-database` is complete, merged, **public**, and green on real GitHub Actions
(15 jobs, not only under act). Verified publicly readable without credentials.

```toml
[project]
dependencies = ["l3io-wp-database>=1.0.0"]

[tool.uv.sources]
l3io-wp-database = { git = "https://github.com/ravensorb/py-wordpress-database.git",
                     rev = "945069bf36329315f8c2536c8a272b33e1d6b7af" }
```

**Pin `rev`, not `branch`.** A branch re-resolves on every `uv lock -U`, and that
repository's `main` moved three commits past a locked SHA during its own build.
Build with `uv build --no-sources` so the git source never reaches published
metadata — verified to emit a plain `Requires-Dist` for wheel and sdist alike.

That repo renamed `master` to `main`. Two things will mislead you: `gh repo view`
served a **stale** default branch for a while afterwards, so trust the `/branches`
list; and `branches/master` still resolves to the same SHA via the rename
**redirect**, not a surviving branch.

**Its API is entirely new. Assume nothing in this handoff's history survives** — no
`wpdatabase2` name is preserved and there is no shim. 31 names are exported from
`l3io.wp.database`. Five changes that break a direct port:

1. **Credentials resolve explicitly.** `.username` / `.password` are gone as
   property getters. Call `resolve()`, which returns a frozen `ResolvedCredentials`.
   That is AD-9 implemented.
2. **Existence is a six-state enum, not a boolean.** `inspect()` returns
   `ConnectionState` with `.is_ready`, `.needs_provisioning`, `.blocks_provisioning`.
   Per AD-29, `authentication_failed` is **provisionable** — before first
   provisioning the account does not exist, so refusing on it would reject the
   create case. Only `unreachable` and `credentials_unobtainable` block.
3. **Catch `WpDatabaseError`, never a driver type.** Nothing from PyMySQL, boto3 or
   `l3io-wp-config` crosses the boundary (AD-14). Your `except` clauses change.
4. **`database_version(table_prefix=...)` takes the prefix.** The old hardcoded
   `wp_options` failed on every prefixed site. Get the real value from
   `WpConfigSource(path).table_prefix`.
5. **WordPress support floor is 5.0.** The version map is derived from release tags,
   never hand-edited.

**AD-28 is exported.** `from l3io.wp.database import quote_grant_database`. Do not
reimplement it. Use `quote_identifier` for literal-name cases — `CREATE DATABASE`
and connection parameters need the unescaped name, and escaping those breaks
provisioning.

## The credential guard is YOUR problem, not theirs

`l3io-wp-database` ships a test asserting **no module imports `subprocess`**. That
test is vacuous there — nothing in it shells out, so "no password in `argv`" is
trivially true. **This package invokes `mysqldump`, `mysql` and `wp`, so the same
guarantee has to be carried by real discipline and real assertions.**

Two requirements in the definition of done were being carried by review rather than
by tests. Make them mechanical here:

- **No credential in any log record**, at any level, asserted against captured
  structlog events *and* stdlib records, across a full backup and a full restore —
  the paths that actually emit a command line.
- **No credential in any constructed argument vector**, asserted against the vector
  itself rather than by reading the code.
- **Every `repr` clean** — descriptor, credentials, connection.
- **The exception raised to a caller clean.** A traceback is log output by another
  name.
- **The option file's mode is 0600 and it is removed**, asserted on both the success
  and the failure path.

And the transport rule those guard (AD-7, ADR-0003): `--defaults-file` at mode 0600
deleted in a `finally` — **never** the additive `--defaults-extra-file`, where an
ambient `~/.my.cnf` carrying `[client] host=` can silently redirect a restore to a
different database server — and never `MYSQL_PWD`.

## Architecture

Ports and adapters with a functional core (ADR-0001). `domain/` and `core/` are
pure and import no I/O module; effects are reached only through `ports/`
Protocols satisfied by `adapters/`; `cli/` and `api/` are composition roots.

Work the 27 ADs in the spine. The ones most likely to be got wrong:

- **AD-4 — Dry Run is adapter selection, never a conditional.** No `if dry_run:`
  anywhere outside a composition root. Every port splits into queries and
  commands; a Dry Run binds real queries and no-op commands, so validation,
  verification, preflight and refusal all execute for real.
- **AD-5 — no function consuming a `RestoreMode` may default it.** This is the
  invariant that maps directly to the unconditional-`rmtree` data loss.
- **AD-17 — restore phase order is an ordered enum, not a diagram.** A plan is a
  subsequence; reordering must be structurally unrepresentable. `REWRITE_CONFIG`
  precedes `SEARCH_REPLACE` because WP-CLI has no credential flags and bootstraps
  from the config just written — forced by the tool, not chosen.
- **AD-18 — a killed Run must be recoverable.** `mysql < dump.sql` is not one
  transaction; a crash midway leaves a site that **boots and looks fine** with
  mixed state. Run Journal, atomic `os.replace` config write, staging-database
  cutover.
- **AD-25 — the flag matrix is a total function.** `--cleanfirst` × `--force` ×
  `--mode` is twelve reachable states; every one needs an entry, with
  `OverrideSet` a distinct type so `--force` cannot select a Mode.
- **AD-9 — remove the silent privilege escalation, which lives in THIS repo.**
  `wpbackup2/classes/wpsite.py:40` reads
  `self.admin_credentials = admin_credentials if admin_credentials is not None else credentials`,
  so when no admin credentials are supplied the ordinary WordPress database
  credentials are silently used for `CREATE DATABASE` and `GRANT`. Absent admin
  credentials must be an error naming what is missing. Behaviour change — changelog it.
- **AD-28 — escape the database name in any `GRANT` this package issues.** MySQL
  matches it as a LIKE pattern; `_` is a wildcard and backticks do not suppress it.
  **Do not reimplement this.** `l3io-wp-database` exports `quote_grant_database`
  (plus `quote_identifier` for the literal-name cases, which must NOT be escaped —
  `CREATE DATABASE` and connection parameters need the real name).
  `from l3io.wp.database import quote_grant_database`. Duplicating it is a Core §2
  defect, and the two functions differing is the whole point.
- **AD-29 — ask the administrator what exists; never infer it from a failed login.**
  MySQL authenticates before resolving the database, so a fresh site yields
  `1045 Access denied` and never `1049 Unknown database`. Any existence check uses
  administrator credentials. This is the second, independent reason AD-9's credential
  fallback has to go.
- **AD-26 — no silent plaintext Safety Snapshot.** The frozen CLI has no
  passphrase surface; adding one is required, not optional.

## Sequence

1. **Packaging first.** `src/l3io/wp/backup/`, uv + PEP 621, `uv.lock`. Get
   `make ci` green on the existing workflows before touching behaviour — the
   contract gates they invoke (`tools/check_purity.py`,
   `tools/check_mode_defaults.py`, the flag-map test) do not exist yet and must
   be written.
2. **Domain and core**, pure and fully tested without a live WordPress or MySQL.
3. **Adapters**, then the composition roots.
4. Relocation (FR-11, FR-12, FR-13) last — it is the largest greenfield block and
   is scheduled for v1.0.1.

## Explicitly out of scope

- Re-opening any recorded decision. If one is wrong, say so and stop.
- Remote storage, retention, scheduling, the AWS credential provider — all v1.1.
- Publishing.

## A warning about this repository's tests

The existing suite is of the same vintage as the code being replaced, and the
architecture review found tests that assert nothing, a test that name-mangles to a
non-existent attribute and therefore cannot pass, and class-level temp directories
shared across tests. Treat every existing expectation as evidence of what the old
code did, not of what is correct — a fixture generated by a buggy implementation
locks the defect in. One has already been found in a sibling repository encoding a
greedy-match defect as its expected output. This repository's own
`tests/data/wp-config.php` uses WordPress's `define( 'KEY', 'value' );` spacing,
which is precisely the formatting a naive whole-statement verification rejects.

## Divergence-pair triage — read it, it contains decisions

`reviews/TRIAGE-divergence-pairs.md` dispositions all 32 pairs from the two
adversarial reviews: 12 closed by later ADs, 10 decided there, 6 deferred with a
reopen condition, 4 won't-fix. **Ten of those are decisions you must build to**, not
background. The three most likely to be got wrong:

- **`--whatIf` keeps its spelling.** Renaming it to `--what-if` looks like a defect
  fix and silently disables Dry Run for every existing caller. An alias is fine.
- **`--log-level` defaults to `INFO`, not `CRITICAL`.** AD-24 promises the operator
  a log file and `jq`; the preserved default emits nothing, which makes that claim
  false. A behaviour fix, permitted by AD-22.
- **A v1 Archive is gzipped.** The frozen `--archive` help says `.tar.gz`; AD-6's
  "tar container" describes the member layout, not the compression.

## Known open items

The spine's Deferred section lists thirteen lower-ranked divergence pairs from
the second adversarial review, in
`_bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/reviews/review-adversarial-divergence-delta.md`.
The six release-blocking ones are closed. **Triage the rest before the first work
that touches the restore path.**

## Done when

The shared context's definition of done, plus: every AD that names a mechanical
check has that check running in CI; a v0 and a v1 archive both restore in
integration tests; and no invocation passes a credential in `argv` or emits one
to a log at any level.
