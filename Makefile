# l3io-wordpress-backup — local developer entry points.
#
# CI is replayed locally with nektos/act, configured by .actrc plus
# .act.{vars,env,secrets}. The same workflow files run here and on GitHub.
#
# First-time setup:
#   make act-init       copies .act.{vars,env,secrets}.example -> .act.{vars,env,secrets}
#   make infisical-init links this repo to its Infisical project
#
# Secrets are never stored in this repo. `make ci` runs act under `infisical run`,
# which supplies them as environment variables — which is exactly how act resolves
# the bare `-s NAME` declarations in ~/.actrc.
#
# Useful targets:
#   make lint         ruff check + format --check
#   make types        mypy --strict
#   make test         pytest against a local MySQL (needs one running)
#   make contracts    the architecture gates (AD-1, AD-4, AD-5, AD-25)
#   make ci           replay the whole CI pipeline locally via act
#   make ci-job JOB=  replay one job, e.g. make ci-job JOB=contracts
#   make ci-dryrun    parse and plan the workflow without running it
#   make build        uv build --no-sources

ACT_FILES := .act.vars .act.env .act.secrets

# ---- secrets ---------------------------------------------------------------
# All secrets come from Infisical, via the official CLI (never the SDK).
# ~/.actrc declares shared secrets as bare `-s NAME`, which act resolves from the
# environment — so `infisical run` supplies them and act picks them up. Nothing
# secret is ever written to disk in this repo.
#
#   INFISICAL_ENV         environment to read (default: prod)
#   INFISICAL_PROJECT_ID  the home-lab project (ADR-0008); an environment value wins
#   INFISICAL_PATH        this repo's CI leaf, /ci/<platform>/<repo>
INFISICAL_ENV ?= prod
INFISICAL_PROJECT_ID ?= 7ca0e01b-28f6-4a61-b901-5fe834e1661a
INFISICAL_PATH ?= /ci/act/l3io-wordpress-backup
INFISICAL_RUN := infisical run --env=$(INFISICAL_ENV) --projectId $(INFISICAL_PROJECT_ID) --path $(INFISICAL_PATH) --
# Bare `-s NAME` entries in ~/.actrc that act prompts for. They only need to be
# non-empty. GITHUB_TOKEN is deliberately NOT here: act uses it to fetch actions,
# so a placeholder makes every dry-run leg fail for the wrong reason.
ACT_PLACEHOLDER_SECRETS := PYPI_CUSTOM_USERNAME PYPI_CUSTOM_PASSWORD PYPI_TOKEN \
                           PYPI_TEST_TOKEN GITEA_TOKEN DOCKERHUB_TOKEN \
                           REGISTRY_PASSWORD NPM_REGISTRY_TOKEN

ACT := $(INFISICAL_RUN) act

.PHONY: help act-init infisical-init secrets-check lint format types test contracts verify-wheel ci ci-job ci-dryrun ci-list build clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

# Bootstrap any .act.* file from its .example counterpart on first use.
$(ACT_FILES): %: %.example
	@if [ ! -f $@ ]; then cp $< $@; echo "Created $@ from $<. Edit it to set local values."; fi

act-init: $(ACT_FILES) ## Bootstrap .act.{vars,env,secrets} from .example versions

infisical-init: ## Link this repo to its Infisical project (writes .infisical.json)
	infisical init

secrets-check: ## Verify the Infisical CLI is present and the project resolves
	@command -v infisical >/dev/null || { \
	  echo "infisical CLI not found. Install it, then: make infisical-init"; exit 1; }
	@$(INFISICAL_RUN) sh -c 'test -n "$$GITHUB_TOKEN" || { \
	  echo "Infisical resolved no GITHUB_TOKEN for env=$(INFISICAL_ENV)."; \
	  echo "Run make infisical-init, or set INFISICAL_PROJECT_ID=<uuid>."; exit 1; }' \
	  && echo "Infisical ok (env=$(INFISICAL_ENV))"

lint: ## ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

format: ## Apply ruff formatting
	uv run ruff format .
	uv run ruff check --fix .

types: ## mypy --strict
	uv run mypy --strict src

contracts: ## Architecture contract gates (AD-1, AD-4, AD-5, AD-25)
	uv run lint-imports
	uv run python tools/check_purity.py
	uv run python tools/check_mode_defaults.py
	uv run pytest tests/contracts -q

test: ## Run the test suite (expects a database on DB_HOST)
	uv run pytest -q --cov=l3io.wp.backup --cov-report=term-missing

build: ## Build wheel + sdist
	uv build --no-sources

verify-wheel: build ## Install the BUILT WHEEL into a clean env and import it
	@# The substantive half of CI's verify-install job, which act cannot run because
	@# its artifact server rejects upload-artifact@v7. Installing the working tree
	@# would pass even when the published package cannot resolve — that is the blind
	@# spot this closes, so it must be the wheel.
	@set -eu; wheel=$$(ls -t dist/*.whl | head -1); \
	  echo "verifying $$wheel"; \
	  uv run --isolated --no-project --with "$$wheel" \
	    python -c "from l3io.wp import backup; print('import ok')"; \
	  uv run --isolated --no-project --with "$$wheel" python -c "\
import importlib.util, sys; \
[sys.exit('AD-8 — base install pulled ' + m) for m in ('boto3','botocore','opentelemetry.sdk') if importlib.util.find_spec(m)]; \
print('base install clean')"

# ---- local CI replay -------------------------------------------------------

ci: act-init secrets-check ## Replay the full CI pipeline locally
	$(ACT) push

ci-job: act-init secrets-check ## Replay one job: make ci-job JOB=contracts
	@test -n "$(JOB)" || { echo "usage: make ci-job JOB=<job-id>"; exit 2; }
	$(ACT) push -j $(JOB)

ci-dryrun: ## Replay every publish/release leg as a dry run (no tags, no publishes)
	@# Nine legs, declared in .github/act-dryrun-legs.json. The table is DATA so
	@# tests/contracts/test_act_dryrun_legs.py can assert it is complete against the
	@# workflows' own triggers and choice options -- a leg list inside this recipe
	@# plus a test naming the expected legs would drift silently.
	@#
	@# WHY NINE AND NOT ONE. An act dry run resolves every `uses:` ref against the
	@# remote, so it catches an action version that does not exist -- but it only
	@# reaches the jobs the EVENT reaches, and a skipped job never has its refs
	@# resolved. Measured here with a nonexistent ref planted in publish.yml's
	@# release job: `workflow_dispatch target=testpypi` exits 0 and reports success;
	@# a tag-push payload exits 1 and names the bad ref. One leg is a false green,
	@# and it is false at the exact job where changelog-parser@v3.0.14 lived.
	@#
	@# --dryrun IS LOAD-BEARING, not tidiness. release.yml creates tags and
	@# dispatches publishes; without the flag this target would do both from a
	@# laptop. It is hardcoded here and must stay hardcoded.
	@#
	@# ci.yml is excluded: act SEGFAULTS on a dry run of it (nil pointer in
	@# containerReference.GetHealth) because the `test` job declares a `db` service
	@# a dry run never starts. Reproduced: SIGSEGV, exit 2. `make ci` runs it for real.
	@#
	@# GITHUB_TOKEN must be REAL -- act fetches actions with it, so a placeholder
	@# makes every leg fail for the wrong reason. The other bare `-s NAME` entries in
	@# ~/.actrc only need to be non-empty, or act prompts and dies with
	@# "inappropriate ioctl for device".
	@set -eu; \
	command -v act >/dev/null || { echo "act is not installed"; exit 1; }; \
	command -v $(GH) >/dev/null && $(GH) auth status >/dev/null 2>&1 \
	  || { echo "gh must be authenticated: act needs a real GITHUB_TOKEN to fetch actions"; exit 1; }; \
	export GITHUB_TOKEN="$$($(GH) auth token)"; \
	for s in $(ACT_PLACEHOLDER_SECRETS); do export $$s=unused-by-this-repo; done; \
	fail=0; n=0; \
	while IFS=$$'\t' read -r wf event args; do \
	  n=$$((n+1)); \
	  printf '  %-13s %-18s %-24s ' "$$wf" "$$event" "$$args"; \
	  if act "$$event" -W ".github/workflows/$$wf" --dryrun $$args >/tmp/act-leg.$$$$ 2>&1; then \
	    echo "ok"; \
	  else \
	    echo "FAILED"; fail=$$((fail+1)); \
	    grep -iE "couldn't find remote ref|Error:" /tmp/act-leg.$$$$ | head -3 | sed 's/^/      /'; \
	  fi; \
	  rm -f /tmp/act-leg.$$$$; \
	done < <(uv run scripts/act-legs.py); \
	echo "  $$(uv run scripts/act-legs.py | wc -l) legs run"


ci-list: act-init secrets-check ## List the jobs act can see
	$(ACT) push --list

clean: ## Remove build and cache artifacts
	rm -rf dist build .artifacts .uv-cache .pytest_cache .mypy_cache .ruff_cache
	find . -name '__pycache__' -prune -exec rm -rf {} +


# ---------------------------------------------------------------------------
# Releasing
#
# These targets do NOT compute a version, build, or publish. They dispatch
# release.yml and stop. The version is derived from the git tag by hatch-vcs
# (AD-30), so anything that worked out a version locally would be a second
# implementation of the one thing that must have exactly one.
#
# `make release patch` and `make release BUMP=patch` are the same command. The
# bare words are no-op targets that exist only so make does not fail on the
# second goal.
# ---------------------------------------------------------------------------

# Process substitution in ci-dryrun needs bash; /bin/sh on this box is dash.
SHELL := /bin/bash

GH ?= gh
RELEASE_WORKFLOW ?= release.yml
RELEASE_BRANCH ?= main
BUMP ?=

_BUMP_WORDS := patch minor major dev
_BUMP_GOAL := $(firstword $(filter $(_BUMP_WORDS),$(MAKECMDGOALS)))
_BUMP := $(if $(BUMP),$(BUMP),$(_BUMP_GOAL))

.PHONY: release release-patch release-minor release-major release-dev $(_BUMP_WORDS)

release: ## Cut a release: make release patch|minor|major|dev
	@set -eu; \
	bump="$(_BUMP)"; \
	if [ -z "$$bump" ]; then \
	  echo "usage: make release patch|minor|major|dev   (or make release BUMP=patch)"; \
	  exit 2; \
	fi; \
	case "$$bump" in patch|minor|major|dev) ;; *) echo "unknown bump '$$bump'"; exit 2 ;; esac; \
	command -v $(GH) >/dev/null || { echo "gh is not installed"; exit 1; }; \
	$(GH) auth status >/dev/null 2>&1 || { echo "gh is not authenticated: run 'gh auth login'"; exit 1; }; \
	branch=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$branch" != "$(RELEASE_BRANCH)" ]; then \
	  echo "on '$$branch', not '$(RELEASE_BRANCH)' -- release.yml tags whatever it checks out"; exit 1; \
	fi; \
	if [ -n "$$(git status --porcelain --untracked-files=no)" ]; then \
	  echo "tracked files are modified. That work is NOT in the release, and a dirty"; \
	  echo "tree also makes a local build report a different version than the tag."; \
	  git status --short --untracked-files=no; exit 1; \
	fi; \
	git fetch --quiet origin $(RELEASE_BRANCH); \
	if [ "$$(git rev-parse HEAD)" != "$$(git rev-parse origin/$(RELEASE_BRANCH))" ]; then \
	  echo "HEAD and origin/$(RELEASE_BRANCH) differ -- the workflow releases the PUSHED commit,"; \
	  echo "so push or pull first. Local: $$(git rev-parse --short HEAD)  origin: $$(git rev-parse --short origin/$(RELEASE_BRANCH))"; \
	  exit 1; \
	fi; \
	latest=$$(git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -1); \
	echo "  repo         $$($(GH) repo view --json nameWithOwner -q .nameWithOwner)"; \
	echo "  commit       $$(git rev-parse --short HEAD)"; \
	echo "  latest tag   $${latest:-<none: the first release will be v1.0.0>}"; \
	echo "  bump         $$bump"; \
	if [ "$$bump" = "dev" ]; then \
	  echo "  effect       publishes this commit to the internal mirror as <next patch>.dev<distance>; NO tag, NO GitHub release"; \
	else \
	  echo "  effect       pushes the next $$bump tag, which triggers build, smoke, mirror publish and a GitHub release"; \
	fi; \
	printf "\nType the bump to confirm: "; \
	read -r reply; \
	if [ "$$reply" != "$$bump" ]; then echo "aborted"; exit 1; fi; \
	$(GH) workflow run $(RELEASE_WORKFLOW) --ref $(RELEASE_BRANCH) -f bump="$$bump"; \
	echo; \
	echo "dispatched. Watch it with:  $(GH) run watch \$$($(GH) run list --workflow $(RELEASE_WORKFLOW) --limit 1 --json databaseId -q '.[0].databaseId')"

release-patch: ## Release a patch version (alias for: make release patch)
	@$(MAKE) --no-print-directory release BUMP=patch

release-minor: ## Release a minor version
	@$(MAKE) --no-print-directory release BUMP=minor

release-major: ## Release a major version
	@$(MAKE) --no-print-directory release BUMP=major

release-dev: ## Publish a dev build of this commit to the mirror (no tag)
	@$(MAKE) --no-print-directory release BUMP=dev

# Reached only as the second goal of `make release <word>`. On its own it is a
# typo for the real target, so say so rather than silently succeeding.
$(_BUMP_WORDS):
	@case " $(MAKECMDGOALS) " in \
	  *" release "*) : ;; \
	  *) echo "make: '$@' is not a target. Did you mean 'make release $@'?"; exit 2 ;; \
	esac
