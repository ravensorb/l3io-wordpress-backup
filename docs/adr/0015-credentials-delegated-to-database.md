# ADR-0015: Credentials reach MySQL client tools only through `l3io-wp-database`

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Shawn Anderson
- **Epic:** E002 (stories 2.1, 2.4), E003 (stories 3.4, 3.5), E005 (story 5.1)
- **Supersedes:** [ADR-0003](0003-credential-transport-option-file.md)
- **Departs from spec:** _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-7--credentials-reach-a-subprocess-by-file-never-by-argument-or-environment

## Context

ADR-0003 had this package write a `[client]` option file at mode `0600` into the per-Run
workspace and pass it as `--defaults-file`. `l3io-wp-database` v0.1.0 owns `dump` and
`load`, and its ADR-0002 passes the same options through an anonymous pipe
(`--defaults-file=/dev/fd/N`) with a scrubbed environment and, on MySQL 8.4+,
`--no-login-paths`. Nothing reaches disk, a crash leaves nothing behind, and a hostile
`~/.my.cnf` or `~/.mylogin.cnf` changes nothing — stronger than a file on disk.

Two transports in one family would mean two implementations of the guarantee, and only
one tested against the tools.

## Decision

This package **never builds an argument vector for, or an option file for,
`mysqldump`/`mysql`/`mariadb-dump`/`mariadb`**. It calls `l3io-wp-database`:

- `dump` and `load` (with `replace=`) for the database half of backup and restore;
- `survey`, `ensure` and `drop_database` for provisioning — AD-29's existence checks and
  the spine's "exactly one provisioning implementation";
- `CredentialChain` for credential providers (story 5.1).

AD-7's invariant stands for this package: no credential in any log record, argument
vector, `repr` or exception raised to a caller. Its **mechanism** and the assertions about
the option file now belong to `l3io-wp-database` (its ADR-0002 and tests). This package
keeps the assertions on what it emits itself, and a test that no module here invokes a
MySQL client binary.

## Consequences

- One credential transport for the family, owned where the client tools are called.
- Story 2.4 shrinks to composing database's API and asserting this package's own output;
  it no longer needs the per-Run workspace for an option file.
- Restore depends on database's `load` semantics, including staging (`replace=`).
- **Revisit when:** this package needs a client-tool invocation database does not offer.
  Add it to database rather than here.
