# Shared context — read this first

Every handoff prompt in this folder assumes this file. Read it before acting.

## What is being built

Three Python packages, published together, that back up and restore self-hosted
WordPress. They are being **rewritten** — outward compatibility is preserved, the
internals are not. The published package has been **uninstallable since 2020**:
`pip install wpbackup2` fails with `ResolutionImpossible` because two of its
dependencies were removed from PyPI.

| Publish order | Distribution | Import | Repository |
|---|---|---|---|
| 1 | `l3io-wp-config` | `l3io.wp.config` | `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wpconfigr` |
| 2 | `l3io-wp-database` | `l3io.wp.database` | `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-database` |
| 3 | `l3io-wp-backup` | `l3io.wp.backup` | `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-backup` |

## Authoritative documents — do not re-derive these decisions

Read the ones your task touches. They are final; if you believe one is wrong,
**say so and stop** rather than quietly diverging.

- **PRD** — `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-backup/_bmad-output/planning-artifacts/prds/prd-py-wordpress-backup-2026-09-12/prd.md`
  30 functional requirements (FR-n), 8 NFRs, four release phases. `check_prd.py`
  beside it validates structure; run it after any edit.
- **Architecture spine** — `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-backup/_bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md`
  27 invariants (AD-n). These bind all three repositories.
- **ADRs** — `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-backup/docs/adr/` (13 records, indexed in README.md).
- **Engineering standards** — `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-backup/.claude/skills/l3io-arch-review/references/`
  (`standards-core.md` plus the Python and GitHub Actions overlays).

## Non-negotiable constraints

**AD-27 — the namespace will break the other two packages if you get it wrong.**
`l3io.wp` is a PEP 420 *native* namespace. **No distribution ships an
`__init__.py` at `l3io/` or `l3io/wp/`.** Every packaging tutorial and most
build-backend defaults will encourage you to add one. If you do, your package
becomes a regular package, shadows the namespace, and makes its siblings
unimportable — and your own tests will still pass, because the failure only
appears when two are installed together. Layout is exactly:

```
src/l3io/wp/<area>/__init__.py      <- the only __init__.py in the tree
```

With hatchling: `[tool.hatch.build.targets.wheel] packages = ["src/l3io"]`.

**`mypy --strict` will tell you to add the file that breaks everything.** On a
namespace package it suggests an `__init__.py`. Do not take the suggestion — set
`namespace_packages`, `explicit_package_bases` and `mypy_path` instead.

**You can prove coexistence today without waiting for the sibling packages.** Build
a throwaway distribution claiming the same namespace — about ten lines of
`pyproject.toml` and one module. **The editable-plus-wheel shape is mandatory and
the two-wheel shape is not sufficient:** two wheels unpack into the same
`site-packages` directory, so a planted `l3io/wp/__init__.py` leaves that regular
package's `__path__` entry containing the sibling anyway, and the sibling imports
despite the defect. The shadow is observable only across **different `sys.path`
entries**. Measured, not reasoned.

**AD-2 — dependency direction is one-way and `l3io-wp-config` stays dependency-free.**
`l3io-wp-config` <- `l3io-wp-database` <- `l3io-wp-backup`. `l3io-wp-config`
declares **zero** runtime dependencies, permanently.

**AD-8 — an optional dependency is an optional import.** Anything behind an extra
is imported *inside the function that uses it*, never at module scope. CI asserts
a base install imports every public module.

**AD-14 — no dependency's exception type crosses a public boundary.** Each package
owns its exception hierarchy; catch and re-raise with `raise ... from`.

**Global rule — never hand-roll what a maintained library does.** Parsers,
crypto, HTTP, retry, date/time, argument parsing. If you find yourself more than
~100 lines into one, stop and surface it. The single existing exception is
recorded in ADR-0010 and is not a licence for more.

**Global rule — enforce mechanically, not by prose.** When you write a rule, write
the check in the same change. A rule that lives only in a comment will be violated
invisibly.

## Toolchain (verified 2026-09-15/16 — re-verify before pinning anything new)

uv **0.11.6** (the version on the dev machines; 0.12.15 is current but generating a
lock with a version CI does not use breaks `uv sync --locked` only in CI — pin
`[tool.uv] required-version` in `pyproject.toml` so the drift is impossible rather
than documented, and raise an upgrade as a decision, not a side effect) · ruff 0.16.7 (pin exactly, pre-1.0) · mypy 2.3.1 · pytest 9.1.1 +
pytest-cov 7.1.0 · structlog 26.1.0 · `requires-python = ">=3.11"`.
`pyproject.toml` is the single source of truth; `uv.lock` is committed; CI runs
`uv sync --locked`. Retire `setup.py`, `setup.cfg`, `build.sh`, `publish.sh`,
`test.py`.

## Traps already paid for — do not rediscover these

1. **`env.ACT` is unreliable.** Gitea runners also set `ACT=true`, and `env.ACT`
   does not work in a job-level `if:`. Gate on **`vars.LOCAL_ACT`**, set in
   `.act.vars`.
2. **act cannot run the publish workflow.** It has no OIDC *and ignores
   `job.permissions` entirely*, so an `if:` guard will not protect it. Keep
   `publish.yml` a separate file and pin act to `ci.yml` in `.actrc`.
3. **Service containers are on `127.0.0.1` under act too — do NOT address them
   by label.** act's `--network` defaults to `host` (confirmed in `act --help`), so a
   service label fails DNS outright with "Temporary failure in name resolution"
   while the published port appears on the loopback address, exactly as on GitHub's
   VM runner. Leave `DB_HOST` unset in `.act.vars` so the workflow default applies.
   Label addressing works only if act is given a user-defined network via
   `--network`. Verified both ways against a nine-test integration suite.
4. **`mysql:lts` now means 9.7 and `mariadb:lts` means 12.3** — the aliases moved.
   Pin `mysql:8.4` and `mariadb:11.4`.
5. **Node 20 leaves the runner images on 2026-09-23** — a future date as of writing, so an action major running on Node 20 works *today* and breaks after it —
   and **not every publisher ships a floating major tag.** Verified 2026-09-16:

   | Action | Latest floating major | Latest exact |
   |---|---|---|
   | `astral-sh/setup-uv` | **v7** | **v10.1.0** |
   | `actions/checkout` | v7 | v7.0.1 |
   | `actions/upload-artifact` | v7 | v7.0.1 |
   | `actions/download-artifact` | v8 | v8.0.1 |

   `setup-uv` is the odd one: astral-sh stopped floating majors after v7, so `@v10`
   resolves nowhere — under act *and* on GitHub — while `@v10.1.0` is real and
   current. Pin `astral-sh/setup-uv@v10.1.0`. Before pinning, list **all** tags:
   `git ls-remote --tags <repo> | grep -oE 'refs/tags/v[0-9.]+$'`. A filter of
   `^v[0-9]+$` shows only floating majors and will hide every exact version.

6. **Secrets come from Infisical via the official CLI, never the SDK.** `make ci`
   runs act under `infisical run`, which exports them as environment variables.
   Three things about act's bare `-s NAME` declarations in `~/.actrc`, all verified:
   **only a non-empty environment variable satisfies them** — an empty value counts
   as unset and act prompts, then dies outside a TTY; `--secret-file` does **not**
   satisfy them at all, populated or not; and **`GITHUB_TOKEN` must be left absent
   rather than given a placeholder**, because act hands it to git when fetching
   actions and GitHub rejects a fake one, breaking action resolution — absent means
   an anonymous clone, which is what public actions need. Never write a secret to
   disk in the repo, and never print a secret value (grep env for *names*).
   **A stale credential presents as a workflow bug.** The `PYPI_CUSTOM_USERNAME` /
   `PYPI_CUSTOM_PASSWORD` pair in the secret store is **not valid** for
   `git.ravenwolf.org` — verified 401 against `/api/v1/user`, while `GITEA_TOKEN`
   returns 200. Gitea's package registry takes basic auth with a **token as the
   password**, so use the username plus `GITEA_TOKEN`. Note also that `~/.actrc`
   carries a `gitea.example.com` placeholder URL beside those declarations, and the
   live registry path is under the `liquidlogiclabs` org, not `ravensorb`. When a
   push 401s, test the credential against the API before touching the workflow.
10. **`--bind` plus a parallel matrix will corrupt the working tree.** `~/.actrc`
   uses `--bind`, so the workspace is the developer's real checkout and containers
   run as root. Matrix legs then race on `.venv` and leave it root-owned, breaking
   every later local `uv` command with EACCES. **ANYTHING the run writes into the
   bound tree is left root-owned**, and the next local command fails with EACCES.
   Enumerating outputs one at a time is the wrong shape — four separate victims
   were found this way, each after the previous fix: the venv, `dist/` and
   `dist-verify/`, `.coverage`/`coverage.xml`, and `__pycache__` bytecode inside
   `src/`. Redirect **every** write path out of the workspace:
   `UV_PROJECT_ENVIRONMENT`, the build `--out-dir`, `COVERAGE_FILE` and the XML
   report path, and `PYTHONPYCACHEPREFIX`. Then verify by running `make clean` and
   `uv build` as yourself afterwards — a pipeline that passes while leaving the tree
   unusable has not passed. Recovering a root-owned file needs a container
   (`docker run --rm -v "$PWD:/w" -w /w alpine:3 rm ...`); no non-root path works. `runner.temp` cannot be used in a job-level
   `env:` block — the runner context is step-level only — but `matrix` can.
11. **An FR number is only unique within ONE PRD.** There are three in this family
   and they number independently — py-wordpress-backup ends at FR-30, py-wordpress-database
   runs to FR-51 — so "FR-43" identifies nothing on its own and resolves to a real
   requirement in one document and to nothing in another. **Always name the document
   with the number.** This is a scoping hazard, not a fabrication hazard; the remedy
   is a qualified citation, not distrust of FR numbers.
12. **Prefer LiquidLogicLabs actions over third-party or hand-rolled `run:` steps**
   where one exists — `git-action-tag-info`, `git-action-tag-validate-version`,
   `git-action-release` (all at v2). Verify the tag with `git ls-remote` and the
   inputs against the action's own `action.yml` before pinning. Note that
   `git-action-docker-act-compatibility` is Dockerfile path resolution only despite
   the name; it is not a general act shim.
13. **act allocates every matrix leg's service container before any job runs**, so
   legs publishing the same host port collide — nine legs on 3306 means eight fail
   with "port is already allocated", and `--concurrent-jobs 1` does not help because
   allocation precedes execution. A container that fails to start is not removed by
   `--rm` and strands the port until removed by hand. A single leg chosen with
   `--matrix` passes, which is what makes this easy to miss. Collapse the matrix
   under `vars.LOCAL_ACT` with `fromJSON` rather than branching, so one code path
   serves both environments.
14. **A matrix `include:` entry whose keys match no existing combination ADDS a leg
   rather than extending one.** Collapsing a matrix dimension therefore turns the
   remaining `include:` entries into phantom legs with empty values for the collapsed
   key — which run, and fail confusingly. Carry per-variant data on the matrix object
   itself (`engine.image`, `engine.health`) instead of using `include:` at all.
15. **act's artifact server rejects `upload-artifact@v7`** (protobuf decode error on
   an unknown `mime_type` field), and v4 is not a fallback because it runs on Node
   20. Gate the upload and anything needing it on `!vars.LOCAL_ACT`, and keep the
   substantive check runnable locally another way.
7. **PyPI permanently burns filenames.** A version already uploaded can never be
   re-uploaded, even after the project is deleted. This is almost certainly what
   defeated the original author of `wpconfigr`.
8. **PyPI has no rename, redirect or alias.** Migration means a final release of
   the old name depending on the new one.
9. **A fixture generated by a buggy implementation locks the defect in as the
   expectation.** All three repositories carry test fixtures of 2018-2020 vintage,
   written by the code being replaced. When a fix makes an existing expectation
   fail, establish which of the two is wrong before "restoring" the test — an
   expected-output file recording the old behaviour is evidence of the bug, not of
   correctness. One such fixture has already been found encoding a greedy-match
   defect as its expected output.

16. **`uv run` syncs default groups only and PRUNES extras.** Every `uv run`
   silently uninstalls an optional extra, so tests guarding it skip rather than run
   and the gap is invisible. Put optional dependencies in the dev group as well;
   optionality is still enforced where it counts — against the built wheel in an
   isolated environment.
17. **`ruff format` now formats Python code blocks inside Markdown.** A README can
   fail CI's `ruff format --check .` while a hand-run `ruff format --check src tests`
   passes. Always run the make targets, which use the same commands CI does.
18. **A `master` → `main` rename leaves two traps.** `gh repo view` can serve a
   **stale** default branch afterwards — and so can the `/branches` list itself, which
   listed the old name on one call and not the next, observed directly during this
   work. Re-read, or cross-check with `git ls-remote --heads`, which goes over the
   wire protocol with no API cache in front of it — and
   `branches/master` still resolves to the same SHA through the rename **redirect**
   rather than a surviving branch. Pin `main` or a rev, never `master`.

19. **A workflow job that reads a repo file must have `actions/checkout`** — and the
   jobs that consume an artifact usually do not. The failure is a `FileNotFoundError`
   in a publish path, which is a bad place to learn it. Found once, in a step whose
   whole purpose was to *stop* a job failing, failing that job on its first run.
   Derive name and version from the **artifact** rather than `pyproject.toml`: it needs
   no checkout, and it answers the question actually being asked — whether *these*
   artifacts are present, not what the repo currently declares, which diverges the
   moment a version is bumped after a build.

   **Auditing for it has two false-positive traps**, both observed. A matcher keying on
   `uv (sync|build|run|lock)` flags every `uv run --isolated --no-project`, which is the
   exact flag that makes it not need the project. And a matcher grepping for filenames
   hits the *comments* explaining why a job does not read that file — so the
   best-commented jobs look worst.

   **The underlying fact is bigger than the audit.** A `run:` block's text, comments
   included, exists in **three** places: the file, the parsed step, and the **execution
   log** — GitHub echoes the script before running it. Anything searching any of the
   three will find it. That explains a second failure mode entirely unrelated to audits:
   `gh run view --log | grep <phrase>` matches the echoed script before the step's
   actual output, so a phrase appearing in both finds the echo first. Easy to misread as
   a sloppy grep; it is the same property.

   **Comment placement is therefore a trade, not a correctness question.** A shell
   comment inside `run:` survives the parse *and* reaches the log, so the explanation is
   in front of whoever is reading a failed step at 2am — at the cost of tripping
   filename audits. A YAML comment above the step does neither: audits stay clean, and
   the reasoning is invisible exactly when the step fails. You cannot have both from one
   comment. Choose deliberately; the two repositories here chose differently and neither
   chose on purpose.

   **If this recurs, the enforceable version** is a contract test over the workflow
   YAML: for each job, if any *executable* line — comments stripped — references a repo
   path or calls `uv` without `--no-project`, assert that job has an `actions/checkout`
   step. Derived from the workflow rather than a hand-kept list, so a job added later
   cannot escape it. Deliberately not written yet: one real instance across two
   repositories is not evidence of a pattern, and a guard nobody has needed twice is
   its own cost.

## One discipline worth more than the trap list

Three separate errors in this work shared a single shape, and none of them was a
bad source:

- a subagent reported `setup-uv v10.1.0` correctly; it was **shortened** to `@v10`,
  a tag that does not exist;
- a sibling PRD stated `FR-43` correctly; it was **cited without its document**, and
  FR numbers are only unique within one PRD;
- `git ls-remote` returned every tag correctly; a **`^v[0-9]+$` filter** dropped all
  the exact versions, and the narrowed result looked verified.

In each case a correct input was **degraded in use**, and then the input was blamed.
Two of those blames were wrong and cost a further correction each.

The remedy is not to distrust sources. It is: **preserve what you were given, and
when you narrow it, make the narrowing visible.** A shortened tag, an identifier
without its scope, and a grep that drops most of its input are the same move.

This is the same defect the engineering standards describe for guards — a check
whose scope is narrower than the question it answers will report success over a set
that no longer contains what matters. It applies to how you read evidence, not only
to how you write checks.

## Definition of done, for every repository

- `uv sync --locked` succeeds; `uv.lock` committed.
- `ruff check`, `ruff format --check`, `mypy --strict` clean.
- `pytest` green, with the architecture contract tests present and passing.
- `make ci` replays the pipeline locally under act.
- The built **wheel** installs into a clean isolated environment and imports —
  not the working tree. Installing the working tree would have passed throughout
  the entire outage; that is the blind spot this closes.
- `py.typed` shipped. `__all__` declares the public surface.
- No `__init__.py` at `l3io/` or `l3io/wp/`.

## How to report back

State plainly: what you changed, what you verified and how, what you could not do
and why, and any decision you had to make that the documents did not cover.
Do not claim something passes without having run it.
