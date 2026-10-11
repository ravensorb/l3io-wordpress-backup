# PRD Fidelity Review — wpbackup2 PRD (2026-09-12)

Adversarial truth check of `prd.md` and `addendum.md` against the actual codebase
(`py-wordpress-backup`), the sibling repos `py-wpconfigr` and `py-wordpress-database`,
and live PyPI/GitHub data. Scope: truth only, no style/structure opinions.

---

## 1. FALSE / MISLEADING: "maintained fork" is not supported by the evidence

**Quotes:**
- prd.md:35 — "`wpconfigr` is **not lost** — it exists as a maintained fork at version 1.4 in the sibling repository `py-wpconfigr`, 343 lines with no runtime dependencies of its own, awaiting publication under this project's namespace."
- prd.md:460 — "`wpconfigr` ... **already exists as a maintained fork** — version 1.4 in the sibling repository `py-wpconfigr`..."
- addendum.md:58 — "`wpconfigr` is **not lost**. It exists as a maintained fork at version 1.4 ..."

**What is actually true:** The local `py-wpconfigr` repository has **zero commits by anyone other than Cariad Eccleston**. `git log --all --format="%an" | sort -u` returns only `Cariad Eccleston`. The last commit is `Thu Dec 6 20:59:52 2018` — nearly 8 years stale as of the PRD's own 2026-09-12 date. The repo's `setup.py` still declares `author='Cariad Eccleston'`, `author_email='cariad@cariad.me'`, and `url='https://github.com/cariad/py-wpconfigr'` (the *upstream* repo, not `ravensorb/py-wpconfigr`). The only thing that differentiates this "fork" from a plain clone is that `git remote -v` points at `github.com/ravensorb/py-wpconfigr` — there is no evidence of any independent maintenance activity: no new commits, no changed package metadata, no changelog entry.

This contrasts directly with the sibling `wpdatabase2` repo, which genuinely does have Shawn Anderson commits (e.g., "Bump version: 0.0.14 → 0.0.15", "Updated boto3 version") — i.e., the PRD's authors had a real example of an actually-maintained sibling package one directory over and did not apply the same scrutiny to `wpconfigr`.

The LOC count (343) and version (1.4) are themselves accurate — verified by summing `wpconfigr/__init__.py` (7) + `wp_config_file.py` (52) + `__main__.py` (80) + `wp_config_string.py` (204) = 343, and `setup.py:version='1.4'`. Only the word "maintained" is false.

**Severity:** High. This is exactly the kind of overclaim the "Why Now" section (§2) leans on to justify urgency ("The product is offline for want of a release, not for want of code") — the code exists, but calling it "maintained" overstates its state and could mislead a reader (or an architect) into assuming ongoing upstream tracking/patches that are not happening.

---

## 2. UNSUPPORTED / STALE: "It is absent from PyPI because it was never published, not because it was withdrawn"

**Quote:** addendum.md:58 — "It is absent from PyPI because it was never published, not because it was withdrawn."

**What is actually true:** Nothing in the local repo (no PyPI credentials, no `.pypirc`, no changelog, no tag matching a release workflow) supports distinguishing "never published" from "published then removed." This is stated as verified fact but is an inference dressed as certainty. Given `pypi.org/simple/wpconfigr/` returns a plain 404 (confirmed via curl), that is consistent with either explanation. Minor but worth flagging since the document elsewhere is careful to mark inferences with `[ASSUMPTION]` — this one isn't, despite being no more certain than the tagged ones.

---

## 3. INTERNAL CONTRADICTION: FR-25 asserts the "clean" AWS-optional claim that FR-14 explicitly flags as unresolvable

**Quotes:**
- prd.md:251 (FR-14, flagged): "AWS Secrets Manager is supported as a provider, and its dependencies are optional — a base install pulls no AWS libraries, **transitively included**. `[ASSUMPTION: achieving this requires \`boto3\` to become an optional extra in the sibling \`wpdatabase2\` package, where it is currently a hard runtime dependency; see §15 Q-9]`"
- prd.md:387 (FR-25, **not flagged**): "Optional capabilities (AWS, remote targets) are optional extras and their absence does not break a base install."
- Q-9 itself (prd.md:562) even says: "If the sibling package will not change, FR-14's consequence must be rewritten to match reality rather than left aspirational" — but only mentions FR-14, not FR-25.

**What is actually true:** `wpdatabase2/setup.py` declares `install_requires=['boto3>=1.9.0', 'mysql-connector>=2.1.0', 'wpconfigr>=1.0.0,<=2.0.0']` — `boto3` is a **hard, unconditional runtime dependency**, not an extra. Since `wpbackup2` depends on `wpdatabase2` unconditionally, *any* `pip install wpbackup2` pulls `boto3` today, regardless of whether the AWS credential provider is used. FR-25 is listed in the v1.0 MVP scope (§13.2: "Resolvable, locked, reproducible installation on supported Python versions (FR-25, FR-26, FR-27)"), and its consequence bullet asserts the exact "no AWS libraries in a base install" property that Q-9 says is "unsatisfiable from this repository alone." The Assumptions Index (§16) attaches the `[ASSUMPTION]`/Q-9 tag only to §5.4/FR-14, not to FR-25 — so FR-25's identical, equally-unresolved claim ships in the v1.0-scoped requirements text as if it were settled. This is precisely the contradiction the review brief asked to check for, and it is **not** properly flagged — FR-25 is the "other part of the document [that] still asserts the clean version."

**Severity:** High — this is a real, checkable internal contradiction, not a nuance.

---

## 4. FACTUAL ERROR: "FR-1…FR-31" — the document only defines FR-1 through FR-27

**Quote:** prd.md:15 — "features are grouped with functional requirements nested and numbered globally (FR-1…FR-31) so downstream artifacts have stable references"

**What is actually true:** `grep -o "FR-[0-9]*" prd.md | sort -u` shows the highest defined requirement is **FR-27** (External tool dependency declaration, §5.8). FR-28, FR-29, FR-30 and FR-31 do not exist anywhere else in the document — "FR-31" appears exactly once, in this range statement. This reads as a stale artifact from an earlier draft that had more requirements before a revision trimmed the set (consistent with the brief's warning that this PRD was revised mid-flight and accumulates stale claims). Downstream BMad workflows (epics/stories) that trust this range statement for "stable references" will look for FR-28–FR-31 and find nothing.

---

## 5. IMPRECISION / apparent internal inconsistency: total LOC claim (~1,265) vs. addendum's own diagram (909)

**Quotes:**
- prd.md:13 — "informed by — but not limited to — the ~1,265 LOC that exist today at v0.2.21"
- addendum.md:67 — "`wpbackup2  (909 LOC)`" (dependency-graph diagram)

**What is actually true:** `wpbackup2/` package source sums to exactly **909 LOC** (verified by `wc -l` across all `.py` files under `wpbackup2/`, matching the addendum's diagram exactly: 2+19+194+16+8+16+15+14+16+141+159+6+224+79 = 909). `tests/` sums to **356 LOC**. 909 + 356 = **1,265**, so the PRD's §0 figure appears to be package + tests combined, while the addendum's diagram (in the same document set, describing "the dependency graph as published") labels the same package with only the 909 figure and no stated methodology difference. Neither number is fabricated, but the two documents present two different totals for "how big is wpbackup2" without reconciling them or stating that one includes tests — a reader comparing §0 to addendum §C.2b will reasonably conclude the two disagree.

---

## 6. UNVERIFIED CLAIM STATED AS FACT: "cariad/py-wordpress-backup (PyPI `wpbackup`)"

**Quote:** addendum.md:20 — `| **cariad/py-wordpress-backup** (PyPI `wpbackup`) | ... |`

**What is actually true:** `pypi.org/pypi/wpbackup/json` returns **404** — the package does not currently resolve on PyPI under that name (verified by curl). The upstream repo's own `setup.py` does declare `name='wpbackup'`, so the *intended* name is right, but the table presents "(PyPI `wpbackup`)" as a plain descriptive fact with no caveat, in a document whose entire premise is "packages returning 404 from PyPI is the load-bearing crisis." The addendum does mark "Maintenance status unverified" for this same row but does not flag that the package itself is not (or no longer) resolvable — an omission inconsistent with the rigor applied elsewhere in the same table.

---

## 7. MISMATCH: README credit link does not point at the credited predecessor

**Quotes:**
- prd.md:501 (§13.1) — "**Not novel.** `cariad/py-wordpress-backup` did substantially this first and is credited; ..."
- addendum.md:20 — "*Not a gap — a lineage.* ... Already credited in the current README"

**What is actually true:** `README.md:18` reads: `Credit for the original version of this goes to [Cariad Eccleston](https://github.com/cariad/py-wordpress-database).` — the hyperlink points to **`cariad/py-wordpress-database`** (a different repository, the DB package), not `cariad/py-wordpress-backup` (the actual predecessor being discussed in §13.1 and addendum §A). The credit line names the right person but the wrong repo. Both `prd.md` and `addendum.md` assert the README credits "`cariad/py-wordpress-backup`" specifically, and/or call the credit adequate/accurate, without noting that the actual link target is wrong. This matters because §12's risk table explicitly worries about "positioned as novel when a near-identical predecessor exists" and proposes "state the lineage ... plainly" as the mitigation — but the current README's lineage statement is itself broken.

---

## 8. INTERNAL TENSION: §1's "CLI control usually behind a paywall" vs. the addendum's own competitive research

**Quotes:**
- prd.md:21 (§1) — "The plugin ecosystem — UpdraftPlus, Duplicator, All-in-One WP Migration — is excellent and WordPress-admin-first, with CLI control usually behind a paywall and automation bolted on afterward."
- addendum.md:16 — "**All-in-One WP Migration** | `wp ai1wm backup` / `restore` built into core | CLI present and **free** | Remote storage behind paid extensions"

**What is actually true:** The addendum's own competitive-landscape table (produced the same day, cited as the evidentiary basis for §1) reports that All-in-One WP Migration's CLI is present and free — only its *remote storage* is paywalled. Duplicator's row makes no paywall claim about its CLI either (only UpdraftPlus explicitly has "WP-CLI control is a Premium add-on"). §1 names all three tools together as examples of CLI-behind-a-paywall, which its own supporting addendum contradicts for at least one of the three. The "usually" hedge softens but does not resolve this — one of the three named examples is stated elsewhere in the same document set as the opposite of what §1 claims.

---

## 9. OVERSTATED CONFIDENCE: WP-CLI called "the reference implementation" while the addendum lists three equivalent tools

**Quotes:**
- prd.md:203 (§5.3) — "wpbackup2 delegates that rewrite to WP-CLI's `search-replace`, which is the reference implementation."
- prd.md:91 (Glossary) — "wpbackup2 delegates serialization-safe database URL rewriting to it [WP-CLI]." (stated as established fact, no hedge)
- addendum.md:34 — "WP-CLI `search-replace`, Duplicator, and `interconnect/it Search-Replace-DB` all solve it identically: unserialize each value, replace within the real string, re-serialize..."

**What is actually true:** The addendum's own evidence section (§B) states three separate tools solve the serialization problem "identically" — none is singled out as more canonical or "reference" than the others. Calling WP-CLI specifically "the reference implementation" in the PRD body is a stronger claim than the addendum's own cited evidence supports; "the most convenient one to shell out to, with no PHP-parser ownership cost" would match the evidence, "the reference implementation" implies a canonical/authoritative status not established anywhere in the sourced material.

---

## 10. Confirmed accurate (spot-checked, no error found)

For completeness — these specific, checkable claims were verified against ground truth and found **correct**, so they are not findings, but are recorded since they were explicitly named in the review brief:

- `chesney.is_appointed()` is called exactly once, at `wpbackup2/__main__.py:164` — confirmed by grep; only import is line 9, only call is line 164.
- `wpconfigr` returns PyPI 404, `chesney` returns PyPI 404, `wpdatabase2` returns PyPI 200 at version `0.0.15` with upload date `2020-12-04` — all confirmed via `pypi.org/pypi/<name>/json`.
- `mysql-connector` latest is `2.2.9`, uploaded `2019-04-01`; `mysql-connector-python` latest is `26.7.0`, uploaded `2026-07-29` — both confirmed via PyPI JSON API, matching addendum §C.2b/§F exactly.
- `wpconfigr` package LOC = 343 across 4 files; `wpdatabase2` package LOC = 752; `wpbackup2` package LOC = 909 — all confirmed by direct line counts.
- `wpconfigr>=1.0.0,<=2.0.0` is declared identically in both `wpbackup2/setup.py` and `wpdatabase2/setup.py` — confirmed.
- `wpdatabase2/setup.py` declares `boto3>=1.9.0` and `mysql-connector>=2.1.0` as hard runtime dependencies — confirmed (this is the evidence *behind* finding #3 above, not a contradiction of it).
- README's Python 3.6 claim ("py-wordpress-backup requires Python 3.6 or newer") is real and current, supporting §9's statement that it "is not a target."
- `--mode db` choice vs. `str(args.mode).upper() == "DATABASE"` comparison in `__main__.py` confirms the carried-forward finding M-1 (`db`.upper() = `DB` ≠ `DATABASE`) is accurate, not stale.
- The Assumptions Index (§16) round-trips correctly against the seven actual inline `[ASSUMPTION]` tags in `prd.md` (lines 251, 276, 417, 458, 473, 499, 528) — every tag has a matching index entry and Q-number, and vice versa. No drift found here.
- `wpconfigr` is imported directly by `wpbackup2` (three call sites: `wp_internal_backup.py`, `wpsite.py`, `wp_internal_restore.py`), supporting §13.1's "still relied on directly" — confirmed.

---

## Summary of severity

| # | Finding | Severity |
|---|---|---|
| 1 | "maintained fork" (wpconfigr) unsupported — zero independent commits, 8-year-stale, metadata still points at upstream | High |
| 3 | FR-25 silently asserts the same unresolved AWS-optional claim that FR-14/Q-9 explicitly flags as unsatisfiable | High |
| 4 | "FR-1…FR-31" range is stale — document only defines through FR-27 | Medium |
| 7 | README credit link points to the wrong upstream repo; PRD/addendum assert the credit is adequate without checking the link target | Medium |
| 5 | Two different total-LOC figures (1,265 vs 909) for wpbackup2 presented without reconciliation | Low-Medium |
| 8 | §1's "CLI behind paywall" claim about All-in-One WP Migration contradicted by addendum's own research table | Low-Medium |
| 2 | "never published, not withdrawn" stated as fact with no supporting evidence | Low |
| 6 | cariad's PyPI package name asserted without noting it doesn't currently resolve | Low |
| 9 | WP-CLI called "the reference implementation" — stronger than the addendum's own three-way-tie evidence | Low |
