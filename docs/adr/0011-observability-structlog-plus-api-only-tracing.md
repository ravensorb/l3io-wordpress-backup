# ADR-0011: Structured logging with structlog; tracing API-only and inert by default

- **Status:** Proposed
- **Date:** 2026-09-16
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD FR-20 covers structured logging only — tracing is a capability the PRD does not yet carry
- **Principle(s) in tension:** Core §9 unified correlated logging, §7 dependency selection, §8 GA over preview

## Context

The rewrite is asked to do "logging and tracing" properly. Two distinct questions hide in that: what emits the operational record, and whether distributed tracing earns its place in a single-process batch CLI that is also an embeddable library.

Verified live 2026-09-16, with the behavioural claims executed rather than recalled:

- `opentelemetry-api`, `-sdk` and `-exporter-otlp` are all 1.44.0 (2026-07-16). OTel graduated CNCF 2026-05-21.
- **Traces and Metrics are Stable. The Logs signal is "Development" *in the Python implementation*** — its modules are underscore-private (`opentelemetry._logs`) and the 1.44.0 changelog warns of deprecations and breaking changes. The *specification's* logs API and data model are marked Stable; it is Python that has not landed. The distinction matters: this decision is about what we can depend on today, not about the standard's maturity.
- `opentelemetry-api` alone has **one** transitive dependency (`typing-extensions`), ~0.7 MB. In a clean venv with no SDK it yields `ProxyTracer` / `NonRecordingSpan`, `is_recording()` False, all-zero IDs, no output and no error.
- `TRACEPARENT` env-carrier propagation: the OTel spec is a **Release Candidate**, Python's implementation is underscore-private (`opentelemetry.propagators._envcarrier`), and **none of `mysqldump`, `mysql` or `wp` reads the environment variable** — mysql-server vendors otel-cpp's `environment_carrier.h` but nothing under `client/` references it, and wp-cli has no hits. One precision: MySQL *does* ingest trace context by another route, the `traceparent` **query attribute**. The accurate claim is that env-var propagation is inert here, not that the toolchain is trace-blind.
- Adoption in comparable tools: borg — none. restic — none of its own, though its `go.mod` carries **twelve** `// indirect` OTel lines pulled in by cloud-backend SDKs. uv, ruff, pytest — none. Airflow and dbt — yes, but both opt-in and off by default, and both are *orchestrators* whose runs fan out across hosts and tasks.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. structlog only, no tracing | One dependency; everything a span would carry is already a log field; matches every comparable backup CLI | A host application that already runs an SDK gets nothing from us | §9 satisfied, but ignores the embedded-library case the PRD stakes the product on |
| B. **structlog + `opentelemetry-api` only** | Costs one 0.7 MB dependency and no configuration; verified to no-op when unconfigured; lights up automatically inside an already-traced host | ~30 lines of span code to maintain; no value for the cron operator | §9, §7 — the cheapest honest answer to both audiences |
| C. structlog + full OTel SDK as a runtime dependency | Turnkey | Forces a collector and configuration on cron users; the umbrella exporter drags `grpcio`, the classic install-everywhere failure | Fails §7 on footprint |
| D. OTel for logs as well as traces | One system | The logs signal is Development and underscore-private | Fails §8 outright |

## Decision

**Option B.**

- **Logging is structlog**, configured once at a composition root (AD-10). The OTel logs signal is not used until it is Stable and public.
- **Tracing is `opentelemetry-api` only** (AD-24). The SDK and an exporter ship in an optional `otel` extra; the umbrella `opentelemetry-exporter-otlp` is forbidden because of `grpcio`, with `opentelemetry-exporter-otlp-json-file` — pure Python, JSONL to disk — preferred for cron-shaped use.
- Spans follow AD-17's phases, one root per Run and one child per phase. `process.command_args` is recorded only post-redaction (AD-7): a span attribute is as public as a log line.
- **`TRACEPARENT` is not injected into subprocesses.** Nothing in our toolchain reads it.
- **Every phase emits `phase`, `duration_ms`, `exit_code` and `bytes` as log fields whether or not tracing is configured.** Tracing is never the only way to see what a Run did.

The honest framing: for the operator running this from cron, tracing buys nothing that `jq` over a log file does not already give — a trace of six sequential phases in one process is a bar chart, not a trace. It is adopted because the PRD stakes the product on being *embedded* in other people's Python automation, and for that reader the cost is one small dependency and the payoff is spans appearing in their existing pipeline with zero configuration on our side.

## Consequences

- Positive: no configuration burden, no collector, no `grpcio`; correct behaviour in both audiences; reversible, since API-only instrumentation is deletable in an afternoon.
- Negative: ~30 lines of instrumentation earning nothing for the majority audience, and a dependency added for a benefit we cannot yet measure.
- **Revisit when:** evidence arrives that users embed the library in traced pipelines (which this step is designed to make cheap to discover), **or** a tool in the subprocess chain starts reading `TRACEPARENT`, **or** the OTel logs signal reaches Stable — any of which changes the arithmetic.
