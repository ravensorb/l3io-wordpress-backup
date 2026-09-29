# ADR-0008: boto3 becomes an optional extra via lazy import

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD Q-9, FR-14
- **Principle(s) in tension:** Core §1 separation of concerns, §7 footprint

## Context

PRD FR-14 requires that a base install pull no AWS libraries. It cannot today: `wpdatabase2/classes/credentials.py:3` imports `Secret` at module scope, and `wpdatabase2/classes/secret.py:7` imports `boto3` at module scope. Importing `WpCredentials` — which every `wpbackup2` path does — therefore drags `boto3` and `botocore` into every installation, AWS user or not. PRD Q-9 left open whether this was fixable from outside `wpbackup2`.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. **Lazy import inside `Secret`** | Three lines; `boto3` moves to an `aws` extra; no API change | Import error surfaces later, at resolve time | §1, §7 |
| B. Split a `wpdatabase2-aws` package | Hard boundary | A fourth package to release for one class | Fails §5 |
| C. `botocore` alone | Smaller install | Low-level API explicitly outside boto3's stability guarantees | Fails §8 |
| D. Rewrite FR-14's consequence to match reality | Honest | Accepts a permanent unnecessary dependency | Rejected — the fix is cheap |

## Decision

**Option A.** `boto3` moves to the `aws` optional extra in `wpdatabase2`; `Secret` imports it inside the method that uses it and raises a package-owned error naming the extra when absent. Generalized as AD-8: no module-scope import of an optional dependency, anywhere.

CI asserts a base install — no extras — imports every public module.

## Consequences

- Positive: answers Q-9 affirmatively and cheaply; removes `boto3` + `botocore` + `s3transfer` + `jmespath` from the default install.
- Negative: an AWS user who forgets the extra learns at resolve time rather than import time — mitigated by the named error and by preflight (AD-13).
