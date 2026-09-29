# ADR-0001: Ports and adapters with a functional core

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** n/a
- **Principle(s) in tension:** Core §1 separation of concerns, §4 testability, §5 brevity

## Context

The existing packages put decisions and effects in the same methods. `--what-if` is an `if not self.__what_if:` repeated at eight effect sites, and `restore_mode` was passed to `restore()` then dropped at two sub-calls, making `shutil.rmtree` unconditional. Both are one defect class: a value every call site must remember to honor. PRD NFR-8 also requires most behavior to be testable without a live WordPress or MySQL, which the current layout cannot deliver.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. Keep class-per-operation, fix the bugs | Smallest diff | Leaves the defect class intact; every new effect site is another chance to forget | Fails §4 — untestable without a live stack |
| B. **Ports and adapters, functional core** | Dry Run becomes adapter selection, not a conditional; core is pure and unit-testable; ratifies what `wpconfigr` already does | More indirection; more files for a small codebase | §1, §4 directly |
| C. Full clean/onion architecture | Maximal decoupling | Ceremony far exceeding ~2,000 LOC of product | Fails §5 |

## Decision

**Option B.** `domain/` and `core/` are pure and import no I/O module; effects are reached only through `ports/` Protocols satisfied by `adapters/`. Composition roots (`cli/`, `api/`) bind adapters and the Run ID. Enforced by an import-linter contract in CI — a rule that lives only in prose will be violated invisibly (§3).

`wpconfigr` already splits `WpConfigString` (pure) from `WpConfigFile` (I/O). This ratifies an existing convention rather than importing a new one.

## Consequences

- Positive: Dry Run correctness is structural (AD-4). A new adapter cannot forget the flag because there is no flag. The core tests without fixtures.
- Negative: more indirection than the current code; contributors must learn where a change belongs.
- Follow-up: bind an import-linter version after verifying it current; the contract is the enforcement, not review.
