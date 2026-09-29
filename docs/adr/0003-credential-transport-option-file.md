# ADR-0003: Credentials reach MySQL clients by option file, never argv or MYSQL_PWD

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD FR-15
- **Principle(s) in tension:** Core §9 logging hygiene, §3 design by contract

## Context

The current code builds `['mysqldump', ..., '-p' + password]` and logs the full argument vector at DEBUG, and the restore path logs `DB_PASSWORD` directly. Any local user reading `ps`/`/proc` sees the password. PRD FR-15 forbids both.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. `MYSQL_PWD` in the child environment | Trivial | MySQL 8.4 manual: *"must be considered extremely insecure"*; **deprecated as of 8.4 and expected to be removed**; readable in some `ps` configurations | Fails §8 — building on a removal-scheduled mechanism |
| B. **`--defaults-file`, mode 0600** | Official recommendation; no argv, no environment; `--defaults-file` **replaces** the default option-file chain, where `--defaults-extra-file` only *adds* to it | Must precede other options; a file on disk needs a guaranteed `finally` | §9, §3 |
| C. `mysql_config_editor` login-path | Oracle's most-secure option | Requires interactive setup; unsuitable for a library invoked from automation | Fails automation-first premise |

## Decision

**Option B, using `--defaults-file` — not `--defaults-extra-file`.** One credential-transport adapter writes a `[client]` option file into the per-Run workspace (AD-12) at mode `0600`, passes `--defaults-file=<path>` **before any other option**, and deletes it in a `finally` on both success and failure.

The distinction is load-bearing. `--defaults-extra-file` is **additive**: an ambient `~/.my.cnf` or `/etc/my.cnf` still applies and can carry a `[client] host=` that redirects a restore to a different database server — silently, and at the worst possible moment. `--defaults-file` replaces the chain entirely, so the Run's connection is determined only by what we wrote.

**This mechanism does not extend to WP-CLI.** `wp search-replace` bootstraps PHP and uses `$wpdb`; it never invokes the `mysql` client and takes no option file. Its credentials come from the `wp-config.php` we rewrite first — see ADR-0005 and AD-17.

Verified 2026-09-15 against the MySQL 8.4 manual: both mechanisms still function; only this family is recommended, and `MYSQL_PWD` is deprecated.

## Consequences

- Positive: closes the disclosure path for every MySQL invocation with one adapter rather than a rule to remember per call site.
- Negative: a window exists where a 0600 file holds the credential; on a filesystem without POSIX permissions the guarantee weakens — detect and refuse rather than proceed silently.
- Follow-up: a test asserts no credential appears in any constructed argument vector, and none in captured log output for a full backup and a full restore.
