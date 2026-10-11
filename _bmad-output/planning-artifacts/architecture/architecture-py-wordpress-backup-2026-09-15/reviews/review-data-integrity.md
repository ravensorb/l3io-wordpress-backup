# Review — Data Integrity and Security Lens

- **Target:** `ARCHITECTURE-SPINE.md` (wpbackup2 family, 2026-09-15, draft)
- **Supporting:** `docs/adr/0001`–`0010`, PRD `prd-py-wordpress-backup-2026-09-12`, `arch-review-2026-09-12.md`
- **Lens:** data integrity and security, against NFR-1 — *"no operation may leave a Site in a state worse than not having run it."*
- **Date:** 2026-09-15

---

## Verdict

**The spine closes the five historical defects. It does not close the failure class that
produced them, and it introduces two new unbuildable specifications on the restore path.**

The five named regressions are each answered by a named invariant — AD-5 for the discarded
`restore_mode`, AD-7 for credentials in argv and logs, AD-11 for `extractall`, AD-12 for the
hardcoded `/tmp`. That is real progress and the invariants are well aimed. But every one of
those defects was a *step-level* defect, and the spine reasons at step level too. The restore
sequence is a chain of eleven independently-failing, individually-irreversible steps, and **no
AD makes the chain recoverable.** A restore killed at step 9 of 11 leaves a WordPress site with
files from the archive, a database half from the archive and half from before, and no record
anywhere that this happened. The Safety Snapshot is the stated answer and it is taken early
enough — but it is never verified, is not required to be encrypted, and the operator is told
where it is in a log line rather than by any durable artifact the next run can find.

Two specifications cannot be implemented as written. ADR-0006 requires the KDF salt to live in
a Manifest that lives inside the ciphertext the salt is needed to decrypt, and requires the
total chunk count to be bound as AAD into chunk 0 of a stream whose length is unknown until
chunk N. ADR-0003 asserts that `--defaults-extra-file` "works uniformly for … WP-CLI's
bootstrap"; ADR-0005 states the opposite three pages later, and ADR-0005 is correct.

And FR-28, a v1.0-committed requirement with five specific testable consequences, has **no
invariant at all** — the capability map points it at AD-12, which provides per-Run *isolation*,
the opposite of mutual exclusion.

**Gate: NOT PASSED.** Findings 1–4 are blocking. Findings 5–8 should land in the same pass.

---

## How the five historical defects fare

| Historical defect | Invariant | Actually closed? | Enforced mechanically? |
|---|---|---|---|
| `restore_mode` discarded → unconditional `rmtree` | AD-5 | **Yes.** "No function that consumes a Restore Mode may declare a default for it" is the precise rule | **No.** Prose only — see Finding 8 |
| DB restore silently skipped, success reported | AD-5 (partly) | **No.** AD-5 fixes the *cause* (mode plumbing). The *reporting* half — an early return on a "nothing to do" branch plus a success log — has no invariant. See Finding 10 | n/a |
| Passwords in `argv` and at DEBUG | AD-7 | **Yes**, and AD-7 names its own test | **Yes** |
| `extractall` without containment | AD-11 | **Yes**, and explicitly refuses to rely on the interpreter default | **No** — see Findings 8, 11 |
| Hardcoded `/tmp`, fixed filenames | AD-12 | **Yes** for the happy path; **no** for SIGKILL — see Finding 6 | **No** |

The pattern: where the spine names a defect it closes it well. Where the defect was a *second-order*
consequence — success reported by a function that returned early, a `finally` that a signal skips —
the invariant stops at the first order.

---

# Findings, ranked by blast radius

---

## 1. BLOCKER — A killed restore leaves an unrecoverable chimeric site; no AD requires recovery to be possible

**Blast radius:** total, silent, and the product's stated reason to exist. Every destructive restore.

### The walk

Taking the spine's own mermaid sequence, step by step, asking what a SIGKILL / power loss /
disk-full / network drop leaves behind:

| # | Step | State if the process dies here | Recoverable? |
|---|---|---|---|
| 1–3 | bind Run ID, build plan, preflight | Nothing changed | ✅ |
| 4 | verify Manifest | Nothing changed. Workspace may hold a decrypted plaintext dump — Finding 6 | ✅ |
| 5 | **Safety Snapshot** | A *partially written* snapshot archive on disk, indistinguishable from a complete one. Site untouched | ⚠️ site fine, snapshot poisoned |
| 6 | **extract, `filter='data'`** | **Site Root is a mixture** of archive files and pre-existing files, in arbitrary proportion. `wp-config.php` not yet rewritten, database untouched. A plugin directory half-replaced runs a PHP fatal on the next request | ❌ only by hand, from the snapshot |
| 6′ | extract in a `-clean` mode | `rmtree` completed, extraction did not: **Site Root empty or near-empty** | ❌ |
| 7 | **rewrite `wp-config.php`** | Truncated or zero-length `wp-config.php`. Site returns a blank page or leaks PHP source. **The one file WordPress cannot boot without** | ❌ |
| 8 | **load dump via `mysql`** | **Database partly loaded.** `mysql < dump.sql` is not one transaction: it is thousands of statements, and any MyISAM table or any implicit DDL commit breaks atomicity regardless. Result: `wp_options` from the archive, `wp_postmeta` from before. WordPress boots and looks fine | ❌ **and silent** |
| 8′ | load in a `-clean` mode | Tables dropped, some reloaded, some absent | ❌ |
| 9 | `wp search-replace` | URLs rewritten in some tables, not others. Site loads with broken menus and mixed-content assets | ⚠️ *idempotent* — re-running the same replace completes it. But nobody knows to |

Steps 6 through 9 all produce a site **worse than not having run the restore**, which is the
literal text of NFR-1. Step 8 is the worst of them because it produces a site that *works* while
being internally inconsistent — the failure mode nobody detects for weeks.

### What covers it today

- **FR-8 / AD-12 Safety Snapshot.** It exists, and it is taken at the right point — step 5, before
  the first destructive step. That is correct and it is the design's strongest move. But it is a
  *manual* recovery path: it requires an operator to notice, to find the snapshot path in log
  scrollback of a `cron` job that ran at 03:00, and to run a second restore which is itself
  destructive and non-atomic. See Finding 3 for why the snapshot is also not trustworthy as built.
- **PRD §11:** *"Documentation states what a failed restore leaves behind at each stage, where the
  Safety Snapshot is, and how to recover from it."* This is the only coverage, and it is **prose,
  in a runbook, describing a state the product does not record.** It cannot be checked, and the
  operator reading it at 03:40 has no way to know which stage the run reached.
- **No AD requires recovery to be possible.** AD-12 governs workspace *cleanup*. AD-5 governs
  *authorization* of destruction. Nothing governs *reversal* of destruction.

### What closes it

Three changes, in increasing value:

**(a) New AD-16 — A destructive Run leaves a durable intent record.**

> Before the first destructive step, the shell writes a Run Journal outside the workspace,
> alongside the Safety Snapshot, and `fsync`s it: Run ID, UTC start, Restore Mode, Site identity,
> absolute Safety Snapshot path, archive identity, and the step about to begin. Each step
> transition rewrites and `fsync`s it. On success the journal is removed.
>
> A Run that finds an existing journal for the same Site **refuses to start**, names the stranded
> Run ID, the step it died on, and the snapshot that reverses it. `wpbackup2 restore --resume` /
> `--rollback <run-id>` consume the journal; `--abandon` removes it and is logged.
>
> *Enforcement:* a test that `SIGKILL`s the process at each step boundary and asserts the journal's
> recorded step matches the observed on-disk state. The step list is derived from the plan value,
> not hand-enumerated, so a new step cannot be added without appearing in the test.

This converts every ❌ above into *"known state, named recovery action"* — which is the property
NFR-1 actually needs, and the one that makes an unattended 03:00 restore (UJ-1) defensible.

**(b) Atomic `wp-config.php` write.** Write to a temp file in the same directory, `fsync`, `os.replace`,
`fsync` the directory; preserve the pre-write copy for the duration of the Run. This removes step 7
from the list entirely at a cost of about six lines. It is also load-bearing for ADR-0010 — see
Finding 7(e). Belongs in AD-3 or ADR-0010.

**(c) Structural: make the database load non-destructive.** Load the dump into a **staging database**
(`<dbname>_restore_<runid>`), then switch by rewriting `DB_NAME` in `wp-config.php`. Because (b)
makes the config write atomic, the entire database cutover becomes a single atomic filesystem
operation. Step 8 stops being destructive; the only destructive database moment becomes dropping
the *old* database, which happens last and can be deferred entirely (leave it, let FR-17 retention
reap it). This also reorders the sequence — load DB, rewrite config, search-replace — which is
compatible with ADR-0005's WP-CLI constraint, since `search-replace` still runs after the config
rewrite against the config that now names the staging database.

This is the single highest-value change in the review. It costs one extra database's worth of
disk and removes the design's worst failure mode.

---

## 2. BLOCKER — The ADR-0006 encryption envelope cannot be built as specified, and the construction is unsound against cross-archive splicing and wrong-passphrase detection

**Blast radius:** every Archive and every Safety Snapshot the product ever writes. An archive that
cannot be decrypted is indistinguishable, to the operator, from having had no backup at all.

ADR-0006's shape is right — Argon2id + chunked AES-GCM with per-chunk nonces and framing bound as
AAD is the correct family, and rejecting Fernet for the documented reason is correct. The recipe
as written has six specific defects, two of which make it unimplementable.

### (a) Bootstrap paradox — the salt is inside the ciphertext it decrypts *(unbuildable)*

ADR-0006 states both:

> *"Salt, KDF parameters and algorithm identifiers live in the Manifest. **The key never does.**"*
>
> *"**Format:** the Manifest is a JSON member inside the archive, not a sidecar."*

If the envelope wraps the tar stream, the salt needed to derive the key is **inside the ciphertext**.
The archive is undecryptable. If instead encryption wraps individual *members*, member names, member
count and member sizes all leak in plaintext, and FR-4's *"yields no plaintext … content to an
inspector"* is only half met.

`addendum.md` line 102 flags precisely this as open — *"whether encryption wraps the whole archive
or the members; whether streaming encryption is compatible with the chosen integrity scheme"* —
and ADR-0006 closes the first half of the question while leaving the second half to whoever writes
the code. Backup and restore are the two sides of the one contract AD-6 exists to keep from
drifting; this is exactly where they will drift.

**Fix — specify three layers explicitly in AD-6:**

```
[ Envelope Header ]  plaintext, authenticated, fixed layout
    magic | envelope_version | archive_id (16B random) | kdf_id | argon2 params
    | salt (16B, per-archive) | aead_id | chunk_size | key_commitment (32B)
[ Chunk 0 ] [ Chunk 1 ] … [ Chunk N ]   ciphertext+tag each
    plaintext = the tar stream, of which member 0 is manifest.json
```

The Manifest (per-member checksums, format version, timestamps, exclusions) stays **inside** the
ciphertext where it belongs — it carries site-identifying data. Only the parameters needed to
*reach* the Manifest sit outside, and the entire header is bound as AAD into every chunk so it
cannot be edited. This also satisfies FR-4's *"encryption parameters sufficient to decrypt …
recorded in the Manifest"* if the header is defined as the Manifest's envelope section.

### (b) Total chunk count is not knowable at write time *(unbuildable)*

> *"chunked AES-GCM with a unique nonce per chunk and the **chunk index and total chunk count**
> bound in as AAD, so truncation and reordering are detected"*

The archive is a streamed `tar`+compress of a multi-gigabyte site (NFR-7: *"streamed, never buffered
whole in memory"*). The total chunk count is unknown until the last chunk is produced. Binding it
into chunk 0's AAD requires either buffering the whole archive first — contradicting NFR-7 and
doubling both workspace and wall-clock — or a second pass.

**Fix:** use the standard streaming-AEAD framing instead. AAD per chunk is
`header_bytes || u64(chunk_index) || u8(is_final)`, and the final chunk carries `is_final = 1`.
Truncation is detected because the stream ends without a chunk whose AAD says final; reordering and
chunk deletion are detected by the index. This is the construction streaming AEADs use (STREAM /
`age`'s payload framing) precisely because it needs no advance length, and it is strictly stronger
than a total count, which a truncating attacker could not forge anyway but a *truncating disk* can
produce plausibly.

### (c) No archive identity in the AAD — chunks splice between archives

Chunk index + total count binds a chunk's position **within an archive**. It does not bind it **to**
an archive. Given two archives encrypted under the same key, chunk 7 of archive A can be substituted
for chunk 7 of archive B and every authentication check passes.

Is the same key reachable? Yes, by two routes, and FR-8 makes both likely: Safety Snapshots are
**always on**, so a single operator passphrase covers hundreds of archives over a site's life.

**Fix:** the 16-byte per-archive `archive_id` from (a) is in the header, and the header is AAD on
every chunk. Splicing across archives then fails authentication unconditionally, regardless of key
reuse.

### (d) Per-archive salt is not stated, and Argon2id's cost creates pressure to violate it

ADR-0006 says *"≥16-byte random salt"* and *"RFC 9106 parameters"* — it never says **per archive**.
RFC 9106's first-choice profile is 2 GiB and roughly a second of CPU. An implementer backing up
twelve sites in one nightly run, or taking a snapshot inside every restore, will notice that cost
and cache the derived key. That is the natural optimisation and nothing in the ADR forbids it.

Combine a cached key with the other natural implementation choice — a **counter-based nonce**, which
is nearly forced because the chunk index is already tracked and bound as AAD — and two archives share
`(key, nonce=0), (key, nonce=1), …`. **That is catastrophic GCM nonce reuse:** it discloses the XOR
of the two plaintexts *and* recovers the GHASH authentication subkey `H`, at which point an attacker
can forge a valid tag for arbitrary chunk content. Forged chunks become PHP files written into a web
root — see Finding 9.

Neither the ADR nor AD-6 states which nonce construction is used. The wrong pair of individually
reasonable choices produces a total break, silently.

**Fix — state all three, and test them:**
- The salt is `os.urandom(16)` **per archive**. A derived key is never reused across archives; a key
  cache keyed by anything other than `(passphrase, archive_id)` is a defect.
- Nonce is `nonce_prefix(4B, per-archive random, in the header) || u64_be(chunk_index)`.
- *Test:* encrypt identical plaintext twice under the same passphrase; assert the salts differ, the
  nonce prefixes differ, and the ciphertexts share no 12-byte nonce. The test derives the chunk count
  from the fixture, not a constant.

### (e) No key commitment — FR-4's named-error consequence is unsatisfiable

> FR-4: *"Restoring an encrypted Archive without a key fails with a **distinct, named error**, not a
> generic corruption error."*

AES-GCM is not a committing AEAD. A wrong passphrase produces a well-formed key that fails the first
chunk's tag. A corrupted archive produces a correct key that fails a tag. **The construction cannot
tell them apart** — both surface as `InvalidTag`. The chosen recipe therefore cannot meet a
requirement the same ADR claims to realise, and an operator holding the right passphrase for an
archive damaged in transit is told their passphrase is wrong, and vice versa.

**Fix:** derive 64 bytes from Argon2id; bytes 0–31 are the AEAD key, bytes 32–63 are a
`key_commitment` written in the plaintext header. On open, re-derive and compare in constant time
*before* streaming a single chunk. A mismatch is `ArchivePassphraseError`; a tag failure after a
commitment match is `ArchiveCorruptError`. Two named errors, checked in milliseconds rather than
after a gigabyte of I/O.

### (f) Manifest checksums establish integrity, not authenticity — and only for encrypted archives

For an **unencrypted** archive the Manifest lives inside the tar with unkeyed checksums. Anyone who
can write to the Storage Target can modify a member *and* rewrite its checksum; Verification passes.
The spine presents verification as if it established trust — *"pass / fail → abort before any
destruction"* — under an AD titled **"An Archive is untrusted input"** whose only actual mechanism is
extraction containment.

**Fix:** AD-6 states plainly that Verification establishes integrity **against corruption only**;
authenticity requires the AEAD envelope (or a signature, deferred). And `--encrypt` is the default
for any archive written to a Storage Target the operator has not declared trusted.

---

## 3. BLOCKER — The Safety Snapshot is the whole of NFR-1 and is the least specified artifact in the design

**Blast radius:** total. Every claim in the PRD's risk table (§ *"A restore destroys a live site and
the backup turns out to be bad"*) terminates here.

Five concrete gaps:

**(a) The snapshot is never verified.** Every *incoming* archive is verified before use (AD-6, FR-3,
the mermaid's step 4). The one archive the entire safety property depends on — the one written by a
process that is about to `rmtree` the site — is written and trusted. A snapshot truncated by a
disk-full at 99%, or by the crash in Finding 1 step 5, is indistinguishable from a good one until the
operator tries to use it, which is by definition the worst moment.

> **Fix (one sentence into AD-12 / FR-8):** the Safety Snapshot is written to a `.partial` name,
> then verified through **the same code path FR-3 uses for an incoming archive**, then renamed into
> place. The destructive restore proceeds only after the rename. A `.partial` snapshot found by a
> later Run is reported, never silently reused, never counted by retention.

**(b) The snapshot is not required to be encrypted — which reopens the exact hole the PRD's own Q-8
closed.** PRD Q-8 found that always-on snapshots (FR-8) plus deferred encryption (FR-4) meant *"v1.0
would have written unencrypted, never-pruned copies of the full database to local disk as a side
effect of its own safety feature"*, and pulled FR-4 into v1.0 to fix it. **Pulling encryption into
v1.0 does not make it mandatory for snapshots.** FR-4 is operator-supplied-passphrase, opt-in. FR-8
is automatic and always-on. An unattended `cron` restore with no `--passphrase` configured writes an
unencrypted complete database dump — every user record, every password hash — to disk today, exactly
as Q-8 described. Nothing in the spine or ADR-0006 refuses it.

> **Fix:** AD-12's Safety Snapshot clause requires an encryption passphrase to be resolvable, or the
> destructive restore refuses (FR-8 already has the refusal semantics: *"if the Safety Snapshot
> cannot be taken, the destructive restore does not proceed"* — this is one more reason it cannot be
> taken). If a site-scoped snapshot passphrase is not configured, generate one, and — since losing it
> means losing the snapshot — the refusal must name how to configure it. An explicit
> `--snapshot-unencrypted` opt-out is logged, per FR-8's existing opt-out shape.

**(c) The snapshot's location may be inside the web root.** AD-12 says only *"written outside the
workspace … their location is reported."* Reported where — a log line. If the default is derived from
the Site Root (the obvious choice: `<site_root>/.wpbackup2-snapshots/`), a complete database dump
becomes **HTTP-fetchable** on a running WordPress site. Combined with (b) that is a full credential
and PII disclosure from a feature whose purpose is safety.

> **Fix:** AD-12 states the snapshot destination is never under the Site Root, defaults to a
> sibling or an operator-configured directory, and the Run **refuses** if the resolved path resolves
> under the Site Root (`os.path.commonpath` after `realpath`, so a symlink cannot smuggle it in).

**(d) The snapshot's scope is not derived from the Restore Mode.** A `files-clean` restore destroys
files only; a `database-clean` restore destroys the database only. If the snapshot is always a full
backup, a files-only restore pays a full `mysqldump` it does not need and requires `mysqldump` at
preflight (AD-13) when the restore itself does not. If the snapshot is hand-mapped per mode, that
mapping is exactly the hand-kept list that drifts.

> **Fix:** the snapshot scope is **computed from the plan** — the union of everything the plan's
> steps will destroy — not from a table. The six-row FR-6 mode table is the source of truth. A test
> asserts, for every mode in that table (iterated from the enum, not listed), that the snapshot's
> Manifest covers every element the mode's row marks destructive.

**(e) The mermaid gives the snapshot no return edge.** Every other safety step in the diagram has
one — preflight has *"present / absent → abort, nothing changed"*, verify has *"pass / fail → abort
before any destruction"*. `Root->>Arc: Safety Snapshot (AD-12)` has none, while FR-8 explicitly
requires *"if the Safety Snapshot cannot be taken, the destructive restore does not proceed."* This
is the arch review's M-16 shape — a return value that exists and is discarded, exiting 0. In a
document whose purpose is to be implemented from, the missing arrow is the bug.

> **Fix:** add the edge, `Arc-->>Root: verified / failed → abort before any destruction`.

---

## 4. BLOCKER — FR-28 (concurrency) has no invariant; the capability map points it at the mechanism that does the opposite

**Blast radius:** two Runs racing on one Site during a `-clean` restore. UJ-1, the flagship journey,
is an unattended 03:00 timer against a tool that calls `rmtree` and `DROP DATABASE`.

The Capability → Architecture Map says:

| FR-21 exit codes, **FR-28 concurrency** | `cli/` | **AD-12, AD-14** |

AD-12 gives each Run a *private workspace* — that is **isolation**, the exact opposite of mutual
exclusion. Two Runs with two workspaces race on one Site perfectly happily. AD-14 is the exception
hierarchy. **FR-28 is architecturally unimplemented**, while carrying five specific testable
consequences and shipping in v1.0 *"whether or not a scheduler ever does."*

Four things must be decided or two implementers will build two incompatible locks:

**(a) What identifies "the Site"?** The Site Root path? Two paths reach one site through a symlink or
a bind mount, and the lock silently does not hold. The `DB_NAME`+host? A **relocating** restore
changes both mid-Run. It must be a canonicalised identity — `realpath` plus `st_dev`/`st_ino` of the
Site Root — and a relocating Run must hold **both** the source and destination identities.

**(b) Where does the lock live?** If it lives in the Site Root, a `files-clean` restore **`rmtree`s
its own lock** at step 6, and a second Run starting at step 7 acquires it cleanly and begins
destroying a site mid-restore. This is a concrete self-defeat that nobody has caught because FR-28
has no AD to catch it in. The lock must live somewhere no Run can delete — a per-user runtime
directory keyed by the site identity hash.

**(c) Mechanism.** FR-28 requires release *"on success, on failure, and on signal"* and *"a stale
lock … detected and reclaimed rather than requiring manual removal."* `fcntl.flock` gives all of
that free — the kernel drops it on any process death including `SIGKILL`, which a PID file cannot do
without a racy liveness check. But `flock` requires a companion sidecar to satisfy *"names the
holding Run's ID and start time"*, and it degrades silently over NFS without NFSv4 — and NFS/EFS
docroots are common in exactly the autoscaling deployments this codebase came from (`chesney`,
`--only-appointed-in-asg`). A lock that silently does not lock is worse than none.

**(d) FR-28's text promises more than any local mechanism can deliver.** *"Two Runs cannot operate
on the same Site at once"* is unqualified. A local `flock` cannot prevent two Runs on two hosts
against one shared docroot. The spine must state the achievable bound rather than let the requirement
read stronger than its mechanism.

> **Fix — new AD-17, "One Run per Site, and the lock outlives nothing":**
>
> - Site identity is `sha256(realpath(site_root) || st_dev || st_ino)`, computed once at the
>   composition root. A relocating Run holds source and destination identities, acquired in sorted
>   order to preclude deadlock.
> - The lock is an `fcntl.flock(LOCK_EX|LOCK_NB)` on `<runtime_dir>/wpbackup2/<identity>.lock`,
>   **never** under the Site Root or the workspace. A JSON sidecar written under the same lock
>   carries Run ID and UTC start for FR-28's error message.
> - Acquired before the first read of Site state — **before** the plan is built, i.e. before step 2
>   of the sequence diagram, which currently shows no lock step at all.
> - If `flock` is unavailable or unreliable on the lock directory's filesystem, the Run **refuses**
>   and names `--lock-dir`. It does not proceed unlocked.
> - **Stated bound:** the guarantee is per host. A Site shared across hosts requires an operator-
>   supplied lock directory on shared storage, and the docs say so rather than implying otherwise.
> - *Enforcement:* a test spawning two real processes against one fixture Site, and a test that
>   `SIGKILL`s the holder and asserts the next Run acquires without manual cleanup.

### Two Runs against *different* Sites sharing a Storage Target

FR-28 locks by Site, so these proceed concurrently — correctly, they should. But they contend on the
Storage Target, and nothing governs it:

1. **Retention can delete the only good backup.** FR-17's prune enumerates archives, then deletes.
   A concurrent Run's upload that completes between the enumeration and the deletion is invisible to
   the prune's view; worse, a *truncated* upload from a crashed Run is visible and may be counted as
   "a recent backup", licensing the prune to delete a good older one. That is the single way this
   product can leave an operator with **zero** valid archives.
2. **Non-atomic upload.** Nothing requires an Archive to be written to a temporary key and promoted
   only on completion. A crash mid-upload leaves a truncated object that looks like an archive.
   Restore-time verification catches it (GCM will), but retention runs long before any restore does.
3. **Name collisions.** If archive names derive from site name plus timestamp, two sites with the
   same basename backed up by the same 03:00 timer collide.

> **Fix, into AD-6 / the `ArchiveStore` port contract:**
> - An Archive is written to a `.partial` key and **promoted by rename only after its Manifest is
>   written and Verification passes.** Retention considers only promoted archives.
> - **Retention never deletes unless at least one verified Archive remains** for that Site, and never
>   deletes the newest N. This is the NFR-1-shaped clause and it belongs in the invariant, not in the
>   retention feature.
> - Archive keys carry the Site identity hash from AD-17, not a display name.

---

## 5. MAJOR — ADR-0003 is factually wrong about WP-CLI, and `--defaults-extra-file` lets an ambient `~/.my.cnf` redirect a restore to the wrong server

**Blast radius:** a restore loading a dump into the wrong database; and an implementer building a
credential path for a tool that cannot consume it.

### (a) WP-CLI cannot consume `--defaults-extra-file` — and ADR-0005 says so

ADR-0003's options table, for the chosen option B:

> *"Official recommendation; **works uniformly for `mysql`, `mysqldump` and WP-CLI's bootstrap**; no
> argv, no environment"*

ADR-0005, on the same page of the same decision set:

> *"`wp search-replace` has **no credential flags**. It bootstraps WordPress and uses `$wpdb`, reading
> the constants in `wp-config.php`."*

ADR-0005 is correct. `wp search-replace` runs inside PHP and connects through `$wpdb` → mysqli. It
never invokes the `mysql` client and never reads a MySQL option file. (Only the `wp db *` subcommands
shell out to the client, and those are not on this path.) Two ADRs in one directory assert opposite
facts about the same tool, and the **credentials** ADR carries the wrong one — so it is the one an
implementer building the credential adapter will act on. They will wire the transport adapter into
the WP-CLI adapter, observe that `wp` ignores it, and reach for a workaround under time pressure.

There is also a *real* consequence that neither ADR states: because WP-CLI reads `wp-config.php`,
`search-replace` operates against **whatever the config rewrite actually wrote**. If that rewrite
silently failed — and ADR-0010 documents four ways it can — `search-replace` rewrites URLs in the
**old** database. The mermaid's ordering saves this only because ADR-0010's read-back runs at step 7
and aborts before step 9; that dependency is load-bearing and currently unstated.

> **Fix:** correct ADR-0003's table — option B covers `mysql` and `mysqldump`; **WP-CLI is out of
> scope for credential transport entirely** because it takes credentials from `wp-config.php`. Add
> to AD-7: *"WP-CLI is credentialled by the config file the Run has just written and read back
> (ADR-0010); the read-back is a precondition of invoking WP-CLI, not merely a config-write check."*

### (b) `--defaults-file` is the correct flag, not `--defaults-extra-file`

`--defaults-extra-file` is read **in addition to** the standard option files — `/etc/my.cnf`,
`/etc/mysql/my.cnf`, `~/.my.cnf`. An operator (or a compromised home directory) with
`[client] host=` or `socket=` in `~/.my.cnf` silently redirects the connection. On the restore path
that means **loading a dump into the wrong database server** — a data-integrity failure, not merely
a hygiene one, and precisely the class NFR-1 exists to prevent.

`--defaults-file=<path>` causes that file to be the **only** option file read. It has the same
argv-position-1 requirement, so the change is a one-token edit with no structural cost.

> **Fix:** ADR-0003 and AD-7 specify `--defaults-file`, and the option file written by the adapter
> carries `host`, `port`, `user`, `password` and `socket` explicitly, since nothing else will supply
> them. Extend AD-7's existing test to assert no ambient option file can alter the effective
> connection target.

### (c) Crash before the `finally` leaves the password on disk indefinitely

ADR-0003 acknowledges *"a window exists where a 0600 file holds the credential."* The window is
larger than stated: a `SIGKILL` or power loss skips the `finally` **and** AD-12's workspace cleanup,
leaving a plaintext password in `/tmp/tmpXXXXXX/` with nothing that ever removes it. See Finding 6
for the general form.

> **Fix (portable, one line):** `os.unlink` the option file **immediately after the child has been
> spawned**, not in the `finally`. The client has already opened it; the inode survives for the open
> descriptor and is reclaimed by the kernel on exit. The window shrinks from the subprocess lifetime
> plus any crash to microseconds. Keep the `finally` as a belt.
>
> Stronger, Linux: `memfd_create` / an unlinked temp plus an inheritable fd, passing
> `--defaults-file=/proc/self/fd/<n>`; nothing ever reaches a persistent filesystem. Worth naming as
> the preferred path with the unlink-after-spawn fallback.

### (d) The no-POSIX-permissions response is inadequate as written

> *"on a filesystem without POSIX permissions the guarantee weakens — **detect and refuse rather than
> proceed silently**."*

Three problems. **It names no detection mechanism** — the obvious `chmod` then `stat` and compare
`st_mode & 0o777` **passes on CIFS mounts that report the requested mode while enforcing nothing**,
so the check returns a false green, which is the worst available failure mode. **Refusing is a dead
end** for an operator whose only writable temp is such a mount, and an alternative exists: the
unlinked-fd path in (c) needs no filesystem permissions at all. And **the analysis is scoped to the
option file only** — the Safety Snapshot lives outside the workspace on a *different* filesystem and
contains a complete database dump; the same question applies there and is never asked.

> **Fix:** ADR-0003 states the detection as an affirmative test — create the file `0600`, reopen it,
> and where the platform supports it confirm enforcement rather than reported mode; treat "cannot
> confirm" as "unsuitable", not as "fine". On unsuitable, fall back to the unlinked-fd transport;
> refuse only if that is also unavailable, and name why. Extend the same filesystem-suitability
> check to the Safety Snapshot destination (Finding 3b/3c), since that is the larger secret.

---

## 6. MAJOR — AD-12's `finally` does not run on SIGKILL, and nothing ever reclaims an orphaned workspace

**Blast radius:** a plaintext full database dump and a plaintext database password left on disk
permanently, after any crash. Directly contradicts NFR-3 and NFR-4.

AD-12: *"removes it in a `finally` on both success and failure."* A `finally` does not run on
`SIGKILL`, on `SIGTERM` with no handler installed (the default for `systemd` shutdown and for OOM
paths), or on power loss. What is in the workspace at that moment: the **decrypted** database dump
(Finding 2 — verification of an encrypted archive necessarily materialises plaintext), the
credential option file (Finding 5c), and staged extraction content. `mkdtemp` names are random, so
nothing can find them later; they accumulate silently until the filesystem fills.

NFR-4 — *"a failed Run leaves no state that makes a subsequent Run unsafe"* — is not met, and nothing
in AD-12 addresses reclamation.

> **Fix, into AD-12:**
> - Workspaces are created under one stable parent — `<tmp>/wpbackup2-<uid>/<run-id>/`, `0700` — so
>   they are **findable**. The Run ID is already a UUIDv4 bound at the composition root.
> - Every Run sweeps orphaned sibling workspaces whose owning process is gone. **This is the same
>   liveness check FR-28 requires for stale locks (Finding 4c)** — build it once, use it twice,
>   rather than two mechanisms with two sets of bugs.
> - `SIGTERM` and `SIGINT` are trapped at the composition root and converted into the normal cleanup
>   path. FR-28 already requires lock release *"on signal"*; no AD implements it, and the same handler
>   serves both.
> - Any file in the workspace that has held key material or plaintext database content is overwritten
>   before unlink where the filesystem makes that meaningful, and this is documented as best-effort
>   rather than claimed as erasure.

---

## 7. MAJOR — ADR-0010's read-back verification does not close the regex-parser risk; it closes the half that was already loud

**Blast radius:** a site silently pointing at the old database, or a site with `AUTH_KEY` deleted,
reported as a successful restore.

The read-back — *"re-read every constant written and assert the value round-trips"* — is the right
instinct and it does convert several blind spots into loud failures. Four classes it does **not**
catch, all reachable from ADR-0010's own documented limits:

**(a) Greedy `(.*)` collateral damage to constants we did not write.** ADR-0010 states both patterns
are greedy and *"a line carrying two `define()` calls … is not handled."* A greedy match spanning
from the target `define()` to a later one on the same line replaces the whole span — **destroying the
intervening constant.** The read-back checks only the constants it *wrote*; those round-trip fine.
The deleted `AUTH_KEY`, `DB_CHARSET` or `WP_CACHE` is never examined. This is the highest-severity
write failure in the set and it produces a clean green.

> **Fix:** the read-back compares the **full constant set** before and after. Every constant not in
> the write set must be byte-identical; the count must match. The set is enumerated from the file,
> not from a list — which is also what keeps the check's scope correct as the writer grows.

**(b) Duplicate `define()`, caught or not by a coin flip.** ADR-0010 documents that the string path
matches single-quoted values only, so a pre-existing `define("DB_NAME", "old")` is not matched. If
`set()` then *inserts* a new `define('DB_NAME','new')` rather than replacing, the file holds two.
**PHP's `define()` keeps the first and emits a notice** — so the site runs against the *old*
database. Whether the read-back catches this depends on which of the two definitions the reader's
`re.search` reaches first, i.e. on their order in the file. Sometimes caught, sometimes a silent
false pass on a site now pointed at the wrong database. A coin flip is not a mitigation.

> **Fix:** the read-back asserts **exactly one** definition of each written constant exists — count
> the matches and require 1. Trivial, and it turns the coin flip into a deterministic failure.

**(c) The read-back uses the same reader whose blind spots it is verifying.** Where the reader's
defect is *symmetric* with the writer's — both mishandle the same construct the same way — the value
round-trips through a shared misunderstanding and the check passes. (a) and (b) above are the two
instances that matter; the fixes for both are structural (set comparison, count assertion) rather
than another read through the same regex, which is the point.

**(d) Durability.** Read-back verifies content, not persistence. A pass followed by a crash before
`fsync` leaves a **zero-length `wp-config.php`** on ext4 with delayed allocation — the classic
rename-without-fsync outcome. See Finding 1(b).

**(e) The ADR's central claim is currently unsupported.** *"On mismatch, fail the restore rather than
leave a site with a half-written config."* At the moment of mismatch the config **is already
written**. Failing the restore does not un-write it. The stated benefit — *"a loud, recoverable
failure"* — requires the original to be recoverable, and no mechanism provides that.

> **Fix, one clause into ADR-0010:** the pre-write copy of `wp-config.php` is preserved in the
> workspace; on read-back mismatch it is atomically restored **before** the Run fails, and the Run
> reports that it did so. Combined with (d)'s atomic replace this makes the ADR's claim true. As
> written it is prose that overstates its own coverage.

---

## 8. MAJOR — AD-4, AD-5 and AD-11 are the invariants that map to the historical BLOCKERs, and all three are unenforced prose

The spine is unusually good about naming enforcement where it names it: AD-1 has an import-linter
contract, AD-6 derives its supported range from committed fixtures, AD-7 names its test, AD-8 and
AD-15 name CI jobs. That makes the silent ones conspicuous:

| AD | Rule | Enforcement named | Cheap mechanical check that exists |
|---|---|---|---|
| **AD-4** | *"no `if dry_run:` anywhere in `core/` or `adapters/`"* | none — *"a review rejection"* | AST scan for any branch on a name matching `dry_run`/`what_if` under those packages |
| **AD-5** | *"no function that consumes a Restore Mode may declare a default for it"* | none | `inspect.signature` over every callable whose annotation resolves to `RestoreMode`; assert `default is Parameter.empty`. **Derived from the type, not a list of functions** |
| **AD-11** | *"passes `filter='data'` explicitly on every call"* | none | AST scan for `tarfile` extraction calls; assert the keyword is present and literal |
| AD-12 | workspace per Run, cleaned | none | kill-at-step test (Finding 1) covers it |
| AD-13 | preflight before first effect | none | assert the plan's required-resource set is non-empty and consulted before any effecting adapter is called |

AD-4, AD-5 and AD-11 correspond to the arch review's B-3 (`--force` semantics), B-3 (`rmtree`) and
M-14 (`extractall`) respectively — **the three defects that destroyed data.** AD-4's rule explicitly
delegates to human review, which is the mechanism that already failed here once.

Each check above **derives its scope from the source** — the type annotation, the call site, the AST
— rather than from a hand-kept list of files or functions, so a new call site cannot be added outside
the check's reach.

> **Fix:** every AD states its enforcement in the same section as its rule, or states explicitly that
> it cannot be checked mechanically and what *is* covered. A guard test plants a violation that
> attacks the **scope** (a new module, a new adapter, a new consumer of `RestoreMode`) and asserts the
> check still fires — not only a violation of the rule inside a file the check already reads.

### Related: AD-4's no-op adapter set is defined too broadly to work

> *"A Dry Run binds recording no-op adapters that log the intended effect and return plausible
> results."*

FR-19 requires a Dry Run to *perform* Verification, credential resolution, WP-CLI availability checks
and relocation planning. If the `ArchiveStore` is a no-op, **Verification cannot read the archive**,
and the Dry Run's most valuable check becomes vacuous — returning a "plausible result" for a
verification that did not happen is a false green about whether a real restore would be safe. The
distinction the design needs is **read ports versus effecting ports**, and the spine never draws it.
Get it wrong in one direction and Dry Run is destructive; in the other, it validates nothing.

> **Fix:** `ports/` classifies each Protocol as read-only or effecting — an effecting port inherits a
> marker base. Only effecting ports acquire no-op adapters. A test asserts every port carries a
> classification (iterating the module, not a list), and that the Dry Run adapter set no-ops exactly
> the effecting ones.

---

## 9. MAJOR — Restoring from an untrusted Storage Target is remote code execution by design, and AD-11 reads as if it covers this

AD-11 is titled *"An Archive is untrusted input"* and its mechanism is `filter='data'` plus a
containment re-check — which prevents an archive from writing **outside** the destination. It does
nothing about what an archive writes **inside** the destination, and the destination is a directory
from which a web server executes PHP. An archive that passes Verification and extracts perfectly
safely can contain `wp-content/plugins/x/x.php` with arbitrary code.

For an *encrypted* archive the AEAD makes this a non-issue: producing one requires the passphrase.
For an unencrypted archive from a shared bucket, an over-broad S3 write policy, or a file an operator
downloaded, it is a direct path from "write access to the backup store" to "code execution on every
site restored from it" — and Finding 2(f) means Verification will not notice, and Finding 2(d)'s
nonce-reuse break extends it to encrypted archives too.

This is not boilerplate: the spine's verification step is drawn in the sequence diagram with a
`pass / fail` gate that reads like a trust boundary, and it is not one.

> **Fix:** AD-11 states its actual reach — *containment, not authenticity* — and points at AD-6 for
> the authenticity property. Restoring an unencrypted Archive from a Storage Target not marked
> trusted requires an explicit acknowledgement, in the same shape as FR-7's per-destruction
> authorization.

---

## 10. MAJOR — No invariant states that a reported success must be derived from recorded step outcomes

This is the uncovered half of historical BLOCKER B-3. The `restore_mode` plumbing defect (closed by
AD-5) was the cause; the *symptom that made it lethal* was separate — a guard named "delete database
before restore" took an early `return` and the Run **logged success and exited 0** having restored
nothing. The same family produced M-16: `run_from_cli` returned `-1` and the value was discarded, so
the process exited 0 on a failure path.

FR-9 names the requirement — *"It never reports success without having restored"* — and the
capability map routes FR-9 to AD-5, AD-12 and NFR-1. None of them says anything about outcome
reporting. The spine has no invariant that outcome is computed rather than assumed, and the
architecture that would make it structural is already present and unused: **the core produces a plan
value.**

> **Fix — new AD-18, "Outcome is computed from the plan, never from reaching the end":**
>
> Every step in a plan produces a typed outcome — `performed`, `skipped(reason)`, or `failed(cause)`.
> The Run's exit code and its operator-facing summary are **derived from the collection of outcomes**,
> not from control flow reaching the end of a function. A planned step with no recorded outcome is a
> failure, not a success. A step recorded `skipped` whose Restore Mode named it is a failure.
>
> *Enforcement:* the plan is a value, so the core can assert totality — every planned step has exactly
> one outcome — as a pure unit test with no live MySQL, satisfying NFR-8. The step set is iterated
> from the plan, so a new step cannot escape the assertion.

---

## 11. MAJOR — `filter='data'` will reject legitimate WordPress sites, at restore time

`tarfile`'s `data` filter rejects absolute paths, links escaping the destination, device nodes, and
setuid/setgid bits, and by default **raises on the first rejected member**. A very common WordPress
deployment has `wp-content/uploads` as a symlink to a separate data volume — outside the Site Root.

The backup stores the symlink happily. The restore refuses it — **at restore time**, which is the
worst possible moment to discover an archive is unrestorable, and precisely the failure PRD §8 calls
*"the product's central failure."* The archive is not corrupt; it was never restorable, and nothing
said so for the months the operator held it.

> **Fix, into AD-6 and AD-11:** the archive **writer** validates every member against the same filter
> policy the reader will apply, and fails the backup — loudly, naming the member — rather than
> producing an Archive that cannot be restored. Where a link is legitimate and intended, the operator
> resolves it explicitly (follow it, or exclude it under FR-5) at backup time.
>
> *Enforcement:* one shared policy function used by both sides — AD-6's *"one module owns the
> format"* already gives it a home — and a fixture archive containing each rejected member class,
> asserted to fail at write. The class list is derived from the filter's own behaviour, not
> hand-enumerated.

---

## 12. MEDIUM — AD-13's preflight covers external tools only; disk space and database privileges are the same defect class

AD-13's own justification is: *"Prevents a partial relocation — config rewritten, content URLs not —
because WP-CLI was discovered missing halfway through."* Identical reasoning applies to two resources
it does not cover:

- **Free space.** A restore extracting a 40 GB archive onto a filesystem with 30 GB free produces
  Finding 1's chimeric site. Loading a dump onto a full disk can leave a corrupted InnoDB tablespace.
  Writing the Safety Snapshot onto a full disk at least fails safely (FR-8 refuses) — the one case
  that works, by accident.
- **Database privileges.** FR-9 requires the restore to *"ensure the target database and user exist
  before loading"*, and AD-9 correctly removes the silent admin-credential fallback. But if the
  supplied admin credential lacks `CREATE`/`DROP`, that is discovered when `mysql` fails partway
  through — after the snapshot, after the extraction, after `wp-config.php` was rewritten.

Both are knowable before the first destructive step, and both are cheap: the Manifest already carries
per-member data, so total uncompressed size is derivable rather than guessed; a privilege check is
one `SHOW GRANTS`.

> **Fix:** widen AD-13 from *"external tools"* to **"every resource the plan requires"** — tools and
> versions, free space on the Site Root filesystem, on the workspace, and at the snapshot destination,
> database connectivity and the specific privileges the plan's steps need, and (for Finding 1c's
> staging strategy) whether the staging directory is on the same device as the Site Root.
>
> *Enforcement:* the plan declares its required resources as data; preflight iterates that
> declaration. A new step that needs a resource declares it, and the check reaches it without being
> edited — scope derived from the plan, not from a list in the preflight module.

---

## 13. MEDIUM — Verification of an encrypted Archive costs a full decryption pass, and NFR-7's 1.5× bound makes safety the thing that gets cut

Answering the ordering question directly: **verification of an encrypted archive before decryption
is not possible**, and the ordering in AD-6/AD-11 still holds, but not for free.

- AES-GCM authenticates each chunk *as it is decrypted*. Detecting truncation, reordering or chunk
  corruption therefore requires streaming and decrypting the entire archive.
- The Manifest's per-member checksums are over **plaintext** members, so verifying them requires the
  decrypted tar stream, not merely the ciphertext.
- FR-3 requires detecting *"a missing Dump inside an Archive whose Manifest declares one"* — a
  semantic property of the tar index, reachable only after decryption.

So verification is a full decrypt-and-discard pass, and extraction is a **second** full pass. For an
archive on S3 that is two downloads unless the first pass materialises plaintext in the workspace —
which requires workspace capacity equal to the uncompressed site (Finding 12) and leaves a plaintext
database dump for Finding 6 to lose on a crash.

Now count the restore against NFR-7's *"no more than 1.5× the baseline wall-clock"* of a bare
`mysqldump` plus `tar`:

    verification pass (full decrypt)  +  Safety Snapshot (a complete backup, dump + tar)
      +  extraction  +  dump load  +  search-replace

That is comfortably 3× baseline and structurally cannot be 1.5×. NFR-7 is stated for *"a wpbackup2
Run"* without distinguishing backup from restore, so as written it is unachievable on the restore
path — and the way an engineer under a failing performance gate makes it pass is by removing the
verification pass or the snapshot.

The PRD anticipated this exactly once, as counter-metric **SM-C1**: *"Restore speed must not be
optimized at the expense of Verification or the Safety Snapshot. A slower restore that cannot destroy
a site is the correct trade."* The counter-metric is right and the NFR contradicts it.

> **Fix:** NFR-7's 1.5× bound is scoped to the **backup** path. The restore path gets its own stated
> envelope that names its passes — verification, snapshot, extraction, load — as deliberate costs, so
> the number a future CI gate asserts is a number that includes the safety machinery rather than one
> that indicts it. AD-6 states that verification of an encrypted Archive materialises plaintext in the
> workspace, which makes Finding 12's space check and Finding 6's reclamation both mandatory rather
> than nice-to-have.

---

## 14. MEDIUM — FR-10's legacy no-Manifest path bypasses every safety property and no AD constrains it

AD-6: *"A Manifest is written on every Archive and read before every restore."*
FR-10: *"An Archive with no Manifest is refused **unless the operator opts into a documented legacy
path**."*

The legacy path is a restore with no format gate, no per-member checksums, no verification and — for
an unencrypted legacy tarball — no authenticity whatever. It is the pre-rewrite archive format, so
the archives that will actually travel this path are the ones written by the v0.2.21 code the arch
review condemned. Nothing in the spine bounds it.

> **Fix:** AD-6 states the legacy path's terms: a Safety Snapshot is mandatory and not opt-out-able
> on it; it may not be combined with any `-clean` mode (no destruction is authorized for content that
> cannot be verified); extraction still goes through AD-11's single function; and the Run's summary
> records that verification was skipped, in the journal from Finding 1 as well as the log.

---

## 15. MINOR — The backup side has no consistency invariant, so a verified Archive can be internally torn

Not a restore defect, but it lands as one. Nothing in the spine or the ADRs requires
`mysqldump --single-transaction`. Against a live site, a multi-minute dump without it reads
`wp_posts` at 03:00:01 and `wp_postmeta` at 03:04:00 — the resulting dump is internally inconsistent,
passes Verification perfectly (the checksums describe exactly the bytes that were written), and
produces a broken site on restore. NFR-1 is measured at restore, but it is *caused* here.

Similarly, the ordering of the database dump relative to the file tar is unspecified. Dump first,
then files, means the files are a superset of what the database references — a post referencing an
upload that exists. Files first, then dump, means the database can reference uploads the archive does
not contain: missing media, the recoverable direction being the other one.

> **Fix:** AD-6 or a short ADR-0011 records both — `--single-transaction` (with the MyISAM caveat
> stated, since it does not apply there and that is worth an operator warning), and dump-then-files
> ordering with the reason. A test asserts the flag reaches the constructed argument vector, in the
> same shape as AD-7's existing argv assertion.

---

## Summary of proposed changes

| # | Change | Where |
|---|---|---|
| 1 | **New AD-16** — durable Run Journal; `--resume` / `--rollback`; kill-at-each-step test | spine |
| 1b | Atomic `wp-config.php` write (temp + fsync + replace + dir fsync) | AD-3 / ADR-0010 |
| 1c | Database restored into a staging database, cut over by the atomic config write | AD-5 / ADR-0011 |
| 2 | Three-layer envelope; `is_final` framing not total-count; per-archive salt, nonce prefix and `archive_id` in AAD; key commitment; integrity ≠ authenticity stated | **ADR-0006 rewrite**, AD-6 |
| 3 | Snapshot verified via FR-3's path before promotion; encryption mandatory or explicit opt-out; never under the Site Root; scope computed from the plan; abort edge added to the diagram | AD-12 / FR-8 |
| 4 | **New AD-17** — Site-identity lock: `flock`, outside Site Root and workspace, stale reclaim, per-host bound stated. Storage-target: `.partial` promotion, retention never deletes the last verified Archive | spine, AD-6 |
| 5 | ADR-0003: WP-CLI claim corrected; `--defaults-file`; unlink-after-spawn / `/proc/self/fd`; affirmative permission detection extended to the snapshot destination | ADR-0003, AD-7 |
| 6 | Findable workspace parent, orphan sweep sharing FR-28's liveness check, signal handlers | AD-12 |
| 7 | Read-back: full-set comparison, exactly-one-definition assertion, pre-write copy restored on mismatch | ADR-0010 |
| 8 | Enforcement named in AD-4, AD-5, AD-11, AD-13; read vs effecting port classification for Dry Run | spine, several ADs |
| 9 | AD-11's reach stated; untrusted-store restore requires explicit acknowledgement | AD-11 |
| 10 | **New AD-18** — outcome computed from plan step outcomes; totality asserted | spine |
| 11 | Archive writer validates members against the reader's filter policy | AD-6, AD-11 |
| 12 | AD-13 widened from tools to all plan-required resources, declared as plan data | AD-13 |
| 13 | NFR-7's 1.5× scoped to backup; restore envelope names its passes | PRD NFR-7, AD-6 |
| 14 | Legacy no-Manifest path bounded: snapshot mandatory, no `-clean` | AD-6 |
| 15 | `mysqldump --single-transaction`; dump-then-files ordering recorded | AD-6 / ADR-0011 |

---

*Findings 1, 2, 3 and 4 are blocking: each is a path to an unrecoverable production WordPress site or
an unusable Archive, and each is reachable through the design as currently written rather than through
an implementation mistake.*
