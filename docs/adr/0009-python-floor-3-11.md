# ADR-0009: Python floor of 3.11

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD §9
- **Principle(s) in tension:** Core §8 GA over preview; Python overlay — supported, non-EOL runtime

## Context

The README currently claims "Python 3.6 or newer" — EOL since 2021 — and no package declares `requires-python`. A floor must be chosen for three packages released together.

Verified against devguide.python.org, 2026-09-15: 3.9 is EOL (2025-10-31); **3.10 reaches EOL 2026-10**, roughly six weeks away; 3.11 security-only to 2027-10; 3.12 to 2028-10; 3.13 and 3.14 in bugfix.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. `>=3.10` | Widest reach | Dies within the release window of anything shipped now | Fails the overlay's non-EOL rule |
| B. **`>=3.11`** | Every supported version is in security support for the foreseeable release cadence; mypy 2.x requires ≥3.10 to run anyway | Excludes 3.10 holdouts | Overlay-compliant |
| C. `>=3.14` | `tarfile` extraction defaults to `filter='data'` for free | Excludes almost every current deployment for a benefit obtainable by passing the argument explicitly | Fails on reach for no real gain |

## Decision

**Option B, `requires-python = ">=3.11"`**, declared in all three `pyproject.toml` files and enforced by a CI matrix covering every version in the range.

Option C's only advantage is dropped by AD-11, which mandates passing `filter='data'` explicitly on every call regardless of interpreter — necessary anyway, because on 3.11 the parameter's presence is patch-level-dependent via backport and on 3.12/3.13 the default is still `fully_trusted`.

## Consequences

- Positive: no supported version is EOL during the v1.0 support window.
- Negative: 3.10 users must upgrade; it is weeks from EOL, so this is the right prompt rather than a burden.
- Follow-up: the floor is reviewed at each Python EOL, not at each release.
