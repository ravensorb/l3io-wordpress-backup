# Implementation handoffs

Self-contained prompts for separate agents. Each assumes no context from the
planning conversation, so **`00-SHARED-CONTEXT.md` is required reading** for all
of them — it carries the namespace rule that can break two packages at once, plus
eight traps already paid for in discovery.

| # | Prompt | Repository | Depends on |
|---|--------|-----------|------------|
| 1 | [`01-l3io-wp-config.md`](01-l3io-wp-config.md) | `py-wpconfigr` | — |
| 2 | [`02-l3io-wp-database.md`](02-l3io-wp-database.md) | `py-wordpress-database` | 1 published |
| 3 | [`03-l3io-wp-backup.md`](03-l3io-wp-backup.md) | `py-wordpress-backup` | 2 published |
| 4 | [`04-legacy-names-and-registrations.md`](04-legacy-names-and-registrations.md) | PyPI only | 1, 2, 3 published |

**1 and 2 can be worked in parallel**; only *publishing* is ordered, and each
prompt hands back before publishing. 3 depends on nothing until its integration
tests need the other two installed. 4 is genuinely last.

Order exists because the release gate is "does the built artifact resolve and
import **from the index**" — which can only be checked after the upstream package
is actually live. Installing the working tree would have passed throughout the
entire outage.

None of these prompts authorises publishing to PyPI. Each ends with a verified
artifact; a human releases.
