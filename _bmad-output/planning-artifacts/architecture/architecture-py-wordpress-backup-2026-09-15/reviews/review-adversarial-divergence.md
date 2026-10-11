---
lens: adversarial-divergence
target: ARCHITECTURE-SPINE.md (wpbackup2 family, 2026-09-15)
supporting: docs/adr/0001..0010
date: 2026-09-15
verdict: 'SPINE INCOMPLETE — 14 construct-two-compliant-units divergence pairs found; 5 are release-blocking'
---

# Adversarial Divergence Review — wpbackup2 family spine

**Method.** For each pair of plausible implementation units one level below the spine
(epic teams, adapter authors, package teams), construct a concrete scenario where both
units obey every AD-1..AD-15 *literally* and still emit code that does not compose.
Only divergence pairs are reported. Style, prose and general architecture opinions are
out of scope by instruction.

**Result.** 14 pairs. Ranked by (likelihood the divergence actually happens) ×
(cost of discovering it late). D-1 through D-5 are release-blocking: each produces a
defect whose first observation is in production, on the restore path, against an
operator's only copy of their data.

**Summary table**

| # | Divergence | Units | Rank | Closing AD |
|---|---|---|---|---|
| D-1 | Manifest inside or outside the encryption envelope | encryption adapter / verification | 1 | AD-6 tighten |
| D-2 | Safety Snapshot re-enters a composition root | restore epic / backup epic | 2 | new AD-16 |
| D-3 | Restore step order lives only in a diagram | restore epic / relocation epic | 3 | new AD-17 |
| D-4 | Dry-run no-op adapters: reads vs writes | S3 store / local store | 4 | AD-4 tighten |
| D-5 | FR-29 out-of-root `wp-config.php` vs AD-11 containment | backup epic / restore epic | 5 | AD-6 tighten |
| D-6 | Site Descriptor field set, nullability, and source | wpdatabase2 / wpbackup2 | 6 | AD-3 tighten |
| D-7 | Exit-code table has no owner and no derived scope | CLI epic / credentials epic | 7 | new AD-18 |
| D-8 | Optional-dependency absence: AD-8 vs AD-13 scope | S3 adapter / AWS provider | 8 | AD-13 tighten |
| D-9 | Safety Snapshot destination | restore epic / storage epic | 9 | AD-12 tighten |
| D-10 | Site Lock location and Site Identity key | CLI epic / API epic | 10 | new AD-19 |
| D-11 | `wpconfigr` zero-deps vs one-logger | wpconfigr / wpbackup2 | 11 | AD-10 tighten |
| D-12 | Two owners of database provisioning, two credential transports | wpdatabase2 / wpbackup2 | 12 | new AD-20 |
| D-13 | Storage Target addressing and Archive naming | backup epic / prune epic | 13 | new AD-21 |
| D-14 | Clock port under Dry Run vs structlog timestamps | backup epic / logging epic | 14 | AD-4 tighten |

---

## D-1 — The Manifest is both inside the encryption envelope and required to decrypt it

**Rank 1.** Likelihood: certain, because both readings are written down. Cost: the
Archive is the third contract (PRD §8), held by operators for months; a layering
mistake here is not fixable after the first archive ships.

### The two units

- **Unit A — the encryption adapter** (`adapters/crypto`, FR-4, ADR-0006).
- **Unit B — the archive/verification adapter** (`adapters/tar`, `domain/archive`, FR-3, FR-10).

### How both comply

AD-6: *"one module in `domain/` owns member names, the Manifest schema, the format
version **and the encryption envelope**."* Both import that module. Neither defines a
member name. Both write a Manifest on every Archive and read it before every restore.

ADR-0006 gives each unit a different, equally literal instruction:

- *"Salt, KDF parameters and algorithm identifiers live in the Manifest."*
- *"the Manifest is a JSON member inside the archive, not a sidecar — an operator moving
  one file must not be able to separate an Archive from its integrity data."*

### The incompatibility, concretely

**Unit A** reads the first sentence as binding and produces:

```
archive.wpb2
  └─ AESGCM_envelope(key = Argon2id(passphrase, salt))
       └─ tar
            ├─ manifest.json      {format_version, salt, kdf_params, members[...]}
            ├─ dump.sql
            └─ site-root/...
```

`salt` is inside the thing the salt is needed to open. Unit A has to solve this, so it
emits an unencrypted 64-byte header prefix carrying `salt` + `kdf_params` + a magic —
a field that exists in **no** schema, because AD-6 says `domain/` owns the schema and
the schema is the Manifest.

**Unit B** reads the second sentence as binding and produces:

```
archive.wpb2 (tar)
  ├─ manifest.json                {format_version, salt, kdf_params, members[...]}
  ├─ dump.sql.enc                 AESGCM chunks
  └─ site-root/... .enc           AESGCM chunks
```

Both satisfy AD-6 word for word. They are not the same file format, and neither can read
the other. Worse, three PRD consequences decide *against* Unit A and the spine never says so:

- FR-10: *"An Archive with a newer major format version is refused with a message naming
  the version and the supported range."* Under Unit A the format version is inside the
  envelope — you cannot name the version of an archive you cannot decrypt.
- FR-4: *"Restoring an encrypted Archive without a key fails with a distinct, named
  error, not a generic corruption error."* Under Unit A, no key means an AEAD tag
  mismatch on byte zero — indistinguishable from corruption. This consequence is
  *unimplementable* under Unit A's layout.
- FR-3: *"A Verification command reports pass or fail and makes no filesystem or database
  write outside its own temporary working area."* Under Unit A, Verification of an
  encrypted Archive without the passphrase is impossible; under Unit B it can at least
  verify structure, format version and Manifest integrity.

There is a further unowned question neither unit can answer from the spine: **what are
the per-member checksums taken over?** AD-6 owns the *schema* (field names, types); the
*computation* is a streaming hash and therefore lives in an adapter under AD-1. Unit A
hashes plaintext member bytes before encryption; Unit B hashes the ciphertext as stored.
Both are "per-member checksums". A backup written by one and verified by the other fails
100% of the time — and the failure mode is a **Verification failure on a good archive**,
which under FR-3 aborts the restore. The safety machinery refuses valid backups.

### Closing AD

> **Tighten AD-6.** The Archive is a fixed three-layer stack, normative and versioned:
> (1) an **unencrypted outer container** (tar) whose **first member is `manifest.json`**;
> (2) `manifest.json` carries `format_version`, `created_at`, `encryption` (algorithm,
> KDF id, KDF parameters, salt, chunk size — never the key), per-member role, and
> per-member checksum; (3) **member payloads** are individually encrypted when encryption
> is requested. The Manifest is never encrypted. Per-member checksums are taken over
> **the bytes as stored in the container** (post-encryption, post-compression), so
> Verification is possible without a key; a second `plaintext_sha256` field, present only
> for unencrypted archives, covers the decrypted form. One function in `adapters/`
> computes a member checksum, and backup, verification and restore all call it — asserted
> by an import-linter contract that no other module calls a hashing primitive.
> A committed fixture Archive per format version, encrypted and unencrypted, is the
> source of truth for the supported range (AD-6 already requires this; extend it to
> require one fixture of each encryption state).

---

## D-2 — The Safety Snapshot re-enters a composition root and forks the Run

**Rank 2.** Likelihood: very high — it is the obvious implementation, and FR-22 actively
pushes toward it. Cost: self-deadlock in an unattended 03:00 restore, plus a Run ID that
changes halfway through the highest-risk operation.

### The two units

- **Unit A — the restore epic** (`core/restore`, FR-6..FR-9).
- **Unit B — the backup epic** (`core/backup`, `api/`, FR-1, FR-2, FR-5).

### How both comply

- AD-10: *"the Run ID is bound with `structlog.contextvars`"*, `structlog` *"configured
  once at the composition root and never in a library module."*
- AD-12: *"**the shell creates one workspace per Run** via `tempfile.mkdtemp` ... and
  removes it in a `finally` on both success and failure."*
- FR-8: *"Before any destructive restore step, wpbackup2 captures a Safety Snapshot."*
  A Safety Snapshot is, per the Glossary, *"an Archive of the target Site"* — i.e. a backup.
- FR-22: *"Every operation available on the CLI is available through the API."*

Unit A therefore implements the Safety Snapshot by calling `wpbackup2.api.backup(...)`.
That is the correct, DRY, AD-6-respecting choice: it guarantees the snapshot is a real
Archive with a real Manifest rather than a second, drifting archive writer.

Unit B implements `api.backup()` as a composition root per the layer table
(`cli/`, `api/` — *"Composition roots — bind adapters, bind the Run ID, translate errors"*).

Both units are literally correct. The spine explicitly names `api/` a composition root
and never says a composition root may not be entered from inside a Run.

### The incompatibility, concretely

At the moment Unit A calls `api.backup()` for the snapshot:

1. **Run ID forks.** Unit B binds a *new* UUIDv4 via `structlog.contextvars` (conventions:
   *"Run ID is a UUIDv4 string, generated at the composition root"*). Every record emitted
   during the snapshot carries `run_id=<B>`, not `<A>`. FR-20's first consequence —
   *"Every record emitted by a Run carries the same Run ID"* — fails precisely during the
   one step an operator will want to trace after a bad restore. `contextvars` binding is
   also not automatically unbound on return, so unless Unit B uses
   `bound_contextvars` as a context manager (nothing requires it), records emitted
   **after** the snapshot — the extraction, the config rewrite, the dump load — carry
   the snapshot's Run ID too. The restore's own Run ID disappears from its own log.
2. **`structlog` is reconfigured mid-Run.** AD-10 says *"configured once at the
   composition root"*. Unit B's root calls `structlog.configure(...)` again. Processor
   chain, renderer (JSON vs human — the conventions make this TTY-dependent) and the
   `ProcessorFormatter` bridge are all replaced. If the outer caller is a library user who
   bound their own correlation ID (FR-20: *"A library caller can bind their own
   correlation ID and see it on wpbackup2's records"*), that binding is silently discarded.
3. **The workspace is destroyed under the outer Run.** Unit B creates its own
   `mkdtemp` workspace and removes it in a `finally`. If either unit's workspace root is
   derived from a caller-supplied temp location (AD-12 permits an override of *where*),
   and either implements cleanup as "remove the workspace directory tree" rather than
   "remove exactly the directory I created", the inner `finally` can take the outer
   Run's staging area with it — while the credential option file (AD-7) is still open in
   it, which is the one file AD-7 guarantees is deleted in a `finally`. Two `finally`
   blocks, one directory, no stated ownership.
4. **FR-28 self-deadlock.** *"A Run acquires a lock identified by the Site before its first
   read of Site state"* and *"A second Run against a locked Site exits non-zero without
   touching the Site, and names the holding Run's ID."* The restore holds the lock. The
   snapshot is a second Run against the same Site. It exits non-zero, naming the restore's
   own Run ID as the holder. Under FR-8 — *"If the Safety Snapshot cannot be taken, the
   destructive restore does not proceed"* — **every destructive restore refuses, always.**
   This is not a subtle bug; it is a product that cannot restore. But it only appears once
   both FR-8 and FR-28 are wired, which will be two different stories in two different
   sprints.

The same fork occurs on the CLI→API path: the layer table makes `cli/` and `api/` both
composition roots, and the natural implementation of `cli/restore` is to parse args then
call `api.restore()`. Two roots, two Run IDs, two workspaces, two `structlog.configure`
calls, on *every* invocation.

### Closing AD

> **New AD-16 — One Run, one Run Context, created by the outermost root.**
> A **Run Context** is a frozen value created exactly once per Run, carrying: the Run ID,
> the workspace path, the bound logger, the acquired Site Lock, the Clock, and the
> selected adapter set. A composition root creates a Run Context **only if one is not
> already active** (detected via a `contextvars` sentinel); otherwise it joins the active
> one and creates nothing — no Run ID, no workspace, no `structlog.configure`, no lock
> acquisition. Every public operation entry point accepts an optional Run Context; every
> internal operation requires one. `structlog.configure` is called from exactly one
> function in the codebase, guarded by an idempotence check, asserted by a grep-style CI
> contract. Workspace cleanup removes **only the directory the calling root created**,
> recorded in the Run Context. The Safety Snapshot is an *internal backup operation*
> invoked with the restore's Run Context, never through the public `api.backup()` root,
> and the Site Lock is **re-entrant for the Run that holds it**.
> Enforced by a test that performs a destructive restore against recording adapters and
> asserts: exactly one distinct `run_id` across all records, exactly one `mkdtemp` call,
> exactly one lock acquisition, and exactly one `structlog.configure`.

---

## D-3 — The binding restore order exists only in a mermaid diagram, and the one ADR that cites it cites it wrong

**Rank 3.** Likelihood: high — `core/` is where plans are built and both orders are
expressible in pure code. Cost: silent wrong-database restores and no-op relocations.

### The two units

- **Unit A — the restore epic** builds `RestorePlan` in `core/restore`.
- **Unit B — the relocation epic** builds `RelocatePlan` in `core/restore` (capability map
  puts relocation in `adapters/wpcli` but the *plan* must be pure, per AD-1).

### How both comply

Read AD-1 through AD-15 and extract every ordering constraint that is actually stated
as a rule:

| Stated in an AD | Constraint |
|---|---|
| AD-13 | preflight for every tool the plan requires, before executing **any** step |
| AD-11 | Verification completes before the **first destructive step** |
| AD-6 | a Manifest is read **before every restore** |
| AD-12 | Safety Snapshots outlive the Run (a *lifetime* rule, not an order rule) |
| FR-8 | Safety Snapshot before the **first destructive** operation |
| FR-9 | target database and user exist **before loading the Dump** |

That is the complete set. **Nothing states the relative order of: extract → rewrite
config → load dump → search-replace.** That order appears in exactly one place — an
unnumbered mermaid `sequenceDiagram` in the *Structural Seed* section. A diagram is not
an AD, it binds nothing, and the Deferred list explicitly says *"Concrete module tree
below the layer directories — the code owns it."*

The evidence that this gap is already live: **ADR-0005 cites the diagram as
"AD-13's sequence diagram"**. AD-13 contains no diagram. A load-bearing ordering
constraint is cited by number to an AD that does not contain it — which is exactly the
failure mode of a rule that lives only in prose.

### The incompatibility, concretely

**Unit A** emits: `preflight → verify → snapshot → extract → rewrite-config → load-dump → search-replace`.

**Unit B** emits: `preflight → verify → snapshot → extract → load-dump → rewrite-config → search-replace`.

Unit B's reasoning is sound on its face: `wp search-replace` needs both the config and a
populated database, and loading the dump earlier parallelizes with nothing else. B breaks
two things, neither of which any AD forbids:

1. **The dump is loaded into the wrong database.** In a Relocation, `--new-db-name` is a
   relocation value (FR-11). Under B the dump is loaded before `DB_NAME` is rewritten, so
   it lands in the *source* archive's database name. The site then boots against the
   *new* name — empty. The restore reports success (FR-9's checks all pass: the load
   completed, rows were inserted) and the operator sees a fresh-install WordPress.
2. **FR-9's provisioning precondition moves.** *"The restore ensures the target database
   and user exist before loading the Dump."* Under A the target is known from the
   rewritten config; under B it is known from the plan. Two different notions of "target",
   and a third unit (D-12) may create it with a different collation.

A third unit could equally emit `rewrite-config → extract`, on the reasoning that the
config is not part of the Site Root tree in the FR-29 layout (see D-5). Under `all-clean`,
extraction then clears the Site Root that the rewritten config lives in.

All three plans are pure, all three pass AD-1's import-linter contract, and nothing in CI
distinguishes them.

### Closing AD

> **New AD-17 — The restore phase order is a domain value and is normative.**
> `domain/` defines `RestorePhase` as an ordered enumeration:
> `PREFLIGHT → VERIFY → ACQUIRE_LOCK → SNAPSHOT → PROVISION_DB → CLEAR_SITE_ROOT →
> EXTRACT → REWRITE_CONFIG → VERIFY_CONFIG_READBACK → LOAD_DUMP → SEARCH_REPLACE →
> REPORT`. A plan is a **subsequence** of this enumeration — plan construction may omit a
> phase (a non-relocating restore omits `SEARCH_REPLACE`; `files` mode omits
> `PROVISION_DB` and `LOAD_DUMP`) but may **never reorder**. The plan type in `domain/`
> enforces this structurally: the constructor takes a set of phases and emits them in
> enumeration order, so an out-of-order plan is unrepresentable rather than merely
> forbidden. The sequence diagram in the spine is regenerated from the enumeration, not
> hand-drawn. **Enforcement:** a test executes every Restore Mode × relocation
> combination against recording adapters and asserts the recorded call order is a
> subsequence of `RestorePhase`; the *set* of combinations tested is derived from the
> `RestoreMode` enum and the FR-6 table, never hand-listed.
> **Also:** correct ADR-0005's citation from "AD-13's sequence diagram" to "AD-17".

---

## D-4 — "Return plausible results" lets two no-op adapters describe two different worlds

**Rank 4.** Likelihood: high — every adapter author faces this independently, and AD-4
gives them no rule. Cost: Dry Run is the product's principal safety affordance (FR-19,
UJ-1); a Dry Run that reports a plan the real run will not execute is worse than no Dry Run.

### The two units

- **Unit A — the local storage adapter** (`LocalArchiveStore` / `NoopLocalArchiveStore`).
- **Unit B — the S3 storage adapter** (`S3ArchiveStore` / `NoopS3ArchiveStore`), or
  equivalently the filesystem adapter vs the SQL adapter.

### How both comply

AD-4: *"no `if dry_run:` anywhere in `core/` or `adapters/`. A Dry Run binds recording
no-op adapters that log the intended effect and **return plausible results**. The core is
byte-identical between a real run and a Dry Run."*

Both units write a no-op class per the naming convention (`Noop`-prefixed). Neither
contains a conditional. Both return plausible values. Both pass review.

### The incompatibility, concretely

The ports are not split into queries and commands, so a "no-op adapter" has to decide
what to do about the **read** methods, and AD-4 does not say.

**Unit A** reads AD-4 as *the adapter is a no-op* and implements every method:

```python
class NoopLocalArchiveStore:
    def exists(self, key: str) -> bool:        return False   # plausible
    def is_empty(self, path: Path) -> bool:    return True    # plausible
    def put(self, key, stream) -> StoreResult: return StoreResult(key=key, bytes=0)
```

**Unit B** reads AD-4 as *a Dry Run makes no change* and implements read-through:

```python
class NoopS3ArchiveStore:
    def __init__(self, real: S3ArchiveStore): self._real = real
    def exists(self, key): return self._real.exists(key)      # real read
    def put(self, key, stream): self._record(key); return StoreResult(key=key, bytes=0)
```

Now run `wpbackup2 restore --dry-run --mode all-clean` against a **non-empty** Site Root:

- Under Unit A's filesystem no-op, `is_empty()` returns `True`. `core/` — byte-identical
  between real and dry, per AD-4 — builds a plan with no FR-7 refusal. The Dry Run reports
  *"would restore files, would drop database, would load dump"* and exits 0.
- The real run calls the real adapter, `is_empty()` returns `False`, and FR-7 fires:
  *"Restoring into a non-empty Site Root without explicit authorization exits non-zero,
  changes nothing, and names the flag."*

The Dry Run said it would work. The real run refuses. FR-19's *"A Dry Run reports the
actions it would take, in order"* is violated, and the operator's mental model — the one
UJ-1 and UJ-3 are built on — is wrong in the direction that matters.

The reverse is equally reachable: a `NoopSqlClient.database_exists()` returning `True`
makes the Dry Run report *"would drop database"* where the real run would report
*"would create database"* (FR-9: *"reports which of those it created"*).

FR-19 in fact already decides this — *"A Dry Run performs Verification, credential
resolution, WP-CLI availability checks and relocation planning — **the checks, not just
the writes, are exercised**"* — but AD-4 does not carry that sentence, and an adapter
author reads AD-4, not FR-19. A rule in the PRD that is absent from the spine is a rule
that will be violated by a compliant implementation.

### Closing AD

> **Tighten AD-4.** Every port is split into **queries** (no observable effect) and
> **commands** (observable effect), declared as two Protocols. A Dry Run binds the
> **real** query implementation and a **recording no-op** command implementation. A no-op
> command's return value is **derived from the real pre-state read through the query
> port** — never a fabricated constant; where no such derivation exists, the command
> returns a `NotPerformed` sentinel that the core is required to handle.
> **Enforcement:** an import-linter/AST contract asserting no `Noop*` class implements a
> query Protocol, plus a **plan-equality test** — for each fixture site, build the plan
> under the dry-run adapter set and under the real adapter set (without executing) and
> assert the two plan values are equal. The set of fixtures is derived from the Restore
> Mode enum crossed with {empty site root, non-empty site root, absent database,
> present database}, not hand-listed.

---

## D-5 — FR-29's out-of-root `wp-config.php` collides with AD-11's containment check, and AD-6 has no slot for it

**Rank 5.** Likelihood: high, and it only bites on the *documented WordPress convention*
layout — i.e. on real sites, not on fixtures. Cost: either a refused restore or a
config written outside the destination by an archive that declares it.

### The two units

- **Unit A — the backup epic** decides how `wp-config.php` is placed in the Archive.
- **Unit B — the restore/extraction epic** owns *"one extraction function in `adapters/`,
  used by every restore path"* (AD-11).

### How both comply

- FR-29: *"A Site whose `wp-config.php` sits one level above the Site Root — WordPress's
  own documented convention — is backed up, restored and relocated correctly."*
- FR-5: *"Exclusions never apply to `wp-config.php`."* So it is always in the Archive.
- AD-6: *"one module in `domain/` owns member names ... neither defines a member name."*
  AD-6 names `DB_DUMP_ARCNAME` and `WP_DIR_ARCNAME` as the duplication it exists to kill —
  **it names two roles. There is no third role for the config.**
- AD-11: *"re-checks containment after member-path rewriting."*

### The incompatibility, concretely

**Unit A** has a Site Root at `/srv/site/public/` and a config at `/srv/site/wp-config.php`.
Two AD-compliant placements:

- **A1 — preserve the relative location.** Member path `../wp-config.php` under
  `WP_DIR_ARCNAME`. The Archive faithfully records the layout. It imports the member-name
  module; it defines no new name. Compliant.
- **A2 — flatten it in.** Member path `wp-config.php` at the Site Root level, with the
  original location recorded nowhere, because the Manifest schema has no field for it.
  Compliant.

**Unit B** implements AD-11 exactly: `filter='data'`, then re-check containment after
rewriting. `tarfile`'s `data` filter **already rejects** absolute paths and `..`
components — so A1's `../wp-config.php` is rejected by the filter, and again by B's
containment re-check.

Result under A1: **every restore of a site using WordPress's own documented layout fails
extraction**, and the failure looks like a malicious-archive rejection (CVE-2007-4559
class), so the natural fix a developer reaches for is *loosen the containment check* —
turning a security invariant into a special case, on the restore path, under time pressure.

Result under A2: the restore silently relocates the config into the Site Root. The site
now has `wp-config.php` in a web-served directory when the operator had deliberately put
it above one — a security regression, delivered by the backup tool, invisible until
someone fetches `/wp-config.php.bak`. And FR-29's *"The configuration path can be stated
explicitly by the operator, and the stated path is used rather than being re-derived"*
has nowhere to be recorded: the Manifest's *"source Site Descriptor"* per the Glossary
carries *"Site Root, site URL, site home URL, database host, database name, and a
Credential Provider"* — **no config path**.

There is a knock-on for the `files-clean` and `all-clean` modes: *"Clears Site Root
first"*. Under A1/A2 the config is inside the Site Root after restore, so clearing then
extracting is consistent. Under a faithful out-of-root restore the config is *outside* the
cleared area — so `files-clean` leaves the **old** `wp-config.php` in place and the
restore proceeds against the previous site's database credentials. NFR-1 violated:
the Site is left in a state worse than not having run.

### Closing AD

> **Tighten AD-6.** The Manifest declares a fixed, enumerated set of **member roles** —
> `dump`, `site-root`, `config` — and **every member is stored under a role-prefixed,
> normalized, relative path** inside the container (`site-root/...`, `dump.sql`,
> `config/wp-config.php`). **No member path may contain `..` or be absolute**, so AD-11's
> containment check never requires an exception and the `data` filter never rejects a
> well-formed Archive.
> The config's *original* location is **Manifest metadata** — a `config_path` field on the
> Site Descriptor record, stored as a path relative to the Site Root (which may begin
> `..`) — never an archive path. Restore writes the config to the operator-supplied path
> if given, else to the Manifest-recorded relative location, else to the Site Root; the
> resolved destination is reported.
> **Extend AD-3** so the Site Descriptor carries `config_path` as a required field.
> **Extend AD-5** so a `*-clean` mode's destruction scope is defined as *the Site Root
> tree only*, and an out-of-root config is **replaced, never cleared** — stated as an
> explicit exception rather than left to inference.
> **Enforcement:** a fixture Site in the out-of-root layout is part of the committed
> fixture set exercised by the round-trip test; a test asserts no member path emitted by
> the backup writer contains `..` or a leading `/`, with the member set derived from a
> real archive rather than a list.

---

## D-6 — The Site Descriptor is two named types with two field sets, and two of its Glossary fields have no source

**Rank 6.** Likelihood: high — AD-3 names two existing types and never says they are one.
Cost: relocation that silently does nothing.

### The two units

- **Unit A — the `wpdatabase2` team**, owning `WpConnection`.
- **Unit B — the `wpbackup2` team**, owning `WpSite`.

### How both comply

AD-3 *"Binds: `wpdatabase2.WpConnection`, `wpbackup2.WpSite`, every consumer of connection
details"* — it binds **two types by name** and never says whether they are the same type,
whether one contains the other, or which package owns the Site Descriptor. AD-2 permits
`wpbackup2` to contain a `wpdatabase2` type but not the reverse, and permits a shared
capability to move down to `wpconfigr` *"only if it can arrive dependency-free"* — a frozen
dataclass qualifies, but nothing decides it. The Deferred list defers the *module tree*,
which a reader can easily read as deferring this too.

Both units build a frozen value object, constructed once at the boundary, splitting
`host:port` at construction, with no setters. Both comply.

### The incompatibility, concretely

**Field-set divergence.** Unit A: `WpConnection(host, port, database, credentials)`.
Unit B: `WpSite(site_root, config_path, site_url, home_url, db_host, db_port, db_name,
credential_provider)` — flat, because AD-3 says the descriptor is constructed once from
one source and no module below the root may re-open `wp-config.php`. Now the Manifest
records *"source Site Descriptor (credentials excluded)"* (Glossary) — **which shape?**
Backup (Unit B) writes the flat shape. A relocating restore must hand `wpdatabase2` a
`WpConnection`. The adapter between them is unowned, and its defaulting rules are unstated:

**Port nullability.** `wp-config.php` says `define('DB_HOST', 'db')` — no port. AD-3 says
*"`host:port` is split during construction and never afterwards"* and says nothing about
absence. Unit A materializes `port=3306` (MySQL's default; plausible). Unit B stores
`db_port: int | None = None` (faithful; the operator did not say). The Manifest of the
same site therefore reads `"db_port": 3306` or `"db_port": null` depending on which unit
wrote it. On restore into a site whose config says `DB_HOST=db:3307`, FR-11 makes port a
relocation value — so does the Manifest's `3306` override the target's `3307`, or is
`null` "leave unchanged"? Two units, two answers, and the wrong one connects the restored
site to the wrong MySQL instance.

**site_url and home_url have no source.** The Glossary puts *site URL* and *site home URL*
in the Site Descriptor. WordPress stores these in **`wp_options.siteurl` and
`wp_options.home`** — in the *database* — unless `WP_SITEURL`/`WP_HOME` constants are
defined, which most sites do not define. AD-3 requires the descriptor be built *"from
exactly one source"* and forbids any module below the root from re-reading the config.
So:

- Unit B (backup) builds the descriptor from `wp-config.php` alone; `site_url` and
  `home_url` are `None` for a typical site. The Manifest records `null`.
- Unit A (relocation) needs the **old** URL to run `wp search-replace <old> <new>`.
  It reads `null`.

Result: `wp search-replace None https://staging.example.com` — either a crash, or a
search-replace that matches nothing and reports `0 replacements`. FR-12's consequence
*"After a relocation to a new URL, no row in `wp_options` or postmeta contains the old
site URL"* fails, and UJ-3's entire climax — widgets and menus intact — is a no-op.
Nobody notices, because a relocation that changes nothing produces no error.

The alternative — query `wp_options` for the old URL — requires a **second source**, an
*effect* at descriptor-construction time, and a live database connection before preflight.
AD-3 forbids all three as written.

### Closing AD

> **Tighten AD-3.** There is **one** Site Descriptor type, defined in the lowest package
> that can define it dependency-free, re-exported by the other two; `WpConnection` becomes
> a projection of it, not a peer. Its field list is **enumerated in the AD** with types,
> nullability and defaulting rules, including `config_path` (D-5). Fields are partitioned
> into two declared groups:
> - **config-sourced** (`site_root`, `config_path`, `db_host`, `db_port`, `db_name`,
>   `table_prefix`) — sourced from `wp-config.php` or explicit override, exactly once;
>   `db_port` is `int | None` and `None` means *"the client's default"*, never materialized
>   to `3306` by any producer.
> - **runtime-resolved** (`site_url`, `home_url`) — sourced from `WP_SITEURL`/`WP_HOME`
>   when the constants exist, otherwise from a **single** `wp_options` read performed at
>   the composition root through the `SqlClient` query port, before plan construction.
>   This is the one sanctioned second source, and the Manifest records **which source each
>   field came from** in a `field_sources` map.
>
> A relocation plan whose `site_url` is unresolved is a **construction-time error**, not a
> zero-replacement search-replace. **Enforcement:** the Manifest schema test enumerates the
> Site Descriptor's fields by reflection and asserts each appears in the Manifest record —
> scope derived from the dataclass, not hand-listed.

---

## D-7 — The exit-code table has no owner, no source of truth, and three CLIs

**Rank 7.** Likelihood: certain — the second exception type added after the table is
written will not be in it. Cost: silent misclassification in automation; exit-code
meanings are a §10 *breaking-change* surface.

### The two units

- **Unit A — the CLI epic**, which per the capability map owns FR-21 in `cli/`.
- **Unit B — the credentials epic** (or any epic that introduces a new exception type).

### How both comply

Capability map: *"FR-21 exit codes, FR-28 concurrency | `cli/` | AD-12, AD-14"*.
AD-14: *"each package defines its own exception hierarchy under a single base."*
FR-21: *"Documented, distinct exit codes separate at minimum: usage error, Verification
failure, missing external dependency, credential failure, and operation failure."*

Unit A writes `cli/exit_codes.py` with a dict keyed by exception class and a default of
`EXIT_OPERATION_FAILURE`. Compliant, documented, tested against the five named categories.

Unit B implements AD-9's requirement — *"absent admin credentials is an error naming what
is missing"* — and adds `AdminCredentialsMissingError(WpBackupError)`. It carries
structured fields per AD-14. It is exported and has a reachable raise site per FR-23.
Compliant.

### The incompatibility, concretely

`AdminCredentialsMissingError` is not in Unit A's dict. It falls to the default and exits
with the **operation failure** code. FR-21 requires **credential failure** to be distinct.
The failure is invisible: the exception type is right, the message is right, the
structured fields are right, and only the integer is wrong — and no test catches it,
because Unit A's tests enumerate the five *categories* it wrote, not the exception
hierarchy as it exists.

This is the exact anti-pattern the project's own engineering rules name: **a hand-kept
list of types that drifts from the thing it is supposed to cover, with the check reporting
success over a set that no longer contains what matters.**

Compounding it: **there are three CLIs.** FR-20 requires verbosity to be *"consistent
across `wpbackup2`, `wpconfigr` and `wpdatabase2`"*, which presumes all three have a CLI.
The spine's capability map assigns exit codes to `cli/` — singular, and in the
`wpbackup2` structural seed. Nothing gives `wpdatabase2` or `wpconfigr` the same table.
Unit A's `wpbackup2` exits `4` for a missing external tool; a `wpdatabase2` CLI written by
another unit exits `2`. An operator's `systemd` `OnFailure=` matching on exit code behaves
differently depending on which package's entry point the automation called — and per §10
*"Exit-code meanings are part of the CLI contract; reassigning one is a breaking change"*,
fixing it later is a major version across three packages.

### Closing AD

> **New AD-18 — One exit-code table, derived from the exception hierarchy.**
> `ExitCode` is an `IntEnum` defined once, in the lowest package that can hold it
> dependency-free (`wpconfigr`), carrying the FR-21 categories plus `SUCCESS`, and
> re-exported by all three packages. **Every package-owned exception base declares its
> exit code as a class attribute**; a subclass inherits its parent's unless it overrides.
> The CLI maps an exception to a code by **walking the MRO**, never by a lookup table, so
> a new exception type is classified by construction. All three CLIs import the same
> table. **Enforcement:** a CI test that discovers every concrete subclass of each
> package's exception base by reflection and asserts each resolves to a non-default code —
> the set derived from the hierarchy, not enumerated; and a planted-violation test that
> adds an exception subclass with no code and asserts the guard fails.

---

## D-8 — AD-13's preflight covers binaries; AD-8's optional dependency is not a binary

**Rank 8.** Likelihood: high — ADR-0008 already states the wrong belief. Cost: a restore
that aborts *after* the Safety Snapshot and extraction, i.e. after the destruction AD-13
exists to prevent.

### The two units

- **Unit A — the S3 storage adapter** in `wpbackup2` (`S3ArchiveStore`).
- **Unit B — the AWS Secrets Manager credential provider** in `wpdatabase2`.

### How both comply

AD-8: *"a dependency declared under an optional extra is imported **inside the function or
method that uses it**, never at module scope. Absence raises a package-owned error naming
the extra to install."* Both units do exactly this.

AD-13: *"every external **binary** (`mysqldump`, `mysql`, `wp`) sits behind a port exposing
a preflight check ... The composition root runs preflight for every tool the *plan*
requires before executing any step of it."* `boto3` is not a binary. AD-13 does not bind
either unit. Neither registers a preflight.

### The incompatibility, concretely

ADR-0008 asserts the opposite of what AD-13 says: *"an AWS user who forgets the extra
learns at resolve time rather than import time — **mitigated by the named error and by
preflight (AD-13)**."* AD-13's scope is external binaries. The mitigation ADR-0008 claims
does not exist.

**Unit B** happens to be invoked early — credential resolution is in the plan's preflight
window (FR-19 lists *"credential resolution"* among the checks a Dry Run exercises) — so
its `ImportError`-derived package error fires before anything is touched. It maps to the
**credential failure** exit code (FR-21).

**Unit A** is invoked at the *last* step of a backup — the upload. The sequence for
`wpbackup2 backup --target s3://...` with the `aws` extra missing:

1. preflight: `mysqldump` present, `mysql` present. Pass — AD-13 satisfied.
2. dump the database into the workspace (minutes; gigabytes).
3. tar the Site Root (more minutes).
4. encrypt.
5. `S3ArchiveStore.put()` → lazy `import boto3` → `MissingExtraError("install wpbackup2[aws]")`.

The Run exits non-zero having done all the work and published nothing. Under UJ-1 that is
merely wasteful. **Under restore it is the failure AD-13 exists to prevent**: a restore
reading from an S3 Storage Target fails at *fetch* — but a restore that *writes* a Safety
Snapshot to an S3 target (see D-9) fails **after** the snapshot path has been reported and
**before** the snapshot is durable, and FR-8's *"If the Safety Snapshot cannot be taken,
the destructive restore does not proceed"* holds only if the failure is detected before
the destruction begins. AD-13's own promise — *"A missing tool aborts with nothing changed,
names the tool, and states why it was needed"* — is not extended to cover this.

And the **exit codes differ** for the same operator-visible condition ("you didn't install
the aws extra"): Unit B routes to *credential failure*, Unit A to *missing external
dependency* or, more likely given D-7, to the generic *operation failure*.

### Closing AD

> **Tighten AD-13 — preflight covers every absent-at-runtime capability, not only binaries.**
> Rewrite the rule as: *every capability the plan requires that can be absent at runtime —
> an external binary, an optional Python distribution behind an extra, or a Storage Target's
> reachability and write permission — is reachable through a port exposing
> `preflight() -> CapabilityStatus`, and the composition root runs preflight for the full
> set the plan requires before executing any step.* An adapter that lazy-imports an
> optional dependency (AD-8) **must** implement `preflight()` with an
> `importlib.util.find_spec` probe that does not import the module.
> The package-owned error AD-8 requires is a **subclass of the preflight
> missing-capability error**, so AD-18's MRO walk gives it one exit code everywhere.
> **Enforcement:** a CI test that enumerates every class implementing a port Protocol and
> asserts each declares `preflight()` — scope derived from the Protocol registry, not
> hand-listed; plus a base-install (no extras) test that runs a full backup plan to an S3
> target in Dry Run and asserts it aborts in the preflight phase.

---

## D-9 — The Safety Snapshot's destination is unspecified, and the two plausible answers have opposite failure modes

**Rank 9.** Likelihood: medium-high. Cost: either a snapshot on the disk being destroyed,
or a restore that a network blip can block entirely.

### The two units

- **Unit A — the restore epic** (FR-8).
- **Unit B — the storage epic** (`ports/ArchiveStore`, FR-16, FR-17).

### How both comply

AD-12: *"Safety Snapshots (FR-8) are the deliberate exception: they outlive the Run, are
written outside the workspace, and their location is reported."* That is a *lifetime* rule
and a *not-the-workspace* rule. It does not name a destination.

FR-8: *"The Safety Snapshot path is reported to the operator and is not deleted by the Run
that created it."*

**Unit A** writes the snapshot to a local directory derived from the Site Root
(`<site_root>/../.wpbackup2-snapshots/<run_id>.wpb2`). Outside the workspace. Reported.
Compliant.

**Unit B** observes the Glossary — *"Safety Snapshot — **an Archive** of the target Site"* —
and AD-6 — *"A Manifest is written on every Archive"* — and FR-16 — *"An operator can write
an Archive to ... a local path or a remote Storage Target"* — and writes it to the
configured Storage Target, the same one the restore is reading from. Outside the workspace.
Reported. Compliant.

### The incompatibility, concretely

**Unit A's failure:** under `all-clean` against a site whose parent directory is the same
filesystem being cleared, or under an operator who set `--site-root /srv/site` with the
snapshot at `/srv/.wpbackup2-snapshots/`, the snapshot is a full unencrypted-or-encrypted
copy of the site on **the same disk** as the thing being destroyed. A disk failure or a
`rmtree` with a symlinked parent takes both. NFR-1's *"no operation may leave a Site in a
state worse than not having run it"* is then only as strong as one disk.

**Unit B's failure:** FR-8 says *"If the Safety Snapshot cannot be taken, the destructive
restore does not proceed."* With the snapshot on S3, a transient 503, an expired IAM token,
or a missing `aws` extra (D-8) **blocks every destructive restore** — turning a safety
feature into an availability dependency during an incident, which is exactly when the
operator is restoring. UJ-2's Marcus, at 16:40 with a white-screened site, cannot restore
because the snapshot upload timed out.

**Retention collision.** Under Unit B the snapshot lands in the same object namespace as
backup Archives. FR-17: *"Pruning never removes the most recent Archive that passes
Verification"* — snapshots pass Verification, so a prune can delete the most recent *backup*
because a *snapshot* is more recent and satisfies the guard. Under Unit A snapshots are
invisible to retention entirely — and §13.2 already records unbounded snapshot lifetime as
a v1.0 limitation, so this is a known hole that D-9 makes two-shaped.

**Encryption.** FR-4 was pulled into v1.0 specifically because snapshots would otherwise
write unencrypted full-database copies to local disk (PRD Q-8). That reasoning assumes
Unit A's local destination. If Unit B ships, the reasoning changes but the requirement
does not — and nothing states whether a snapshot is encrypted with the *restore's*
passphrase, the *archive's* passphrase, or a separately supplied one. Three answers, all
compliant with AD-6.

### Closing AD

> **Tighten AD-12.** The Safety Snapshot is written to a **distinct, named Snapshot
> Target**, separate from the backup Storage Target and never in the same object
> namespace. Its default is a **local** path derived by one function in `domain/` from the
> operator's data directory (not the Site Root's parent, and asserted to be on a path that
> no Restore Mode clears); an operator may override it, including to a remote target, and
> the override is recorded in the Run's log. **Snapshots are excluded from Retention Policy
> until FR-17 defines snapshot lifetime explicitly**, and `ArchiveStore.list()` used by
> prune is scoped to the backup namespace by construction, not by a name filter.
> A snapshot is always encrypted when the Run has a passphrase; when it does not,
> the Run **refuses** unless the operator passes the explicit opt-out FR-8 already
> defines, and the opt-out is logged.
> **Enforcement:** a test asserting the default snapshot path is not a descendant of the
> Site Root nor of the workspace, for each Restore Mode; and a prune test asserting a
> snapshot in the snapshot target is never a candidate.

---

## D-10 — The Site Lock has two possible homes and two possible keys

**Rank 10.** Likelihood: medium-high. Cost: the concurrency guarantee FR-28 was extracted
into v1.0 to provide, silently absent for library callers.

### The two units

- **Unit A — the CLI epic.** Capability map: *"FR-21 exit codes, **FR-28 concurrency** |
  `cli/`"*. It implements the lock in `cli/`.
- **Unit B — the API epic.** FR-28: *"Locking is independent of how the Run was started:
  the guarantee holds for a `cron` entry, a `systemd` timer, a shell, **and a library
  caller alike**."* It implements the lock in `api/`.

Both are following a written instruction. The capability map and FR-28 disagree, and
neither is an AD, so neither wins.

### The incompatibility, concretely

**Two implementations, mutually invisible.** Unit A's lock is
`/run/lock/wpbackup2-<key>.lock` via `fcntl.flock`; Unit B's is
`<site_root>/.wpbackup2.lock` via an O_EXCL pidfile. A `cron` CLI backup and a library
caller's restore run concurrently against the same Site, each holding "the" lock. `rmtree`
during `mysqldump`.

**Two keys.** FR-28 says *"a lock identified by the Site"*; the Glossary says a Site is
*"one Site Root plus one database"*. Unit A keys on `sha256(realpath(site_root))`.
Unit B keys on `sha256(f"{db_host}:{db_port}/{db_name}")`. Both are "identified by the
Site" and both are partial:

- Unit A's key misses two Sites sharing one database (a staging clone pointed at prod's DB
  by a misconfiguration — precisely what Relocation exists to prevent).
- Unit B's key **changes mid-Run under Relocation**: FR-11 makes `db_host`, `db_port` and
  `db_name` relocation values, so after the config rewrite the Site's identity is a
  different string. The lock acquired at the start is no longer the lock for the Site at
  the end — either it is released against the wrong key, or a second Run acquires the new
  key while the first is mid-restore.
- FR-29 means one Site can be named by a Site Root *or* by a config path; Unit A's
  `realpath(site_root)` differs depending on which the operator passed if the CLI accepts
  both (as today's `WpSite` does).

Neither key survives a symlinked Site Root vs its target being passed on successive runs
unless `realpath` is mandated — and nothing mandates it.

### Closing AD

> **New AD-19 — The Site Lock is a port, owned by the Run Context, keyed canonically.**
> `SiteLock` is a Protocol in `ports/` with one adapter. It is acquired by the **Run
> Context** (AD-16) — therefore by whichever root is outermost, CLI or API, exactly once —
> before the first read of Site state, and released in a `finally` on success, failure and
> signal. The key is `SiteIdentity(descriptor)`, **one pure function in `domain/`** over
> `realpath(site_root)` only; it is computed once at Run Context creation from the
> *source* descriptor and **never recomputed**, so Relocation cannot change it mid-Run.
> The lock is **re-entrant for the holding Run Context** (see D-2). Lock file location is
> a single declared rule with an OS-appropriate default and an operator override; stale
> detection is by recorded PID + start time, per FR-28.
> **Enforcement:** a test that starts a Run through `cli/` and a Run through `api/`
> against the same Site and asserts the second is refused, naming the first's Run ID;
> a test that a relocating restore holds one lock key start to finish; and a test that a
> symlinked and a resolved Site Root produce the same key.

---

## D-11 — `wpconfigr` cannot carry the Run ID, because AD-2 forbids it the dependency AD-10 requires

**Rank 11.** Likelihood: certain — it is a direct contradiction between two ADs.
Cost: the Run ID is missing from records emitted during the config rewrite and read-back,
the single highest-risk step (ADR-0010).

### The two units

- **Unit A — the `wpconfigr` team.**
- **Unit B — the `wpbackup2` team.**

### How both comply

- AD-2: *"`wpconfigr` declares **zero** runtime dependencies, permanently."* `structlog` is
  a runtime dependency.
- AD-10: *"`structlog` over stdlib `logging` ... library modules only acquire a bound
  logger ... The Run ID is bound with `structlog.contextvars`, with `merge_contextvars`
  **first** in the processor chain, and appears on **every record**."*

Unit A cannot import `structlog`. It uses `logging.getLogger(__name__)`. Compliant with
AD-2, and AD-10's *"third-party records are routed through `ProcessorFormatter` so one
stream carries everything"* appears to cover it — `wpconfigr` is, from `wpbackup2`'s
perspective, third-party.

Unit B uses `structlog.get_logger()` and configures the chain with `merge_contextvars`
first. Compliant.

### The incompatibility, concretely

`structlog.contextvars.merge_contextvars` is a **structlog processor**. It runs on
structlog's chain. Stdlib records entering via `ProcessorFormatter` are processed by the
`foreign_pre_chain`, which is a **separate** list. AD-10 specifies *"the processor
chain"* — singular — and says nothing about `foreign_pre_chain`. The default
`foreign_pre_chain` is `None`.

So: `wpbackup2` binds `run_id` in a contextvar. `wpconfigr.WpConfigFile.set()` emits
`logger.info("writing DB_NAME")` through stdlib. That record reaches the handler, is
formatted by `ProcessorFormatter` with an empty `foreign_pre_chain`, and comes out
**without `run_id`**.

FR-20's first consequence: *"Every record emitted by a Run carries the same Run ID,
including records emitted around subprocess boundaries."* It fails, and it fails for
exactly the package performing the operation ADR-0010 identifies as the one with known
silent-corruption modes and a read-back mitigation. When a read-back verification fails in
production, the record saying so is the one the operator cannot correlate to their Run ID
(SM-5: *"Issues arrive with a Run ID and structured log excerpt"*).

The same applies to `wpdatabase2` if it chooses stdlib for symmetry — nothing says it must
use structlog, and AD-2 only exempts `wpconfigr` from dependencies, so `wpdatabase2` *may*
take structlog but is not told to.

Second-order: FR-20 requires verbosity *"consistent across `wpbackup2`, `wpconfigr` and
`wpdatabase2`"*. A consistent verbosity mapping across a structlog package and a stdlib
package needs a shared level table, and AD-10 defines none.

### Closing AD

> **Tighten AD-10.** State the split explicitly: **`wpconfigr` (and any zero-dependency
> package) logs through stdlib `logging` only and never imports `structlog`**; packages
> permitted runtime dependencies use `structlog`. The composition root **must** install
> `ProcessorFormatter` with a `foreign_pre_chain` **beginning with
> `structlog.contextvars.merge_contextvars`**, so contextvar-bound fields reach stdlib
> records. The verbosity level mapping (operator flag → numeric level) is a single table in
> the lowest dependency-free package, imported by all three.
> **Enforcement:** a test that runs a full restore with `caplog`/a capturing handler and
> asserts **every** emitted record — including at least one originating inside
> `wpconfigr` — carries the Run ID. The assertion is over *all captured records*, not a
> sampled list, so a new silent emitter cannot slip through.

---

## D-12 — Two owners of database provisioning, and AD-7's transport rule does not bind one of them

**Rank 12.** Likelihood: medium — the Deferred list makes this an open question, which is
how it becomes two answers. Cost: silent charset/collation corruption, discovered months
later; and a credential path outside AD-7's tested scope.

### The two units

- **Unit A — the `wpdatabase2` team**, which today owns provisioning.
- **Unit B — the `wpbackup2` restore epic**, which owns FR-9.

### How both comply

The Deferred list: *"**Whether `wpdatabase2` keeps a provisioning role at all** — AD-3 and
AD-9 remove most of its current reason to exist as a separate package. Revisit after
Release A."* So the question is explicitly open *while both teams are implementing*.

FR-9: *"The restore ensures the target database and user exist before loading the Dump,
and reports which of those it created."* That is a `wpbackup2` requirement.
Unit B implements it against the `SqlClient` port using `mysql` + `--defaults-extra-file`
(AD-7, ADR-0003).

Unit A keeps `WpDatabase.ensure_exists()` using PyMySQL (ADR-0004 selects PyMySQL for
*"provisioning queries only"* — the ADR presumes provisioning stays in `wpdatabase2`).

Both compliant. Both shipped.

### The incompatibility, concretely

**Two `CREATE DATABASE` statements with different defaults.** Unit A emits
`CREATE DATABASE {name}` and inherits the server default — on MySQL 8 that is
`utf8mb4_0900_ai_ci`, on MariaDB 10.x `latin1_swedish_ci` or `utf8mb4_general_ci`
depending on build. Unit B emits `CREATE DATABASE {name} CHARACTER SET utf8mb4 COLLATE
utf8mb4_unicode_ci` because WordPress's own `wp-config.php` carries `DB_CHARSET`/
`DB_COLLATE`. Whichever runs, a database created with a different collation than the dump
was taken from produces **silent** corruption of emoji, non-Latin content and sort order —
the classic WordPress utf8mb3/utf8mb4 failure — surfacing weeks later as "some posts show
question marks". PRD §9 commits to *tested* MySQL/MariaDB parity, which makes this a
cross-engine divergence with no owner.

**AD-7's rule does not bind Unit A.** AD-7 says *"one credential-transport adapter writes a
`[client]` option file ... passes it as `--defaults-extra-file` in argv position 1 ... A
test asserts both properties **against a constructed argument vector** and against captured
log output."* PyMySQL is not a subprocess. Unit A passes the password as a Python keyword
argument — which is fine in itself, but it means:

- the `finally`-delete guarantee AD-7 provides applies to Unit B's path and not Unit A's;
- **AD-7's test — which inspects an argv vector — cannot see Unit A at all.** The
  hygiene rule is enforced over the set of *subprocess call sites*, and Unit A is not one.
  Per the project's own guard rule, the check's scope is not derived from the source of
  truth (the set of things that touch credentials), so it reports success over a set that
  does not contain the new path.
- PyMySQL's connection failure exceptions carry the DSN; if one escapes as an
  `args` tuple into a structured log field, AD-14's *"No exception message contains a
  credential"* is satisfied (the *message* is clean) while the credential leaks through the
  structured field (see D-14's sibling issue in D-7's fix).

**Two GRANT policies.** FR-9 also requires the *user* to exist. Unit A grants
`ALL ON db.*`; Unit B grants the minimum for a WordPress runtime. Which the restored site
gets depends on which unit's code path ran, and a site granted `ALL` violates NFR-3's
least-privilege claim.

### Closing AD

> **New AD-20 — Provisioning has exactly one owner, named now, behind one port.**
> Close the Deferred item before implementation rather than after Release A: database and
> user provisioning is a `wpbackup2` capability, reached through the `SqlClient` port, and
> `wpdatabase2`'s provisioning role is **removed** (or, if retained, `wpbackup2` calls it
> and implements none of its own — either answer, but one, decided in the AD).
> `CREATE DATABASE` charset and collation are **derived from the Archive's Manifest**
> (recorded at backup time from the source database's actual collation), never from a
> server default or a hard-coded literal, and the grant set is a single declared list in
> `domain/`.
> **Extend AD-7** so its scope is *"every path that transports a credential to a database
> engine — subprocess or in-process driver"*, and its test scope is **derived from the set
> of classes implementing `SqlClient` and `CredentialProvider`**, not from the set of
> subprocess call sites. Add a planted-violation test: a new `SqlClient` implementation
> that passes a credential unredacted must fail the guard.

---

## D-13 — Storage Target addressing and Archive naming were deferred, but v1.0 must decide both

**Rank 13.** Likelihood: medium. Cost: a v1.1 grammar change is a CLI-contract break (§10),
and a prune that cannot see backup's objects.

### The two units

- **Unit A — the backup epic**, which must accept a target string in v1.0 (FR-16's
  *"A Storage Target is addressable as a single string"*; §13.2 ships local targets in v1.0).
- **Unit B — the prune/retention epic** (v1.1) or the snapshot epic (v1.0).

### How both comply

Deferred: *"**Storage Target addressing scheme** (URL grammar for S3/SFTP/rsync) — v1.1,
and **the port shape in AD-1 is enough to keep v1.0 from foreclosing it**."*

That claim is false in one specific way: the *port shape* is preserved, but the **accepted
string grammar** is a CLI contract surface (§8: *"Command names, option names, accepted
values"*) and §10 makes changing accepted values a breaking change. v1.0 must accept
something.

Unit A accepts a bare filesystem path: `--target ./backups`. Unit B, writing the prune
command or a snapshot target, accepts `file:///srv/backups`. Both compliant with a
deferred decision.

### The incompatibility, concretely

**Grammar.** When S3 lands in v1.1 the grammar becomes scheme-prefixed. Now
`--target C:\backups` on Windows parses as scheme `c`, and a relative path
`--target s3/archives` is ambiguous with `s3://`. Retrofitting normalization is a breaking
change to accepted values under §10 — across three packages that release together (AD-15).

**Archive naming, which is *not* in the Deferred list and therefore has no owner at all.**
AD-12 killed the fixed `database.sql` name inside the workspace, and AD-6 owns *member*
names *inside* the Archive. **Nothing owns the Archive object's own name at the Storage
Target.** Unit A names archives
`wpbackup2-{site}-{created_at.isoformat()}.wpb2` — an ISO-8601 timestamp with a `:` in
it, which is illegal in a Windows filename and awkward as an S3 key requiring escaping in
a console. Unit B's prune parses the name to obtain age (FR-17: *"Retention is expressible
by count and by age"*) and its regex does not match Unit A's `{site}` segment when the site
name contains a `-`. Prune sees zero candidates and reports *"nothing to prune"* forever —
a failure that reports success, which is the worst available mode, and that only manifests
after the retention window elapses, i.e. weeks after release.

A second naming hazard: if `{site}` is derived from the Site Root path, two Sites at
`/srv/a/public` and `/srv/b/public` both name as `public` and overwrite each other at the
target — an archive collision that destroys the previous night's backup, exactly the thing
UJ-1's edge case says must never happen.

### Closing AD

> **New AD-21 — Storage Target addressing and Archive naming are decided in v1.0, in
> `domain/`, with a round-trip guarantee.**
> One parser in `domain/` accepts a Storage Target string and normalizes it to a
> `StorageTarget` value: a string with no `://` is a local path (resolved, including
> Windows drive letters, before any scheme inspection); a string with `://` is parsed by
> scheme, and an unknown scheme is a named error listing the supported schemes. The v1.0
> supported set is `{file}`; adding a scheme is additive and therefore a minor version.
> **Archive object naming** is one function in `domain/` with a declared, filesystem- and
> S3-safe grammar (basic-latin timestamp, no `:`; a Site component derived from
> `SiteIdentity` (AD-19), not from a path basename), and an inverse `parse` asserted to
> round-trip by a property test over generated Site Roots and timestamps.
> **Retention derives an Archive's age from its Manifest, never from its object name** —
> so prune cannot silently match nothing.

---

## D-14 — The Clock port under Dry Run, vs structlog's real timestamps

**Rank 14.** Likelihood: medium. Cost: low individually, but it makes retention dry-runs
unfalsifiable.

### The two units

- **Unit A — the backup epic**, which takes `created_at` from the `Clock` port (it is in
  the `ports/` list in the Structural Seed, and AD-1 forbids a clock read in `core/`).
- **Unit B — the logging epic**, which configures structlog with a `TimeStamper` processor
  (AD-10).

### How both comply

AD-4: a Dry Run binds *no-op adapters that log the intended effect and return plausible
results*. `Clock` is a port; the naming convention gives it a `NoopClock`. A `NoopClock`
returning a fixed sentinel (`1970-01-01T00:00:00+00:00`, or a frozen "now") is plausible
and compliant. A `NoopClock` that delegates to the real clock is also compliant — see D-4;
AD-4 does not distinguish query from command.

`TimeStamper` reads the real clock unconditionally; there is no port between structlog and
the system clock, and AD-10 does not mention one.

### The incompatibility, concretely

Under `--dry-run`:

- The reported would-be Manifest carries `created_at` from `NoopClock` — possibly frozen,
  possibly epoch.
- Every log record carries a real UTC timestamp from `TimeStamper`.

The conventions table requires *"UTC, ISO-8601 with explicit offset, **in the Manifest and
in every log record**"* — satisfied in form, contradicted in content: the same Run reports
two different "now"s.

The consequential case is **retention dry-run** (FR-17: *"A Dry Run lists exactly which
Archives would be pruned and removes none"*). Age-based retention compares
`now - archive.created_at` against the policy window. If `now` comes from a `NoopClock`
returning epoch, **every** archive is in the future and nothing is listed as prunable —
the dry run reports "would prune: none", the operator approves, and the real run deletes
forty archives. The dry run's entire purpose is inverted, and it reports success.

### Closing AD

> Covered by the **AD-4 tightening in D-4**: `Clock.now()` is a **query**, so a Dry Run
> binds the **real** clock. Add to AD-10: log record timestamps come from the same `Clock`
> port as domain timestamps (a `structlog` processor that reads the Run Context's clock),
> so a Run has exactly one notion of "now". **Enforcement:** a test asserting that for a
> single Run the Manifest's `created_at` and the first log record's timestamp are within a
> declared tolerance, under both real and dry-run adapter sets.

---

## What these have in common

Three structural causes account for all fourteen:

1. **Ownership of cross-cutting *instances* is unstated.** AD-10 and AD-12 name *who
   creates* the Run ID and the workspace ("the composition root", "the shell") but the
   spine defines **two** composition roots and never says what happens when one is entered
   from inside another. D-2, D-9, D-10 and half of D-3 all descend from the missing
   Run Context (AD-16).
2. **Ownership of *schemas* is stated; ownership of *content* is not.** AD-6 says one
   module owns the Manifest schema. It does not say what a member checksum is taken over
   (D-1), what member roles exist (D-5), what the Site Descriptor's fields are (D-6), or
   what an Archive is called (D-13). "One owner" closes the *drift* hole and leaves the
   *underspecification* hole open.
3. **Two guards have a scope that is hand-enumerated rather than derived** — AD-7's
   redaction test over subprocess call sites (D-12), and the implicit exit-code table over
   a written list of categories (D-7). Both will keep reporting success over a set that no
   longer contains what matters, which is the project's own §4 failure mode.

**Recommended sequence:** add **AD-16 (Run Context)** first — it closes or halves five
pairs. Then the **AD-6 tightening** (D-1 and D-5 together, since both are archive layout).
Then **AD-17 (restore phase order)**, which is cheap and turns a diagram into a test.
Then the **AD-4 tightening** (D-4, D-14). Then AD-18/AD-19/AD-20/AD-21 and the AD-3,
AD-10, AD-12, AD-13 tightenings.

Two of the Deferred items should be **un-deferred before implementation starts**:
Storage Target addressing (D-13, because v1.0 must accept *some* grammar and §10 makes
it a breaking surface) and the `wpdatabase2` provisioning question (D-12, because leaving
it open while two teams implement is what produces two answers).
