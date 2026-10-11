# Reconciliation: arch-review-2026-09-12.md against prd.md / addendum.md

Question answered: which of the review's 33 findings (4 BLOCKER, 19 MAJOR, 10 MINOR) have no
home in the PRD? Every finding is walked below. The addendum's §D mapping table is checked
against the actual PRD text cited, not trusted.

## Full disposition, every finding

| ID | Classification | Disposition |
|---|---|---|
| B-1 | ABSORBED | FR-25, FR-26, §9. Addendum D correctly maps this. FR-25's "a dependency that cannot resolve fails the release, not the user" directly catches the defect. |
| B-2 | ABSORBED | FR-25 ("A lockfile is committed and CI installs frozen from it"). Accurate. |
| B-3 | ABSORBED | FR-6, FR-7, FR-9 together cover all three sub-defects (mode discarded, unconditional rmtree, DB restore silently skipped-as-success). FR-6's "a test exists per mode asserting both what it does and what it does not touch" is a near-verbatim match to B-3's own remediation. Accurate mapping. |
| B-4 | ABSORBED | FR-15, NFR-3 cover all three exposure vectors (log.debug, argv, full-arglist-at-DEBUG). Accurate. |
| M-1 | ABSORBED | FR-2 ("no accepted value silently falls through to a different scope"). Reasonable, though FR-2 is framed around Backup Scope generically rather than the specific CLI-token-to-enum mapping bug; still catches the defect's effect. |
| M-2 | ABSORBED | FR-11 ("Every relocation option exposed on the CLI has an observable effect — no option is accepted and then discarded"). Direct and accurate. |
| M-3 | ABSORBED | FR-2 ("database scope produces a complete, well-formed Archive... It does not leave a loose dump file and no Archive"). Direct, accurate. |
| M-4 | **PARTIAL / addendum inaccuracy** | Addendum D cites only FR-11. See "Gap 1" below — FR-11 covers the relocation symptom but not the general defect (WpSite overrides silently ignored for *any* connection, including non-relocating restores/backups using a Credential Provider). Should also cite FR-14 and arguably FR-1/FR-9. |
| M-5 | **Addendum overstates; correctly out of scope in substance** | Addendum D cites FR-22 ("typed domain objects") plus "architecture." FR-22 is about typed API surface, not about decomposing a god object — it doesn't actually test for M-5. In substance this is legitimately an internal-design concern (own ADR: `wpsite-decomposition`), correctly not a PRD requirement — but the table's citation is misleading, not accurate. |
| M-6 | DELIBERATELY OUT OF SCOPE | Copy-pasted exception message string. Pure bug/hygiene, no product capability implication. Not in addendum D (correctly omitted). |
| M-7 | DELIBERATELY OUT OF SCOPE | Duplicated subprocess-run-and-check block. Code reuse / internal structure, covered only by §7.3's general "maintenance cost is a first-class constraint" and addendum C.4's incidental mention of a shared helper. No PRD FR needed. |
| M-8 | **GAP (see Gap 2)** | Test fixture/helper duplication across three modules, plus a dead unused loader. Folds into the missing test-strategy treatment — see Gap 2. |
| M-9 | **GAP (see Gap 2)** | Test that cannot pass (name-mangled `__update_config` reference) and currently hidden because the module fails to import. Addendum D cites NFR-8 — but NFR-8 ("majority of behavior verifiable without a live WordPress/MySQL") does not test for import-broken or unreachable tests. No FR/NFR requires CI to fail on a test-collection error. Real gap, and it is the exact failure mode called out in the user's own engineering rules ("a bespoke/broken harness reports success while checking nothing"). |
| M-10 | **GAP (see Gap 2)** | Assertion-free tests reporting a false PASS, and one test fully commented out. Same NFR-8 mis-citation as M-9. No requirement anywhere states the test suite must actually assert outcomes. |
| M-11 | **GAP (see Gap 2)** | Class-level `TemporaryDirectory` / order-dependent tests. Same NFR-8 mis-citation. |
| M-12 | ABSORBED (mostly) | FR-25/FR-26 imply CI exists ("succeeds in CI," "a mechanical check fails the build"), which is the load-bearing half of M-12. The narrower half of M-12's remediation — ruff/mypy/pytest as gates, least-privilege permissions, pinned actions, Dependabot — has no explicit FR, but this is normal architecture/CI-config detail, reasonably left to implementation. Acceptable. |
| M-13 | **ABSORBED, but missing from addendum table D entirely** | FR-22 ("The public API is fully type-annotated and passes a strict type check") is a precise, accurate match for the zero-annotations finding. This is a completeness gap in the addendum's table (the row is simply missing), not a PRD gap — flagging so it isn't miscounted as unaddressed. |
| M-14 | ABSORBED | NFR-5 ("Extraction cannot write outside the destination, whatever member paths it declares"). Direct, accurate. |
| M-15 | ABSORBED | NFR-4 ("Temporary working areas are per-Run and cleaned on both success and failure") addresses predictability/concurrency/leftover-dump. Accurate. |
| M-16 | ABSORBED | FR-21 ("No failure path returns a value that the process then discards"; "Invoking with no operation is an error, not a silent success"). Direct, accurate. |
| M-17 | **Partial** | Addendum D cites FR-6, FR-11. FR-6 covers `--mode` being inert on restore. FR-11's "no option accepted and discarded" is scoped to *relocation* options — `--cleanfirst` is not a relocation flag, so nothing in the PRD generally states "every declared CLI flag has an observable effect or is removed." Minor gap; low materiality since this is exactly the kind of thing a CLI-contract ADR/test would catch, but worth a line item. |
| M-18 | ABSORBED (requirement); **mechanism ADR missing — see Gap 3** | FR-20, NFR-6 cover the requirement thoroughly (Run ID on every record including subprocess boundaries, structured format, caller-bindable correlation ID). The `logging-schema-and-run-id` ADR the review recommends to pin the actual mechanism, however, is not carried anywhere in the addendum's §C (mechanism decisions) — see Gap 3. |
| M-19 | **ABSORBED, but missing from addendum table D entirely** | FR-26 is an excellent, specific match: bounded versions, dependency inventory, no pre-1.0 dependency without a recorded exit plan, and — remarkably — it names the exact `mysql-connector` → `mysql-connector-python` remediation and a mechanical staleness-window check. Like M-13, this is a completeness gap in the table, not in the PRD. |
| M-20 | **PARTIAL — GAP (see Gap 4)** | Addendum D cites "§11 runbook; documentation is a release gate" for M-20/M-21 together. §11 does cover the runbook half of M-20. It does **not** cover the other three asks: a `docs/` index, C4/sequence diagrams, or backfilling `docs/adr/`. Nowhere in the PRD does "documentation is a release gate" actually appear as a requirement — that phrase in the addendum table is not supported by the cited section. See Gap 4. |
| M-21 | **PARTIAL — GAP (see Gap 4)** | §9 fixes the specific stale claim about Python 3.6 (supported range "declared in package metadata and enforced in CI"). Nothing in the PRD requires a mechanical check that keeps README usage text in sync with the actual CLI (the review's own remediation: "regenerate the usage section from `--help` and check it in CI"). This is the precise failure class the review, and the user's global engineering rules, both call out: a rule that isn't enforced mechanically will drift again. See Gap 4. |
| M-22 | DELIBERATELY OUT OF SCOPE (mostly) | `sudo python3 setup.py install` in `build.sh`, and an interactive `git commit` in a script. Addendum C.5 names the fix ("Release via CI with trusted publishing rather than a local `twine` script running under `sudo`") as an architecture decision. No PRD FR is needed for a build-script hygiene fix; reasonably left to the packaging ADR. |
| m-1 | DELIBERATELY OUT OF SCOPE | Blanket pylint disables instead of wrapped lines. Pure lint hygiene. |
| m-2 | DELIBERATELY OUT OF SCOPE | Banner comment blocks. Pure style, explicitly the kind of finding the reconciliation brief names as legitimately homeless in a product PRD. |
| m-3 | DELIBERATELY OUT OF SCOPE | Bare `try/except: pass` around a log statement. Code-level defensive-coding hygiene. |
| m-4 | DELIBERATELY OUT OF SCOPE | Dead `site_host` property that raises `AttributeError` if ever read. A real bug, but scoped to one internal accessor with no stated product capability behind it; FR-22's "fails at construction, not at use" is adjacent but not a direct match — not worth forcing. |
| m-5 | **ABSORBED (worth noting explicitly)** | FR-23: "The package does not raise a dependency's exception types across its own public boundary." This is a precise, direct match to m-5 (raising `wpdatabase2`'s `InvalidArgumentsError` instead of a `wpbackup2` exception). Not in addendum table D (minors are out of its scope by design), but confirmed here so it isn't miscounted as a gap. |
| m-6 | DELIBERATELY OUT OF SCOPE | Wrong (copy-pasted) exception message text. Pure bug, no capability behind it. |
| m-7 | DELIBERATELY OUT OF SCOPE | Dead class-level attributes shadowed by `__init__`. Pure code hygiene. |
| m-8 | **Folds into Gap 2** | Hand-rolled `test.py` runner wrapping `coverage`/`unittest`, with coverage reporting silently disabled. This is precisely the "custom test harness" pattern the user's own global CLAUDE.md singles out as a standing violation. No PRD/addendum text requires standardizing on `pytest` or retiring `test.py`; addendum C.5 only says "and `test.py`" in a retirement list, with no rationale tied back to this finding. |
| m-9 | DELIBERATELY OUT OF SCOPE (explicitly, per the brief's own example) | Commented-out code in seven places. Textbook code-hygiene finding with no product-capability content. |
| m-10 | **GAP (see Gap 5)** | No `console_scripts` entry point; documented invocation is `python3 -m wpbackup2`. The PRD's own UJs assume an installed, directly-invocable command (UJ-1: "A systemd timer invokes wpbackup2 at 03:00 per site"), but no FR anywhere requires a proper CLI entry point. See Gap 5. |

## Gap 1 — M-4's mapping in addendum §D is too narrow

Addendum §D maps M-4 ("internals bypass `WpSite` and re-read config") to FR-11 alone, framed as
"single source of truth for the Site Descriptor." FR-11 is scoped to *relocation* — it tests that
values the operator supplies for relocation reach the rewritten `wp-config.php`. But M-4's actual
defect is broader: `WpInternalBackup` and `WpInternalRestore` re-open `WpConfigFile` and read
connection details from *that* instead of from the `WpSite` they were handed, for **every**
run, not only relocating ones. That means a `Credential Provider` (FR-14) supplying explicit
credentials, environment-sourced credentials, or a custom provider could be silently ignored by
the code that actually opens the database connection, because the connection code never
consults the resolved `Site Descriptor` — it goes back to the config file. FR-14's own testable
consequences ("Each built-in provider resolves credentials and is selectable... A library caller
can implement and pass a provider without subclassing internal types") would not, as currently
scoped, actually exercise this failure mode unless a test explicitly asserts that the credentials
used at the `mysql`/`mysqldump` boundary are the ones the Credential Provider produced — not the
ones re-read from `wp-config.php`. Recommend the addendum's §D row for M-4 cite FR-14 alongside
FR-11, or FR-14's consequences be extended to say so explicitly.

## Gap 2 — Test-suite integrity findings (M-8, M-9, M-10, M-11, m-8) have no real PRD/addendum home

Addendum §D cites NFR-8 for M-9/M-10/M-11. Read NFR-8's actual text: "The majority of behavior is
verifiable without a running WordPress installation or a live MySQL server; integration paths
that genuinely need them are identified and separated." This is a statement about *what* needs a
live dependency, not about whether the tests that exist are truthful. It would not catch any of:
a test module that fails to import (M-9), a test that calls the API and asserts nothing (M-10), a
test file that is entirely commented out and still counted as passing (M-10), class-level
`TemporaryDirectory` state that makes tests order-dependent (M-11), or fixture duplication with a
dead unused loader (M-8). None of these is a "does it need live WordPress" question; they are all
questions of whether the test suite tells the truth.

This matters more than an ordinary MAJOR cluster because it is the exact false-green failure mode
called out by name in the user's own global engineering rules ("a bespoke harness... reports
success while checking nothing... its bugs surface as false greens, the worst failure mode
available"). The review's own recommended ADR list includes `test-strategy` ("pytest, fixture
strategy, and what requires a real MySQL vs. a fake") for exactly this reason. Table D mentions a
"test strategy ADR" only once, in the M-9/10/11 cell, as a passing aside — it is never actually
tracked in addendum §C the way every other recommended ADR is (C.1–C.6 each get a subsection;
`test-strategy` gets none). m-8 (the hand-rolled `test.py` runner) is the same story: addendum
C.5 lists retiring `test.py` in a bullet with no discussion of *why*, and no PRD text says the
project standardizes on `pytest` or that CI must fail on a collection/import error.

Recommend either: (a) add an NFR or a testability consequence under an existing FR stating the
test suite must be collectible and assertive as a CI-enforced condition (ties into FR-25/FR-26's
"mechanical check fails the build"), or (b) explicitly promote `test-strategy` to a tracked
decision in addendum §C with the same treatment as C.1–C.6, and reference it from §15 Open
Questions so it isn't silently dropped between "recommended by the review" and "actually decided
somewhere."

## Gap 3 — Two of the review's nine recommended ADRs are untracked anywhere in PRD or addendum

The review's "Recommended ADRs" table lists nine decisions. Cross-checking against addendum §C
(the section whose own intro says "Each needs an ADR. None is settled here") and PRD §15 (Open
Questions):

| ADR (from review) | Tracked? |
|---|---|
| `dependency-recovery-chesney-wpconfigr` | Yes — addendum C.2 (resolved), Q-6 |
| `packaging-uv-pyproject` | Yes — addendum C.5 |
| `restore-mode-semantics` | **No.** Not in §C, not in §15, despite the review calling B-3 "the single most important action" and FR-6 depending entirely on a defined Restore Mode vocabulary the PRD deliberately leaves undefined ("Restore Mode... every destructive element is named explicitly" — but which elements, and what the modes are called, is nowhere decided). |
| `credential-handling-subprocess` | Yes — addendum C.4 |
| `logging-schema-and-run-id` | **No.** Not in §C, not in §15, despite FR-20 requiring a Run ID propagated across the subprocess boundary — the actual mechanism (structlog vs. stdlib+JSON, contextvars propagation) is completely undecided and untracked. |
| `wpsite-decomposition` | Only a passing mention in table D's M-5 cell ("architecture"); not a tracked decision in §C or §15. |
| `archive-format-contract` | Yes — addendum C.6 |
| `test-strategy` | Only a passing mention in table D's M-9/10/11 cell; not tracked in §C or §15 (see Gap 2). |
| `python-support-range` | Effectively resolved by §9 ("supported versions are those with upstream security support... declared in package metadata and enforced in CI"); reasonable to treat as decided rather than open. |

Net: of nine recommended ADRs, three (`restore-mode-semantics`, `logging-schema-and-run-id`,
`test-strategy`) and a fourth borderline one (`wpsite-decomposition`) are not carried into either
the addendum's own "needs an ADR" tracking section or the PRD's Open Questions list — despite the
addendum being the document whose stated job is exactly this kind of tracking. The first two are
the more material of the three: they sit directly underneath FR-6/FR-7/FR-9 (the B-3 fix) and
FR-20 (the M-18 fix), the two blocker/major clusters the review treats as highest priority.

## Gap 4 — M-20/M-21 (documentation): the addendum's citation overstates what the PRD actually requires

Addendum §D's cell for M-20/M-21 reads: "§11 runbook; documentation is a release gate." Checking
§11 directly: it requires a runbook ("Documentation states what a failed restore leaves behind at
each stage..."), a diagnostics command, and states failure-visibility/support expectations. It
does **not** say documentation is a release gate anywhere — that clause in the addendum table has
no textual support in the PRD. Searching the full PRD for "release gate" and "docs/adr" and
"diagram" turns up nothing outside this one addendum cell.

Concretely, of M-20's four asks (docs/ index, C4 diagram, restore sequence diagram, backfilled
`docs/adr/`), only the runbook is required by the PRD. Of M-21's asks (fix flags that don't exist,
fix the invalid dev snippet, drop the stale TODO, state the real Python range), only the Python
range is covered (§9). The broader, more durable fix the review is actually asking for — a
mechanical check that keeps documented CLI usage in sync with the real CLI ("regenerate the usage
section from `--help` and check it in CI") — has no PRD or addendum home at all. This is worth
flagging pointedly because it is the specific failure mode the review frames as self-perpetuating
("Docs that contradict the code stop the next reader from looking") and it is the same category
of failure the user's own global engineering rules treat as a first-class risk ("a rule that lives
only in prose will be violated, and the violation will be invisible... when you write a rule,
write the check that enforces it in the same change"). Recommend either adding this as an explicit
FR/NFR consequence (e.g., under FR-24's "declared public surface" or as a new documentation-sync
consequence) or, at minimum, correcting the addendum table so it doesn't claim a "release gate"
requirement that isn't in the PRD.

## Gap 5 — m-10 (no console_scripts entry point) has no PRD home despite the journeys assuming one

UJ-1 narrates "A systemd timer invokes wpbackup2 at 03:00 per site" — i.e., the vision text
assumes `wpbackup2` is a directly-invocable installed command, not `python3 -m wpbackup2`. No FR
in §5.8 (Distribution and Supply Chain) or elsewhere requires a `console_scripts` entry point.
FR-25 covers install resolvability but not the shape of what gets installed on the PATH. This is
minor relative to the four gaps above, but it is a real, product-visible capability the review
named and the PRD silently drops — worth a one-line FR (or a consequence under FR-25) requiring
an installed `wpbackup2` command.

## Summary — none of the 4 blockers or 4 addendum-cited majors are actually dropped

All 4 BLOCKERs are accurately absorbed. The clearest real gaps are concentrated in exactly the
areas the reconciliation brief flagged for extra scrutiny: test-suite integrity (M-8/M-9/M-10/M-11
+ m-8), the §10 documentation findings (M-20/M-21), and two of the review's nine recommended ADRs
(`restore-mode-semantics`, `logging-schema-and-run-id`) going untracked despite sitting directly
under the PRD's two highest-priority requirement clusters (FR-6/7/9 and FR-20). M-4's addendum
citation is too narrow (misses FR-14). M-5's citation (FR-22) doesn't actually match the finding
though the underlying disposition (out of PRD scope, architecture concern) is correct. M-13 and
M-19 are well absorbed by the PRD but simply missing as rows from the addendum's own table.
