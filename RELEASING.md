# Releasing

Three packages publish together and **must be released in dependency order**.
Ordering is manual and deliberate: the gate that matters — "does the published
artifact actually resolve and import *from the index*?" — can only be checked
after the upstream package is live, so automating the chain would only automate
guessing.

```
l3io-wordpress-config  ->  l3io-wp-database  ->  l3io-wordpress-backup
```

All three share the PEP 420 namespace `l3io.wp` (ADR-0012, AD-27).

| # | Distribution | Import | Repository |
|---|--------------|--------|------------|
| 1 | `l3io-wordpress-config` | `l3io.wp.config` | `py-wpconfigr` |
| 2 | `l3io-wp-database` | `l3io.wp.database` | `py-wordpress-database` |
| 3 | `l3io-wordpress-backup` | `l3io.wp.backup` | `py-wordpress-backup` |

## The gate

After each release, before starting the next:

```bash
uv run --isolated --no-project --with l3io-wordpress-config==<ver> \
       python -c "from l3io.wp import config; print('ok')"
```

Run it against **PyPI**, not a local build. Installing the working tree would
have passed throughout the entire period when the published package could not
resolve at all — that blind spot is what let the original outage ship, and this
ordering exists to close it.

`l3io-wp-database` additionally must not pull `boto3` in a base install (AD-8).
`l3io-wordpress-backup`'s release pipeline runs the cross-package namespace check
(AD-27): all three wheels installed into one interpreter, all three imported,
and no `__init__.py` at either namespace level.

## Per-package steps

1. Ensure the default branch is green in CI.
2. Bump the version in `pyproject.toml`; update the changelog.
3. Tag `vX.Y.Z` and push it. `publish.yml` builds, runs the clean-install smoke
   matrix and the namespace check, then publishes via PyPI trusted publishing.
4. Run the gate above.

Rehearse without publishing: `workflow_dispatch` with `target: testpypi`.

## Legacy names

`wpbackup2` and `wpdatabase2` are owned by this project and currently **fail to
install** — 0.2.21 requires `chesney` and `wpconfigr`, both removed from PyPI, so
`pip install wpbackup2` ends in `ResolutionImpossible`.

Each gets **one final pointer release** whose only dependency is its `l3io-wp-*`
replacement, emitting a `DeprecationWarning` on import that names the successor.
PyPI has no rename, redirect or alias mechanism, so this is the only migration
path available — and it repairs the broken install for everyone still on the old
name. Publish these *after* the corresponding `l3io-wp-*` package is live.

`wpbackup`, `wpdatabase` and `wpconfigr` are registered as thin pointer packages:
they are the names a stranger searches and the names this project's own history
references, and leaving them unregistered leaves them open to revival hijack.

## Why there is no cross-repo automation

PyPI's trusted publishing matches the *called* workflow's filename, so the publish
job cannot live in a reusable workflow shared across repositories. Comparable
multi-package Python projects that release in dependency order — Pallets, and
OpenTelemetry Python's core/contrib split — document the ordering rather than
automate it.

## Local replay

Everything except publishing runs locally:

```bash
make act-init             # first time only — creates .act.{vars,env,secrets}
make secrets-check        # confirms Infisical resolves for this environment
make ci                   # full pipeline
make ci-job JOB=contracts # one job
```

Secrets come from Infisical: `make ci` runs act under `infisical run`, which exports
them as environment variables — which is how act resolves the bare `-s NAME`
declarations in `~/.actrc`. Nothing secret is written to disk in this repository.
`INFISICAL_ENV` and `INFISICAL_PROJECT_ID` are taken from your environment when set.

`publish.yml` is deliberately excluded from act: act has no OIDC and ignores
`job.permissions`, so it cannot run those jobs meaningfully.
