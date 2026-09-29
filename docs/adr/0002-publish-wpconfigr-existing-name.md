# ADR-0002: Publish wpconfigr under its existing name, adopting maintenance

> **Superseded by [ADR-0012](0012-package-naming-l3io-wp-namespace.md).** Two facts found after this was written overturn it: upstream did not stop — it renamed and republished as `wpconfigger` in 2022 — and publishing this fork as `wpconfigr` would both misattribute (the metadata still credits Cariad Eccleston and points at his repository) and likely fail to upload, since PyPI permanently burns filenames and the fork is still version 1.4. The capability decision in ADR-0010 stands; only the name and provenance change.

- **Status:** Superseded by ADR-0012
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD Q-6
- **Principle(s) in tension:** Core §7 dependency selection, §8 GA over preview

## Context

`wpconfigr` is a hard runtime dependency of both `wpdatabase2` and `wpbackup2` and returns HTTP 404 from PyPI, so `pip install wpbackup2` cannot resolve. The code is not lost: `py-wpconfigr` holds version 1.4, 343 lines across four modules, zero runtime dependencies. It is an **unmodified** fork of `cariad/py-wpconfigr` — `git log` shows no commit by anyone but the original author, the last dated 2018-12-06, and `setup.py` still declares upstream's author, email and URL. Why it is absent from PyPI is not determinable from the repository: no tags, no changelog, no release credentials distinguish "never published" from "published and withdrawn".

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. **Publish as `wpconfigr`** | Existing declarations in both dependents keep working; no coordinated rename | Claims a name whose history is not ours; if upstream ever returns, contested | §7 — but requires taking on maintenance explicitly |
| B. Publish under a new name | Clean provenance | Coordinated change in two repos; two names in the wild for one library | Neutral |
| C. Vendor into `wpbackup2` | No third package to release | `wpdatabase2` also needs it → duplication, or a cycle | Fails §2 |
| D. Delegate to `wp config get/set` | No parser to own at all | Makes WP-CLI mandatory for *all* operations, contradicting PRD FR-13 | Fails FR-13 |

## Decision

**Option A.** Publish as `wpconfigr` 1.5, with authorship and project URL corrected to this project and the MIT © 2018 Cariad Eccleston notice retained. This is an explicit adoption of unmaintained code — cheap at 343 lines, but it is adoption, not inheritance of a maintained line.

Both dependents pin `wpconfigr>=1.5,<2`. The current `>=1.0.0,<=2.0.0` in both repos is replaced: it admits an unreviewed 2.0 (`<=2.0.0` includes 2.0.0 exactly).

## Consequences

- Positive: resolves the outage cheaply and keeps the shared kernel dependency-free (AD-2).
- Negative: we now own a PHP-subset parser (see ADR-0010) and a name with someone else's history.
- Follow-up: if upstream republishes, we hold the name — reach out rather than contest it.
