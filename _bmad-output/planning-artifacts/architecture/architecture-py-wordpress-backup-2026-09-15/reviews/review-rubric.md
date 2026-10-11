---
review: good-spine rubric walk
target: ARCHITECTURE-SPINE.md (wpbackup2 family, 2026-09-15, draft)
supporting: docs/adr/0001..0010 + README.md, .memlog.md
reviewer: rubric walker (pre-handoff gate)
date: 2026-09-15
---

# Rubric Review — ARCHITECTURE-SPINE.md (wpbackup2 family)

## Summary verdict

This is a well-grounded spine. Nearly every claim it makes about the brownfield code is
literally true in the source — I checked fifteen of them line by line and did not find one
that was overstated — and every version in the Stack table matches the live index today.
The invariants it does fix (dependency direction, descriptor ownership, Dry Run as adapter
selection, Restore Mode as a defaulted-nowhere value, one owned archive contract, credential
transport, extraction containment, per-Run workspace, preflight, release ordering) are the
right ones, and most carry a named mechanical check rather than prose.

It is held back by three things: a handful of **genuinely silent dimensions** — the Site lock
(FR-28), Storage Target write atomicity (NFR-2), the streaming shape of the archive ports
(NFR-7), the OS/platform envelope, and the MySQL/MariaDB engine matrix; a **contradiction
between AD-1's layer table and the `wpconfigr` code it claims to ratify**, which the mandated
import-linter contract would fail on day one; and **two of its sharpest rules left to review**
when both are one grep away from mechanical. None of these is fatal, all are cheap to close now
and expensive later, and the document is otherwise the right length for what it governs.

---

## Checklist verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Fixes the real divergence points, misses none | **adequate** |
| 2 | Every AD's Rule genuinely enforceable | **adequate** |
| 3 | Nothing under Deferred can let two units diverge | **strong** |
| 4 | Named technology verified-current, not asserted | **strong** |
| 5 | Ratifies the brownfield codebase | **adequate** |
| 6 | Covers the driving spec's capabilities | **adequate** |
| 7 | Every dimension decided, deferred, or open | **thin** |

---

## 1. Does it fix the real divergence points for the level below? — **adequate**

### What it gets right

The spine's central claim — that Dry Run correctness and destructive-mode correctness are the
same defect class, "a value that every call site must remember to honor" — is correct, and the
three ADs that attack it (AD-1, AD-4, AD-5) are exactly the entries that pass the test "could
two units built independently choose incompatibly?" A backup epic and a restore epic building
in parallel genuinely could pick different answers to:

- which module owns the arcnames and the Manifest schema (**AD-6**) — and did, in the live code:
  `DB_DUMP_ARCNAME = 'database.sql'` and `WP_DIR_ARCNAME = 'wp-root'` are duplicated literals in
  both `wp_internal_backup.py` and `wp_internal_restore.py`;
- how a credential reaches a subprocess (**AD-7**);
- whether the temp workspace is shared or per-Run (**AD-12**);
- whose exception type crosses a package boundary (**AD-14**) — and did:
  `WpSite.from_wp_config` raises `wpdatabase2`'s `InvalidArgumentsError` from inside `wpbackup2`;
- who depends on whom across three separately-released repositories (**AD-2**).

AD-5 is the strongest single entry in the document. `**no function that consumes a Restore Mode
may declare a default for it**` is not advice; it is a constraint that makes the B-3 defect
unexpressible, and it is narrower and better than the obvious alternative ("pass the mode
through"), which is what the current code already tries to do and fails at.

### What it misses

**M1 (HIGH) — FR-28, the Site lock, is fixed by no AD, and is mis-filed.**
The Capability map's only mention is:

> `| FR-21 exit codes, FR-28 concurrency | cli/ | AD-12, AD-14 |`

AD-12 is the per-Run *workspace*; it says nothing about a lock. This is a textbook divergence
point and the map's own placement makes it worse. FR-28's consequences require:

- a lock "identified by the Site" — *what names a Site?* Site Root realpath? Site Root + database?
  Two units will answer differently, and two different answers mean two Runs both acquire;
- acquired "before its first read of Site state" — i.e. before the Site Descriptor is even built,
  which puts it above the descriptor in the composition-root ordering AD-3 governs;
- released "on success, on failure, **and on signal**";
- stale-lock reclaim — *by what criterion?* PID liveness, mtime, both;
- and explicitly: "the guarantee holds for a `cron` entry, a `systemd` timer, a shell, **and a
  library caller alike**."

That last consequence is directly contradicted by filing FR-28 under `cli/`. A library caller
entering through `api/` gets no lock at all under the map as written, and `api/` and `cli/`
are two separately-built composition roots. This is the classic shape: the destructive tool
(`shutil.rmtree`, database drop) with two entry points and no shared mutual exclusion.

**M2 (MED-HIGH) — NFR-2 (artifact atomicity) is bound by nothing.**
No AD's **Binds** line names NFR-2, and no Capability map row covers it, yet the frontmatter
asserts `binds: [FR-1..FR-29, NFR-1..NFR-8]`. The invariant NFR-2 needs is a property of the
`ArchiveStore` port contract — *an Archive becomes visible at a target only after it is complete
and verifiable* — which is precisely a decision `LocalArchiveStore` and a future `S3ArchiveStore`
could make incompatibly (write-in-place vs. write-temp-then-rename vs. multipart-then-complete).
Deferring remote targets to v1.1 does not defer this: local storage ships in v1.0, and UJ-1's
edge case ("`mysqldump` fails — no partial Archive is published to the Storage Target, and last
night's Archive is left untouched") is a v1.0 behaviour.

**M3 (MED-HIGH) — NFR-7's streaming/memory shape is bound by nothing.**
NFR-7 states "Archives are streamed, never buffered whole in memory: peak resident memory does
not scale with Archive size", and says it is asserted in the suite. The spine never says it.
This matters because it is a *port signature* decision: does `ArchiveStore` take `bytes` or a
file-like object? Does the crypto adapter consume an iterator of chunks? ADR-0006 makes the
streaming argument beautifully on the encryption side ("the docs state the complete message must
be in memory... Unusable for multi-GB archives") and then the spine does not carry the conclusion
up into an invariant that the tar adapter, the store adapter and the crypto adapter must all
satisfy. The live code is the counter-example and shows how easy the wrong choice is:

```python
completed = subprocess.run(args, capture_output=True)   # whole dump in memory
with open(db_dump_filename, 'wb') as stream:
    stream.write(completed.stdout)
```

Three adapters, one unstated contract, built by different stories — that is the definition of a
divergence point.

**M4 (MED) — Exit code ↔ exception mapping.**
PRD §8 makes exit-code meanings part of the CLI contract and §10 makes reassigning one a breaking
change; FR-21 enumerates five that must be distinct. AD-14 establishes a per-package exception
hierarchy with structured fields. Nothing joins them. Whether the exit code is *derived from the
exception type* (one table at the composition root, mechanically complete by construction) or
*chosen per command* is exactly a non-obvious call with a real trade-off, and two command
implementations will pick differently and collide. One sentence in AD-14 or the Conventions table
closes it.

**M5 (LOW-MED) — the Capability map is a hand-kept second copy of a relation that already exists,
and it has already drifted.** Every AD carries a **Binds:** line; the map's "Governed by" column
restates the same FR→AD relation by hand. It is wrong in at least one place:

> `| FR-25, FR-26, FR-27 supply chain | CI, pyproject.toml ×3 | AD-2, AD-15 |`

FR-27 is external-tool declaration, detection and the diagnostic command. It is governed by
**AD-13**, whose own Binds line says so ("Binds: FR-13, **FR-27**, NFR-1"), and it lives in
`ports/` and `cli/`, not in CI and `pyproject.toml`. Derive the map from the Binds lines, or drop
the "Governed by" column and let Binds be the single source.

---

## 2. Is every AD's Rule genuinely ENFORCEABLE? — **adequate**

Most are. Five carry a named, mechanical check and would survive contact with a hostile
contributor:

| AD | Enforcement named | Assessment |
|---|---|---|
| AD-1 | "an import-linter contract in CI, **not by review**" | mechanical, with a reach gap (below) |
| AD-6 | "derived from committed fixture Archives exercised in CI — **never a hand-maintained list**" | exemplary — derives scope from the source of truth |
| AD-7 | "a test asserts both properties against a constructed argument vector and against captured log output" | mechanical, and tests the two distinct disclosure paths separately |
| AD-8 | "CI asserts that a base install — no extras — imports every public module successfully" | mechanical; catches the exact live defect |
| AD-15 | "a CI job that, in a clean environment on every supported Python version, installs the built artifact **from the index** and imports it" | mechanical, and correctly refuses to test the working tree |

AD-6 and AD-15 are the two best-constructed rules in the document. AD-6 derives the supported
format range from the fixture set rather than a list someone must remember to edit; AD-15
installs from the index rather than the tree, which is the precise blind spot that let the
outage ship.

### Findings

**E1 (MED) — AD-5's sharpest clause names no enforcement.**
AD-5 exists to prevent a data-loss defect and its Rule is excellent, but nothing in it says how
`no function that consumes a Restore Mode may declare a default for it` is checked. This is
AST-checkable in about fifteen lines (walk `FunctionDef`, any parameter annotated `RestoreMode`
with a non-`None` default is a failure) or approximable with a ruff/flake8 custom rule. As
written it is a rule that lives only in prose, governing the one defect the document says is
the most consequential in the codebase. Write the check in the same change as the rule.

**E2 (MED) — AD-4 explicitly downgrades itself to review.**
The Rule opens mechanically — "no `if dry_run:` anywhere in `core/` or `adapters/`" — and then
closes with "a conditional in an adapter **is a review rejection**." A grep for
`dry_run|what_if|dry-run` under `core/` and `adapters/` is a one-line CI step. The rule is
already phrased as something grep can check; leaving it to review is a choice, and it is the
wrong one for the defect class the paradigm was chosen to eliminate.

**E3 (MED) — AD-1's stated enforcement does not reach the whole of AD-1's Rule.**
The Rule forbids core/domain from touching `subprocess`, `socket`, `shutil`, `tarfile`, **`open`**,
`boto3`, "no clock or RNG read". import-linter analyses the *import graph*. It will catch
`import subprocess`, `import tarfile` and `import boto3` cleanly. It cannot catch `open(...)`,
which is a builtin and appears in no import statement; it will catch `import time` / `import
random` only if those modules are enumerated in the contract, and a hand-enumerated forbidden-module
list is the drift-prone shape. So the guard proves part of the rule and the Rule's own sentence —
"Enforced by an import-linter contract in CI, not by review" — overstates its coverage. Either
name the second check (a ruff rule / flake8-builtins for `open` in those trees) or state plainly
what import-linter covers and what it does not.

**E4 (LOW-MED) — AD-9's first sentence is a constraint; its second is advice.**
"a Credential Provider is a port with one explicit `resolve()` returning a frozen credential
value" is structural and enforceable — a Protocol with one method makes the property-getter shape
unexpressible. "**Property getters perform no I/O and no mutation**" is a review rule with no
check, and it is the sentence aimed directly at the live defect (`WpCredentials.username` calling
`_resolve_secret()`, which performs an AWS round trip and mutates `self`). The structural half
does most of the work if the port is the only way credentials are obtained; say that, and the
advice sentence becomes redundant rather than unenforced. The third sentence —
"**A provider never silently substitutes one credential for another**" — is the genuinely
load-bearing one (the live code has `self.admin_credentials = admin_credentials if
admin_credentials is not None else credentials`) and it *is* enforceable structurally: make
admin credentials a distinct, non-defaulted parameter on the operations that need them, which is
the same move AD-5 makes for Restore Mode. Say that explicitly.

**E5 (LOW) — AD-2 and AD-10 name no enforcement.** Both are highly checkable. AD-2's
"`wpconfigr` declares **zero** runtime dependencies, permanently" is a two-line CI assertion
against the built metadata, and "No package imports a dependent" is an import-linter contract
already being stood up for AD-1. AD-10's "configured once at the composition root and never in a
library module" is a grep for `structlog.configure` outside `cli/` and `api/`. Both are free
given the machinery AD-1 and AD-15 already require.

**E6 (LOW) — AD-14's mechanical consequence is dropped.** FR-23 asks for something specific and
checkable: "Every exception type exported from the package has at least one reachable raise site,
**asserted mechanically**. An exported type that nothing raises is either wired up or removed —
today `WpBackupNotFoundError` is public API that no code path can produce." I confirmed that:
`WpBackupNotFoundError` is exported from `wpbackup2/__init__.py` and raised nowhere. AD-14 carries
none of this. The same is true of FR-6's "Mode names round-trip... asserted mechanically against
the table rather than a hand-kept list" — AD-5 does not carry it. Both are exactly the
derive-don't-enumerate discipline AD-6 models so well; they should not be lost between the PRD
and the spine.

---

## 3. Could anything under Deferred let two units diverge? — **strong**

This is the dimension the spine handles best, and it is the one most drafts fail. Each deferral
names the seam that keeps the option open rather than simply postponing:

- *Incremental backup* — "Would change the archive format; **AD-6's version field is the seam**."
  Correct, and AD-6 makes the seam real by owning the format version in one `domain/` module.
- *Multisite* — "would change the Site Descriptor's **cardinality**." Correct, and AD-3 makes the
  descriptor a single frozen construction point, so the cardinality change has one site.
- *Concrete module tree below the layer directories* — "the code owns it. Only the layer
  boundaries are fixed (AD-1)." This is the correct seed/invariant call.
- *Whether `wpdatabase2` keeps a provisioning role at all* — this looks alarming (deferring a
  package boundary while units are being built) but is right at this altitude. AD-2 fixes the
  dependency direction, AD-3 fixes what crosses it, and AD-9 fixes how credentials are obtained;
  with those three in place, provisioning can move between packages without any unit having
  chosen incompatibly. Deferring it until "the three repos are releasable and the question can be
  answered without also fixing an outage" is good sequencing judgement.
- *Scheduling internals* — FR-18 is v1.1, and FR-28 was already extracted out of it by the PRD, so
  the deferral takes no safety guarantee with it.

**One flaw, and it is in the justification rather than the decision.** The Storage Target entry
reads:

> "**Storage Target addressing scheme** (URL grammar for S3/SFTP/rsync) — v1.1, and the port shape
> in AD-1 is enough to keep v1.0 from foreclosing it."

AD-1 says nothing about port shape. It says core and domain perform no I/O and reach effects
through Protocols; it does not define `ArchiveStore` or constrain its signature. The port *names*
appear only in the Structural Seed, which the Deferred list itself declares the code owns. So the
stated safety net does not exist — and see M2/M3 above, where the *unstated* parts of the
`ArchiveStore` contract (atomicity, streaming) are the parts that actually matter in v1.0. Fix
the justification by fixing the port contract, not by rewording the deferral.

**Also note what is absent: there is no "Open Questions" section.** Deferred answers "not now";
it does not answer "we do not know". Without a register of genuine unknowns, a reader cannot
distinguish a dimension that was considered and left open from one that was never raised — which
is exactly the ambiguity around FR-28, NFR-2, NFR-7 and the OS envelope below.

---

## 4. Is named technology verified-current rather than asserted? — **strong**

I checked every pinned version in the Stack table against the live index today, 2026-09-15:

| Claimed | Live today | |
|---|---|---|
| PyMySQL 1.2.0 | 1.2.0 (uploaded 2026-05-19) | ✓ — and ADR-0004's date matches to the day |
| structlog 26.1.0 | 26.1.0 | ✓ |
| cryptography 50.0.1 | 50.0.1 | ✓ |
| ruff 0.16.7 | 0.16.7 | ✓ |
| mypy 2.3.1 | 2.3.1 | ✓ |
| pytest 9.1.1 / pytest-cov 7.1.0 | 9.1.1 / 7.1.0 | ✓ |
| uv 0.12.15 | 0.12.15 | ✓ |
| boto3 1.43.95 | 1.43.95 | ✓ |
| WP-CLI 2.12.0 (external) | tag `v2.12.0`, published 2025-05-07 | ✓ — including the staleness |

Ten for ten, exact. This is verification, not assertion, and the ADRs carry the evidence in
checkable form rather than as a claim: ADR-0004 tabulates three drivers with version *and release
date* and rejects two on licence and wheel availability; ADR-0006 cites the `cryptography` docs
for why Fernet cannot stream; ADR-0009 cites devguide.python.org with specific EOL dates; ADR-0003
cites the MySQL 8.4 manual's own words on `MYSQL_PWD`. ADR-0005 does the hardest version of this
honestly — it *adopts a dependency whose staleness it flags*, states the 16-month gap, and pays
for it with a named exit plan ("the dependency is confined to one adapter behind one port... the
port is re-satisfied without touching `core/`"). That is the right shape for a GA-over-preview
rule under pressure.

### Two blemishes

**V1 (LOW) — the Stack table's header overstates its own coverage.** It says
"**Verified current 2026-09-15**" over a table one of whose rows says
"import-linter (AD-1 enforcement) | **current at adoption — verify before binding**". Either the
table is verified or it is not. import-linter is **2.15** today; the placeholder is unnecessary
and can be replaced with the pin now. This matters more than a typo would, because import-linter
is the enforcement mechanism for AD-1, the invariant the whole paradigm rests on — the one tool
whose currency is left unverified is the one that polices everything else.

**V2 (LOW) — `structlog` carries an AD but no ADR.** AD-10 makes specific API-level commitments
(`structlog.contextvars`, `merge_contextvars` **first** in the chain, `ProcessorFormatter` for
third-party records) that will not survive a library swap, and the memlog records no comparison
against stdlib `logging` + `contextvars`, `loguru`, or `structlog`'s own stdlib-integration path.
Every other named runtime dependency (PyMySQL, cryptography, boto3, WP-CLI, uv) got an ADR with
alternatives and a rejection reason. The asymmetry is visible.

---

## 5. Does it RATIFY the brownfield codebase? — **adequate**

I read the three packages and checked every defect claim the spine makes. **All of them are
literally true**, which is unusual and worth saying plainly:

| Spine claim | Source |
|---|---|
| "`--what-if` is an `if not self.__what_if:` repeated at **eight** effect sites" | exactly 8 occurrences across `wp_internal_backup.py` / `wp_internal_restore.py` |
| "`restore_mode` was dropped at two call sites and produced an unconditional `rmtree`" | `restore()` calls `self.__restore_files(archive_filename)` and `self.__restore_database()` — both without the mode; both default to `WpRestoreMode.ALLCLEAN`; `shutil.rmtree` follows |
| "`db_host`'s setter derives `_db_port` by splitting on `:` while `db_port` has its own independent setter" | `connection.py` — verbatim |
| "the internal backup/restore classes re-read `wp-config.php` instead of using the descriptor" | `WpInternalBackup.__init__` and `__restore_database` both construct a fresh `WpConfigFile`, then read `DB_HOST`/`DB_NAME`/`DB_USER` from it rather than from `WpSite` |
| "`DB_DUMP_ARCNAME` and `WP_DIR_ARCNAME` are duplicated literals in two modules" | verbatim, both files |
| "passes `-p<password>` in `argv` and logs the full argument vector at DEBUG" | `'-p' + self.__wp_config.get('DB_PASSWORD')`, then `self.__log.debug("CMD: %s", args)` |
| "the restore path logs `DB_PASSWORD` directly" (ADR-0003) | `__update_config`'s DEBUG line passes `wp_config.get('DB_PASSWORD')` |
| "`credentials.py` imports `Secret` at module scope and `secret.py` imports `boto3` at module scope" | `credentials.py:3`, `secret.py:7` — verbatim |
| "`.username` and `.password` are property getters that call `_resolve_secret()`" | verbatim, and `_resolve_secret` mutates `self._username`, `self._password`, `self._secret` |
| "the current fallback of reusing ordinary database credentials as admin credentials" | `self.admin_credentials = admin_credentials if admin_credentials is not None else credentials` |
| "`extractall` is called with rewritten member paths and no containment check" | `member.path = member.path[root_dir_len:]` then `stream.extractall(members=wp_members, ...)`, no `filter=` |
| "the temp path is hardcoded `/tmp` with the fixed filename `database.sql`, and the dump is left behind" | `__temp_path = "/tmp"`; `DB_DUMP_ARCNAME = 'database.sql'`; no cleanup anywhere |
| "`WpSite.from_wp_config` raises `wpdatabase2`'s `InvalidArgumentsError`" | verbatim |
| "the current README documents three flags that do not exist" | README shows `--admin-user`, `--new-site-host`, `--new-db-port`; the parser declares `--admin-username`, `--new-site-home-url`, and no port flag at all |
| "`>=1.0.0,<=2.0.0` in both repos... admits an unreviewed 2.0" (ADR-0002) | both `setup.py` files, verbatim |

The paradigm section also ratifies rather than replaces where it can, correctly identifying that
`wpconfigr` "already embodies the split (`WpConfigString` pure, `WpConfigFile` the I/O shell)" —
which is true: `WpConfigString` takes a `content` string and never touches the filesystem;
`WpConfigFile` does the `open()`/`read()`/`write()`.

### Findings

**R1 (HIGH) — AD-1's layer table forbids the arrangement the spine says it ratifies.**
The table reads:

> `| adapters/ | Real implementations: subprocess, filesystem, tar, storage, secrets | domain/, ports/ |`

`adapters/` may import `domain/` and `ports/` — **not `core/`**. But in the code being ratified:

```python
class WpConfigFile(WpConfigString):   # the I/O shell *subclasses* the pure core
```

The I/O shell does not merely import the pure core, it inherits from it, and `WpConfigFile.set()`
calls `super().set()` before writing. Under AD-1's table as written, an import-linter contract
would fail this on the first run — against the very package the Design Paradigm section holds up
as the precedent ("The paradigm ratifies that rather than replacing it").

There is a second half to this. `WpConfigString` fits neither layer the table defines: `domain/`
is "Value objects, Restore Mode, Backup Scope, archive-format constants, plan types" and `core/`
is "Plan construction, validation, decisions. Pure functions" that "return plan values." A pure
regex reader/writer for a PHP subset is neither. So AD-1 binds all three packages to a layer
table that has no home for the smallest of them.

This needs one of three fixes, all cheap now: (a) allow `adapters/ → core/` in the table, (b) put
pure non-plan logic like `WpConfigString` in `domain/` and widen that row's description, or (c)
scope AD-1's layer table to `wpbackup2` and `wpdatabase2` and state that `wpconfigr`'s existing
pure/shell split satisfies the intent at 343 lines. Left as is, the first contributor to run the
mandated contract gets a red build and will resolve the ambiguity by guessing — which is the
divergence the spine exists to prevent.

**R2 (LOW) — ADR-0007's context claim is false.** It states "There is **no CI** in any of the
three." Two of the three carry `.circleci/config.yml`: `py-wordpress-database` and `py-wpconfigr`.
They are dead (`circleci/python:3.7.1`, `python test.py`) and they do the exact thing ADR-0007
correctly warns against — `pip install -e .[dev]`, i.e. the working tree, which "would have passed
while `wpconfigr` was unresolvable." So the real evidence is *stronger* than the ADR's claim and
the ADR weakens itself by getting the fact wrong. More consequentially, ADR-0007's retirement list
— "Retire `setup.py`, `setup.cfg`, `build.sh`, `publish.sh` and `test.py`" — **omits
`.circleci/config.yml`**, leaving a second, stale CI definition alive alongside the new GitHub
Actions one. A stale green is the failure mode this whole project is recovering from.

**R3 (LOW) — AD-3's carve-out is worded in a way ADR-0010 contradicts.**
AD-3: "The single exception is the config *writer* (FR-11), **which writes and does not read for
its own use**." ADR-0010's mitigation requires precisely a read: "After writing, **re-read every
constant written** and assert the value round-trips." The intent is compatible (the writer does
not *source values* from the file) but the phrasing invites a builder to treat the required
read-back as a violation. Say "does not source values from the file"; the read-back is a
verification, not a source.

**R4 (LOW) — ADR-0004's "Departs from spec: n/a" is inaccurate.** PRD §13.2's Release A bullet
names the replacement specifically: "`mysql-connector` (2.2.9, last released 2019) replaced by
the maintained **`mysql-connector-python`**". ADR-0004 chooses PyMySQL and rejects
`mysql-connector-python` on licence friction. FR-26's wording ("...or by another actively
maintained driver") permits that, and the decision is well argued — but it *is* a departure from
a named Release A bullet and the header should record it rather than say `n/a`. The header field
exists for exactly this.

---

## 6. Does it cover the driving spec's capabilities? — **adequate**

All 29 FRs appear somewhere. FR-18 is the only one absent from the Capability map, and it is
correctly and explicitly Deferred ("FR-18 is v1.1 and may yet be cut to declarative config only"),
matching the PRD's own `[NOTE FOR PM]` hesitation. The map is otherwise dense and the FR→AD
attributions are mostly right.

The frontmatter, however, claims `binds: [FR-1..FR-29, **NFR-1..NFR-8**]`, and the NFR side does
not hold up:

| NFR | Bound by | |
|---|---|---|
| NFR-1 data integrity | AD-5, AD-13, Capability map | ✓ |
| NFR-2 artifact atomicity | **nothing** | ✗ (see M2) |
| NFR-3 secret hygiene | AD-7, AD-9 | ✓ |
| NFR-4 idempotence / per-Run temp | AD-12 | ✓ |
| NFR-5 untrusted archives | AD-11 | ✓ |
| NFR-6 observability | AD-10 | ✓ |
| NFR-7 performance & streaming | **nothing** | ✗ (see M3) |
| NFR-8 testability without live stack | AD-1, AD-9, Conventions | ✓ |

Two of eight NFRs are asserted as bound and are not. Per the same discipline AD-6 applies to
format versions: a blanket `binds:` range is a hand-kept claim about scope; either derive it or
narrow it to what the ADs actually carry.

### Other spec-coverage gaps

**S1 (MED) — MariaDB is nowhere in the spine, and the Stack silently excludes it.**
PRD §9 does not treat MariaDB as an aspiration; it makes it a *tested requirement from v1.0*:
"Parity between them is a **tested** claim, not a stated one: the integration suite runs against
both from v1.0... This roughly doubles integration runtime and is accepted deliberately — MariaDB
is the default engine across much of the self-hosted market this product targets." Q-3 confirms
it ("*Answered: a requirement*"). The spine mentions MariaDB zero times, and its Stack row reads:

> `| mysqldump / mysql (external) | client 8.0+ |`

MariaDB's clients version as 10.x/11.x, so "client 8.0+" as a preflight predicate excludes every
MariaDB installation. AD-13 requires preflight to report "presence and **version**" — against what
supported range, for which of two engines? Two units implementing `SqlClient` and the preflight
adapter will answer that differently. This is a real divergence point created by a spec
requirement the spine does not carry.

**S2 (MED) — two explicitly-mechanical FR consequences are not carried into any AD.**
Covered under E6 above: FR-23's reachable-raise-site assertion and FR-6's mode-name round-trip
"asserted mechanically against the table rather than a hand-kept list". Both are the PRD handing
the architecture a derive-don't-enumerate obligation; both are dropped.

**S3 (LOW) — FR-16's recorded default is not acknowledged.** The PRD records a default answer
for remote targets — "delegate to `rclone` rather than own three protocol integrations" — which
is a shape decision for the `ArchiveStore` port even though the capability is v1.1. The Deferred
entry defers the URL grammar without noting that the recorded default is *delegation*, which is
the thing that would most constrain the port. One clause.

**Where coverage is genuinely strong:** the safety cluster (FR-3, FR-6–FR-10, FR-19, NFR-1) is
the best-served part of the document, and the restore sequence diagram earns its place by showing
the forced ordering and the two abort-before-destruction gates. The supply-chain cluster
(FR-25–FR-27, Release A) is equally well served by AD-15 + ADR-0007 + ADR-0002.

---

## 7. Is EVERY dimension this altitude owns decided, deferred, or an open question? — **thin**

For a library-plus-CLI family, "deployment" largely *is* distribution, and that dimension is
covered unusually well: AD-15 fixes release ordering and the resolvability gate, ADR-0007 fixes
the toolchain and trusted publishing ("no long-lived token, no local `twine`, **no `sudo`**" —
directly answering `build.sh`'s `sudo python3 setup.py install`), ADR-0002 fixes the name and the
adoption, ADR-0009 fixes the runtime floor with a CI matrix. CI, the release gate, packaging, and
the supported-Python envelope are all decided.

Three sub-dimensions are **silent** — not deferred, not open, simply absent:

**O1 (MED) — the OS / platform envelope.** Nothing in the spine or the ADRs states which
operating systems are supported, yet the document commits to POSIX-only mechanisms in two ADs:

- AD-7: an option file "at mode **`0600`**";
- AD-12: a workspace via `tempfile.mkdtemp`, "**owner-only**".

ADR-0003 comes within one sentence of noticing — "on a filesystem without POSIX permissions the
guarantee weakens — detect and refuse rather than proceed silently" — and then no AD says whether
that detection is a supported path or an unsupported platform. Meanwhile ADR-0004 selects PyMySQL
partly *because* "a base install works **everywhere** with no build step", and the external tools
(`mysqldump`, `mysql`, `wp`) all exist on Windows. So the stack is chosen for portability and the
invariants assume POSIX. Two units — the credential-transport adapter and the workspace adapter —
will resolve that tension independently, and the CI OS matrix has no basis to be derived from.
This is the classic operational-envelope omission: a domain-focused draft that decides the
mechanism and never states the environment it runs in.

**O2 (MED) — the database-engine matrix.** See S1. MySQL vs MariaDB is an environment dimension
the PRD already decided and priced; the spine does not carry it, and AD-13's version predicate
and the Stack's "client 8.0+" are both wrong for half the target market.

**O3 (LOW-MED) — the integration environment.** Conventions says only "a small integration tier
is marked and separable". NFR-8 requires an *enumerated* integration list "itself asserted to be
complete, so a new consequence cannot quietly join it", and §11 makes the integration suite a
release gate. How that tier is provisioned (service containers, fixtures, engine versions) may be
below this altitude, but "which engine versions and which OSes the gate runs on" is not — it is
the same set AD-15's matrix and O1/O2 need, and it should be derived once.

**O4 (LOW) — no Open Questions register.** Deferred says "not in this release"; there is no place
that says "not known". For a spine that inherited a PRD with all eleven questions closed, an empty
Open Questions section would itself be a useful signal — and would have forced O1–O3 to the
surface rather than leaving them silent.

---

## Length, bloat, and seed-vs-invariant

### Is it too long?

**No.** 255 lines and ~20KB for fifteen invariants spanning three separately-released packages,
a rewrite, and a production outage is proportionate. The two diagrams both earn their place: the
dependency graph makes AD-2's direction and the optional/mandatory split visible at a glance, and
the restore sequence diagram carries information the prose does not — specifically the two
abort-before-destruction gates and the note "order is forced — WP-CLI has no credential flags and
bootstraps from the config we just wrote", which is a constraint, not a preference. Prose is
tight throughout; the **Prevents:** lines do real work by naming the concrete defect rather than
an abstraction.

If anything is to be cut, it should be duplicated relations (the Capability map's "Governed by"
column, M5) rather than content.

### Does any AD state what a competent builder would do anyway?

Mostly no — the Prevents lines are the test, and almost all of them cite a live defect. Three
places where trimming would help:

- **AD-12**, "The core never learns a filesystem path it did not receive." This is already
  entailed by AD-1 (core performs no I/O and receives plan values). Redundant sentence; AD-12's
  real content is the per-Run workspace, the `finally`, and the Safety Snapshot carve-out.
- **AD-14** is the weakest-earning AD. "each package defines its own exception hierarchy under a
  single base", "`raise ... from`", "Exceptions carry structured fields" — these are ordinary
  competent library practice. Its non-obvious half is real and specific to *this* system (three
  packages, so *whose* type crosses *which* boundary is a genuine cross-unit agreement, and the
  live code gets it wrong). Keep the boundary rule, trim the generic craft advice, and add the
  exit-code mapping from M4 — that would convert AD-14 from the weakest entry to a load-bearing one.
- **Consistency Conventions** rows for Typing (`mypy --strict`) and Tests (`pytest`) are what a
  competent builder does anyway. At *convention* altitude that is acceptable — the point is that
  three packages agree — so this is a note, not a finding.

Conversely, one entry that looks like bloat and is not: **AD-4**. It could be read as a corollary
of AD-1, but a builder can satisfy AD-1 fully (pure core, effects behind ports) and still write
`if dry_run: return` inside an adapter. AD-4 closes that, and it earns its place.

### Invariants hiding in the Stack / Structural Seed

The Stack is labelled "**Seed** — the code owns this once it exists." Two rows are not seed:

- **`Python (floor) | >=3.11`.** The code does not own this. It is a cross-package invariant: the
  same `requires-python` must appear in three `pyproject.toml` files, ADR-0009 decides it, AD-15's
  clean-environment gate runs "on every supported Python version", and AD-11's `filter='data'`
  rule is justified by which interpreter versions are in range. It belongs in an AD (or at minimum
  in AD-15's Rule) rather than under a heading that says the code may change it.
- **`boto3 (extra: `aws`)`.** The *name of the extra* is public surface. Users type
  `pip install wpdatabase2[aws]`, and AD-8's Rule requires the error to name "the extra to
  install" — an error message that must name a string that the seed table says the code owns.
  Invariant, not seed.

Going the other way, one AD names something that is seed: **AD-11**'s "one extraction function in
`adapters/`". The invariant is *exactly one extraction path, and it passes `filter='data'`
explicitly*; the directory is seed, and the Deferred list already says "Concrete module tree below
the layer directories — the code owns it." Minor, and the same pattern appears in AD-6 ("one
module in `domain/`"). Both are harmless as long as the layer, not the module, is the fixed part —
worth a word so it is not read as fixing a file.

---

## Findings, by severity

| ID | Severity | Finding |
|---|---|---|
| M1 | **HIGH** | FR-28's Site lock — lock identity, acquisition point, signal-time release, stale-reclaim rule — is fixed by no AD, and the Capability map files it under `cli/`, contradicting FR-28's requirement that the guarantee hold for library callers too. Two composition roots, one destructive tool, no mutual exclusion. |
| R1 | **HIGH** | AD-1's layer table forbids `adapters/ → core/`, but `WpConfigFile` **subclasses** `WpConfigString` in the very package the Design Paradigm says it ratifies; and neither `domain/` nor `core/` as described has a home for a pure config parser. The mandated import-linter contract fails on day one. |
| M2 | MED-HIGH | NFR-2 (an Archive is visible at a target only once complete) is bound by no AD. `ArchiveStore` atomicity is a port-contract decision two store adapters will answer incompatibly, and local storage ships in v1.0. |
| M3 | MED-HIGH | NFR-7's streaming/peak-memory guarantee is bound by no AD, though it dictates the `ArchiveStore` / crypto / tar port signatures. ADR-0006 makes the argument and the spine never lifts it into an invariant. |
| E1 | MED | AD-5's decisive clause — "no function that consumes a Restore Mode may declare a default for it" — names no enforcement, despite being AST-checkable, and it governs the document's most consequential defect. |
| E2 | MED | AD-4 downgrades itself: "a conditional in an adapter is a **review rejection**", when the rule as phrased is a one-line grep. |
| E3 | MED | AD-1's "Enforced by an import-linter contract in CI, not by review" overstates coverage: import-linter cannot see `open()` (a builtin), and catches clock/RNG only via a hand-enumerated forbidden list. |
| S1/O2 | MED | MariaDB appears nowhere, though PRD §9/Q-3 make parity a *tested* v1.0 requirement; the Stack's "mysqldump / mysql — client 8.0+" silently excludes every MariaDB client, and AD-13's version predicate has no defined range. |
| O1 | MED | No supported-OS/platform statement anywhere, while AD-7 (`0600`) and AD-12 (owner-only `mkdtemp`) are POSIX-only mechanisms and the stack is chosen for portability. ADR-0003 notices the tension and no AD resolves it. |
| M4 | MED | No rule joins AD-14's exception hierarchy to FR-21's exit codes, though exit-code meanings are a versioned public contract. |
| E4/E6 | LOW-MED | AD-9's "property getters perform no I/O" and AD-14's dropped FR-23 raise-site assertion are advice where a constraint or a check was available. FR-6's mode-name round-trip check is likewise dropped from AD-5. |
| M5 | LOW-MED | The Capability map's "Governed by" column is a hand-kept duplicate of the ADs' `Binds:` lines and has already drifted — FR-27 is attributed to AD-2/AD-15 when AD-13 governs it. |
| — | LOW-MED | The frontmatter asserts `binds: NFR-1..NFR-8`; NFR-2 and NFR-7 are bound by nothing. |
| — | LOW-MED | `Python floor >=3.11` and the `aws` extra name are cross-package invariants sitting under a table labelled "Seed — the code owns this once it exists." |
| R2 | LOW | ADR-0007's "There is no CI in any of the three" is false — two repos carry dead CircleCI configs that install the working tree, the exact blind spot the ADR names — and the retirement list omits `.circleci/config.yml`. |
| V1 | LOW | The Stack header says "Verified current 2026-09-15" over a row that says "verify before binding". import-linter is 2.15 today; pin it. |
| R3 | LOW | AD-3's "the config writer... writes and does not read for its own use" reads as forbidding ADR-0010's mandatory read-back verification. Reword to "does not source values from the file". |
| R4 | LOW | ADR-0004's "Departs from spec: n/a" is inaccurate: it departs from PRD §13.2's named `mysql-connector-python` bullet (permitted by FR-26's "or another actively maintained driver", but a departure). |
| V2 | LOW | `structlog` carries an AD with specific API commitments but no ADR, unlike every other named runtime dependency. |
| — | LOW | Deferred's Storage Target entry justifies itself with "the port shape in AD-1", but AD-1 defines no port shape; the port names live in the Structural Seed, which the same list says the code owns. |
| — | LOW | No Open Questions register, so a silent dimension is indistinguishable from a considered one. |

## Recommended disposition

Not a blocker on the spine's substance. Close **M1, R1, M2, M3** before handoff — each is one AD
or one clause, and each is a decision that gets expensive the moment two stories start building
against it. **E1 and E2** are a few lines of CI apiece and should land with the rules they
enforce. **O1 and S1/O2** need one paragraph together: state the supported OS set and the
supported engine set, and derive the CI matrix from that one statement rather than from three
places. Everything below that is copy-editing on an otherwise unusually well-evidenced document.
