# Input Reconciliation: Codebase vs. PRD

Input: the existing codebase (`wpbackup2` v0.2.21, plus siblings `py-wpconfigr` v1.4 and
`py-wordpress-database`/`wpdatabase2` v0.0.15) at
`/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/`.

Target: `prd.md` and `addendum.md` in this folder.

Scope discipline: this is not a quality review of the PRD, and it does not re-report anything
the PRD already discusses as a defect (arch-review items B-1..M-21, all carried forward in
addendum.md §D) or anything explicitly cut (`--only-appointed-in-asg` / `chesney`, §13.1). It
reports capability, behavior, or stated intent that exists in the source material and has no
textual home — no FR, no NFR, no glossary entry, no §12/§13 mention — anywhere in the PRD.

---

## 1. Database port is a supported relocation target, but FR-11 never names it

`WpConnection.db_host` (`py-wordpress-database/wpdatabase2/classes/connection.py:40-54`) parses
`host:port` and exposes `db_port` as an independent property. `WpSite` inherits this
(`wpbackup2/classes/wpsite.py`), and the actual restore-time config rewrite uses it:

```python
# wpbackup2/classes/wp_internal_restore.py:75
wp_config.set('DB_HOST', "{}{}".format(self.__wp_site.db_host,
              ":{}".format(self.__wp_site.db_port) if (self.__wp_site.db_port is not None) else ""))
```

`README.md:64` documents a `--new-db-port 3306` flag as part of the restore-with-relocation
example. The domain model treats port as first-class and the maintainer's own docs advertise a
flag for it (the flag doesn't actually exist in `__main__.py` today — that's the already-tracked
M-20/21 doc-drift defect — but the *intent* to relocate onto a different port is independent of
that bug).

FR-11 ("Configuration rewriting") lists exactly what an operator can relocate: "a new database
host, database name, database credentials, site URL and site home URL." Port is not in that
list, and none of FR-11's testable consequences mention it. As written, a relocation that must
move to a differently-ported database host (a common real case — Docker Compose, RDS, a
non-default MySQL port) has no requirement obligating support for it, even though the
underlying `WpConnection`/`WpSite` types already carry the concept end to end.

**Home:** §5.3/FR-11 (add database port to the enumerated relocation values), and arguably §4
Glossary's Site Descriptor entry, which lists "database host" as if it were a single scalar
rather than the host+port pair the code already models.

---

## 2. `WpBackupNotFoundError` is exported public API with no raise site and no PRD counterpart

`wpbackup2/exceptions/backup_not_found.py` defines `WpBackupNotFoundError` ("Raised when backup
file cannot be found"), and it is re-exported from the package root at
`wpbackup2/__init__.py:9`. A repo-wide search turns up zero call sites that ever raise it — it
is declared, exported, and dead. The clear original intent (readable straight off the docstring)
was that attempting to restore from a nonexistent archive path should fail with this typed
error. Today `WpInternalRestore.restore()` opens the archive directly
(`wp_internal_restore.py:111`, `tarfile.open(archive_filename, 'r:gz')`) with no existence check,
so a missing archive instead raises a bare `FileNotFoundError` (or `tarfile.ReadError` for a
corrupt one) — an untyped, non-package exception crossing the public boundary.

FR-23 ("Exception contract") states "Every documented failure mode maps to a documented
exception type exported from the package" and "The package does not raise a dependency's [or,
by the same logic, the standard library's] exception types across its own public boundary." Both
consequences describe exactly the gap this type was built for, yet the PRD never names
`WpBackupNotFoundError`, never lists "archive file does not exist" as a failure mode next to the
similar and already-covered "Archive with no Manifest is refused" (FR-10), and gives no
disposition (keep it and wire it up / retire it) for this specific exported symbol.

**Home:** §5.7/FR-23, or alongside FR-10 in §5.2 where "archive not found" is the sibling case
to "archive format not supported."

---

## 3. `--version` is an existing, working CLI capability with no PRD line

`wpbackup2/__main__.py:36-37`:

```python
arg_parser.add_argument('--version', action='version',
                version='%(prog)s {version}'.format(version=__version__))
```

`python3 -m wpbackup2 --version` works today and prints the installed package version (the same
pattern exists verbatim in the sibling `wpdatabase2/__main__.py`). No FR or NFR mentions CLI
self-versioning. §11's "Diagnostics" bullet ("A single command reports environment readiness:
Python version, external tool presence and versions, optional extras installed, and Storage
Target reachability") is a different capability — environment inspection, not "what version of
wpbackup2 am I running" — and doesn't subsume this one. §10 (Versioning and Deprecation Policy)
talks about what a version *means* but never states that the CLI must be able to report its own
version.

**Home:** §5.6 (Safety, Observability and Exit Behavior) or §11, as a one-line FR/consequence.

---

## 4. `--log-level` verbosity control exists today, in all three sibling packages, and has no PRD requirement

`wpbackup2/__main__.py:38-41` (default `'CRITICAL'`), `py-wpconfigr/wpconfigr/__main__.py:35-38`
(default `'CRITICAL'`), and `py-wordpress-database/wpdatabase2/__main__.py:44-46` (default
`'INFO'`) all expose an operator-settable `--log-level` flag feeding `logging.basicConfig`. FR-20
("Structured logging correlated by run ID") covers output *format* selection and Run ID
correlation, but nowhere states that an operator can control verbosity, nor does it acknowledge
the flag that already does this. It's also worth surfacing that the three packages already
disagree on a sensible default (`wpbackup2`/`wpconfigr` at `CRITICAL`, i.e. near-silent by
default, vs. `wpdatabase2` at `INFO`) — exactly the kind of "family" inconsistency §9/Q-10
already flags as unowned across the three repos, but concretely, in this one flag, today.

**Home:** §5.6/FR-20, as an explicit consequence ("an operator can select log verbosity from the
CLI"), and a note for the cross-package policy in Q-10.

---

## 5. Admin-credential fallback default (`wpsite.py:40`) has no home in the credential-provider requirements

```python
# wpbackup2/classes/wpsite.py:40
self.admin_credentials = admin_credentials if admin_credentials is not None else credentials
```

When no distinct admin credentials are supplied, `WpSite` silently reuses the ordinary
connection credentials as the admin credentials passed to
`wpdatabase2.WpDatabase.ensure_database_setup()` — which runs `CREATE DATABASE IF NOT EXISTS`
and `GRANT ALL PRIVILEGES ... TO <user>`. This is a real, load-bearing default: it means a
low-privilege application DB user can silently be handed database-creation and
privilege-granting duties whenever the operator doesn't think to pass separate admin
credentials.

FR-14 ("Pluggable credential providers") states "Provider resolution order is documented and
deterministic" — but that's about which *source* wins among several for the same credential
slot (explicit / env / `wp-config.php` / secret store). It says nothing about this different
axis: the aliasing between the *admin* credential slot and the *ordinary* credential slot when
one is absent. Nothing in §5.4, §7.1 (Safety) or §7.2 says whether this fallback is being kept
as a convenience, tightened (e.g. admin credentials become mandatory for any operation that can
create a database/user), or removed.

**Home:** §5.4/FR-14, as an explicit consequence about admin-vs-connection credential
resolution, or §7.1 (least-privilege is currently only framed as "no credential in argv/logs,"
not "no credential is used for more privilege than the operator intended for it").

---

## 6. README TODO — "Handle `wp-config.php` being somewhere other than the default location" — has no FR

`README.md`'s TODO section reads:

```
## TODO
 - Unit tests.
 - Handle `wp-config.php` being somewhere other than the default location.
```

The first item is addressed (NFR-8, plus addendum §D's M-9/M-10/M-11 → "a test strategy ADR").
The second is not addressed anywhere. It's stated maintainer intent, not a defect the arch review
flagged, and not something §13 lists as cut. §4's Glossary defines Site Root as "the filesystem
directory containing the WordPress installation. Contains `wp-config.php` in the default
layout" — the phrase "in the default layout" tacitly acknowledges non-default layouts exist, but
no FR anywhere gives an operator a way to point wpbackup2 at a `wp-config.php` that isn't at
`<site_root>/wp-config.php` (the same constraint that produces `WpConfigNotFoundError` today,
`wp_internal_backup.py:76`, when it isn't). This is exactly the "README TODO the PRD drops"
case the reconciliation pass is meant to catch.

**Home:** either promote it into an FR under §5.1/§5.2 (an operator can specify an explicit
`wp-config.php` path independent of Site Root), or make it an explicit, named non-goal in §13.1
so it isn't silently absent.

---

## 7. (Minor/secondary) wpconfigr's typed value round-trip is a sibling behavior FR-11 quietly depends on

`py-wpconfigr/wpconfigr/wp_config_string.py` — `get()` (lines 93-126) coerces PHP `true`/`false`
literals to Python `bool` and numeric literals to `float`; `set()` (lines 143-204) special-cases
`bool` back to a lowercase PHP literal and otherwise treats the value as a string, quoting it.
This means constants like `WP_DEBUG` (boolean) or numeric constants round-trip through a type
conversion, not a raw string copy. FR-11's consequence "The rewritten `wp-config.php` remains
valid PHP and preserves constants wpbackup2 does not manage" implicitly assumes this machinery
works, but the PRD states no requirement that boolean/numeric constant fidelity be preserved
through a relocation rewrite — a plausible seam for architecture to silently regress if
`wpconfigr` is ever reworked (addendum §C.2 treats `wpconfigr` as "resolved," not open, so this
dependency is easy to overlook).

**Home:** a testable consequence under FR-11, or a note in addendum §C.2/§C.6.

---

## 8. (Minor/secondary) `WpSite` accepts either a Site Root or a full `wp-config.php` path interchangeably

```python
# wpbackup2/classes/wpsite.py:42-44
if "wp-config.php" in site_path:
    site_path = Path(site_path).parent
```

This forgiving normalization (also present in `WpSite.from_wp_path`,
`wpbackup2/classes/wpsite.py:61-72`) is real, existing ergonomics: callers can pass either a
directory or the config file itself. Neither the Site / Site Root / Site Descriptor glossary
entries (§4) nor FR-1 mention this flexibility as something to keep, extend (see item 6 above),
or intentionally narrow.

**Home:** §4 Glossary (Site Root definition) or FR-1's consequences.

---

## Summary of what's NOT a gap (checked, and already covered)

- `--only-appointed-in-asg` / `chesney` — explicitly cut, §13.1.
- `--cleanfirst` disconnection from actual restore mode selection — captured as arch-review
  M-17 → FR-6/FR-11 in addendum §D.
- `--mode db` never matching `WpBackupMode.DATABASE` — M-1 → FR-2.
- `boto3` / `mysql-connector` transitive dependency issues — FR-14/FR-26, Q-9, addendum §C.2b.
- Sibling-package exceptions (`InvalidArgumentsError`, `RegionNotKnownError`, etc.) crossing the
  `wpbackup2` public boundary today (e.g. `wpsite.py:79`) — FR-23's "does not raise a
  dependency's exception types across its own public boundary" directly targets this class of
  problem, even without naming the specific types.
- README documenting flags that don't exist (`--new-db-port`, `--new-site-host` vs.
  `--new-site-home-url`) — M-20/21 → "documentation is a release gate," addendum §D.
