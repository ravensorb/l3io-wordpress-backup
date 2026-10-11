---
lens: adversarial-divergence
run: delta (second pass)
target: ARCHITECTURE-SPINE.md (wpbackup2 family, 24 ADs, updated 2026-09-16)
supporting: docs/adr/0001..0011; prd.md §5, §7, §8; wpbackup2/__main__.py @ 01ee58c
prior: reviews/review-adversarial-divergence.md (14 pairs, D-1..D-14)
date: 2026-09-16
verdict: 'SPINE INCOMPLETE — 18 NEW divergence pairs; 4 of the prior 14 fixes do not close what they claim and 3 more close only half; 6 new pairs are release-blocking'
---

# Adversarial Divergence Review — DELTA

**Method, unchanged.** For each pair of plausible implementation units one level below the
spine, construct a scenario where both obey every AD *literally* and still emit code that
does not compose. Only divergence pairs are reported.

**Two jobs this pass.** Part 1 verifies that AD-16..AD-21 and the AD-3/4/6/10/12/13
tightenings actually close D-1..D-14. Part 2 attacks the delta — AD-22, AD-23, AD-24, the
AD-6 "Reading v0" paragraph and the AD-10 amendment.

**Result.** Part 1: seven of fourteen fully closed, three half-closed, **four not closed at
all** — and one prior fix was applied to an ADR and never propagated to the AD it
contradicts, which is worse than not fixing it, because the spine now states the corrected
decision's *opposite* under an "ADOPTED" heading. Part 2: **18 new pairs.** E-1 through E-6
are release-blocking: each produces a defect whose first observation is in production, on
the restore path, against an operator's only copy of their data.

---

# Part 1 — Do the prior fixes close what they claim?

| Prior | Closing AD claimed | Status | What is still open |
|---|---|---|---|
| D-1 Manifest in/out of envelope | AD-6 tighten | **CLOSED** | — (AD-6 ¶2 and ADR-0006 agree: first member, never encrypted) |
| D-2 Snapshot forks the Run | new AD-16 | **CLOSED** | — |
| D-3 Order lives in a diagram | new AD-17 | **CLOSED** | test scope is per-Mode, not per-Mode × archive-version → **E-3** |
| D-4 No-op adapters describe two worlds | AD-4 tighten | **HALF** | query/command split landed; the **anti-fabrication rule did not** — "derived from the real pre-state, or a `NotPerformed` sentinel" is absent from AD-4. That omission is what makes **E-8** constructible |
| D-5 FR-29 config vs containment | AD-6 tighten | **CLOSED for v1** | v0 has no `config` role and no metadata slot → **E-17** |
| D-6 Site Descriptor field set | AD-3 tighten | **NOT CLOSED** | AD-3 is verbatim unchanged. No field list, no nullability, no `db_port: int \| None`, no `field_sources`, no ruling that `WpConnection` is a projection rather than a peer. The entire proposed closing text was dropped |
| D-7 Exit-code table has no owner | new AD-18 | **NOT CLOSED** | Spine AD-18 is *recoverability*. The exit-code proposal survives only as a Capability-map cell — `FR-21 exit codes \| domain/exit_codes, cli/ \| AD-14`. No `ExitCode` enum owner, no MRO walk, no reflection-derived guard. **Renumbering collision**: three proposed ADs (18/20/21) were given to different content, and their proposals were not re-homed |
| D-8 Preflight covers binaries only | AD-13 tighten | **NOT CLOSED** | AD-13 still reads "every external binary (`mysqldump`, `mysql`, `wp`)". No optional-distribution probe, no Storage-Target reachability, no `CapabilityStatus`, no Protocol-registry-derived guard |
| D-9 Snapshot destination | AD-12 tighten | **CLOSED** | — |
| D-10 Site Lock home and key | new AD-19 | **CLOSED** | exit code for a conflict is unowned → **E-9** |
| D-11 wpconfigr zero-deps vs one logger | AD-10 tighten | **NOT CLOSED** | AD-10 still says "**Binds:** … all three packages" and "structlog over stdlib logging". AD-2 still says wpconfigr declares **zero** runtime dependencies, permanently. The two ADs contradict each other in the same document. The proposed stdlib-only carve-out, the `foreign_pre_chain` beginning with `merge_contextvars`, and the shared verbosity table are all absent. This is a *live, unmodified* contradiction, not a new one — re-reported here only because the fix was claimed |
| D-12 Two provisioning owners | new AD-20 | **HALF** | Deferred §5 now names `wpdatabase2` as sole owner ✅. But **AD-7 was not extended to in-process drivers** — it still describes an option file and `argv`, and its test still asserts "against a constructed argument vector", so PyMySQL's `connect(password=…)` is outside the guard's scope. Collation-from-Manifest and the declared grant list are absent |
| D-13 Storage addressing + Archive naming | new AD-21 | **HALF** | Deferred §1 un-defers the *grammar* ✅. No `StorageTarget` parser owner, no naming function, no round-trip property test, and no "retention derives age from the Manifest, never from the object name". Now **worse than when it was deferred**: `--archive` is `default=None` in the frozen CLI, so the auto-generated Archive name is an *observable, frozen* behaviour |
| D-14 Clock vs structlog timestamps | AD-4 tighten + AD-10 | **HALF** | Clock is a port and AD-4 makes it a query, so the mechanism is right by construction. The AD-10 sentence ("log timestamps come from the same Clock") and the one-notion-of-now tolerance test were not added |

## V-1 — The one fix that was applied backwards

**ADR-0003 was corrected. AD-7 was not.** The memlog records:

> `(change) ADR-0003 CORRECTED: --defaults-extra-file is ADDITIVE, so an ambient ~/.my.cnf
> can redirect a restore to the wrong database server. Changed to --defaults-file. Also
> removed the false claim that it works for WP-CLI`

ADR-0003 now reads "`--defaults-file=<path>` **before any other option**" and "**This
mechanism does not extend to WP-CLI.**"

AD-7 still reads, unchanged: "passes it as **`--defaults-extra-file` in argv position 1**"
and "**Binds:** … every MySQL and **WP-CLI** invocation."

This is not a stale cross-reference; it is the spine asserting the exact behaviour the ADR
was corrected *away from*, under a heading a builder is told is normative. It generates a
divergence pair on its own and is reported as **E-2**.

---

# Part 2 — New divergence pairs

**Summary table.** Rank = (likelihood the divergence actually happens) × (cost of
discovering it late).

| # | Divergence | Units | Rank | Closing AD |
|---|---|---|---|---|
| E-1 | `--cleanfirst` × `--force` × `--mode` → RestoreMode is an unowned function | CLI epic / restore epic | 1 | **new AD-25** |
| E-2 | AD-7 says `--defaults-extra-file` and binds WP-CLI; ADR-0003 says neither | sql adapter / wpcli adapter | 2 | **AD-7 rewrite** |
| E-3 | A v0 Archive has no Manifest, no roles, no checksums — AD-6/11/17/21 each read two ways | archive-format epic / restore epic | 3 | **AD-23 tighten** |
| E-4 | AD-23 puts detection in `domain/`; AD-1's CI gate forbids `tarfile` there | domain author / tar adapter | 4 | **AD-23 tighten** |
| E-5 | Safety Snapshot encryption has no configuration surface on the frozen CLI | CLI epic / restore epic | 5 | **new AD-26** |
| E-6 | Two redaction implementations; AD-7's guard scope sees only logs | logging epic / tracing epic | 6 | **AD-7 + AD-24 tighten** |
| E-7 | `--whatIf` is top-level; re-declaring it per-subcommand clobbers Dry Run to `False` | CLI epic / compat-test author | 7 | **AD-22 tighten** |
| E-8 | Spans in a Dry Run: is `Tracer` a query port or a command port? | tracing epic / dry-run epic | 8 | **AD-24 tighten** |
| E-9 | Exit codes for lock conflict, stale journal, retired flag are unowned | lock adapter / CLI epic | 9 | **new AD-27** (re-homes D-7) |
| E-10 | The Run Journal's directory is defined relative to a Snapshot that may not exist | restore epic / journal author | 10 | **AD-18 tighten** |
| E-11 | Snapshot inside the ArchiveStore or beside it → retention prunes the last real backup | restore epic / retention epic | 11 | **AD-12 + AD-20 tighten** |
| E-12 | `--mode {files,db,all}` vs FR-6's six-name table and its mechanical round-trip guard | CLI epic / domain author | 12 | fold into **AD-25** |
| E-13 | FR-10 "refused unless opted in" vs AD-6/AD-23 "read by default, permanently" | restore epic / PRD-conformance test author | 13 | **AD-23 tighten** + PRD reconcile |
| E-14 | `--log-level` default `CRITICAL` makes AD-24's jq-and-a-log-file promise emit nothing | CLI epic / observability epic | 14 | **AD-22 + AD-10 tighten** |
| E-15 | "A Run Context is already active" — process-, thread-, or context-scoped? | api epic / cli epic | 15 | **AD-16 tighten** |
| E-16 | Is a v1 Archive gzipped? `.tar.gz` in frozen help vs AD-6's "tar container" | backup epic / detection author | 16 | **AD-6 tighten** |
| E-17 | v0 + FR-29: no `config` member, no metadata, and AD-3 forbids re-deriving the path | restore epic / config-writer author | 17 | fold into **AD-23** |
| E-18 | AD-6's fixture-derived *version range* cannot express v0, which has no version field | CI gate author / archive-format epic | 18 | fold into **AD-23** |

---

## E-1 — `--cleanfirst`, `--force` and `--mode` compose into twelve CLI states and nothing owns the function that maps them onto six Restore Modes

**Rank 1.** Likelihood: certain — the mapping must be written by someone and no AD contains
it. Cost: this is the B-3 data-loss defect re-entering through the one seam the rewrite
declared frozen. First observation is an emptied Site Root.

### The two units

- **Unit A — the CLI epic**, which owns `cli/` and reads AD-22 as its specification.
- **Unit B — the restore epic**, which owns `core/restore` and reads AD-5 and FR-6/FR-7.

### How both comply

AD-5 defines Restore Mode as "an explicitly enumerated, closed set… defined once in
`domain/`… resolved at the composition root". FR-6 fixes the six members. AD-22 fixes the
flags and says what each *means*:

> `--cleanfirst` selects the clean Restore Mode flags rather than being ignored; `--force`
> overrides the non-empty-target refusal (FR-7) rather than being the only way to reach
> clean mode

Both units obey every word. Neither document contains the **function**. The observable
input space is `--mode ∈ {files, db, all}` × `--cleanfirst ∈ {0,1}` × `--force ∈ {0,1}` —
twelve states — and the output space is six Restore Modes crossed with a refusal-override
boolean. Nothing declares the map, and nothing declares that a map is required.

### The incompatibility, concretely

Take one command line, which is a plausible cron entry:

```
python -m wpbackup2 restore --wp-dir /srv/site --archive b.tar.gz --cleanfirst
```

against a Site Root containing files.

- **Unit A** reasons from FR-7: "Restoring into a non-empty Site Root without explicit
  authorization exits non-zero… and **names the flag that would authorize it**." The flag
  that names that specific destruction is `--cleanfirst` — AD-5 says "A destructive element
  is authorized only by the flag that names that specific destruction." So `--cleanfirst`
  *is* the authorization. Mode `all-clean`, proceed. **`rmtree` runs.**
- **Unit B** reasons from AD-22: `--cleanfirst` **selects the mode**, `--force` **overrides
  the refusal** — two sentences, two flags, two jobs. So `--cleanfirst` alone selects
  `all-clean` and then FR-7's refusal fires against the non-empty target, unoverridden.
  **Exit non-zero, nothing changed.**

One unit destroys, the other refuses, on identical input, both quoting the spine.

Now the other diagonal:

```
python -m wpbackup2 restore --wp-dir /srv/site --archive b.tar.gz --force
```

- **Unit A** maps `--force` to mode `all` with the refusal suppressed: overwrite in place,
  nothing dropped.
- **Unit B** reads AD-22's "rather than being the only way to reach clean mode" as saying
  `--force` still reaches clean mode *among other things* — preserving observed behaviour
  (`WpRestoreMode.ALLCLEAN if args.force else ALLOVERWRITE`) under the "preserve intent"
  half of AD-22, since the shipped `--force` demonstrably meant ALLCLEAN. **Drops the
  database.**

That second reading is the one PRD §7.1 explicitly forbids — "a single option that
authorizes all destruction at once" — and AD-22's own sentence is ambiguous enough to
license it. It is also exactly what arch-review B-3 recorded.

Third: `--mode files --cleanfirst`. Unit A clears the Site Root only (`files-clean`). Unit B
preserves the legacy `ALLCLEAN` semantics of "removes existing files/db" from the flag's own
help text and **drops the database during a files-only restore**.

### Closing AD

> **New AD-25 — The CLI-to-Restore-Mode map is a total function, declared as data, and the
> override is not a mode.**
> `domain/` holds one table mapping every element of the CLI's declared input space —
> the Cartesian product of `--mode`'s `choices` and the boolean restore flags — to a
> `(RestoreMode, OverrideSet)` pair. **`OverrideSet` is a distinct type from `RestoreMode`**,
> so no flag can both select a destruction and authorize it, and `--force` is structurally
> incapable of selecting a mode. The table is **total**: a combination with no sensible
> meaning maps to a named `UsageError`, never to a fallthrough default. AD-5's
> no-default rule extends to `OverrideSet`.
> **Enforcement:** a test that enumerates the input space **by reflection over the argparse
> parser's own `choices` and `store_true` actions** — never a hand-written list — and
> asserts every element resolves to exactly one `(RestoreMode, OverrideSet)` or one named
> `UsageError`. Scope-attack fixture: add a fourth `--mode` choice to the parser and assert
> the guard fails until the table is extended. Second guard: assert that
> `--cleanfirst` alone against a non-empty target and `--force` alone against a non-empty
> target produce the two *different* documented outcomes, so neither collapses into the
> other.

---

## E-2 — AD-7 mandates the option-file flag ADR-0003 was corrected away from, and binds it to a tool that cannot read it

**Rank 2.** Likelihood: certain for the WP-CLI half (a builder implementing AD-7's Binds
line will write it); high for the flag half. Cost: a restore that loads a Dump into the
**wrong database server**, silently, because an ambient `~/.my.cnf` carried a `[client]
host=`. That is unrecoverable and looks like success.

### The two units

- **Unit A — the SQL adapter author**, implementing AD-7 from the spine.
- **Unit B — the WP-CLI adapter author**, implementing relocation from ADR-0005/ADR-0003.

### How both comply

AD-7's rule, current text: "passes it as **`--defaults-extra-file` in argv position 1**
(MySQL requires it first)". AD-7's Binds line: "every MySQL **and WP-CLI** invocation."

ADR-0003's decision, current text: "**Option B, using `--defaults-file` — not
`--defaults-extra-file`**… `--defaults-extra-file` is **additive**: an ambient `~/.my.cnf`
or `/etc/my.cnf` still applies and can carry a `[client] host=` that redirects a restore to
a different database server — silently, and at the worst possible moment." And: "**This
mechanism does not extend to WP-CLI.** `wp search-replace` bootstraps PHP and uses `$wpdb`."

Unit A follows the AD. Unit B follows the ADR. Both are following the documents they were
told are normative.

### The incompatibility, concretely

1. **Two flags.** Unit A emits `mysql --defaults-extra-file=/run/ws/opt.cnf …`. Unit B, if
   it ever touches the SQL path, emits `--defaults-file=`. AD-7's test — "asserts both
   properties against a constructed argument vector" — is written by whichever unit lands
   first and then *pins the wrong one*, and the guard reports green forever. The difference
   is invisible in CI (no ambient `my.cnf` on a runner) and visible only on an operator's
   host that has one.

2. **A tool that takes no option file.** Unit A, reading "every MySQL and WP-CLI invocation",
   writes the credential file and passes it to `wp search-replace`. WP-CLI does not read it.
   Best case it is ignored and the credentials come from the config we just rewrote —
   meaning AD-7's *guarantee* over the WP-CLI path is prose with no mechanism behind it.
   Worse case, the argv-redaction test now enumerates a `wp` invocation as a
   credential-bearing call site and a later author, seeing no credential there, removes the
   redaction wrapper from the `wp` adapter.

3. **Position.** AD-7 says "argv position 1". ADR-0003 says "before any other option" —
   which for `python -m wpbackup2`'s eventual subprocess is not the same claim, and only one
   of them is mechanically checkable.

### Closing AD

> **Rewrite AD-7** to match its own ADR, and record in the AD body that it was corrected:
> the flag is **`--defaults-file`** (replaces the option-file chain; `--defaults-extra-file`
> is additive and an ambient `my.cnf` can redirect the connection), it is **the first
> option in argv**, and AD-7's **Binds line drops WP-CLI**. Add the sentence ADR-0003
> already carries: *WP-CLI receives no credential from us; it bootstraps from the
> `wp-config.php` written in `REWRITE_CONFIG`, which is why AD-17 orders those two phases.*
> **Extend the scope, per D-12's unclosed half:** AD-7 binds *every path that transports a
> credential to a database engine — subprocess argv, option file, or in-process driver
> keyword argument*. **Enforcement:** the guard's scope is **derived from the set of classes
> implementing `SqlClient` and `CredentialProvider`**, not from a list of subprocess call
> sites; planted-violation test adds a `SqlClient` that passes a password as a driver kwarg
> and asserts the guard fails.
> **Add a spine-level guard for the class of defect:** a CI check asserting that every
> literal option flag named in an AD body appears in the ADR it cites, and vice versa —
> because this pass found a corrected ADR and an uncorrected AD living three directories
> apart, and only a mechanical check finds the next one.

---

## E-3 — A v0 Archive has no Manifest, so four ADs that reference Manifest data have two readings each

**Rank 3.** Likelihood: certain — every one of these is a decision a builder must make in
week one. Cost: either v0 archives are unrestorable (the headline promise of the rewrite
mandate, broken) or the containment and verification guarantees silently do not apply to the
format operators actually hold on disk.

### The two units

- **Unit A — the archive-format epic**, owning `domain/archive_format` and AD-23.
- **Unit B — the restore epic**, owning `core/restore` and the phase pipeline.

### How both comply

AD-23 is clear that v0 exists and is read forever. AD-6's amended paragraph says Verification
"degrades to a structural check". Neither document says what *shape* the rest of the system
receives for a v0 Archive. So four ADs, all unamended, keep asserting things about a Manifest
that is not there:

| AD | Text, unchanged | v0 reality |
|---|---|---|
| AD-6 ¶4 | "A Manifest is written on every Archive and **read before every restore**" | there is none to read — and this sentence sits **two paragraphs below** the one saying v0 is read by default, in the same AD |
| AD-11 | "Containment is re-checked after member-path rewriting, **against the enumerated roles of AD-6**" | v0 members are `database.sql` and `wp-root/` — no role prefix exists to check |
| AD-17 | phase enum includes `VERIFY`; "a Restore Mode may omit phases"; test "asserts the phase sequence **for every Restore Mode**" | is `VERIFY` omitted, or present-and-degraded? The *Mode* does not determine it — the *archive version* does, and the guard's scope is Modes |
| AD-21 | "every port that moves Archive bytes exposes a chunked or file-object interface" | v0 is a `.tar.gz`; a gzip member stream is sequential-only, so a v0 "seek to member" implementation buffers or re-reads |

### The incompatibility, concretely

**Roles.** Unit A returns a raw `format=v0` verdict from `domain/` and leaves normalization
to the caller. Unit B, in the tar adapter, synthesizes roles at extraction time:
`database.sql → dump`, `wp-root/ → site-root`. Unit A, in `core/`, also needs roles to build
the plan, and synthesizes its own — with `wp-root` mapping to `site-root` in one and
`wp-root/` (trailing slash, a distinct tar member name) in the other. AD-11's containment
check then runs against a role set the planning half did not produce, and either refuses a
valid archive or passes a member the plan never authorized. This is `DB_DUMP_ARCNAME`
duplicated in two modules — the literal defect AD-6 was written to kill — reintroduced under
a version the AD forgot to cover.

**Verification.** Unit B implements AD-6 ¶4 literally and refuses every manifest-less
Archive. Unit A implements AD-6's v0 paragraph. Both cite AD-6.

**Phase sequence.** Unit A omits `VERIFY` from a v0 plan (nothing to verify). Unit B keeps
`VERIFY` and degrades it. AD-17's test now has two legal answers for `RestoreMode.all`, and
because its scope is derived from the Restore Mode enum, **the fixture set contains no v0
Archive at all** and the guard passes either way. The guard proves the rule over a set that
does not contain the case that matters — the project's own §4 failure mode.

**Streaming.** Unit A reads a v0 `.tar.gz` by `tarfile.open(mode='r|gz')` — true streaming,
one pass, members in file order. Unit B needs the dump *after* the site root (AD-17 puts
`EXTRACT` before `LOAD_DUMP`) and so opens `r:gz`, which seeks, which for gzip means
decompressing from the start again — or buffering. On a 40 GB archive Unit B's
implementation either doubles the wall clock or blows NFR-7's RSS bound. AD-21's CI
assertion is against "a fixture Archive" — singular, and v1.

### Closing AD

> **Tighten AD-23 — detection returns a normalized Archive View; nothing downstream sees a
> version.**
> The detection function's return value is an **`ArchiveView`**: a frozen value carrying the
> format version, an ordered member index, a **role for every member** (synthesized for v0
> by the one mapping declared in `domain/`), a per-member `checksum: str | None`, a
> `config_location: Path | None`, and an **`integrity: VERIFIED | STRUCTURAL_ONLY`**
> discriminator. **No module outside `domain/archive_format` branches on the format
> version** — they branch on `integrity` and on `checksum is None`, both of which are
> total. AD-6's "a Manifest is read before every restore" becomes "an `ArchiveView` is
> constructed before every restore".
> `VERIFY` is **never omitted from a plan**; it consumes the `integrity` discriminator and
> reports which guarantee it made. A restore whose `integrity` is `STRUCTURAL_ONLY` states
> so in the Run's logs, in the Safety Snapshot's Manifest, and on stderr.
> **Enforcement:** (1) a `grep`/AST gate failing on any `format_version` or `== "v0"`
> comparison outside `domain/archive_format`; (2) the AD-17 phase-sequence fixture set is
> derived from **RestoreMode × {v0 fixture, v1 fixture}**, not from RestoreMode alone —
> scope attack: delete the v0 fixture and assert the derived matrix shrinks and the guard
> reports it; (3) AD-21's RSS assertion runs against an oversized **v0** fixture as well as
> a v1 one, because the gzip seek trap exists only in v0; (4) AD-11's traversal fixture is
> built in **both** formats.

---

## E-4 — AD-23 puts format detection in `domain/`, and AD-1's CI gate forbids `domain/` the only library that can do it

**Rank 4.** Likelihood: certain — it is a mechanical contradiction between two enforced
rules, so the first builder hits it on day one. Cost: the escape route a builder takes is to
hand-write a tar header parser, which is a 512-byte-field binary format parser in the layer
with the least test tooling, and it is the exact failure this project's own engineering
standards were written from.

### The two units

- **Unit A — the `domain/` author**, implementing AD-23's "detection happens in one function
  in `domain/`, by inspection".
- **Unit B — the tar adapter author**, implementing AD-11's "one extraction function in
  `adapters/`".

### How both comply

AD-23: "format detection happens in one function in `domain/`, by inspection, before any
other read: a first member named `manifest.json` means v1… Detection is never inferred from
filename or extension."

AD-1's enforcement: "an import-linter `forbidden` contract in CI covers the *module*
prohibitions — `subprocess`, `socket`, `shutil`, **`tarfile`**, `boto3` … and the
inward-facing layer rule."

So: `domain/` must inspect a tar's first member, and `domain/` may not import `tarfile`. It
also may not `open()` the file — AD-1's AST check covers builtins precisely so that
`open()` in `core/`/`domain/` fails.

### The incompatibility, concretely

- **Unit A** takes AD-23 at its word and writes a pure function that reads the first 512
  bytes of a tar header out of a `bytes` argument, parses the name field (offset 0, 100
  bytes, NUL-padded), handles the `ustar` prefix field at offset 345 for long names, handles
  the GNU `L` long-name extension, handles gzip framing because v0 is `.tar.gz`… This is a
  hand-rolled parser for a binary container format, it will be ~150 lines before it handles
  PAX, and its defects present as "your backup is unrecognised" — which for a backup tool is
  the worst string it can print. It is also the specific thing the project's standards
  forbid without an ADR naming evaluated libraries, and the library in question is in the
  standard library.
- **Unit B** takes AD-1's gate at its word, concludes detection *cannot* live in `domain/`,
  and puts it in `adapters/tar` where `tarfile` is legal. Now there are two detection
  functions, or one in a layer AD-23 says it must not be in, and AD-23's entire purpose —
  "**one** function, so two units cannot disagree on how a format is recognised" — is
  defeated by the AD that mandates it.

Either way the first builder must choose, silently, and the CI gate makes Unit B's choice
fail an import-linter contract while Unit A's choice passes it.

### Closing AD

> **Tighten AD-23 — split detection into a probe and a classifier, and say which half is
> where.**
> An **`ArchiveProbe` port**, satisfied in `adapters/`, opens the container with `tarfile`
> and returns a **pure probe value**: the first N member names and sizes, the compression
> framing, and the bytes of `manifest.json` if the first member is named that. A **pure
> classifier in `domain/`** consumes that probe value and returns the `ArchiveView` of E-3.
> `domain/` never touches a file handle; `adapters/` never decides a format. AD-23's
> one-function guarantee holds over the classifier, which is the half two units could
> disagree about.
> Record explicitly in AD-23 that **no tar, gzip or JSON parsing is hand-written anywhere in
> this codebase** — `tarfile`, `gzip` and `json` are the implementations — and that an
> exception requires the ADR the project's standards demand.
> **Enforcement:** the existing import-linter contract already fails Unit A's hand-rolled
> path if the probe is written in `domain/`; add an AST check failing on byte-offset
> slicing of a `bytes` parameter inside `domain/archive_format`, and a unit test asserting
> the classifier is callable with **no filesystem present at all** (it takes a value, not a
> path), which is the property that makes the split checkable rather than stylistic.

---

## E-5 — The Safety Snapshot must be encrypted "when encryption is configured", and the frozen CLI has no way to configure it

**Rank 5.** Likelihood: high. Cost: a complete, unencrypted copy of the site's database —
every user record — written to local disk by the product's own safety feature, never
deleted. This is precisely the defect PRD Q-8 was reopened to close, arriving through a
different door.

### The two units

- **Unit A — the CLI epic**, which owns the frozen 19 flags.
- **Unit B — the restore epic**, which owns the Safety Snapshot.

### How both comply

AD-12: "The Safety Snapshot is a full Archive and is held to every Archive rule… It is
**encrypted when encryption is configured**, closing the same hole the PRD's Q-8 reversal
closed."

AD-22: nineteen flags, listed. **None of them is a passphrase, a key file, or an encryption
toggle.** AD-22 permits new flags ("new flags may be added"), so adding one is legal — but
nothing *requires* one, names it, or says where else a passphrase may come from.

ADR-0006 requires a passphrase to exist (Argon2id over it, key commitment in the Manifest).
FR-4 is in v1.0. PRD §13.2 records that FR-4 was pulled forward *specifically so that
always-on Safety Snapshots would not write plaintext database copies to disk.*

### The incompatibility, concretely

Three units, three answers, all compliant:

- **Unit A** adds `--passphrase-file` to both subcommands. A restore run from an existing
  cron entry has no such flag, so encryption is "not configured", so the Snapshot is written
  **in the clear**. Q-8's hole, reopened, by the letter of AD-12.
- **Unit B** reads a `WPBACKUP2_PASSPHRASE` environment variable, because AD-22 freezes flags
  and an env var is not a flag. Now the two composition roots (`cli/` and `api/`) resolve
  encryption from different sources — the Consistency Conventions say resolution order is
  "explicit argument, then environment, then `wp-config.php`", but a passphrase is not in
  `wp-config.php` and "explicit argument" has no spelling.
- **Unit C** reads AD-12's "closing the same hole Q-8 closed" as normative intent and makes
  Snapshot encryption **mandatory**, prompting for a passphrase — which breaks every
  unattended cron restore, i.e. UJ-1, the flagship journey.

And a fourth divergence sits underneath: if the Snapshot is encrypted and the operator loses
the passphrase, the artifact created to save them from a bad restore is unrecoverable —
ADR-0006 names this consequence for Archives generally but nobody has decided it for the
one Archive taken automatically, without being asked for.

### Closing AD

> **New AD-26 — Encryption configuration has exactly one declared surface, and the Safety
> Snapshot's encryption state is never implicit.**
> Passphrase resolution is a declared, ordered chain in `domain/` — `--passphrase-file`
> (new flag, added under AD-22's additive allowance, accepted on both subcommands),
> then `WPBACKUP2_PASSPHRASE_FILE`, then nothing — and it is **the same chain in `cli/` and
> `api/`**. A passphrase is never read from a TTY prompt on a non-interactive stream, and
> never from `argv`.
> **When no passphrase resolves, a destructive restore does not silently write a plaintext
> Snapshot.** It takes exactly one of two declared paths, and the AD names which: the Run
> refuses with a message naming `--passphrase-file`, **or** it writes an unencrypted
> Snapshot only into a directory created `0700` and **says so on stderr and in the Run
> Journal**. Silence is not an option, because silence is what Q-8 was about.
> The Snapshot's Manifest records `encrypted: true|false` and the KDF profile, so an
> operator can tell from the artifact.
> **Enforcement:** a test that runs a destructive restore with no passphrase configured and
> asserts the Snapshot on disk is either absent-with-refusal or encrypted-or-0700-and-warned
> — never a readable `database.sql` under a world-traversable path; asserted for **both**
> composition roots, with the root set derived by reflection over the package's declared
> entry points rather than hand-listed.

---

## E-6 — Redaction is required in two sinks and owned by one; the guard examines only the other

**Rank 6.** Likelihood: high — the two sinks are reached from different layers and a
structlog processor is not callable from a span attribute setter. Cost: `--new-db-password`
in plaintext inside an operator's trace backend, with AD-7's test reporting green.

### The two units

- **Unit A — the logging epic**, implementing AD-7's redaction and AD-10.
- **Unit B — the tracing epic**, implementing AD-24.

### How both comply

AD-7: "where a command line is logged, credential-bearing elements are replaced with a
redaction marker. A test asserts both properties against a constructed argument vector **and
against captured log output**."

AD-24: "**`process.command_args` is recorded only after the redaction of AD-7** — a span
attribute is as public as a log line."

Unit A implements redaction the idiomatic structlog way: a **processor** in the chain, which
operates on the event dict at emit time. That is the correct design for logs and it is
unreachable from anywhere else — a processor is invoked by structlog's pipeline, not by a
caller.

Unit B needs redacted argv *before* `span.set_attribute("process.command_args", …)`. It
cannot call a structlog processor. It writes `_redact_argv()` in the tracing helper. Both
units have complied with the text of their AD.

### The incompatibility, concretely

There are now two redaction implementations with two credential-key sets. They drift on the
first new flag. AD-7's guard scope — "against a constructed argument vector and against
captured log output" — **does not enumerate span attributes**, so:

1. A new credential-bearing flag is added (or `--admin-password`'s `dest` is renamed in the
   rewrite, which AD-22 explicitly permits since `dest` is not a spelling).
2. Unit A's processor key set is updated; the log test passes.
3. Unit B's helper key set is not; nothing tests it.
4. The password ships to whatever OTLP endpoint the host configured. AD-24's own sentence —
   "a span attribute is as public as a log line" — is correct and unenforced.

There is a second, quieter divergence in the same place. AD-24 says logs and traces correlate
through "a structlog processor that adds `trace_id` and `span_id` when a span is recording
and nothing when it is not… That processor is the *only* coupling between the two systems."
But redaction is now a **second** coupling, and it runs in the opposite direction
(tracing→redaction). The AD asserts a single coupling that its own requirement violates.

### Closing AD

> **Tighten AD-7 and AD-24 — one redaction function, one credential-key set, one guard over
> both sinks.**
> Redaction is a **pure function in `core/`** taking an argv sequence and returning a
> redacted sequence, over a **credential-bearing key set declared in `domain/`**. The
> structlog processor calls it; the span attribute setter calls it; nothing else redacts.
> Correct AD-24's "only coupling" sentence to name both couplings.
> **Enforcement — scope derived, not listed:** the credential-key set is derived from the
> argparse parser's actions (every `dest` carrying a declared `credential=True` marker) so a
> new flag joins the set by construction. The guard asserts redaction **in every sink**, and
> the sink set is derived by reflection over the classes that write a credential-reachable
> value outward — the structlog processor chain and the span-attribute writer — not from a
> list of two. **Scope attack:** add a third sink (a `NoopSqlClient` that echoes argv into an
> exception message, per AD-14's "no exception message contains a credential") and assert
> the guard fails until that sink calls the shared function.

---

## E-7 — `--whatIf` is a top-level flag, and the obvious "defect fix" to it silently turns Dry Run off

**Rank 7.** Likelihood: medium-high — accepting global flags after the subcommand is the
single most common argparse ergonomics fix, and AD-22 explicitly licenses "flags may gain
behaviour". Cost: an operator who typed `--whatIf` watches a real destructive restore run.

### The two units

- **Unit A — the CLI epic**, rebuilding the parser.
- **Unit B — the compat-test author**, writing the AD-22 conformance suite.

### How both comply

AD-22 freezes "all nineteen flag spellings including the camelCase `--whatIf`". It freezes
**spellings**. It says nothing about **position**, and nothing about parse semantics.

In the shipped CLI, `--whatIf`, `--log-level` and `--version` are on the *top-level* parser
and `--wp-dir`, `--mode`, `--archive` are on a shared parent applied to both subparsers. So
every working cron line today reads `python -m wpbackup2 --whatIf restore --wp-dir …` — the
global flag **before** the subcommand, which argparse requires.

### The incompatibility, concretely

**Unit A** improves ergonomics by also declaring `--whatIf` on the subparsers, so both
orderings work. This is a defect fix by AD-22's standard and a strict superset of accepted
input. It is also the classic argparse trap:

```python
parser.add_argument('--whatIf', action='store_true', dest='what_if')
sub.add_argument('--whatIf', action='store_true', dest='what_if')  # default False
```

`parse_args` applies the subparser's namespace **over** the parent's. `--whatIf restore …`
parses the parent's `what_if=True`, then the subparser runs with `--whatIf` absent and writes
its default `False` over it. **Dry Run is silently off.** Every existing invocation — the
ones AD-22 exists to protect — is the broken case, and the *new* ordering is the one that
works.

**Unit B** writes the conformance suite by enumerating the nineteen spellings and asserting
each is accepted. `--whatIf` is accepted in both units. The suite passes. Nothing in the
suite asserts that `--whatIf` **has its effect**, because AD-22 froze spellings and the test
was derived from AD-22.

This is AD-4's whole defect class — "a value that every call site must remember to honor" —
re-entering above the layer AD-4's grep gate covers. AD-4's gate fails on `dry_run` or
`what_if` "in any module outside a composition root"; `cli/` **is** a composition root, so
the gate is blind here by design.

### Closing AD

> **Tighten AD-22 — the frozen contract is (spelling, position, effect), not spelling alone.**
> The CLI conformance suite is generated from a **committed invocation corpus**: the full
> argv vector of every flag in its shipped position, both subcommands, plus the combinations
> AD-25's table enumerates. Each corpus entry asserts the **parsed effect** — the resulting
> `(RestoreMode, OverrideSet, dry_run, …)` value — not merely that argparse did not raise.
> A flag declared on both a parent and a subparser is **forbidden**; a lint check asserts no
> `dest` is declared twice across the parser tree, because argparse's namespace-overwrite
> makes that a silent correctness bug rather than a duplicate-flag error.
> Widening accepted input (a global flag accepted in both positions) is permitted **only**
> via `parse_known_args`-style shared handling that cannot clobber, and the corpus asserts
> the original position still produces the original effect.
> **Scope attack:** add `--whatIf` to a subparser in a test fixture parser and assert the
> duplicate-`dest` check fails.

---

## E-8 — Does a Dry Run emit spans, and does a no-op adapter record that it did something?

**Rank 8.** Likelihood: high. Cost: an incident review reads a trace showing `CLEAN` and
`LOAD_DUMP` completing with `process.exit.code = 0` for a Run that performed no effects —
telemetry that lies about destruction, which is the one thing telemetry exists to be honest
about.

### The two units

- **Unit A — the tracing epic**, implementing AD-24.
- **Unit B — the Dry Run epic**, implementing AD-4.

### How both comply

AD-4: "**Every port splits into queries and commands.** A Dry Run binds the *real* query
implementations and no-op command implementations." A span export is an **observable
external effect** — bytes to a collector or a JSONL file. Under AD-4's own definition,
`Tracer` is a command port, and a Dry Run must bind `NoopTracer`.

AD-24: attributes include **`dry_run`**. An attribute named `dry_run` on a span that is never
emitted during a dry run is dead code. So AD-24 plainly assumes spans *are* emitted in a Dry
Run.

Both readings are compelled by their own AD. They are opposites.

Note also that the prior review's D-4 fix, which would have settled the *content* question —
"a no-op command's return value is derived from the real pre-state… or returns a
`NotPerformed` sentinel" — **was not carried into the spine's AD-4** (Part 1, D-4). So there
is no rule against fabrication for a no-op to violate.

### The incompatibility, concretely

- **Unit A** instruments at the phase executor, above the adapter set — one root span, one
  child per phase, wrapping whatever the phase does. Under Dry Run the `CLEAN` phase runs
  `NoopFilesystem.rmtree()`, returns instantly, and the span closes with `status=OK`,
  `duration_ms=0`, and — because the no-op returned a plausible success — `archive.bytes`
  taken from the *plan*, not from anything written. The trace asserts the site was cleaned.
- **Unit B** treats `Tracer` as a command port, binds `NoopTracer` in a Dry Run, and emits
  **no spans at all**. A host application running this inside its own traced pipeline sees
  the Run vanish from the trace precisely when someone is testing the integration — because
  the first thing anyone runs against a new tool is `--whatIf`.

And a third-order effect: AD-24 says the structlog processor adds `trace_id`/`span_id` "when
a span is recording". Under Unit B, a Dry Run's log records lose those two fields entirely,
so the Dry Run's **log shape** differs from the real Run's — which breaks the property AD-4
sells, that "the core is byte-identical between the two", for the one artifact an operator
actually compares.

### Closing AD

> **Tighten AD-24 — the Tracer is a query-side concern, and a span never asserts an effect
> that did not happen.**
> `Tracer` is **bound identically in both adapter sets**: a Dry Run is traced. Spans are
> emitted for every phase, and **`dry_run=true` is set on the root span and inherited as a
> declared attribute on every child**, so no consumer can read a dry-run trace as a real one.
> **Restore D-4's anti-fabrication rule into AD-4** and extend it to span attributes: an
> attribute whose value would describe an effect that was suppressed is either **omitted** or
> set from the `NotPerformed` sentinel — never a plausible constant. `process.exit.code` is
> **absent**, not `0`, when no process ran. Span status for a suppressed command is a
> declared `NOT_PERFORMED` marker attribute, not `OK`.
> **Enforcement:** a test that runs a full destructive restore under both adapter sets with
> an in-memory SDK exporter attached, and asserts (a) the **span trees are structurally
> identical** — same names, same order, derived from `RestorePhase` rather than hand-listed;
> (b) every attribute present on a dry-run span is either equal to its real-run counterpart
> or explicitly in the declared omitted/`NOT_PERFORMED` set; (c) `dry_run` is present on
> every span in the dry-run tree. **Scope attack:** add a phase to `RestorePhase` and assert
> the comparison covers it without editing the test.

---

## E-9 — The new failure modes AD-18, AD-19 and AD-22 introduce have no exit codes, and the exit-code AD was never written

**Rank 9.** Likelihood: certain — three new refusal paths exist and FR-21's categories cover
none of them cleanly. Cost: a cron wrapper that retries on transient failures either
hammers a live lock forever or gives up on a genuinely retryable one; and §8 makes exit-code
*meanings* part of the frozen contract, so getting this wrong is a compat break in the one
surface AD-22 froze.

### The two units

- **Unit A — the lock adapter author** (AD-19) and the journal author (AD-18).
- **Unit B — the CLI epic**, which maps exceptions to process exit codes.

### How both comply

FR-21 requires "Documented, distinct exit codes separate at minimum: usage error,
Verification failure, missing external dependency, credential failure, and operation
failure." "At minimum" permits more. The spine's only statement is a Capability-map cell:
`FR-21 exit codes | domain/exit_codes, cli/ | AD-14 — the code table is part of the §8 CLI
contract`. There is **no AD** — D-7's proposed AD-18 was never written, and AD-18's number
went to recoverability (Part 1).

Three new refusals arrive with the delta and prior pass, and FR-21's five categories fit none
of them:

1. **Site Lock held by a live PID** (AD-19) — transient, retryable, nothing changed.
2. **Journal from an incomplete Run found** (AD-18) — permanent until an operator acts,
   nothing changed, and *retrying makes it worse* by never clearing.
3. **`--only-appointed-in-asg` supplied** (AD-22) — a retired flag, permanently failing.

### The incompatibility, concretely

**Unit A** mints `EX_LOCKED = 75` (BSD `EX_TEMPFAIL`, the conventional retryable code) and
`EX_JOURNAL_DIRTY = 76`. **Unit B**, finding no table entry, maps both to the generic
operation-failure code, because AD-14 says errors cross the boundary as package-owned types
and the CLI's job is to "translate errors" — with no table, the safe default is the general
bucket. An operator's `systemd` unit with `Restart=on-failure` and
`RestartPreventExitStatus=` cannot distinguish them under Unit B and will retry a dirty
journal indefinitely, or under Unit A will treat a genuine operation failure as terminal.

**The retired flag is worse**, because the divergence is about *when*, not just *what*:

- **Unit A** rejects `--only-appointed-in-asg` at **parse time**, in `cli/`, before the Run
  Context (AD-16), before the Site Lock (AD-19), before anything. Exit code: usage error.
  Nothing on disk changed.
- **Unit B** models it as a **missing capability** — it is, literally, a vanished dependency
  — and routes it through AD-13's preflight, which AD-13 says runs *after* the composition
  root builds the Run Context and *after* AD-19 acquires the lock. Exit code: missing
  external dependency. A Site Lock was taken and released, a Run ID was minted and logged,
  and a journal directory may exist, for an invocation that could never have run.

Both are defensible; they produce different exit codes, different log output, and different
filesystem side effects for the same argv.

### Closing AD

> **New AD-27 — One exit-code table, derived from the exception hierarchy** (re-homing D-7,
> whose closing AD was never written), **extended to cover the refusals AD-18, AD-19 and
> AD-22 introduce.**
> `ExitCode` is an `IntEnum` defined once in the lowest package that can hold it
> dependency-free, re-exported by all three. **Every package-owned exception base declares
> its exit code as a class attribute**; the CLI maps an exception to a code by **walking the
> MRO**, never by a lookup table, so a new exception type is classified by construction.
> The table adds, beyond FR-21's five: **`LOCKED`** (a live holder — declared *retryable*),
> **`INCOMPLETE_RUN`** (a journal awaits resolution — declared *not retryable*), and
> **`RETIRED_OPTION`**. The retryable/not-retryable partition is part of the table and part
> of the §8 contract, because that is the property a cron wrapper actually consumes.
> **AD-22 gains a sentence:** adding an exit code is additive and permitted; **changing the
> meaning of a shipped code is not**, and the retired-option refusal happens **at parse
> time, before any Run Context or Site Lock exists** — named explicitly so Unit B's
> preflight routing is closed off.
> **Enforcement:** a CI test discovering every concrete subclass of each package's exception
> base **by reflection** and asserting each resolves to a non-default code; a planted
> violation adding a subclass with no code and asserting the guard fails; and a corpus test
> asserting `--only-appointed-in-asg` leaves **no lock file and no journal directory**
> behind.

---

## E-10 — The Run Journal lives "in the Safety Snapshot's directory", which may not exist and may be the directory deleted in `finally`

**Rank 10.** Likelihood: medium-high. Cost: the durable record whose entire purpose is to
survive a kill is destroyed by the kill path, and AD-18's recoverability guarantee silently
does not exist.

### The two units

- **Unit A — the restore epic**, placing the journal.
- **Unit B — the journal author**, implementing AD-18's refusal-on-dirty-journal.

### How both comply

AD-18.1: "a durable record written **to the Safety Snapshot's directory** before each phase
begins and after it completes."

Two things undercut that address:

1. **FR-8:** "An operator can **opt out** of the Safety Snapshot explicitly." (There is no
   opt-out flag among the nineteen either — see E-5's sibling problem — but AD-22 permits
   adding one, and FR-8 requires the capability.) With no Snapshot, there is no Snapshot
   directory.
2. **AD-12:** the workspace "is removed in a `finally` on both success and failure." If a
   unit reads "the Safety Snapshot's directory" as somewhere under the per-Run workspace —
   which AD-12's first paragraph makes the natural home for everything a Run creates — the
   journal is deleted by the same `finally` that runs when the Run dies.

### The incompatibility, concretely

- **Unit A** writes the journal into the workspace, because the workspace is the Run's
  private area and AD-12 says "the shell creates one workspace per Run". The Run is killed
  mid-`LOAD_DUMP`. Python's `finally` runs on `SIGTERM`-via-handler and on any exception;
  the workspace and the journal go with it. The next Run finds no journal, proceeds happily,
  and AD-18's entire first requirement — "A Run that finds a journal from an incomplete Run
  refuses to proceed" — has no input. The invariant reports success by finding nothing.
- **Unit B** writes the journal beside the Site Lock in the per-user state directory (AD-19's
  location), which survives. But now a **snapshot-opted-out** Run also journals, and Unit A's
  read path looks in the Snapshot directory and finds nothing. Two Runs on one Site, two
  journal locations, and the dirty-journal check is a no-op across the pair.

Worse: the journal is keyed by nothing declared. Unit A keys it by Run ID (so *every* Run
leaves a journal and the next Run must scan), Unit B keys it by Site identity (one journal
per Site, matching AD-19's lock key). Under Unit A's scheme a crashed Run's journal and a
successful Run's journal are indistinguishable without reading both.

### Closing AD

> **Tighten AD-18 — the Journal's location is the Site's state directory, not the Snapshot's,
> and it is keyed the way the Lock is keyed.**
> The Run Journal lives **in the same per-user state directory as the Site Lock (AD-19),
> keyed by the canonical absolute Site Root path** — never in the per-Run workspace (deleted
> in `finally`), never in the Site Root (deleted by a clean restore), and never at an address
> derived from an artifact the operator can opt out of. A Run Journal is created for **every
> destructive Run**, snapshot or not, and is **removed on clean completion**, so its mere
> presence is the dirty signal and no scan or comparison is required.
> The Journal records the Safety Snapshot's path (or its explicit absence and the fact that
> opting out was recorded, per FR-8), the `ArchiveView.integrity` of E-3, and the resolved
> `(RestoreMode, OverrideSet)` of E-1.
> **Enforcement:** a test that starts a destructive restore, kills the process
> **uncatchably** (`SIGKILL`, so no `finally` runs), and asserts (a) the journal file exists
> and names the interrupted phase, and (b) a second Run against that Site refuses with
> `INCOMPLETE_RUN` (E-9). **Scope attack:** run the same test with the Snapshot opted out and
> assert it still refuses.

---

## E-11 — Is the Safety Snapshot in the ArchiveStore or beside it? One answer lets Retention prune the last real backup

**Rank 11.** Likelihood: medium. Cost: FR-17 prunes an operator's last good backup because a
Safety Snapshot is the most recent Archive that verifies.

### The two units

- **Unit A — the restore epic**, writing Snapshots.
- **Unit B — the retention epic** (FR-17, v1.1), pruning Archives.

### How both comply

AD-12: "**The Safety Snapshot is a full Archive and is held to every Archive rule.**" Every
Archive rule includes AD-20, which binds `ArchiveStore` adapters: temp name, atomic
publication, verified Manifest. The most direct compliant implementation writes the Snapshot
**through an `ArchiveStore`**.

AD-20: "Retention (FR-17) never prunes the most recent Archive that passes Verification."

AD-12 also says the Snapshot is written "outside the Site Root and outside any web-served
directory" — which constrains *where*, not *which store*.

### The incompatibility, concretely

**Unit A** writes the Snapshot through the configured `ArchiveStore` to the same target the
operator's backups go to, because AD-12 said "every Archive rule" and AD-20 is an Archive
rule. The Snapshot is now the newest object in the store.

**Unit B** implements AD-20's retention protection literally: keep the most recent Archive
that passes Verification. That Archive is **the Safety Snapshot** — a point-in-time capture
of a site mid-restore, possibly of a site that was already broken, which is why the Snapshot
was taken. The operator's last *deliberate* backup is now prunable, and gets pruned on the
next scheduled run.

The inverse is equally compliant: **Unit B** excludes Snapshots from the store's listing (a
different prefix, a `kind` field in the Manifest), so retention never sees them — and
therefore **never prunes them**, and PRD §11's "snapshot lifetime remains unbounded until
FR-17" becomes permanent rather than a v1.0 limitation, with every destructive restore
leaving an encrypted full database copy on disk forever.

Nothing in the spine distinguishes the two kinds of Archive. The Manifest schema (AD-6) does
not carry a kind discriminator.

### Closing AD

> **Tighten AD-12 and AD-20 — Archives have a declared kind, and retention's protected set
> is expressed over it.**
> The Manifest carries **`kind: backup | safety-snapshot`** (AD-6 schema), set at write time
> and never inferred from a path or a prefix. AD-20's retention protection reads: *retention
> never prunes the most recent Archive **of kind `backup`** that passes Verification*, and
> Safety Snapshots are governed by their own declared policy — which the AD names now, even
> though FR-17 ships in v1.1, because the write side ships in v1.0 and the naming is what
> FR-17 will have to live with.
> The AD states whether the Snapshot shares the operator's Storage Target or uses a separate
> declared location, and it is **one answer for both composition roots**.
> **Enforcement:** a retention test whose fixture store contains a Snapshot newer than the
> newest backup, asserting the newest backup survives; **scope attack:** make the Snapshot
> the *only* Archive in the store and assert the policy is still total (no crash, no
> prune-everything).

---

## E-12 — `--mode` accepts `{files, db, all}`; FR-6's mechanically-asserted table has six different names

**Rank 12.** Likelihood: high. Cost: either a CI guard that cannot pass, or a dropped
`--mode db` spelling that breaks the frozen contract.

### The two units

- **Unit A — the CLI epic**, preserving `choices=['files', 'db', 'all']`.
- **Unit B — the `domain/` author**, implementing FR-6's round-trip guard.

### How both comply

AD-22 freezes the flags; §8 puts "accepted values" inside the CLI contract; AD-22's defect
list keeps `--mode db` alive ("`--mode db` performs a database backup rather than silently
backing up everything") — so `db` is a frozen accepted value.

FR-6's consequence: "Mode names round-trip: **every accepted CLI value maps to exactly one
API enum member and back**, asserted mechanically against the table rather than a hand-kept
list." The table's rows are `files, files-clean, database, database-clean, all, all-clean`.

`db` is not a row. `all-clean` is not an accepted CLI value. The round-trip is not a
bijection in either direction, and the guard FR-6 mandates is written against the table.

### The incompatibility, concretely

- **Unit B** writes the mechanical guard: for each `RestoreMode`, assert a CLI value parses
  to it and renders back. It fails on `files-clean`, `database-clean` and `all-clean`, which
  have no `--mode` spelling — they are reachable only through `--cleanfirst` (E-1). Unit B
  concludes the fix is to extend `choices` to the six table names, which **changes the
  accepted-value set** — legal as an addition, but Unit B also drops `db` because it is not a
  row, which is a contract break.
- **Unit A** keeps three choices and maps `db → DATABASE`, satisfying AD-22 and breaking
  Unit B's guard.

There is also a live sub-defect the rewrite must not re-import: the shipped code does
`str(args.mode).upper() == "DATABASE"` against a `--mode` whose only database spelling is
`db`, so `--mode db` never matches and falls through to `ALL`. That is arch-review M-1, and
AD-22's defect list names fixing it — but "fix it" without deciding the value set means the
two units fix it two ways.

### Closing AD

> Fold into **AD-25**. The mapping table is the *only* place a CLI mode spelling exists, and
> it is **not a bijection**: it is a total function from the frozen accepted-value set —
> `{files, db, all}` × flags — onto `RestoreMode`, with the six mode names available as
> **additional** accepted `--mode` values (an additive change AD-22 permits). FR-6's
> round-trip guard is restated as **surjectivity over `RestoreMode` plus totality over the
> CLI input space**, asserted against the table, with the CLI side derived from the parser's
> `choices` so a value added to one and not the other fails CI.

---

## E-13 — FR-10 says a manifest-less Archive is refused unless the operator opts in; AD-6 and AD-23 say it is read by default, permanently

**Rank 13.** Likelihood: medium-high — a PRD-conformance test author and a spine-conformance
test author will write opposing assertions. Cost: the rewrite's headline compatibility
promise either works or is gated behind a flag nobody's cron entry has.

### The two units

- **Unit A — the restore epic**, implementing AD-6/AD-23.
- **Unit B — the FR-conformance test author**, deriving tests from the PRD's "Consequences
  (testable)" bullets, which is exactly what those bullets are for.

### How both comply

FR-10, consequence 2, verbatim: "An Archive with no Manifest is **refused unless the operator
opts into a documented legacy path**."

AD-6, amended: "Restore detects that shape and reads it **by default, permanently** — **not
behind a legacy opt-in**."

AD-23: "read v0 forever."

Unit B's test asserts a refusal-without-a-flag. Unit A's implementation reads it. Both are
implementing a governing document; the spine supersedes the PRD on architecture but **not on
a testable product consequence**, and nothing in AD-6 or AD-23 records that FR-10's
consequence was changed or why.

### The incompatibility, concretely

The test suite contains one assertion in each direction, written by two people who never
spoke, and whichever lands second is "fixed" by deleting the other. If the PRD assertion
wins, a v0 restore requires a flag that does not exist in the frozen nineteen, and an
operator restoring a two-year-old archive gets a refusal — which for a backup tool reads as
"your backup is gone", the exact string AD-23's Prevents clause exists to avoid.

### Closing AD

> **Tighten AD-23 with an explicit supersession note**, and reconcile the PRD in the same
> change: *"FR-10's 'unless the operator opts into a documented legacy path' is superseded.
> The rewrite mandate makes v0 reads a default and permanent capability; the 'documented
> legacy path' is the default path, and it is documented here."* Record it in the PRD's
> change log too, because a contradicted consequence bullet is a test somebody will write.
> **Enforcement:** the existing FR-traceability check gains an assertion that no FR
> consequence bullet is contradicted by an AD without a supersession note naming the FR —
> derived by scanning AD bodies for FR references, not hand-listed.

---

## E-14 — AD-24 promises "a log file and `jq`"; the frozen CLI's default log level emits nothing

**Rank 14.** Likelihood: high. Cost: low per incident, but it makes the delta's central
observability claim false by default, and the fix is a contract question nobody owns.

### The two units

- **Unit A — the CLI epic**, preserving `--log-level` with `default='CRITICAL'`.
- **Unit B — the observability epic**, implementing AD-10 and AD-24.

### How both comply

The shipped parser: `arg_parser.add_argument('--log-level', default='CRITICAL', …)`.

AD-24: "**Every phase emits `phase`, `duration_ms`, `exit_code` and `bytes` as structured log
fields regardless of whether tracing is configured.** An operator with a log file and `jq`
gets the full operational picture with no collector."

FR-20: "The Run ID is reported to the operator at the start and end of a Run."

At `CRITICAL`, phase records (INFO) and the Run ID banner do not emit. AD-24's promise and
FR-20's consequence are both unreachable at the default the frozen CLI ships.

### The incompatibility, concretely

- **Unit A** preserves `CRITICAL` because §8 puts "accepted values" in the contract and a
  default is the value an unchanged cron line gets. Result: the product is silent, AD-24
  buys nothing for the majority audience it was justified by, and SM-5 ("failures arrive
  with a Run ID and a structured log excerpt") cannot happen.
- **Unit B** changes the default to `INFO` because AD-24 and FR-20 are unconditional
  ("regardless", "every record"). Result: every existing cron entry starts writing structured
  logs to stderr where previously there were none — which for an operator whose `cron`
  MAILTO is set means nightly mail, and for a `systemd` unit means journal volume. That is a
  behavioural change to the frozen surface, made by nobody's decision.

Both are one-line changes and neither is discussed anywhere. And D-11's proposed shared
verbosity table — "the verbosity level mapping is a single table in the lowest
dependency-free package, imported by all three" — was **not adopted** (Part 1), so FR-20's
"consistent across `wpbackup2`, `wpconfigr` and `wpdatabase2`" has no mechanism either.

### Closing AD

> **Tighten AD-22 and AD-10.** AD-22 states explicitly whether a flag's **default value** is
> part of the frozen contract, and answers it for `--log-level`: the default becomes a
> declared level at which AD-24's per-phase fields and FR-20's Run ID banner **do** emit, and
> it is named in the release notes as a defect fix under AD-22's "defects are fixed" clause —
> because a tool whose default is `CRITICAL` cannot satisfy FR-20, and shipping it silent is
> the defect. AD-10 gains D-11's unadopted sentence: the operator-flag-to-level mapping is
> **one table in the lowest dependency-free package**, imported by all three CLIs.
> **Enforcement:** a test that runs a full backup with **no `--log-level` supplied** and
> asserts that `phase`, `duration_ms`, `exit_code`, `bytes` and the Run ID are all present in
> captured output — with the field set derived from `RestorePhase` and AD-24's declared field
> list, not hand-typed.

---

## E-15 — "Creating a Run Context while one is active is an error" — active in what scope?

**Rank 15.** Likelihood: medium. Cost: a library caller (FR-24, the audience AD-24's entire
cost was justified by) cannot back up two Sites concurrently, or can and races structlog
configuration.

### The two units

- **Unit A — the `api/` author** (FR-22..FR-24).
- **Unit B — the `cli/` author**.

### How both comply

AD-16: "a Run Context… is created exactly once, by the outermost composition root, and passed
inward… **Creating a Run Context while one is active is an error, not a second Run.**"

AD-10: `structlog` "configured once at the composition root" — `structlog.configure()` is
**process-global**. `structlog.contextvars` is **context-local**.

AD-16 does not say which scope "active" is measured in, and its two named mechanisms have
different scopes.

### The incompatibility, concretely

A host application backs up thirty Sites in a thread pool — the obvious way to use an
embeddable library, and the case AD-24 exists for.

- **Unit A** tracks the active context in a `ContextVar`. Thirty contexts coexist; thirty
  workspaces; thirty Run IDs, correctly separated by `merge_contextvars`. But each one calls
  the composition root, which calls `structlog.configure()` — process-globally, thirty times,
  concurrently. The last writer wins and the processor chain is rebuilt underneath in-flight
  records.
- **Unit B** tracks it in a module-level global, which is the reading that matches AD-10's
  process-global `configure()`. The second concurrent Site raises "a Run Context is already
  active." The library cannot do concurrent Sites at all — and AD-19's Site Lock, which is
  keyed *per Site* and explicitly "binds the CLI and library callers identically", implies
  that concurrent Runs against *different* Sites are expected to work.

AD-19 assumes per-Site concurrency; AD-16 may forbid per-process concurrency; AD-10 has a
process-global mechanism. Three ADs, three scopes, no statement.

### Closing AD

> **Tighten AD-16 — name the scope, and separate process-global configuration from per-Run
> context.**
> A Run Context is **context-local** (`contextvars`), so concurrent Runs against *different*
> Sites are supported and each carries its own Run ID, workspace and adapter set. "Already
> active" means *already active in this context*, and nesting within one context is the error
> AD-16 names. **Logging configuration is process-global and idempotent**: the composition
> root calls a `configure_once()` that is safe under concurrency and is a no-op after the
> first call — AD-10 gains that word. Concurrency against the **same** Site remains forbidden,
> and that is AD-19's Site Lock's job, not AD-16's.
> **Enforcement:** a test running N concurrent Runs against N distinct fixture Sites,
> asserting N distinct Run IDs, N workspaces, no interleaved records, and one configuration;
> plus a test asserting two concurrent Runs against **one** Site produce exactly one success
> and one `LOCKED` (E-9).

---

## E-16 — Is a v1 Archive gzipped? The frozen `--archive` help says `.tar.gz`; AD-6 says "tar container"

**Rank 16.** Likelihood: medium. Cost: detection, streaming and the generated README all
depend on the answer, and two units will pick differently.

### The two units

- **Unit A — the backup epic**, writing v1.
- **Unit B — the detection author** (E-4's classifier).

### How both comply

AD-6: v1 is "an **unencrypted tar container**" with "per-member payloads, each encrypted
independently when encryption is on." No statement about compression.

The frozen CLI's `--archive` help: "Path and filename of the archive **(.tar.gz)** to backup
to/restore from." The README's generated `--help` output is checked in CI (Consistency
Conventions), so that string is now a *tested artifact*.

AD-23: "Detection is never inferred from filename or extension."

### The incompatibility, concretely

- **Unit A** writes an uncompressed tar, because AD-6 says "tar container" and per-member
  encryption makes outer compression worthless (ciphertext does not compress). Operators get
  files named `backup.tar.gz` that are not gzipped, and `tar tzf` fails on them — a support
  channel filled with "your backup is corrupt" for archives that are fine.
- **Unit B** writes `.tar.gz` to match the help text and operator expectation, applying gzip
  *outside* the container — which makes `manifest.json`, the first member, unreadable without
  decompressing, and interacts with E-4's probe (the probe must sniff the gzip magic before
  it can read a tar header) and with AD-21 (a gzip stream is sequential-only, so "seek to the
  member you need" is not available for v1 either).
- A third unit compresses **per member**, inside the container, before encryption — which is
  the only choice that keeps `manifest.json` plainly readable *and* compresses effectively,
  and which nothing in the spine either mandates or forbids.

Detection has to handle whichever landed, and AD-23 forbids it from using the extension to
find out.

### Closing AD

> **Tighten AD-6** — state the container's compression explicitly: v1 is an **uncompressed
> outer tar**; **compression is per member, applied before encryption**, and the Manifest
> records each member's compression codec. `manifest.json` itself is **never compressed and
> never encrypted**, so the first 512-byte header plus one member read identifies any v1
> Archive with no codec negotiation. State that **v0's outer gzip is a v0-only property** the
> probe detects by magic bytes, never by extension. AD-22 gains a note that the `--archive`
> help string's `(.tar.gz)` is updated to describe both formats — a help-text change, which
> §8 explicitly excludes from the contract ("log message wording… not part of either
> contract" extends to help prose), while the flag spelling and its acceptance of any path
> are unchanged.

---

## E-17 — A v0 restore of a Site whose `wp-config.php` is outside the Site Root has no source for `config_path`, and AD-3 forbids re-deriving it

**Rank 17.** Likelihood: medium — it bites only on FR-29's layout, which is WordPress's own
documented convention, so it bites on real sites and not on fixtures.

### The two units

- **Unit A — the restore epic**.
- **Unit B — the config-writer author** (FR-11, `ports/ConfigWriter`).

### How both comply

AD-6 handles this **for v1**: a `config`-role member with "its original location recorded as
Manifest *metadata*". D-5's fix, correctly applied.

A v0 Archive has neither. Its members are `database.sql` and `wp-root/`. If the source Site's
`wp-config.php` lived one level above the Site Root, it is either **not in the archive at
all** or it is inside `wp-root/` at a path that lies about where it belongs.

AD-3: "No module below the composition root opens `wp-config.php` for values the descriptor
already carries. The single exception is the config *writer* (FR-11), which writes and does
not read for its own use."

### The incompatibility, concretely

- **Unit A** searches the extracted tree for a `wp-config.php` and writes to whatever it
  finds — re-deriving a path the descriptor is supposed to own, which is the exact defect
  AD-3 exists to kill ("the internal backup/restore classes re-read `wp-config.php` instead
  of using the descriptor they were handed, so every `--new-db-*` override is silently
  ignored").
- **Unit B** takes `config_path` from the Site Descriptor — which for a restore is derived
  from the *target* Site, not the Archive — and writes there. If the target has no config yet
  (a restore onto a fresh host), there is nothing at that path, `REWRITE_CONFIG` writes a
  file the extraction did not produce, and `SEARCH_REPLACE` bootstraps against a config whose
  provenance nobody can state.

FR-29's third consequence — "A Site whose `wp-config.php` cannot be located **fails before
any destructive step**, naming the paths that were searched" — is satisfied by neither, since
both find *something*.

### Closing AD

> Fold into **AD-23's `ArchiveView`** (E-3): the view carries `config_location: Path | None`,
> populated from Manifest metadata for v1 and **`None` for v0**. `REWRITE_CONFIG` consumes
> that field; when it is `None`, the config path comes from the **target Site Descriptor
> only**, resolved at the composition root before `PREFLIGHT`, and a v0 restore onto a target
> with no locatable `wp-config.php` **refuses in `PREFLIGHT`**, naming the paths searched
> (FR-29). No module searches the extracted tree for a config file.
> **Enforcement:** a fixture pair — a v0 archive of an FR-29-layout Site restored onto (a) a
> target with a config at the stated out-of-root path and (b) a bare target — asserting a
> correct write in the first and a pre-destructive refusal in the second.

---

## E-18 — AD-6's supported range is derived from fixtures as a *version range*, and v0 has no version

**Rank 18.** Likelihood: medium. Cost: the mechanism the spine relies on to make "read v0
forever" checkable cannot represent v0, so the promise is prose — which this project's own
standards call out as the worst kind.

### The two units

- **Unit A — the CI gate author**, implementing AD-6's "the supported format range is derived
  from committed fixture Archives exercised in CI — never a hand-maintained list."
- **Unit B — the archive-format epic**.

### How both comply

AD-6 and §8 both express support as a **version range**, derived from fixtures, gated by the
Manifest's `format_version`. AD-23 promises v0 reads "forever". A v0 Archive has **no
`format_version` field** — it is not "version 0", it is *the absence of the mechanism that
carries a version*. There is no integer to put in a range, and "≥ 0" is not a thing the
detection function can answer for an archive it identifies by member names.

### The incompatibility, concretely

- **Unit A** builds the gate over `{fixture.manifest.format_version for fixture in fixtures}`
  — a set comprehension that **skips the v0 fixture entirely**, because it has no manifest
  to read. The derived supported range is `{1}`, the gate passes, and v0 support is covered
  by **zero** derived tests. The guard examines a set that does not contain the case that
  matters.
- **Unit B** assigns v0 a synthetic `format_version = 0` at detection time so it fits the
  range machinery. Now a *malformed* v1 archive whose manifest is unreadable can be
  misclassified as v0 and read with structural-only verification — "a v0 Archive being
  silently treated as a corrupt v1" (AD-23's Prevents clause) inverted into "a corrupt v1
  silently treated as a v0", which is the more dangerous direction, because it **proceeds**.

### Closing AD

> Fold into **AD-23**. The supported-format set is **not a version range**: it is a set of
> **format identities** — `V0_MANIFESTLESS` and `V1(format_version)` — and v0 is a
> first-class member of that set with no version number. The CI gate's scope is derived from
> the **fixture directory** (every committed fixture must be readable), not from manifests,
> so a fixture without a manifest still counts. Detection **never** synthesizes a version for
> v0; a first member named `manifest.json` that fails to parse is **`UNRECOGNISED`, never
> v0** — stated explicitly, since that inversion is the dangerous one.
> **Scope attack:** delete the v0 fixture and assert the derived gate's count drops and CI
> reports the missing identity, rather than silently narrowing.

---

# What these have in common

Three structural causes account for all eighteen, and two of them are repeats.

1. **The delta added a second Archive *shape* without adding a second Archive *type*.**
   AD-23 declares v0 exists and declares detection. It does not declare what the rest of the
   system receives. Eleven ADs written against a Manifest now have an input with no Manifest,
   and each one is a fork. **E-3, E-4, E-13, E-16, E-17, E-18 are all one missing value
   object** — the `ArchiveView` — and closing it closes six pairs. This is the single highest-
   leverage change in the delta.

2. **AD-22 froze a *surface* and the surface has semantics nobody wrote down.** Nineteen
   spellings were frozen; the function from those spellings to behaviour was not. E-1
   (flags→mode), E-7 (flag position and parse order), E-9 (exit codes), E-12 (accepted
   values), E-14 (defaults) and E-5 (what the frozen surface *lacks* — a passphrase, a
   snapshot opt-out) are all the same gap: **"the CLI is frozen" is a statement about
   syntax, and every divergence here is about semantics.** A frozen contract needs a
   conformance corpus, not a flag list.

3. **Guard scope is still hand-shaped where the delta widened the world** — the project's own
   §4 failure mode, reported last pass as structural cause #3 and reintroduced by the delta.
   AD-17's phase test enumerates Restore Modes but the world is now Modes × archive versions
   (E-3). AD-7's redaction test enumerates argv and log output but the world now has span
   attributes (E-6). AD-6's fixture-derived range enumerates manifests but the world now
   contains an archive without one (E-18). In every case the guard keeps reporting success
   over a set that no longer contains what matters.

**And one process finding.** V-1 — ADR-0003 corrected, AD-7 not — is the most expensive
defect in this review per character of fix, because the spine currently states the corrected
decision's opposite under an "ADOPTED" heading. Three previously-proposed closing ADs (D-6,
D-7, D-8, D-11) were dropped without a recorded decision, and two of the AD numbers they were
assigned (18, 20, 21) were reused for different content — so a reader following the prior
review's summary table lands on unrelated ADs and concludes the work was done. **A
mechanical check that every AD number cited in a review's "Closing AD" column resolves to an
AD whose subject matches, or to a recorded decision not to adopt, would have caught all
five.**

**Recommended sequence.**

1. **`ArchiveView` (AD-23 tighten)** — closes E-3, E-4, E-13, E-16, E-17, E-18. Six pairs,
   one value object.
2. **AD-7 rewrite (E-2 / V-1)** — the smallest fix with the largest correctness delta, and it
   is already decided in ADR-0003; it only needs propagating.
3. **AD-25, the CLI→mode table (E-1, E-12)** plus the **conformance corpus (E-7, E-14)** —
   this is what "frozen contract" has to mean to be checkable.
4. **AD-26 encryption surface (E-5)** and **AD-27 exit codes (E-9, re-homing D-7)**.
5. **AD-24 tightening (E-6, E-8)**, then **AD-18/AD-12/AD-20/AD-16 (E-10, E-11, E-15)**.
6. **Re-home the four unadopted prior fixes** — D-6 (Site Descriptor fields), D-8 (preflight
   scope), D-11 (`wpconfigr` logging vs AD-2's zero-deps, which is a standing contradiction
   between two ADOPTED ADs), and D-12's AD-7 scope extension — or record explicitly that each
   was considered and declined, with the reason. Silence is what produced this section.
