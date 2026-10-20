# ADR-0013: GitHub Actions CI that replays locally under act, with secrets from Infisical

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** n/a
- **Principle(s) in tension:** Core §3 enforce mechanically, §7 dependency selection; GitHub Actions overlay

This implements PRD §11's local-reproducibility requirement rather than departing from
anything.

## Context

None of the three repositories has CI. Every gate the spine relies on — AD-1's layer contract, AD-4's dry-run rule, AD-5's defaulted-mode check, AD-11, AD-21, AD-25, AD-27, and FR-25's clean-environment install — exists only as prose until something runs it. The maintainer additionally requires the pipeline be reproducible on a laptop, matching the `nektos/act` convention already used across this org's other projects.

Verified 2026-09-16: act **0.2.89** (2026-06-01, no commits on master since — usable, visibly slowing). Marketplace majors: `checkout@v7`, `setup-uv@v10`, `upload-artifact@v7`, `download-artifact@v8`. **Node 20 leaves the runner images 2026-09-23**, so older action majors break imminently. `mysql:lts` now resolves to 9.7 and `mariadb:lts` to 12.3 — both aliases moved.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. One workflow, guard publishing with `if: !env.ACT` | Single file | **Does not work.** act has no OIDC *and ignores `job.permissions` entirely*, so it would run the publish job and fail confusingly. `env.ACT` is also step-level only — it has no effect in a job-level `if:` | Rejected on mechanism |
| B. **Two files: `ci.yml` replayable, `publish.yml` act never opens** | File separation is the only reliable boundary; `.actrc` pins act to `ci.yml` | Two files to keep aligned | Chosen |
| C. Reusable workflow shared across the three repos | DRY | PyPI trusted publishing matches the *called* workflow's filename, so the publish job cannot live in a reusable workflow at all | Barred by PyPI |

## Decision

**Option B**, with these specifics:

- **Gate on `vars.LOCAL_ACT`, never `env.ACT`.** Gitea's runners also set `ACT=true`, so a real CI run would mistake itself for a local one; and `env.ACT` does not work in a job-level `if:`. `.act.vars` sets `LOCAL_ACT=1`.
- **Service containers are addressed by `127.0.0.1` both under act and on GitHub.** act runs with `--network host`, so a service label fails DNS and the published port is on `127.0.0.1` — the same address GitHub's VM runner uses. `DB_HOST: ${{ vars.DB_HOST || '127.0.0.1' }}`; `.act.vars` leaves `DB_HOST` unset, and setting it to `db` is only right with a user-defined `--network`. *(Corrected 2026-10-20: this line first said act addresses the label `db`, which is how the act runs were first attempted and is not how they work.)*
- **Database images pinned explicitly** to `mysql:8.0`, `mysql:8.4` and `mariadb:11.4` — the full grid on GitHub, collapsed to the `mysql:8.0` leg under act because act creates every leg's service container up front and they collide on port 3306. The `lts` aliases moved under everyone's feet and must not be tracked. *(Corrected 2026-10-20: first written as 8.4 and 11.4 only.)*
- **Secrets come from Infisical via the official CLI, never the SDK** — consistent with the org's existing decision on Infisical transport. `make ci` runs act under `infisical run --env=prod --projectId <home-lab> --path /ci/act/<repo>` (project `home-lab` since 2026-10-18; the earlier `home-lab-discovery` project is retired), which exports secrets as environment variables, which is exactly how act resolves the bare `-s NAME` declarations in `~/.actrc`. **No secret is written to disk in this repository**; `.act.secrets` stays empty and exists only for a deliberate throwaway during debugging. `INFISICAL_ENV` and `INFISICAL_PROJECT_ID` defer to the environment (`?=`) so the Makefile adapts rather than overrides.
- **Release ordering is manual**, documented in `RELEASING.md`. Pallets and OpenTelemetry Python — the comparable multi-package projects that release in dependency order — both document rather than automate it, and the gate that matters can only be checked after the upstream package is actually live.

## Consequences

- Positive: every spine invariant that claimed a mechanical check now has one, and a maintainer can reproduce a CI failure without pushing.
- Positive: `verify-install` installs **the built wheel** into an isolated environment and asserts `boto3` and the OTel SDK are absent (AD-8). Installing the working tree would have passed throughout the entire outage — that is the blind spot this closes.
- Negative: `ci.yml` and `publish.yml` share a build step that must stay aligned by review, since the reusable-workflow route is barred.
- Negative: act is slowing upstream. Nothing load-bearing depends on a future act fix; if it stalls, the workflows still run on GitHub unchanged.
- **Revisit when:** act gains OIDC support (issue #2500), which would let the publish path be rehearsed locally.
