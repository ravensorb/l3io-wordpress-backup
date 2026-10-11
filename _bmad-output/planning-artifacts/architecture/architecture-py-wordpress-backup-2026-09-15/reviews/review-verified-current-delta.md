# Review — "Verified current" lens, DELTA re-run

- **Date:** 2026-09-16
- **Lens:** every committed decision must be web-researched or reality-checked, not asserted from training data
- **Scope:** AD-22, AD-23, AD-24; amended AD-6 ("Reading v0"); amended AD-10; new OpenTelemetry rows in the Stack table; ADR-0011
- **Method:** live PyPI JSON API, live `raw.githubusercontent.com` spec/README/CHANGELOG fetches, `gh search code`, and **executed** checks in a throwaway venv (`python3 -m venv`, `pip install opentelemetry-api`, `pip install --dry-run --report -`). Nothing below is from recall.

## Verdict

**11 CONFIRMED · 1 WRONG · 0 UNVERIFIABLE**, plus **3 confirmed-with-nuance** where the claim is true as written but the artifact's framing is broader than the evidence supports.

This delta is the best-evidenced material in the spine so far. The behavioural claims in ADR-0011 ("executed rather than recalled") were re-executed here and reproduce **exactly** — including the all-zero IDs and the ~0.7 MB figure. The single defect is a precision error in an adoption anecdote, not in a decision input.

---

## Findings

### 1. `opentelemetry-api` / `-sdk` / `-exporter-otlp` versions and dates — **CONFIRMED**

All three are **1.44.0**, all uploaded **2026-07-16T15:25Z**. Still current as of today.

| Package | Version | sdist/wheel upload |
|---|---|---|
| `opentelemetry-api` | 1.44.0 | 2026-07-16T15:25:11 |
| `opentelemetry-sdk` | 1.44.0 | 2026-07-16T15:25:29 |
| `opentelemetry-exporter-otlp` | 1.44.0 | 2026-07-16T15:25:14 |

Source: `https://pypi.org/pypi/<pkg>/json`. Corroborated by the repo CHANGELOG heading `## Version 1.44.0/0.65b0 (2026-07-16)`.

Incidental: `opentelemetry-api` declares `requires_python: >=3.10`, so AD-9's 3.11 floor is compatible with room to spare.

### 2. `opentelemetry-exporter-otlp-json-file` — exists, 0.65b0, Beta, official, pure Python — **CONFIRMED**

- Exists on PyPI; **version `0.65b0`** (matches the Stack row exactly).
- `Development Status :: 4 - Beta` — matches the ADR's "Beta".
- Official: `project_urls.Homepage = github.com/open-telemetry/opentelemetry-python/tree/main/exporter/opentelemetry-exporter-otlp-json-file` — it is in the OTel **core** Python repo, not contrib.
- Pure Python, no protobuf/grpc. Resolved dependency closure (`pip install --dry-run --report -`) is **five packages**, all pure Python:

```
opentelemetry-exporter-otlp-json-file 0.65b0
opentelemetry-exporter-otlp-json-common 0.65b0
opentelemetry-proto-json 0.65b0      <- requires_dist: None
opentelemetry-sdk 1.44.0
opentelemetry-semantic-conventions 0.65b0
```

`opentelemetry-proto-json` has **no dependencies at all** — this is the JSON-serialisation path that replaces `opentelemetry-proto` (which is what drags `protobuf`). The ADR's choice is soundly grounded.

### 3. Logs signal "Development", traces/metrics Stable, modules underscore-private — **CONFIRMED (with a nuance on which "status" is meant)**

Confirmed against the **Python implementation's** own status table (`open-telemetry/opentelemetry-python/README.md`):

```
| Traces  | Stable       |
| Metrics | Stable       |
| Logs    | Development* |
```

…with the accompanying `[!IMPORTANT]` block: *"We are working on stabilizing the Log signal which would require making deprecations and breaking changes."* The same warning is reproduced verbatim at the top of the repo `CHANGELOG.md`, so AD-10's "with the changelog warning of breaking changes" is literally true.

Underscore-privacy **executed and confirmed** in the venv:

```
OK    opentelemetry._logs
FAIL  opentelemetry.logs        ModuleNotFoundError
```

**Nuance worth a one-line edit.** At the *specification* level the picture is more mixed than "the Logs signal is Development" implies: `specification/logs/api.md` is headed `**Status**: Stable, except where otherwise specified` (with a Development block further down at line 183), and `specification/logs/data-model.md` is flatly `**Status**: Stable`. So "Development" is accurate about **Python**, and AD-10 phrases it that way ("at 1.44.0 it is still Development status and its modules are underscore-private") — but ADR-0011's bare "**the Logs signal is 'Development'**" reads as a spec-wide claim that the spec does not support. Suggest ADR-0011 line 17 say "*the Logs signal is Development **in Python***". The decision itself (don't use OTel logs) is unaffected and correct.

### 4. One transitive dependency, ~0.7 MB — **CONFIRMED (measured, not estimated)**

`requires_dist` for `opentelemetry-api` 1.44.0 is exactly `['typing-extensions>=4.5.0']` — one entry, and `typing-extensions` itself has no dependencies. Installed into a clean venv, `pip list` shows only:

```
opentelemetry-api==1.44.0
typing_extensions==4.16.0
```

Measured on-disk footprint:

```
540K  site-packages/opentelemetry
164K  site-packages/typing_extensions.py
----
704K  total  =  ~0.7 MB
```

The "~0.7 MB" figure is not a guess; it reproduces to three digits.

### 5. No-op behaviour with no SDK — **CONFIRMED (executed)**

Run in the clean `opentelemetry-api`-only venv:

```
tracer type: ProxyTracer
span type:   NonRecordingSpan
is_recording: False
trace_id: 00000000000000000000000000000000  span_id: 0000000000000000
```

No stdout, no stderr, no exception. Every element of the ADR's claim — `ProxyTracer`, `NonRecordingSpan`, `is_recording()` False, all-zero IDs, no output, no error — reproduces exactly.

Additionally, the *reason* AD-24 gives ("the pattern OpenTelemetry's own library guidelines mandate") is confirmed at `specification/library-guidelines.md`:

> §2 *"Third party libraries and frameworks that add instrumentation to their code will have a dependency only on the API of OpenTelemetry client."*
> §"Expected Usage" *"Libraries, frameworks, and applications that want to be instrumented with OpenTelemetry take a dependency only on the API packages."*
> §"API and Minimal Implementation" *"if the end user application or a third-party library depends only on it and does not plug a full SDK implementation then the application will still build and run without failing."*

AD-24 is not inventing a pattern; it is citing one, correctly.

### 6. Umbrella `opentelemetry-exporter-otlp` pulls `grpcio` — **CONFIRMED (and it is worse than stated)**

`pip install --dry-run --report -` resolves **15 packages**, including native-wheel dependencies:

```
grpcio 1.84.0            <- the one named
protobuf 7.36.1
googleapis-common-protos 1.75.3
requests 2.34.2 / urllib3 2.8.0 / certifi / charset-normalizer / idna
opentelemetry-exporter-otlp{,-proto-common,-proto-grpc,-proto-http} 1.44.0
opentelemetry-proto 1.44.0 / -sdk 1.44.0 / -semantic-conventions 0.65b0
```

The chain is `opentelemetry-exporter-otlp` → `-proto-grpc` → `grpcio`. The ADR names `grpcio` only; the full cost also includes `protobuf` and a `requests`/`urllib3`/`certifi` HTTP stack. The forbidding decision is, if anything, under-argued in the artifact.

### 7. Env-carrier spec at Release Candidate; Python impl underscore-private — **CONFIRMED**

`specification/context/env-carriers.md` header, fetched today:

```
# Environment Variables as Context Propagation Carriers
**Status**: [Release Candidate](../document-status.md)
```

Python side, confirmed by import in the venv:

```
OK    opentelemetry.propagators._envcarrier
FAIL  opentelemetry.propagators.envcarrier   ModuleNotFoundError
```

Directory listing of `opentelemetry/propagators/` shows `_envcarrier.py` alongside public `composite.py` and `textmap.py` — the underscore is deliberate, not incidental. Both halves of AD-24's parenthetical are exact, including the module path spelling.

### 8. `mysqldump`, `mysql`, `wp` do not read `TRACEPARENT` — **CONFIRMED for the env var, but the absolute framing overstates it**

**How hard I looked.** No `mysql`/`mysqldump`/`wp` binaries exist on this host, so a `strings` check was not available. Instead I searched the upstream sources directly with `gh search code`:

- **`wp-cli/wp-cli`**: zero hits for `traceparent` and zero for `opentelemetry`. Clean absence.
- **`mysql/mysql-server`**: hits exist, but **none of them is the client reading the env var**:
  - `libmysql/libmysql.cc` — `"traceparent"` as a **named query attribute** (`const char *names[2] = {nullptr, "traceparent"}`), i.e. trace context carried *in the protocol*, not from the environment.
  - `mysql-test/suite/perfschema/…/telemetry_traces_prepared_stmt.{test,result}` — tests for that query-attribute telemetry path.
  - `extra/opentelemetry-cpp/opentelemetry-cpp-1.27.0/api/include/opentelemetry/context/propagation/environment_carrier.h` — a **vendored** otel-cpp header that *does* read `TRACEPARENT`/`TRACESTATE`/`BAGGAGE` from the environment. Critically, a follow-up search for `environment_carrier` across the whole repo returns **only** otel-cpp's own `api/test/…/environment_carrier_test.cc` and its `CMakeLists.txt` — no reference from `client/` or anywhere in MySQL's own code.
  - A scoped search for `traceparent path:client` returns **nothing**.

**Conclusion.** The operative claim — *injecting `TRACEPARENT` into these subprocesses' environment would be read by nobody* — is **confirmed**, and this is stronger than bare absence of evidence: the vendored env-carrier reader is present in the tree and demonstrably unwired to the client binaries.

**Nuance.** ADR-0011's "**Nothing in our toolchain reads it**" is broader than what was checked. MySQL 8.x ships a real OTel trace-context ingestion path via the `traceparent` **query attribute** and its telemetry component. That channel is not the env var and is not what AD-24 proposes to skip, but "nothing in our toolchain" invites a reader to conclude MySQL has no OTel story at all, which is false. Suggest narrowing to "*nothing in our toolchain reads it **from the environment***". This also sharpens the ADR's own revisit trigger, which is currently "a tool in the chain starts reading `TRACEPARENT`" — under the narrowed wording that trigger becomes checkable.

### 9. structlog `trace_id`/`span_id` recipe and `add_open_telemetry_spans` — **CONFIRMED that it is real and documented; NUANCE on "ships"**

`add_open_telemetry_spans` is **real and is in structlog's own documentation**, at `hynek/structlog:docs/frameworks.md`, section `## OpenTelemetry`, lines 78–104 — verbatim:

```python
from opentelemetry import trace

def add_open_telemetry_spans(_, __, event_dict):
    span = trace.get_current_span()
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict
    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)
    event_dict["span"] = {
        "span_id": format(ctx.span_id, "016x"),
        "trace_id": format(ctx.trace_id, "032x"),
        "parent_span_id": None if not parent else format(parent.span_id, "016x"),
    }
    return event_dict
```

Two nuances, both minor but both the kind of thing that turns into a wrong implementation:

1. **It is a documented example to copy, not shipped API.** Executed against structlog 26.1.0 in the venv: `'add_open_telemetry_spans' in dir(structlog.processors)` → `False`; no `tele`-matching name anywhere in `structlog` or `structlog.processors`; `grep -rn "opentelemetry" site-packages/structlog/` → **zero hits**. Nobody can `from structlog.processors import add_open_telemetry_spans`. The spine does not claim otherwise (it says only "a structlog processor"), so this is a note for whoever implements it, not a defect in the artifact.
2. **The spine's described shape differs from the documented one.** AD-24 says the processor "adds `trace_id` and `span_id` when a span is recording and **nothing** when it is not". structlog's recipe nests both under a `span` **dict** (with a third key, `parent_span_id`) and explicitly sets `event_dict["span"] = None` when not recording. AD-24 describes a flatter, quieter variant. That is a legitimate design choice — flat `trace_id`/`span_id` is the better fit for the `jq`-over-a-log-file operator AD-24 argues for — but it is a *variant*, and if the intent is "the structlog documented recipe", the artifact and the docs currently disagree.

Also confirmed en route: the recipe uses only `opentelemetry.trace`, i.e. the **API** package. structlog's prose says "the Python OpenTelemetry SDK offers an easy API", but the code needs no SDK — consistent with AD-24's API-only design and with the executed no-op result in §5.

Stack-table cross-check: `structlog` **26.1.0**, uploaded **2026-06-06**, is current on PyPI.

### 10. Adoption claims in ADR-0011's Context — **one WRONG, five CONFIRMED**

Six of the seven named tools were checked directly (more than the "at least three" asked for).

| Claim | Result | Evidence |
|---|---|---|
| borg — none | **CONFIRMED** | `borgbackup/borg:pyproject.toml` `[project.dependencies]` and every `[project.optional-dependencies]` extra — no OTel. `gh search code opentelemetry --repo borgbackup/borg` → zero hits. |
| **restic — none (one transitive `go.mod` line)** | **WRONG** | See below. |
| uv — none | **CONFIRMED** | `astral-sh/uv:Cargo.lock` — `grep -ci opentelemetry` → **0**. |
| ruff — none | **CONFIRMED** | `astral-sh/ruff:Cargo.lock` — `grep -ci opentelemetry` → **0**. |
| pytest — none | **CONFIRMED** | `pytest-dev/pytest:pyproject.toml` `dependencies` = colorama, exceptiongroup, iniconfig, packaging, pluggy, pygments, tomli. No OTel. |
| Airflow — opt-in, off by default | **CONFIRMED** | `airflow-core/…/config_templates/config.yml`: `[metrics] otel_on` `default: "False"` (line 1338) **and** `[traces] otel_on` `default: "False"` (line 1464). Docs `traces.rst` require `pip install 'apache-airflow[otel]'` *and* `otel_on = True`. Two gates, both closed by default. |
| dbt — opt-in, off by default | **CONFIRMED** | `docs.getdbt.com/docs/fusion/telemetry`: needs **both** `OTEL_EXPORTER_OTLP_ENDPOINT` set **and** an explicit `--export-to-otlp` flag. |

> **DEFECT — ADR-0011 line 20: "restic — none (one transitive `go.mod` line)".**
>
> `restic/restic:go.mod` on `master` contains **twelve** OpenTelemetry lines, not one:
>
> ```
> github.com/GoogleCloudPlatform/opentelemetry-operations-go/detectors/gcp v1.32.0 // indirect
> github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/metric v0.57.0 // indirect
> github.com/GoogleCloudPlatform/opentelemetry-operations-go/internal/resourcemapping v0.57.0 // indirect
> go.opentelemetry.io/auto/sdk v1.2.1 // indirect
> go.opentelemetry.io/contrib/detectors/gcp v1.43.0 // indirect
> go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc v0.68.0 // indirect
> go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp v0.67.0 // indirect
> go.opentelemetry.io/otel v1.44.0 // indirect
> go.opentelemetry.io/otel/metric v1.44.0 // indirect
> go.opentelemetry.io/otel/sdk v1.44.0 // indirect
> go.opentelemetry.io/otel/sdk/metric v1.44.0 // indirect
> go.opentelemetry.io/otel/trace v1.44.0 // indirect
> ```
>
> `go.sum` carries **30** OpenTelemetry lines.
>
> **Severity: low — the conclusion survives, the number does not.** Every line is `// indirect`, pulled in by restic's GCS/gRPC cloud-backend dependencies; restic emits no telemetry of its own. So "restic has no first-party OTel instrumentation" is correct and the argument ADR-0011 builds on it is untouched. But "one transitive `go.mod` line" is a specific, checkable number that is off by 12×, and it is the **only** claim in this delta that reads like recall rather than a check — every other number in ADR-0011's Context block reproduces exactly. Fix by replacing the parenthetical with "no first-party instrumentation; the OTel entries in `go.mod` are all `// indirect`, via the cloud-backend SDKs."
>
> Second-order note: restic's indirect pins are `go.opentelemetry.io/otel v1.44.0` — the same 1.44.0 line as the Python packages. That is corroborating evidence the 1.44.0 series is the current one across languages.

Also spot-checked, since AD-22 leans on it: **`chesney` is gone.** `https://pypi.org/pypi/chesney/json` → **HTTP 404**. AD-22's "it required `chesney`, which no longer exists on any index" is confirmed, and the forced-exception design (accept the flag, fail with an explanation) is justified by a live fact.

### 11. AD-23 / AD-6 "Reading v0" — v0 is a `.tar.gz` with `database.sql` + `wp-root/`, no manifest — **CONFIRMED against the actual code**

`wpbackup2/classes/wp_internal_backup.py`:

```python
27: DB_DUMP_ARCNAME = 'database.sql'
28: WP_DIR_ARCNAME  = 'wp-root'
80:     with tarfile.open(archive_filename, 'w:gz') as stream:
90:         stream.add(db_dump_filename, arcname=DB_DUMP_ARCNAME)
97:     stream.add(self.__wp_site.site_path, arcname=WP_DIR_ARCNAME)
```

Every element checks out:

- **`.tar.gz`** — `tarfile.open(..., 'w:gz')`; the read side is `'r:gz'` at `wp_internal_restore.py:111`. `wpbackup.py:46` defaults the filename to `wpbackup2-{db}-{timestamp}.tar.gz`.
- **Members `database.sql` and `wp-root/`** — exactly those two arcnames, and nothing else is ever `add`ed.
- **No manifest** — `grep -n "manifest"` across `wp_internal_backup.py`, `wp_internal_restore.py`, `wpbackup.py` returns **zero hits**. There is no checksum, no version field, no index.
- **The v0 member-name duplication AD-6 complains about is real**: `DB_DUMP_ARCNAME`/`WP_DIR_ARCNAME` are defined **twice**, at `wp_internal_backup.py:27-28` and again at `wp_internal_restore.py:28-29`. AD-6's "Today `DB_DUMP_ARCNAME` and `WP_DIR_ARCNAME` are duplicated literals in two modules" is verified verbatim.

Note supporting AD-23's design: `database.sql` is conditional (`if include_database_dump:`), so a files-only v0 archive has **only** `wp-root/`. AD-23's detection rule says "members `database.sql` and `wp-root/` with no Manifest mean v0" — a files-only v0 archive would fall to "anything else is rejected as unrecognised". Not a verification finding (the rule is a decision, not a fact claim), but the detector spec should probably tolerate the `wp-root/`-only shape the current writer can produce.

### 12. AD-22 — exactly nineteen flags, no `console_scripts` — **CONFIRMED**

Enumerated mechanically from `wpbackup2/__main__.py` (`grep -o "'--[a-zA-Z-]*'" | sort -u`): **exactly 19 distinct long-flag spellings.**

```
 1 --admin-credentials-aws-region     11 --new-db-name
 2 --admin-credentials-aws-secret-id  12 --new-db-password
 3 --admin-password                   13 --new-db-user
 4 --admin-username                   14 --new-site-home-url
 5 --archive                          15 --new-site-url
 6 --cleanfirst                       16 --only-appointed-in-asg
 7 --force                            17 --version
 8 --log-level                        18 --whatIf
 9 --mode                             19 --wp-dir
10 --new-db-host
```

Composition matches AD-22's description: 3 top-level (`--version`, `--log-level`, `--whatIf`), 3 shared across both subcommands (`--wp-dir`, `--mode`, `--archive`), 13 restore-only.

- **camelCase `--whatIf` confirmed** — `__main__.py:42`, `add_argument('--whatIf', ..., dest='what_if')`. A rewrite that normalised this to `--what-if` would break cron files; AD-22 is right to freeze the spelling.
- **`--only-appointed-in-asg` is genuinely unrunnable** — `__main__.py` has `import chesney` at **module scope** (line 9), so with `chesney` 404 on PyPI the CLI cannot even *start* today, let alone run that flag. AD-22's "forced exception" is more urgent than the artifact conveys.
- **No `console_scripts`** — `grep -rn "entry_points\|console_scripts" setup.py setup.cfg` → **no match**. `setup.py` has `packages=[...]` and no `entry_points` key at all. AD-22's "a console-script entry point is **added** alongside, never instead" is the correct tense: there is nothing to preserve, only something to add, and `python -m wpbackup2` (the `prog=` string in the parser, line 34) is today the only invocation.

---

## Summary table

| # | Claim | Verdict |
|---|---|---|
| 1 | otel api/sdk/exporter-otlp all 1.44.0 (2026-07-16), still current | CONFIRMED |
| 2 | `-otlp-json-file` 0.65b0, Beta, OTel core repo, pure Python | CONFIRMED |
| 3 | Logs Development, traces/metrics Stable, `opentelemetry._logs` private | CONFIRMED (nuance: Python-level, not spec-level) |
| 4 | `opentelemetry-api` → one dep, ~0.7 MB | CONFIRMED (measured 704 KB) |
| 5 | No SDK ⇒ ProxyTracer / NonRecordingSpan / not recording / zero IDs | CONFIRMED (executed) |
| 6 | Umbrella exporter pulls `grpcio` | CONFIRMED (also protobuf + requests stack) |
| 7 | Env-carrier spec RC; Python impl underscore-private | CONFIRMED |
| 8 | `mysqldump`/`mysql`/`wp` do not read `TRACEPARENT` | CONFIRMED (nuance: env var only; MySQL has a query-attribute path) |
| 9 | structlog `add_open_telemetry_spans` recipe is real | CONFIRMED (nuance: docs example, not shipped API; different field shape) |
| 10 | borg/restic/uv/ruff/pytest none; Airflow & dbt opt-in, off | 6 CONFIRMED, **1 WRONG (restic "one line" → twelve)** |
| 11 | v0 = `.tar.gz`, `database.sql` + `wp-root/`, no manifest | CONFIRMED (against code) |
| 12 | Nineteen CLI flags; no `console_scripts` | CONFIRMED (against code) |

## Recommended edits

1. **ADR-0011 line 20 (required)** — replace "restic — none (one transitive `go.mod` line)" with "restic — no first-party instrumentation; the OTel entries in `go.mod` are all `// indirect`, via the cloud-backend SDKs".
2. **ADR-0011 lines 17 & 19 (suggested)** — scope two claims to what was actually checked: "the Logs signal is Development **in Python**", and "`mysqldump`, `mysql` and `wp` do not read it **from the environment**" (with the same narrowing applied to line 38's "Nothing in our toolchain reads it" and to the revisit trigger at line 47).
3. **AD-24 (suggested)** — note that the flat `trace_id`/`span_id` processor is a deliberate variant of structlog's documented `add_open_telemetry_spans`, which nests under a `span` dict; and that the function must be written locally, since structlog ships no such processor.
4. **AD-23 (suggested, design not fact)** — the current writer emits `wp-root/` alone when the database is excluded; the v0 detection rule should accept that shape rather than rejecting it as unrecognised.
5. **AD-22 (optional)** — note that `import chesney` sits at module scope in `__main__.py`, so the CLI is currently unimportable, not merely missing one flag.
