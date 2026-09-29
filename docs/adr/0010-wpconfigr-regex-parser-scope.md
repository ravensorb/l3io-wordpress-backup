# ADR-0010: Keep wpconfigr's regex-based wp-config.php reader, with documented limits

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD FR-11, FR-29
- **Principle(s) in tension:** Core §1 NEVER HAND-ROLL A PARSER — this ADR is the required escape hatch

## Context

Core §1 forbids hand-rolling a parser and names the escape hatch expensive on purpose: an ADR naming the libraries actually evaluated, why each was rejected in checkable terms, **the cost being accepted and who owns it**, and the condition that would reopen the decision. `wpconfigr` is a hand-rolled, regex-based reader and writer of a PHP subset. This ADR exists because that rule applies, and adopting the package (ADR-0002) is the moment the decision becomes ours rather than inherited.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. A real PHP parser (`phply`, a tree-sitter PHP grammar via `py-tree-sitter`) | Correct across the whole language | `phply` is a PLY-based parser last meaningfully released years ago — trading one unmaintained dependency for another. tree-sitter adds a native build to a package whose value is installing everywhere (ADR-0004). Both parse far more language than `define()` needs, and neither round-trips formatting on write | §1 favours a library — but §7 rejects both candidates on maintenance and footprint |
| B. Delegate to `wp config get/set` | No parser at all; WordPress's own implementation | Makes WP-CLI mandatory for **every** operation, contradicting PRD FR-13's guarantee that a non-relocating restore does not need it. Also cannot read a config to *find* the site before WordPress is bootstrapped | Fails FR-13 |
| C. **Keep the regex reader, bound its documented scope** | Zero dependencies (AD-2); 343 lines; already works for the `define()` subset WordPress actually writes | Genuinely partial. It is not a PHP parser and must never be described as one | §1 escape hatch, paid for here |

## Decision

**Option C.** `wpconfigr` remains a regex-based reader/writer of `define()` constants, and its documentation states that scope explicitly rather than implying general PHP support.

**The cost being accepted, stated plainly.** Reviewed against the source at `py-wpconfigr@8f25bb8`, these are known limits, not speculation:

**Scope — `define()` constants AND `$table_prefix`.**

`wp-config.php` carries two shapes, not one. Connection settings are `define()`
constants; the table prefix is a **PHP variable assignment** — `$table_prefix = 'wp_';`
— which a define-only pattern cannot see. It is required, not optional:
`l3io-wp-database` cannot report a WordPress version without it, because a non-default
prefix means the version does not live in `wp_options`. The reader therefore handles
simple scalar variable assignments at file scope in addition to `define()`. That is a
bounded extension to a known second shape, not a step toward parsing PHP.

**Parse fidelity.**

- The string-match path matches single-quoted values only (`\'(.*)\'`). A double-quoted `define("DB_NAME", "wp")` falls through to the non-string path and yields the value *including its quotes*.
- Both patterns are greedy (`(.*)`); a line carrying two `define()` calls, or an embedded escaped quote, is not handled.
- Values that are PHP expressions or reference other constants are returned as raw text.

**Type fidelity — `get()` does not round-trip its own writes.** Verified by execution against `py-wpconfigr@8f25bb8`:

- `_get_value_from_match` coerces every numeric-looking value to `float`, **including quoted ones**. `define('DB_PASSWORD', '3306')` is unambiguously a PHP *string*, and the parser knows it — it matched via `_get_string_match` — but returns `3306.0`. `get()` therefore cannot distinguish `define('X', '123')` from `define('X', 123)`, and no integer ever reads back as an `int`.
- `set(key, <int>)` is asymmetric: it raises `TypeError` when the key **already exists** (the update path concatenates the raw value) but succeeds when the key is **missing** (the insert path applies `str(value).lower()`).

**Write fidelity.**

- `set()` inserts a new constant with `content.replace('<?php\n', ...)` and **no count argument**, so it inserts at *every* occurrence of that marker, not the first. A file opening `<?php ` without a newline, or with a leading comment block, silently gets no insertion at all.

**Surface.**

- The CLI's `if got:` guard prints nothing and exits 0 when a value is `false`, `0` or `''`, making a falsy value indistinguishable from a missing key on both stdout and the exit code.

**Owner:** Sanderson, as part of adopting `wpconfigr` (ADR-0002).

**Mitigation, not a fix: read-back verification over the rendered text of the whole file.**

After writing, re-read and assert three things:

1. every constant we wrote has its **value span** render as the text we intended —
   `raw_value` against `render_value(key, value)`, **not** the whole statement.
   A write replaces only the value and preserves the file's existing formatting, and
   WordPress's own `wp-config-sample.php` uses `define( 'DB_NAME', 'value' );` with
   spaces inside the parens. Comparing a whole statement against a canonically
   rendered one therefore rejects a completely correct write to almost every real
   `wp-config.php`. Only the value is ours; the surrounding formatting belongs to
   the file;
2. every constant we did **not** write is byte-identical to before — whole-statement comparison is correct *here*, because we authored none of it — a greedy `(.*)` can swallow a neighbouring `define()` on the same line, so checking only our own keys would miss the damage entirely;
3. no key appears twice, since a duplicate `define()` means the pattern matched one occurrence while WordPress will use the other.

On any mismatch the restore fails and AD-18's atomic config write is never committed, so the original file survives intact.

**The comparison is on rendered text, never on values round-tripped through `get()`.** An earlier form of this requirement compared values, which the type-fidelity defects above make unusable: writing an all-digit database password — entirely ordinary — reads back as a `float` and fails the assertion, so the mitigation meant to prevent corruption would instead block legitimate restores. That is a false-positive path rather than a missed-corruption path, but it makes restore unreliable for a common input. Text comparison also lets all three assertions operate on one representation.

**The type-fidelity defects are to be fixed, not documented.** `l3io-wp-config` has never been published under that name, so it carries no compatibility obligation to anyone. `get()` must preserve the PHP literal's type — quoted stays `str`, unquoted `true`/`false` becomes `bool`, unquoted integers become `int`, unquoted decimals `float`, anything else raw text — `set()` must behave identically whether the key exists or not, the insertion must be bounded to one occurrence, and the CLI must distinguish a falsy value from a missing key in both output and exit code. Read-back is the guard that holds regardless; these fixes stop it from firing on correct input.

This converts the parser's blind spots from silent corruption into a loud, recoverable failure — the property that matters for a tool whose top NFR is never leaving a site worse off.

## Consequences

- Positive: the shared kernel stays dependency-free and installs everywhere; the limits are written down instead of discovered.
- Negative: sites with unusual `wp-config.php` formatting are unsupported, and will be told so by a read-back failure rather than by a corrupted site.
- **Revisit when:** a read-back failure is reported against a `wp-config.php` that WordPress itself wrote (the type-fidelity fixes above should make this signal meaningful rather than noisy), **or** a maintained, pure-Python, round-tripping PHP-constant library appears. Either reopens this decision immediately.
