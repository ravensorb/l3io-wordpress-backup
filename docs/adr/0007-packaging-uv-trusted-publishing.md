# ADR-0007: uv, PEP 621, and trusted publishing across three repositories

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD FR-25, FR-26, Release A
- **Principle(s) in tension:** Python overlay — packaging; Core §3 enforce mechanically

## Context

All three repos use `setup.py` with no lockfile. `build.sh` runs `sudo python3 setup.py install`, and `publish.sh` runs a local `twine`. There is no CI in any of the three. The Python overlay calls the absence of a locked, reproducible install path a BLOCKER — and the packaging outage this project is recovering from is exactly what that rule exists to prevent.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. **uv + PEP 621** | One tool for envs, locking, build and publish; fastest; `uv.lock` committed; PEP 735 dependency-groups | Pre-1.0 tool, pin it | Overlay names uv the default preference |
| B. Poetry | Established | Second tool for build/publish; slower | Acceptable, not preferred |
| C. Keep `setup.py`, add `requirements.txt` | Smallest change | Overlay explicitly rejects a hand-maintained manifest as source of truth | Fails the overlay |

## Decision

**Option A**, uniformly across all three repositories. `pyproject.toml` is the single source of truth; `uv.lock` committed; CI runs `uv sync --locked`. Build with `uv build --no-sources`. **That guarantee is narrower than it first reads, and the two halves are worth keeping apart:**

- **What it does guarantee — resolved dependency metadata is clean.** A wheel's `METADATA` and an sdist's `PKG-INFO` carry only the declared requirement (`Requires-Dist: l3io-wp-config>=1.5.0`), with no `git+`, no `@ git`, no `file://` and no local path, even when `[tool.uv.sources]` points at a working tree or a git branch. Verified on real artifacts from two of the three packages.
- **What it does NOT guarantee — the sdist's own `pyproject.toml` is unchanged.** The sdist still ships the `[tool.uv.sources]` table and `[tool.uv] required-version` verbatim. These are inert today because uv honours them for the project being *developed*, not for a dependency it is building from an sdist, and pip ignores `[tool.uv]` entirely — confirmed by installing an sdist with a deliberately different uv version and with plain pip. **The safety therefore rests on installer behaviour, not on the artifact being clean.** Anyone reading the stronger claim would conclude the artifact is clean and be right about the outcome for the wrong reason; if uv's handling of sdist-embedded configuration changes, this needs re-testing. Publish with GitHub Actions **trusted publishing** — no long-lived token, no local script, no `sudo`. Retire `setup.py`, `setup.cfg`, `build.sh`, `publish.sh` and `test.py`.

Verified 2026-09-15: uv 0.12.15, PEP 735 dependency-groups supported, `--locked` fails on a stale lockfile.

## Console scripts

Recorded here because it was decided in conversation and implemented in code without
ever reaching a governing document — a correct decision preserved in exactly one place,
where the code cannot explain why.

**Every distribution in the family that has a command-line surface declares a console
script under `[project.scripts]`, named for the distribution**, and keeps
`python -m <import.path>` working alongside it rather than instead of it. `l3io-wordpress-config`
ships `l3io-wordpress-config = "l3io.wp.config.cli.main:main"` and `l3io-wordpress-database`
ships `l3io-wordpress-database = "l3io.wp.database.cli:main"` on that basis (both at v0.1.0;
the script names follow the distribution names that ADR-0012's 2026-09-29 amendment
settled, not the earlier `l3io-wp-*` form this section first recorded).

**`l3io-wp-backup` is the deliberate exception and names its script `wpbackup2`.** AD-22
freezes the outward CLI, so the entry point is named for the **preserved interface**, not
for the distribution — an operator's existing cron line must keep working, and renaming the
command would break exactly the callers AD-22 exists to protect. `python -m wpbackup2` is
preserved for the same reason and needs its own packaging provision, since
`packages = ["src/l3io"]` alone cannot ship a top-level `wpbackup2` module.

The rule therefore reads: named for the distribution, **unless an outward-compatibility
constraint names it otherwise**, and where it does, that constraint is cited at the
declaration.

## Consequences

- Positive: reproducible installs, and the release gate of AD-15 has somewhere to run.
- Negative: uv is pre-1.0 — pin it and bump deliberately.
- Follow-up: CI must install the **built artifact from the index** in a clean environment, not the working tree. Installing the working tree would have passed while `wpconfigr` was unresolvable — the exact blind spot that let this ship.
