# Input reconciliation — PRD → ARCHITECTURE-SPINE

**Source input:** `_bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/prd.md` (+ `addendum.md`)
**Target:** `_bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md` + `docs/adr/0001`–`0010`
**Date:** 2026-09-15
**Scope:** what the driving input carried that the spine does not hold. Not a quality review of the spine.

---

## 0. Verdict and counts

The spine holds the PRD's *mechanism* requirements very well and drops its *guarantee* requirements —
the ones that are cross-cutting properties rather than a component.

| Bucket | FRs (29) | NFRs (8) |
|---|---|---|
| COVERED | 24 | 5 |
| PARTIAL (a home exists; a named consequence has none) | — (noted inline) | 1 |
| DEFERRED (spine's Deferred section legitimately pushes it down) | 3 | 0 |
| DROPPED (no home anywhere) | 2 | 2 |

Beyond the FR/NFR grid, **ten non-FR obligations** from §7.2, §8, §9, §10, §11, §13.1 and Release A have no
architectural consequence recorded (§4 below). Those are the larger loss: the AD table is an invariant
structure, and the PRD's governance, contract-versioning and operational-documentation obligations are not
invariant-shaped, so they fell out silently rather than being deferred.

### The Capability → Architecture Map is not trustworthy as a coverage claim

Three specific problems, each verified against the ADs it names:

1. **FR-18 is absent from the map entirely.** (Confirmed — the map lists 28 of 29 FRs.) It *is* held by the
   Deferred section ("Scheduling internals — FR-18 is v1.1"), so this is a labelling defect, not a gap. But
   the map is the artifact a reader checks, and it reports a complete bridge while omitting a row.
2. **Row `FR-21 exit codes, FR-28 concurrency → cli/ → AD-12, AD-14` is false.** AD-12 governs the per-Run
   *temporary workspace*; AD-14 governs *exception types*. Neither governs an exit-code table and neither
   governs a Site-scoped lock. This row is the map asserting coverage that does not exist (§2.1, §2.2).
3. **No NFR appears in the map at all.** NFR-1 is mentioned in one cell; NFR-2, NFR-4, NFR-7 and NFR-8 are
   nowhere in it. Two of those are dropped outright.

---

## 1. FR walk (all 29)

`*` marks COVERED-with-a-named-consequence-unheld; the sub-gap is stated.

| FR | Class | Home | Note |
|---|---|---|---|
| FR-1 full backup | COVERED | `core/backup`, `adapters/tar`; AD-1, AD-6, AD-12 | genuine |
| FR-2 Backup Scope | COVERED | `domain/` BackupScope; AD-6 ("a Manifest on every Archive" answers the M-3 "database scope produces no archive" consequence) | genuine |
| FR-3 Manifest + Verification | COVERED | AD-6, AD-11; ADR-0006 | genuine; AD-11 explicitly puts Verification before the first destructive step |
| FR-4 encryption | COVERED* | ADR-0006 (Argon2id + chunked AES-GCM, AAD-bound chunk index/count) | **Unheld:** "an operator can encrypt without the passphrase appearing in process arguments." AD-7 is scoped to credentials *outbound to* MySQL/WP-CLI subprocesses; nothing governs how the passphrase is *acquired* by wpbackup2 itself (prompt / env / file, never `argv`) |
| FR-5 exclusions | COVERED* | backup row; AD-6 owns the Manifest schema | **Unheld:** "an excluded path is recorded as excluded in the Manifest" — AD-6 enumerates member names, schema, format version and encryption envelope; the exclusion record is not among them |
| FR-6 Restore Mode honored | COVERED | AD-5 (closed set in `domain/`, resolved once, no function may default it) | strongest coverage in the document; answers B-3 and M-1 directly |
| FR-7 refuse destructive over non-empty | COVERED | AD-5 ("authorized only by the flag that names that specific destruction") | genuine |
| FR-8 Safety Snapshot | COVERED* | AD-12's deliberate exception clause | **Unheld:** no invariant states a Safety Snapshot is *always encrypted*. That is the entire reason FR-4 was pulled into v1.0 (PRD Q-8). ADR-0006's Context records the reasoning; no rule enforces it, so "snapshot writes plaintext DB to local disk" is reachable without violating any AD |
| FR-9 honest DB restore | COVERED | `core/restore`; AD-5, AD-9 (explicit admin credentials for CREATE DATABASE/GRANT), NFR-1 | genuine |
| FR-10 format-aware restore | COVERED* | AD-6 (fixture-derived supported range) | **Unheld:** "an Archive with no Manifest is refused *unless the operator opts into a documented legacy path*". AD-6 says a Manifest is read before every restore, full stop. The v0.2.x legacy-archive opt-in has no home |
| FR-11 config rewriting | COVERED | ADR-0010 (+ read-back verification), AD-3 (host:port split once) | genuine, including the FR-11 db-port consequence |
| FR-12 serialization-safe URL rewrite | COVERED | ADR-0005, `adapters/wpcli` | genuine; ordering constraint derived and justified |
| FR-13 honest WP-CLI failure | COVERED | AD-13 (preflight at the port, plan-driven) | genuine |
| FR-14 pluggable providers | COVERED | AD-9 (port with `resolve()`), AD-8 / ADR-0008 (optional extra) | genuine |
| FR-15 credentials never in argv/logs | COVERED | AD-7 / ADR-0003 | strongest of the security invariants |
| FR-16 storage targets | DEFERRED | `ports/ArchiveStore`; Deferred: "Storage Target addressing scheme — v1.1" | Legitimate for the *addressing scheme*. **But** the consequence "a failed upload does not leave a partial Archive visible at the target as if it were complete" is NFR-2 and is dropped, not deferred (§3). Also dropped: the PRD's recorded default for Q-2, *delegate to `rclone` rather than own three protocol integrations* — the spine's Deferred bullet does not carry it |
| FR-17 retention / pruning | DEFERRED | `ports/ArchiveStore`; v1.1 | Mapped only to a port name. The safety consequence "pruning never removes the most recent Archive that passes Verification" is an NFR-1-class rule with no AD; if it is not written now it will be invented at v1.1 by whoever implements prune |
| FR-18 scheduled operation | DEFERRED | Deferred: "Scheduling internals — FR-18 is v1.1 and may yet be cut to declarative config only" | Legitimate. **Absent from the Capability map** (the only FR that is) — labelling defect |
| FR-19 Dry Run | COVERED | AD-4 (adapter selection, never a conditional) | best structural answer in the document |
| FR-20 correlated logging | COVERED* | AD-10 (structlog, contextvars, `merge_contextvars` first, ProcessorFormatter) | **Unheld:** "operator-selectable verbosity is part of the CLI contract, **consistent across `wpbackup2`, `wpconfigr` and `wpdatabase2`**". AD-10 binds all three for *configuration*, not for a consistent verbosity surface |
| FR-21 meaningful exit codes | **DROPPED** | claimed: `cli/`, AD-12, AD-14 — neither AD governs exit codes | see §2.1 |
| FR-22 typed API | COVERED* | `api/`, `mypy --strict` convention, `py.typed` | **Unheld:** "every operation available on the CLI is available through the API." No invariant makes `cli/` a thin shell over `api/`; the layer table makes them *peer* composition roots, and the map then places FR-21 and FR-28 in `cli/` — exactly the CLI-only-capability drift FR-22 forbids |
| FR-23 exception contract | COVERED | AD-14 (`raise ... from`, structured fields, no dependency type across a boundary) | genuine. The FR-23 consequence "every exported exception type has a reachable raise site, asserted mechanically" has no check named, but AD-14 is a plausible home |
| FR-24 declared public surface | COVERED | Conventions: `__all__` per package, "everything else is internal regardless of underscore" | genuine; v1.1 per PRD |
| FR-25 resolvable install | COVERED | AD-15, ADR-0007 (clean-env install of the built artifact from the index) | genuine; ADR-0007's follow-up names the exact blind spot. Console-entry-point-on-`PATH` consequence is not named but sits inside "installs and imports" |
| FR-26 dependency policy | COVERED* | AD-15 (upper bounds, resolvability gate), ADR-0004, ADR-0002 | **Unheld:** the third mechanical check — "fails the build when a dependency **has had no release within a documented staleness window**". AD-15 covers unresolvable and unbounded only. That is the one check that would have caught `mysql-connector` 2.2.9; ADR-0004 fixes the instance, nothing prevents the recurrence. Also unheld: the per-dependency **licence/reason inventory** (ADR-0004 lists it as a follow-up; no rule requires it to exist) |
| FR-27 external tool declaration | COVERED* | AD-13 (preflight port, presence + version) | **Unheld:** "a diagnostic command reports which external tools are present and their versions" — and §11 widens it to Python version, extras installed and Storage Target reachability. No such command surface exists in the Structural Seed or the map (the map files FR-27 under "supply chain → CI, pyproject.toml ×3") |
| FR-28 concurrent-Run prevention | **DROPPED** | claimed: `cli/`, AD-12, AD-14 | see §2.2 |
| FR-29 `wp-config.php` outside Site Root | COVERED | ADR-0010, AD-3, `ports/ConfigWriter` | genuine |

---

## 2. The two dropped FRs, in detail

### 2.1 FR-21 — exit codes have no architectural home

**What the input carried.** FR-21 requires documented, *distinct* exit codes separating at minimum: usage
error, Verification failure, missing external dependency, credential failure, operation failure — plus "no
failure path returns a value that the process then discards" (arch review M-16, the defect where every
failure path exited 0). §8 makes exit-code meanings part of the **CLI contract**. §10 makes reassigning one a
**breaking change**. §7.1 makes a refusal exit non-zero *so that automation notices* — the exit code is the
only channel UJ-1's monitoring watches.

**What the spine has.** One map cell naming `cli/`, AD-12 and AD-14. AD-14 gives an exception hierarchy with
structured fields; nothing maps an exception to a code, nothing declares the code set, nothing forbids
reassignment, and the Consistency Conventions table has no exit-code row (it has rows for identifiers,
timestamps, Manifest, errors, logging, config, typing, tests).

**Where it should have landed.** An AD on the CLI composition root: the exit-code set is enumerated once in
`domain/`, derived from the exception hierarchy rather than hand-mapped at each `cli/` call site (AD-14 is the
natural anchor), and the mapping is asserted mechanically — same derive-from-source-of-truth shape AD-6 uses
for the format range.

### 2.2 FR-28 — concurrent-Run prevention is filed under a workspace rule that does not provide it

**What the input carried.** A Site-identified lock, acquired *before the Run's first read of Site state*,
released on success, on failure **and on signal**; a second Run exits non-zero naming the holder's Run ID and
start time; a **stale lock is detected and reclaimed** rather than requiring manual removal; and the guarantee
holds identically for `cron`, a `systemd` timer, a shell, **and a library caller**. FR-28 was extracted from
FR-18 specifically so it ships in v1.0 regardless of whether a scheduler ever does, because UJ-1 is an
unattended 03:00 timer against a tool that does `rmtree` and database drops.

**What the spine has.** Nothing. `grep -i lock` across the spine and all ten ADRs returns only "lockfile",
"block" and "clock". The map cites AD-12, which is about `tempfile.mkdtemp` per-Run workspaces — that prevents
two Runs *colliding in a temp directory*, which is a different guarantee from two Runs *operating on one Site*.

**Two ways the current filing is actively wrong:**
- Placing it in `cli/` contradicts FR-28's fourth consequence and FR-22's "every operation available on the
  CLI is available through the API": a lock acquired in the argparse composition root does not protect a
  library caller going through `api/`.
- Signal-safe release and stale-lock reclamation are effect-ordering concerns that must be stated where the
  shell is described (AD-12's `finally` discipline is the nearest sibling), and they also carry NFR-4 —
  "a failed Run leaves no state that makes a subsequent Run unsafe" is *exactly* an abandoned lock.

**Where it should have landed.** An AD on the Site lock as a port acquired by *both* composition roots before
any Site read, with the stale-lock/signal rules in the same clause as AD-12's `finally`.

---

## 3. NFR walk (all 8)

| NFR | Class | Home / gap |
|---|---|---|
| NFR-1 data integrity paramount | COVERED | Cited by AD-5, AD-13, the FR-6..9 map row, and ADR-0010's read-back mitigation. Not stated as a *ranking* invariant ("outranks every other quality attribute"), which is how SM-C1's "a slower restore that cannot destroy a site is the correct trade" would be adjudicated — but it is genuinely operative |
| NFR-2 **atomicity of published artifacts** | **DROPPED** | No AD, no convention, no ADR. "atomic", "partial", "temp name", "rename", "publish-on-complete" appear nowhere. AD-6 governs the format, not visibility at a target. FR-16's matching consequence is dropped with it. This is one of the two invariants UJ-1's edge case turns on ("no partial Archive is published to the Storage Target, and last night's Archive is left untouched") and is a v1.0 concern even for a local Storage Target — a `LocalArchiveStore` writing in place is as capable of publishing a truncated Archive as S3 is. **Should have landed as:** an AD on `ports/ArchiveStore` — every store writes to a temporary name and makes the Archive visible under its final name only after the Manifest verifies; no store exposes an incomplete object |
| NFR-3 least privilege / secret hygiene | COVERED | AD-7, AD-9, ADR-0003. Sub-gap: "never in an Archive's Manifest" — ADR-0006 guarantees the *key* is never in the Manifest; AD-6 (which owns the Manifest schema) does not state that no credential is, and the Glossary's "source Site Descriptor (credentials excluded)" has no enforcing rule |
| NFR-4 idempotence / safe retry | COVERED | AD-12 (per-Run workspace, `finally` cleanup on success and failure). "A failed Run leaves no state that makes a subsequent Run unsafe" is only partly satisfied while FR-28's stale-lock reclamation is missing (§2.2) |
| NFR-5 untrusted archives | COVERED | AD-11 — explicit `filter='data'` on every call, containment re-checked after member-path rewriting, interpreter-default trap named. Strongest coverage after AD-5 |
| NFR-6 observability | COVERED | AD-10 — Run ID across subprocess boundaries, without a debug mode that exposes secrets (cross-checked against AD-7) |
| NFR-7 **performance envelope** | **DROPPED** | Two testable commitments, neither held. (a) *"no more than 1.5× a bare `mysqldump` + `tar` baseline, measured on the integration fixture set, asserted in the test suite."* No benchmark tier, no baseline fixture set, no Conventions row — the Tests row names unit / adapter-contract / integration only. (b) *"Archives are streamed, never buffered whole in memory: peak resident memory does not scale with Archive size."* ADR-0006 secures this **for the encryption layer only** (Fernet rejected precisely because it cannot stream); nothing constrains the tar adapter, the dump adapter, the store adapters or the Verification read path. Streaming is a property of the whole pipeline or it is not a property. **Should have landed as:** a streaming invariant binding every `ports/ArchiveStore` and archive adapter ("no adapter materialises an Archive or a Dump in memory"), plus a Conventions test row for the benchmark tier. Note this is also the *only* commitment §11 makes in place of an RTO/RPO figure (Q-4), so dropping it leaves §11's recovery-objective paragraph unbacked |
| NFR-8 testability without a live WordPress | **PARTIAL** | The principle is covered — and structurally, which is the best kind: AD-1 names NFR-8 as its reason for existing, AD-9 binds it, and the Conventions Tests row says the functional core is tested without a live WordPress or MySQL. **Two enforcement clauses are dropped:** (a) the integration list is *"explicitly enumerated … and is itself asserted to be complete, so a new consequence cannot quietly join it"* — the Conventions row says only "a small integration tier is marked and separable", which is a marker convention, the opposite of a derived, asserted-complete roster; (b) *"a test that asserts nothing is a failing test"* — arch review M-9/M-10/M-11 assertion-free cases are to be treated as absent coverage, and no check enforces it. The addendum (§D) also asked for a **test strategy ADR**; none of the ten is one |

---

## 4. Quiet requirements the AD structure dropped

These are the input's non-invariant-shaped obligations. Each is stated with where it should have landed.

1. **§7.2 data governance — personal data, GDPR/erasure, data residency.** Nothing in the spine or any ADR
   mentions personal data, GDPR, erasure or residency. Three distinct losses:
   - *An Archive is a sensitive artifact containing every user record.* The only architectural echo is
     ADR-0006's encryption. Nothing states that a plaintext Dump or extracted tree may exist only inside the
     per-Run workspace (AD-12) and never outside it — and FR-8's unencrypted-snapshot gap (§1) is the same
     hole seen from the other side.
   - *"Data residency of remote Storage Targets is the operator's choice and responsibility; wpbackup2 does
     not relocate data between regions on its own initiative."* This is a **hard constraint on every storage
     adapter** — no implicit cross-region replication, no fallback endpoint, no "convenience" copy — and it is
     exactly the kind of behaviour an S3 adapter acquires by accident. It should be a clause on
     `ports/ArchiveStore`, written now, while the port is still a name.
   - *Retention Policy (FR-17) is the control surface for right-to-erasure into backups.* That makes FR-17 a
     governance mechanism, not only a housekeeping one, and raises the cost of it having no invariant (§1).
2. **§11 runbook — "what a failed restore leaves behind at each stage."** No architectural consequence
   recorded. It is not merely a docs task: AD-1 makes the restore *plan* a first-class value and the spine's
   own sequence diagram enumerates the stages, so the plan's stage list is the natural source of truth for a
   generated, always-current runbook — the same derive-don't-enumerate move the Conventions table already
   makes for README CLI usage. Left as prose, it will drift from the plan the first time a stage is added.
3. **§11 security-report channel and support expectation.** No `SECURITY.md`, no private disclosure channel,
   no triage-without-response-time statement anywhere in the spine, ADRs or Conventions. For a package whose
   ADRs are about credential transport, archive encryption and untrusted-input extraction, the disclosure
   channel is the one operational artifact the security invariants imply. Cheap; entirely absent.
4. **§11 diagnostics command.** See FR-27 above — "a single command reports environment readiness: Python
   version, external tool presence and versions, optional extras installed, and Storage Target reachability."
   It spans AD-13 (tool preflight), AD-8 (extras present) and `ports/ArchiveStore` (reachability); no surface
   in the Structural Seed owns it.
5. **§11 "two ADRs pass to `bmad-architecture`": archive container format ✅ and subprocess invocation
   strategy ❌.** ADR-0006 discharges the first. There is **no ADR on the subprocess invocation strategy** —
   how subprocesses are spawned, how stdout/stderr are captured and streamed, timeouts, signal propagation and
   child cleanup, non-zero-exit translation into AD-14 types, and how the Run ID crosses the boundary (AD-10
   asserts it *does*; nothing says how). AD-7 covers credential transport only; AD-13 covers presence checks
   only. This is a named hand-off from the PRD that the spine did not pick up.
6. **§8 — the structured log schema is part of the CLI contract.** AD-10 governs the logging *transport*
   (structlog, processors, Run ID binding) and the Conventions table fixes timestamp format. Neither treats
   the emitted **field schema** as a versioned contract with the stability §10 attaches to it. Automation
   parses those field names; renaming one is a breaking change under §8/§10 and nothing records that.
7. **§10 versioning and deprecation policy — no home for the deprecation mechanism.** Semver across three
   contracts is implied (AD-6's format range, `__all__`, AD-15's bounds) but the *deprecation cycle itself* —
   a deprecated CLI option or API name keeps functioning for ≥1 minor release, emits a warning naming its
   replacement, and is listed in the changelog — has no AD and no Conventions row. Nor does "exit-code
   reassignment is a breaking change" (see §2.1). There is also no changelog convention.
8. **§9 family-level version policy — explicitly delegated and not picked up.** §9 says the residue that is
   "genuinely unowned" is "the standing family-level policy — compatibility ranges and release ordering beyond
   Release A — which passes to `bmad-architecture`", and addendum C.2 repeats it: *"No ADR is needed for the
   capability itself. One is still worth writing for the cross-package version policy."* AD-15 fixes release
   *ordering*; ADR-0002 pins one range (`wpconfigr>=1.5,<2`) for one release. Nothing states the standing
   policy: whether the three versions move in lockstep, what a `wpconfigr` minor obliges of its two
   dependents, or how ranges are re-set at each cut. This is a hand-off the PRD named twice.
9. **§9 / Q-3 — MariaDB parity.** "MariaDB" appears **nowhere** in the spine or any ADR. The PRD *answered*
   Q-3 as a requirement, not an expectation: both engines run in the integration matrix **from v1.0**, at a
   cost ("roughly doubles integration runtime") deliberately accepted because MariaDB is the default engine
   across much of the target market, and because an unchecked parity claim is the worst kind of unenforced
   prose. The spine's Stack lists only `mysqldump / mysql (external) client 8.0+`; the only CI matrix named
   anywhere is ADR-0009's Python-version matrix. ADR-0004 selects PyMySQL without reference to MariaDB
   compatibility. **Should have landed in:** the Stack table (MariaDB version row), the Conventions Tests row
   (the integration tier runs both engines), and ADR-0004's consequences.
10. **§13.1 non-goals and Release A named items.**
    - **`chesney` / `--only-appointed-in-asg` removal is absent.** "chesney" and "ASG" appear nowhere in the
      spine or ADRs. It is a Release A bullet, a §13.1 non-goal, and addendum C.4 calls it "the cheapest of
      the three supply-chain resolutions [which] should land first". AD-15 sequences the three releases and
      does not mention the removal that unblocks them.
    - **README credit-link correction is absent.** Release A bullet: the credit currently points at
      `cariad/py-wordpress-database` rather than `cariad/py-wordpress-backup`. It also discharges the §12 risk
      "positioned as novel when a near-identical predecessor exists" and §13.1's "Not novel". The Conventions
      table has a README row (generated CLI usage) that would have been the place to also fix provenance.
      ADR-0002 carefully retains upstream's notice for `wpconfigr` and says nothing about `wpbackup2`'s own.
    - Other non-goals carrying architectural force and not recorded: *no alerting* (§11 "the product does not
      own alerting" — a boundary on AD-10's logging), *not a general-purpose backup tool* (a constraint on the
      Site Descriptor's shape), *never reimplement WP-CLI's search-replace* (ADR-0005's exit plan holds this
      one well — the good counter-example).
    - Held: **multisite** is in Deferred with the right reason ("would change the Site Descriptor's
      cardinality").
11. **§4 Glossary discipline — HELD.** Conventions: "Naming — domain terms | The PRD §4 Glossary verbatim. A
    new domain noun is added to the Glossary in the same change." AD-5 also anchors Restore Mode to §4.
    Recorded as an architectural consequence; note only that it is review-enforced, where AD-1 (import-linter)
    and AD-15 (CI gate) are mechanically enforced.

---

## 5. Open questions — does the Deferred section account for them?

| Q | PRD disposition | Spine |
|---|---|---|
| Q-1 ASG cut | Closed; removal is a Release A item | **Not carried.** `chesney` / ASG absent everywhere (§4.10) |
| Q-2 remote Storage Targets | Closed by phasing; **recorded default: delegate to `rclone`** | Deferred bullet covers the *addressing scheme*; the `rclone`-over-three-integrations default and its SM-C3 rationale are not carried. Carrying it matters because it constrains the port shape the bullet claims is "enough to keep v1.0 from foreclosing it" |
| Q-3 MariaDB parity | **Answered: a requirement**, v1.0 integration matrix | **Dropped** (§4.9). Not in Deferred, not in Stack, not in Tests |
| Q-4 absolute perf/RTO/RPO | Closed: no, NFR-7's bound instead | Dropped with NFR-7 (§3) |
| Q-5 incremental backup | Closed by phasing, v1.x | **Held well** — Deferred names it, cites Q-5, and identifies AD-6's version field as the seam |
| Q-6 `wpconfigr` publication name | Answered: existing name; both dependents keep `>=1.0.0,<=2.0.0` **unchanged** | **ANSWERED — and exceeded.** ADR-0002 adopts the existing name with authorship/URL corrected and the MIT © 2018 notice retained (matching the Release A bullet verbatim), and additionally narrows the pin to `>=1.5,<2` because `<=2.0.0` admits 2.0.0 exactly. That narrowing **reverses the second half of Q-6's answer** and takes the trade addendum C.2 explicitly left to architecture — legitimately, and the ADR header declares "Departs from spec: PRD Q-6". What is *not* recorded: the consequence Q-6's wording was chosen to avoid — the pin change is a coordinated edit in both dependents, so AD-15's release sequence must carry it. One line in ADR-0002's Consequences or AD-15 closes this |
| Q-7 keep the name `wpbackup2` | Answered: yes | Consistent with Conventions ("distribution name equals import name") and used throughout. Held implicitly; the §13.1 "Not novel" half of the answer — the README credit correction — is not (§4.10) |
| Q-8 v1.0 encryption deferral reversed | Answered: FR-4 ships in v1.0 | ADR-0006's Context records the reasoning. **Incomplete:** no rule requires the Safety Snapshot itself to be encrypted (§1, FR-8), which is the specific hole the reversal existed to close; and "snapshot lifetime is unbounded until FR-17" is a documented v1.0 limitation with no architectural note |
| Q-9 / Q-10 cross-package obligations and ownership | Answered: Release A preconditions owned by Sanderson | **Q-9 ANSWERED completely** by ADR-0008 — the module-scope-import root cause is named with file and line, the fix is the lazy import, it is generalised to AD-8, and "CI asserts a base install imports every public module" gives it a mechanical check. The `wpdatabase2` driver half is ADR-0004. **Q-10's residue is not:** the standing family-level version policy, which §9 and addendum C.2 both route here (§4.8) |
| Q-11 Restore Mode table | Answered: yes, as derived | **Held** by AD-5 — closed set, defined once in `domain/`, anchored to §4 |

---

## 6. §8 three-contract model and §10 — per-contract verdict

| Contract | Spine home | Verdict |
|---|---|---|
| **Archive format** (§8, versioned independently, "matters more than the other two") | AD-6 + ADR-0006, supported range derived from committed fixture Archives exercised in CI | **Held, and held best.** The derive-from-fixtures rule is exactly the §8 clause "the supported range is derived from the fixture set rather than declared by hand". Gap: the FR-10 legacy no-Manifest opt-in path (§1) |
| **Python API** (§8) | `api/`, `__all__` + `py.typed` conventions, AD-14, `mypy --strict` | **Held.** Gap: nothing guarantees CLI/API operation parity (FR-22, §1) |
| **CLI** (§8: command names, option names, accepted values, **exit-code meanings**, **structured log schema**) | `cli/` as a composition root; README `--help` generation convention | **Partially held.** Command/option surface is implied by the composition root; **exit-code meanings (§2.1) and the structured log schema (§4.6) — both named explicitly in §8 — have no home** |
| **§10 versioning / deprecation across all three** | AD-15 bounds; ADR-0002 pin; AD-6 format range | **Not held as a policy.** No deprecation-cycle rule, no changelog convention, no statement that pre-1.0 surface is removed without ceremony (the clause that makes the §13.1 ASG cut and the Release A churn affordable), no family-level policy (§4.8) |

---

## 7. Release A — named items reflected?

| Release A item | Reflected |
|---|---|
| Publish `wpconfigr` 1.5, authorship/URL corrected, MIT © 2018 Cariad Eccleston notice retained | **Yes** — ADR-0002, verbatim |
| Release `wpdatabase2` with `mysql-connector` 2.2.9 replaced by a maintained driver | **Yes** — ADR-0004 (chose PyMySQL over `mysql-connector-python`; licence and wheel reasoning recorded) |
| Remove `chesney` together with `--only-appointed-in-asg` | **No** — absent from spine and all ten ADRs (§4.10) |
| Lockfile + CI installing the built artifact in a clean env on every supported Python version | **Yes** — ADR-0007 and AD-15; ADR-0007's follow-up names why installing the working tree would have hidden the outage |
| Correct the README credit link to `cariad/py-wordpress-backup` | **No** — absent (§4.10) |
| Release gate: `pip install wpbackup2` resolves and imports, clean env, every supported Python | **Yes** — AD-15 is this gate, plus dependency-ordered release |
| FR-14's precondition: `boto3` optional in `wpdatabase2` **including transitively** | **Yes** — ADR-0008 + AD-8; the transitive clause is the part ADR-0008 explicitly diagnoses |

---

## 8. Recommended additions, in priority order

1. **AD on the Site lock** (FR-28): a lock port acquired by *both* composition roots before the first Site
   read; released on success, failure and signal; stale-lock detection and reclamation; second Run names the
   holder's Run ID and start time.
2. **AD on atomic publication** (NFR-2, FR-16): every `ArchiveStore` writes under a temporary name and makes
   the Archive visible under its final name only after the Manifest verifies. Binds local and remote alike.
3. **AD / Conventions row on streaming and the benchmark tier** (NFR-7): no adapter materialises a Dump or an
   Archive in memory; a benchmark tier asserts the 1.5×-baseline bound against the integration fixture set.
4. **MariaDB into the Stack table and the Tests convention** (§9 / Q-3) and into ADR-0004's consequences.
5. **AD or Conventions row on the exit-code set** (FR-21, §8, §10): enumerated once in `domain/`, derived from
   the AD-14 hierarchy, asserted mechanically, reassignment declared breaking.
6. **Data-governance clause on `ports/ArchiveStore`** (§7.2): no cross-region relocation on the tool's own
   initiative; plaintext Dump and extracted trees exist only inside the per-Run workspace; the Safety Snapshot
   is always encrypted; FR-17 named as the erasure control surface.
7. **ADR on the subprocess invocation strategy** (§11's second named hand-off) and an **ADR on the test
   strategy** (NFR-8's asserted-complete integration roster + the assertion-free-test check; addendum §D asked
   for it).
8. **Conventions rows** for: the structured-log field schema as a versioned contract; the deprecation cycle
   and changelog; the dependency inventory and the staleness-window check (FR-26).
9. **Release A completeness**: add the `chesney`/ASG removal and the README credit-link correction to AD-15's
   sequence, and record in ADR-0002 that the narrowed `wpconfigr` pin adds a coordinated edit in both
   dependents.
10. **Repair the Capability → Architecture Map**: add an FR-18 row pointing at Deferred, correct the
    `FR-21, FR-28 → AD-12, AD-14` row, and add NFR rows so NFR coverage is visible rather than assumed.
