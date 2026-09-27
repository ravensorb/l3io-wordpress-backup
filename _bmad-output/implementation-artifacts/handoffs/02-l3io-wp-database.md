# Handoff 2 — `py-wordpress-database` becomes `l3io-wp-database`

**Read `00-SHARED-CONTEXT.md` in this folder first.**

**Repository:** `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-database`
**Release position:** SECOND — after `l3io-wp-config` resolves from PyPI, before
`l3io-wp-backup`.

## Why this package matters more than its size suggests

It owns database connection details, credentials and provisioning for the family.
Two defects in it are currently *unfixable from the downstream package*, which is
why this repository has to change and not just be renamed.

## Scope

### 1. Rename and re-namespace

`wpdatabase2/` becomes `src/l3io/wp/database/`; distribution `l3io-wp-database`.
Re-read AD-27 before creating directories.

### 2. Make `boto3` genuinely optional — this answers an open PRD question

Today `classes/credentials.py` imports `Secret` at module scope, and
`classes/secret.py` imports `boto3` at module scope. So importing
`WpCredentials` — which every downstream path does — drags `boto3`, `botocore`,
`s3transfer` and `jmespath` into **every** installation, AWS user or not.

Move the `boto3` import **inside the method that uses it** (AD-8, ADR-0008), put
`boto3` behind an `aws` extra, and raise a package-owned error naming the extra
when it is absent. Add a CI assertion that a base install — no extras — imports
every public module and that `boto3` is **not** importable.

This is the mechanical answer to **PRD Q-9**, which was left open because it
could only be fixed here.

### 3. Replace the abandoned driver

`mysql-connector` 2.2.9 was last released **2019-04-01** — the superseded
Oracle-uploaded distribution name, seven years stale, in the runtime path of a
backup tool. **ADR-0004** chose **PyMySQL** (MIT, pure Python, one universal
wheel). `mysqlclient` was rejected on GPL-2.0 plus absent Linux/macOS wheels;
`mysql-connector-python` on licence friction. Do not revisit without reading
ADR-0004.

### 4. Fix the domain model — three defects, all with named invariants

- **AD-3 — one immutable Site Descriptor.** `WpConnection.db_host`'s setter
  parses `host:port` and derives `_db_port`, while `db_port` has its own
  independent setter. Two writers for one value; they can desync. Make it a
  frozen value object, parsed once at construction, no setters.
- **AD-9 — credential resolution is an explicit call, not a property read.**
  `WpCredentials.username` and `.password` are property *getters* that call
  `_resolve_secret()`, which performs an AWS round trip **and mutates `self`**.
  Hidden network I/O behind attribute access: untestable, unpredictable in
  failure timing, invisible at the call site. Replace with an explicit
  `resolve()` returning a frozen credential value.
- **AD-28 — escape the database name in a `GRANT`.** MySQL matches it as a LIKE
  pattern, so `_` is a single-character wildcard and a grant on `wp_site` also
  grants on `wpXsite`. Backticks do not suppress it. One shared escaping function,
  with a regression test proving a neighbouring name is unreachable.

### 5. Credential transport

Any subprocess invocation of `mysql`/`mysqldump` uses **`--defaults-file`**
(mode 0600, deleted in a `finally`) — **not** `--defaults-extra-file`, which is
*additive*: an ambient `~/.my.cnf` can carry a `[client] host=` that silently
redirects to a different database server. `MYSQL_PWD` is forbidden; MySQL 8.4
calls it "extremely insecure" and deprecates it. See **AD-7** and **ADR-0003**.
Credentials reaching PyMySQL go as call arguments, never in a logged or stored
connection string.

### 6. CI

Copy from `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-backup/.github/workflows/ci.yml`. **Keep the database
services** — this package needs them — pinned to `mysql:8.4` and `mariadb:11.4`,
addressed via `DB_HOST` (see trap 3 in the shared context). Drop the WP-CLI
install step. Add the base-install-has-no-boto3 assertion from §2.

## Explicitly out of scope

- Deciding whether this package should continue to exist. The spine's Deferred
  section flags that AD-3 and AD-9 remove much of its reason to be separate, to
  be revisited **after** the family is releasable. Not now.
- Publishing.

## Done when

The shared context's definition of done, plus: a base install imports cleanly and
cannot import `boto3`; `from l3io.wp import database` works from the wheel; the
admin-credential fallback is gone and its removal is in the changelog; and no
invocation anywhere passes a password in `argv` — assert it against a constructed
argument vector, and assert no credential appears in captured log output.
