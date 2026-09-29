# ADR-0005: Delegate serialization-safe URL rewriting to WP-CLI

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD FR-12, FR-13
- **Principle(s) in tension:** Core §1 never hand-roll what a library does, §7, §8 GA over preview

## Context

WordPress stores PHP-serialized values in `wp_options` and postmeta as `s:23:"http://old.example.com";` — the `23` is a byte-length prefix. A SQL `REPLACE` changes the content without recomputing the prefix, producing a value that fails to unserialize; WordPress then silently falls back to defaults and widgets, menus and theme options break, discovered days later. Today wpbackup2 rewrites `wp-config.php` constants only and never touches database content, so `--new-site-url` produces a site still pointing at the old URL throughout.

## Options considered

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. **Delegate to `wp search-replace`** | Reference implementation; walks and re-serializes with corrected lengths; `--dry-run` maps onto FR-19; free correctness | New external runtime dependency; PHP must be present; no tagged release since 2025-05-07 | §1 directly — do not hand-roll a serializer |
| B. Reimplement in Python | No external dependency | Owning a PHP-serialization parser. Subtle, silent, high-blast-radius failure | Fails §1 outright |
| C. Vendor `interconnect/it Search-Replace-DB` | Proven | PHP anyway; unmaintained; licence review | Fails §7 |

## Decision

**Option A.** Relocation shells out to `wp search-replace`, behind a `SearchReplace` port with one adapter.

**A constraint this forces, verified 2026-09-15:** `wp search-replace` has **no credential flags**. It bootstraps WordPress and uses `$wpdb`, reading the constants in `wp-config.php`. It is pointed at a site with the global `--path=<dir>`. Therefore relocation *must* run after the config rewrite, against the restored directory. The ordering — extract, rewrite config, then search-replace — is not a preference; it is the only order that works, and it is normative in **AD-17**, which makes `RestorePhase` an ordered enum so a plan can omit phases but never reorder them.

## Consequences

- Positive: the one genuinely hard problem in this space is solved by the implementation everyone else trusts.
- Negative: WP-CLI 2.12.0 was released 2025-05-07 and has had no tagged release in ~16 months, though `master` carries commits dated today. Accepted: it is the only serialization-safe implementation, and the alternative is worse.
- **Exit plan (required, §8):** the dependency is confined to one adapter behind one port. If WP-CLI is abandoned, the port is re-satisfied without touching `core/`. Version detection at preflight (AD-13) pins the supported range; an integration test exercises relocation against each supported WP-CLI version.
