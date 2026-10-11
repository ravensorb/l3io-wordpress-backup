# PRD Addendum — wpbackup2

Companion to `prd.md`. Everything here is **input to downstream work** — architecture, ADRs, epics — not product requirement. The PRD states *what* and *why*; this file holds *how*, *what was considered instead*, and the evidence behind both.

---

## A. Competitive landscape

From landscape research conducted 2026-09-12. Positions are as-found; flagged items were not verifiable.

| Tool | What it is | Position | Gap it leaves |
|---|---|---|---|
| **WP-CLI** (`wp db export/import`, `wp search-replace`) | The de facto PHP CLI for WordPress. Reads credentials from `wp-config.php`; `search-replace` is the reference serialization-safe rewriter (`--dry-run`, `--precise`) | Free, mature, universally trusted substrate | No file/media backup, no encryption, no remote storage, no orchestration. A toolkit, not a backup product |
| **UpdraftPlus** | Plugin; strong scheduling and remote-storage UI | WP-admin first; WP-CLI control is a Premium add-on | Automation bolted on; no library story |
| **Duplicator (Pro)** | Migration specialist; serialization-aware replace, pre-flight DB backup before search-replace, installer flow for new host/DB/URL | The best-regarded migration path | Plugin-admin audience; installer expects a browser in the loop |
| **All-in-One WP Migration** | `wp ai1wm backup` / `restore` built into core | CLI present and free | Remote storage behind paid extensions |
| **BackWPup** | Free + Pro, WP-CLI automation | Positions WP-CLI for automation | Plugin-shaped |
| **WP Migrate (DB Pro)** | Site-to-site push/pull over HTTP, no SSH or mysqldump | Closest analog to good cross-environment restore | Site-to-site, not archive-to-anywhere |
| **mysqldump + Restic / Borg** | Ad hoc operator scripts | Encryption, dedup, S3/B2 for free | Treats WordPress as an opaque directory. No `wp-config.php` awareness, no search-replace. Every operator rewrites it |
| **`cariad/py-wordpress-backup`** (PyPI `wpbackup`) | **Near-identical predecessor.** mysqldump + tar of the WP directory, restore with admin credentials optionally from AWS Secrets Manager | Already credited in the current README | *Not a gap — a lineage.* The delta wpbackup2 claims is the supported Python API, relocation, and the archive lifecycle. Maintenance status unverified |

**Positioning conclusion carried into PRD §1:** the defensible niche is the *idiomatic Python library*, and only if it is genuinely idiomatic — typed, exceptions not exit codes, no subprocess-string leakage. A thin `subprocess.run(["wp", ...])` shim wrapped in a class does not occupy this position.

## B. The serialized-data problem (evidence behind FR-12)

WordPress stores PHP-`serialize()`d arrays — widget configuration, theme options, transients, postmeta — as strings carrying byte-length prefixes:

```
s:23:"http://old.example.com";
```

The `23` is the byte length. A SQL `REPLACE(column, 'http://old.example.com', 'https://new.example.com')` changes the content without recomputing the prefix, producing `s:23:"https://new.example.com";` — a value that fails to unserialize. WordPress then silently falls back to defaults: widgets vanish, menus break, theme options reset. The damage is discovered days later and is not obviously connected to the migration.

WP-CLI `search-replace`, Duplicator, and `interconnect/it Search-Replace-DB` all solve it identically: unserialize each value, replace within the real string, re-serialize so lengths are recomputed. Never a raw SQL string replace.

**Current behavior:** wpbackup2 rewrites `wp-config.php` constants only and never touches `wp_options` or postmeta. Relocating to a new URL today therefore leaves a site pointing at the old URL throughout its content. This is the single largest functional gap against every credible competitor, and the reason Relocation (PRD §5.3) exists as a feature area rather than a flag.

## C. Mechanism decisions for architecture

Mechanism, not product requirement — this is material for `bmad-architecture` to decide. Most entries below need an ADR and none of those is settled here; C.2 is the exception and says so, and C.3 is shared evidence rather than a decision.

### C.1 Relocation: delegate to WP-CLI

**Decided in PRD (FR-12); mechanism open.** Options weighed:

| Option | For | Against |
|---|---|---|
| **Shell out to `wp search-replace`** *(chosen)* | Reference implementation; free correctness; `--dry-run` maps onto FR-19 | New external runtime dependency; version drift; PHP must be present |
| Reimplement in Python | No external dependency | Owning a PHP-serialization parser — precisely the "hand-roll a parser" failure mode. Subtle, high-blast-radius bugs |
| Vendor `interconnect/it Search-Replace-DB` | Proven | PHP anyway; unmaintained; license review needed |

Architecture must decide: invocation seam, how credentials reach `wp` without `argv` exposure (FR-15), the supported WP-CLI range — FR-27 already requires detection and a declared minimum, the range is the open part — and whether `wp` runs against the restored site directory or a standalone config.

### C.2 The `wp-config.php` capability (FR-11, FR-29)

**Resolved: there is no build-or-buy decision to make.** The four options an earlier revision weighed here — vendor, fork, reimplement, or delegate to WP-CLI `wp config get/set`, the last of which contradicted FR-13 — are moot, and so is the arch review's B-1 remediation, "vendor or fork `wpconfigr`". The fork already exists.

Version 1.4 sits in `py-wpconfigr` (`github.com/ravensorb/py-wpconfigr`, forked from `cariad/py-wpconfigr`): four modules, no runtime dependencies of its own. PRD §9 covers what adopting it costs. Two details matter to architecture and are not in the PRD: the fork is byte-identical to upstream, so there is no local patch set to carry forward or re-apply; and nothing in the repository says why it never reached PyPI — no release credentials, no tags, no changelog — so `pypi.org/simple/wpconfigr/` returning 404 cannot distinguish "never published" from "withdrawn". Plan the release as a first publication.

The action is a release, not a decision. PRD Q-6 settled the naming: republish under the existing `wpconfigr` name, which is what lets both dependents keep their declaration untouched and keeps Release A a two-repository change.

One genuine concern survives that decision. Both packages declare `wpconfigr>=1.0.0,<=2.0.0`, a range that admits an unreviewed 2.0 — so the family would absorb a major version nobody signed off on. Narrowing it is not free, because changing the range in both dependents is the coordinated edit Q-6 was chosen to avoid; doing it at the next release each package cuts anyway costs nothing extra. That trade is architecture's to make.

No ADR is needed for the capability itself. One is still worth writing for the cross-package version policy.

### C.3 The dependency graph as declared

```
wpbackup2  (909 LOC) ──┬─→ wpconfigr  ◄───────────┐   343 LOC, no runtime deps
                       │                          │   v1.4 local · 404 on PyPI
                       ├─→ wpdatabase2 ──┬─────────┘   752 LOC · v0.0.15 (2020-12-04)
                       │                 ├─→ boto3
                       │                 └─→ mysql-connector
                       └─→ chesney   ← genuinely gone · feature CUT
```

Three facts follow, each feeding a PRD requirement or precondition:

1. **`wpconfigr` is a shared kernel**, depended on by both other packages. Its version policy is a family-level concern. PRD Q-10 previously left that unowned; it is now a named Release A precondition owned by Sanderson (PRD §13.2), so the gap is assigned rather than open.
2. **`boto3` is a hard runtime dependency of `wpdatabase2`**, therefore transitively mandatory for every `wpbackup2` install. FR-14 requires the opposite, and that is unsatisfiable from this repository alone — which is why demoting it to an optional extra in the sibling package is now a named Release A precondition (PRD §13.2, closing Q-9) rather than an open question.
3. **`mysql-connector` 2.2.9 last shipped 2019-04-01** and is the superseded Oracle-uploaded distribution name; the maintained package is `mysql-connector-python` (26.7.0, 2026-07-29). A seven-year-stale driver in the runtime path of a backup tool. Feeds FR-26. Architecture should also weigh PyMySQL, which is pure-Python and removes a wheel-availability constraint.

### C.4 `chesney` removal

`chesney.is_appointed()` is called once, at `__main__.py:164`, guarding `--only-appointed-in-asg`. Cutting the feature (PRD §13.1) removes the dependency entirely. No replacement needed. This is the cheapest of the three supply-chain resolutions and should land first.

### C.5 Credential transport (FR-15)

Two established mechanisms, both avoiding `argv`:

- `MYSQL_PWD` in the child process environment — simple; historically discouraged in MySQL docs as environment is readable in some configurations
- A generated `--defaults-extra-file` with mode 0600, removed in a `finally` — the more defensible option; also the one that works uniformly for `mysql`, `mysqldump` and `wp`

Recommend the defaults-file approach. Architecture should confirm behavior when the temp directory is on a filesystem without POSIX permissions.

### C.6 Packaging

`uv` + PEP 621 `pyproject.toml`, committed `uv.lock`, CI installing frozen. Retire `setup.py`, `setup.cfg`, `build.sh`, `publish.sh`, and `test.py`. Optional extras for AWS and remote Storage Targets so a base install stays thin (FR-25). Release via CI with trusted publishing rather than a local `twine` script running under `sudo`.

### C.7 Archive format

The Manifest (FR-3) makes the archive self-describing and is what FR-10's version gate reads. Open for architecture: whether the Manifest lives as a member inside the tar or as a sidecar; whether encryption wraps the whole archive or the members; whether streaming encryption is compatible with the chosen integrity scheme. The PRD's constraint is that encryption parameters live in the Manifest and the key never does.

## D. Existing-code findings carried forward

From `_bmad-output/implementation-artifacts/arch-review-2026-09-12.md`. Listed so implementation knows which requirement each maps to — the PRD deliberately states these as capabilities rather than defects.

| Review finding | Becomes |
|---|---|
| B-1 dependencies unresolvable on PyPI (see C.2) | FR-25, FR-26, §9 |
| B-2 no lockfile or `pyproject.toml` | FR-25 |
| B-3 `restore_mode` discarded; unconditional `rmtree`; DB restore silently skipped | FR-6, FR-7, FR-9 |
| B-4 credentials in logs and `argv` | FR-15, NFR-3 |
| M-1 `--mode db` never matches | FR-2 |
| M-2 `in args` no-ops; `--new-site-home-url` inert | FR-11 |
| M-3 database-only backup produces no archive | FR-2 |
| M-4 internals bypass `WpSite` and re-read config | FR-11 (single source of truth for the Site Descriptor) |
| M-5 `WpSite` god object | FR-22 (typed domain objects), architecture |
| M-9/M-10/M-11 broken and assertion-free tests | NFR-8, and a test strategy ADR |
| M-12 no CI | FR-25, FR-26 — the mechanical checks have nowhere to run without it |
| M-14 `extractall` without containment | NFR-5 |
| M-15 hardcoded `/tmp`, predictable filenames | NFR-4 |
| M-16 failure paths exit 0 | FR-21 |
| M-17 `--cleanfirst` and `--mode` inert on restore | FR-6, FR-11 |
| M-18 no structured logging or correlation ID | FR-20, NFR-6 |
| M-20/M-21 no docs; README documents flags that do not exist | §11 runbook; documentation is a release gate |

## E. Deferred user-supplied depth

Nothing yet. Qualitative material the PRD's FR structure would drop — tone of CLI output, error-message voice, documentation personality — has not been discussed and is a candidate for the UX pass if one is run.

## F. Sources

- Landscape research digest, 2026-09-12 (WP-CLI, UpdraftPlus, Duplicator, All-in-One WP Migration, BackWPup, WP Migrate DB Pro, Restic/Borg patterns, `cariad/py-wordpress-backup`)
- `_bmad-output/implementation-artifacts/arch-review-2026-09-12.md`
- Existing codebase at `01ee58c`, v0.2.21
- Sibling repositories inspected 2026-09-12: `py-wpconfigr` (wpconfigr v1.4) and `py-wordpress-database` (wpdatabase2 v0.0.15)
- PyPI index status checked 2026-09-12 for: wpconfigr (404), chesney (404), wpdatabase2 (0.0.15), mysql-connector (2.2.9, 2019-04-01), mysql-connector-python (26.7.0, 2026-07-29)
