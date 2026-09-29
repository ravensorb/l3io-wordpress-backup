# ADR-0004: PyMySQL as the MySQL driver

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** n/a
- **Principle(s) in tension:** Core §7 dependency selection — licence and maintenance

## Context

`wpdatabase2` depends on `mysql-connector` — version 2.2.9, last released **2019-04-01**. That is the superseded Oracle-uploaded distribution name, seven years stale, in the runtime path of a backup tool. A replacement is required by PRD FR-26.

## Options considered

Verified on PyPI 2026-09-15.

| Option | Version / date | Pure Python | Licence | Wheels | Standards fit |
|---|---|---|---|---|---|
| A. **PyMySQL** | 1.2.0, 2026-05-19 | yes | **MIT** | one universal wheel | §7 — clean |
| B. `mysqlclient` | 2.3.0, 2026-09-14 | no (C) | **GPL-2.0** | **Windows only**; Linux/macOS build from sdist needing dev headers | Fails §7 — copyleft in a shipped artifact, and an install that breaks without a toolchain |
| C. `mysql-connector-python` | 26.7.0, 2026-07-29 | hybrid | GPLv2 + FOSS Exception | broad | Usable, but licence friction §7 explicitly warns against |

## Decision

**Option A, PyMySQL.** MIT, pure Python, one `py3-none-any` wheel, so a base install works everywhere with no build step — which is the point, given FR-25's requirement that installation be reproducible on every supported version.

`mysqlclient` may be offered later as a performance extra; its GPL-2.0 licence makes it unacceptable as a default dependency of an MIT-licensed package.

## Consequences

- Positive: removes the stalest dependency in the graph and the only licence question in it.
- Negative: PyMySQL is slower than the C drivers. The workload is dominated by `mysqldump`/`mysql` subprocesses, so the driver is used for provisioning queries only — the difference is not on any hot path.
- Follow-up: record PyMySQL in the dependency inventory with licence and reason (FR-26).
