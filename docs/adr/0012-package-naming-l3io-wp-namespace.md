# ADR-0012: Publish as the `l3io-wp-*` family under a PEP 420 namespace

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** n/a
- **Principle(s) in tension:** Core §7 dependency selection, §1 separation of concerns

This answers PRD Q-6 and Q-7, and supersedes the naming decision in ADR-0002; the
capability decision in ADR-0010 stands, only the name and provenance change.

## Context

Verified on PyPI 2026-09-16:

- `pip install wpbackup2` fails **today** with `ResolutionImpossible` — 0.2.21 requires `chesney` and `wpconfigr`, both 404. Every published release is uninstallable.
- `wpbackup2` and `wpdatabase2` are owned by this maintainer (author "Shawn Anderson"), last released 2020-12-04. `wpconfigr` is free; so are `wpbackup`, `wpdatabase` and `chesney` — Cariad Eccleston's entire PyPI presence was removed.
- Upstream did **not** stop. `cariad/py-wpconfigr` was renamed in 2022 (PR #7) after upstream issue #6 reported the same install failure; Cariad deleted the package years earlier, could not republish, and shipped it as **`wpconfigger`** (v1.0.0, 2022-09-07), which is live and correctly attributed. PyPI permanently burns *filenames*, so re-uploading `wpconfigr-1.4` was never going to work — the likelier cause of his failure than name reservation.
- `wpbackup2` reads as "version 2 of `wpbackup`", a package nobody can install, and sits near the actively-maintained `WPBackupTool`.
- `wp-toolkit` is free on PyPI but is **a Plesk product** ("WP Toolkit extension — Plesk"). `wpsuite` is held on npm. `l3io`, `l3io-wp` and all three children are free on PyPI and npm.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. Keep `wpbackup2`, publish the fork as `wpconfigr` | No migration | Misattributes — the fork's metadata still names Cariad and points at his repo; the 1.4 filename is burned; trails a package that does not exist | Rejected |
| B. Depend on upstream `wpconfigger` | Correct credit by construction; zero runtime deps | One release, one maintainer — the same bus factor that produced this outage; no ability to fix the parser | Viable, not chosen |
| C. `wpstack-*` / `wpsuite-*` | Function-first, discoverable | `wpsuite` held on npm; neither signals ownership | Viable, not chosen |
| D. **`l3io-wp-*` under a PEP 420 namespace** | Every name free on PyPI and npm; unambiguous ownership; consistent with existing `l3io-*` tooling; scales to future packages | Less discoverable to a stranger searching "wordpress backup" | §7, and PEP 423's live advice that a top-level name signal ownership |

## Decision

**Option D.**

| Distribution | Import | Replaces |
|---|---|---|
| `l3io-wp-config` | `l3io.wp.config` | the `wpconfigr` fork (never published) |
| `l3io-wp-database` | `l3io.wp.database` | `wpdatabase2` |
| `l3io-wp-backup` | `l3io.wp.backup` | `wpbackup2` |

Imports are a **PEP 420 native namespace** at `l3io.wp`. The discipline this demands is an architectural invariant, not a packaging detail, and is recorded as **AD-27**: no distribution ships an `__init__.py` at `l3io/` or `l3io/wp/`, ever. One package getting that wrong breaks imports for the other two, in a way that is hard to diagnose.

**Discoverability is bought back deliberately**, since the name no longer does that work:

- `pyproject.toml` keywords and classifiers carry the function — wordpress, backup, restore, migration, mysqldump, wp-cli.
- `wpbackup`, `wpdatabase` and `wpconfigr` are registered as thin pointer packages. These are the names a stranger searches and the names this project's own history references; leaving them open also leaves them available for revival hijack.

**The two owned names get a final pointer release**, not abandonment: `wpbackup2` and `wpdatabase2` each ship one last version whose only dependency is the corresponding `l3io-wp-*` package, emitting a `DeprecationWarning` on import and naming the replacement. This is the only migration path PyPI offers — it has no rename, redirect or alias mechanism (warehouse #1919, still open). It also repairs `pip install wpbackup2` for everyone currently hitting `ResolutionImpossible`.

**The fork is republished with corrected metadata** — this project's author, email and repository URL, a new name (so PyPI's burned `wpconfigr-1.4` filename no longer applies), and a README credit to Cariad Eccleston's MIT original. Shipping a package under our control that credits someone else and points bug reports at their repository is the specific thing being fixed.

## Consequences

- Positive: installability restored; no public name conflict anywhere checked; ownership legible; room for future `l3io-*` packages.
- Negative: a stranger searching PyPI for "wordpress backup" will not find `l3io-wp-backup` by name — mitigated but not eliminated by keywords and the pointer packages. **This bears directly on SM-1**, whose target is three independent repositories importing the API within twelve months; if that metric fails, name discoverability is a candidate cause and should be examined before concluding the library positioning was wrong.
- Negative: five distributions to publish instead of three, plus two pointer releases.
- **Revisit when:** SM-1 reports at the twelve-month mark, or if a future `l3io` Python package makes the namespace discipline of AD-27 burdensome.

## Amendment — 2026-09-29: the two columns are INDEPENDENT

The distribution names changed; the namespace did not. The table above pairs
`l3io-wp-<area>` with `l3io.wp.<area>`, which reads as a rule that the
distribution name determines the import path. **It is not.** Current state:

| Distribution | Imports as |
| --- | --- |
| `l3io-wordpress-config` | `l3io.wp.config` |
| `l3io-wordpress-database` | `l3io.wp.database` |
| `l3io-wordpress-backup` | `l3io.wp.backup` |

**The namespace is `l3io.wp.*` and is shared, so no single repository can change
it.** A distribution rename is local to one repo; a namespace change is not, and
renaming one of three means the three share no namespace at all.

That inference has now been made twice and acted on twice. `py-wpconfigr` read
the distribution rename as a namespace move, renamed `src/l3io/wp` to
`src/l3io/wordpress`, and broke AD-27 immediately — the coexistence check failed
on both install shapes with `ModuleNotFoundError` for the sibling. This
repository made the same inference an hour later and moved its own tree the same
way, from reading that sibling's mid-change working tree as if it were the
specification. Both reverted.

So the original table did not merely hold stale values; its **shape** invited the
error. Anyone updating it should keep the columns visibly independent.

**Mechanically enforced** in `scripts/check-cicd-alignment.py`: a cross-repo rule
asserts each distribution matches `l3io-wordpress-<area>` and each namespace root
is `l3io/wp`, checked **separately** so neither is derived from the other. It
reads each sibling's **committed** `pyproject.toml` rather than its working tree,
because reading the working tree is what produced the second instance.

Console scripts are unaffected and do not follow the distribution rename:
`l3io-wordpress-backup` still ships `wpbackup2` per AD-22, which ADR-0007 records
as the outward-compatibility exception to naming a script for its distribution.

## Amendment — 2026-10-20: the "above 1.4" version premise

The Decision first required the republished fork to carry "a version above 1.4", which
only mattered while it was to reuse the `wpconfigr` name, where PyPI had burned the
`wpconfigr-1.4` filename. Under a new distribution name no filename is burned and no
version floor applies. Every family package restarted its versioning: config and database
released **v0.1.0**, and backup's first release is **1.0.0** (AD-22 makes its rewrite a
major version). The body now says "a new name" where it said "a version above 1.4".
