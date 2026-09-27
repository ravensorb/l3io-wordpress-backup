# Handoff 1 — `py-wpconfigr` becomes `l3io-wp-config`

**Read `00-SHARED-CONTEXT.md` in this folder first.** It carries the namespace
rule, the toolchain, and eight traps that will cost you a day each if you meet
them cold.

**Repository:** `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wpconfigr`
**Release position:** FIRST. The other two depend on this one; nothing else can
be published until this resolves from PyPI.

## Why this package is the way it is

It reads and writes `define()` constants in a WordPress `wp-config.php`. It is a
fork of `cariad/py-wpconfigr` (MIT), taken at upstream's 2019 state. Upstream
later renamed itself to `wpconfigger` and is live on PyPI; this project publishes
its own fork instead, because it needs to change the parser and will not depend
on a package with one release and one maintainer — the same bus factor that
produced the current outage. **ADR-0012** records that decision and **ADR-0010**
records the parser's accepted limits.

## Scope

### 1. Republish under a correct identity

The fork's `setup.py` currently declares **Cariad Eccleston's** name, email and
repository URL while sitting in this project's control. A user filing a bug goes
to the wrong person. Fix that:

- distribution name `l3io-wp-config`, version **1.5.0 or higher** — the old
  `1.4` filename is burned on PyPI forever and cannot be re-uploaded
- author, email and project URLs point at this project
- **retain the MIT © 2018 Cariad Eccleston notice** in `LICENSE`
- README opens with a credit: this is a fork of `cariad/py-wpconfigr`, MIT, and
  upstream's own successor is `wpconfigger`

### 2. Move to the namespace

`wpconfigr/` becomes `src/l3io/wp/config/`. Re-read AD-27 in the shared context
before you create a single directory. There is no `__init__.py` above
`src/l3io/wp/config/`.

### 3. Modernise packaging

uv + PEP 621 `pyproject.toml`, committed `uv.lock`, `requires-python = ">=3.11"`.
**Zero runtime dependencies — this is permanent (AD-2)**, and it is why this
package must not take `structlog`: it emits through stdlib
`logging.getLogger(__name__)` and the application's `ProcessorFormatter` picks it
up (AD-10).

### 4. Keep the split that already exists

`WpConfigString` is pure — it operates on a string. `WpConfigFile` is the I/O
shell wrapping it. **That is the architecture's paradigm already in place**
(AD-1, ADR-0001), so preserve it: the pure half belongs in `core/`, the shell in
`adapters/`. Do not collapse them.

### 5. Document the parser's real limits, and add read-back verification

ADR-0010 accepts that this is a regex reader of a PHP subset rather than a PHP
parser. Four limits are recorded there, read off the source rather than guessed:
single-quoted string values only; greedy `(.*)` patterns; `set()` inserting after
a literal `<?php\n`; PHP expressions returned as raw text. **Document that scope
explicitly** in the README — it must never read as general PHP support.

Then implement the mitigation ADR-0010 requires, which does not exist yet:
**read-back verification over the rendered text of the whole file.** Re-read ADR-0010
— it was amended on 2026-09-16 and now specifies text comparison, lists four further
verified defects, and directs that the type-fidelity ones be fixed rather than
documented.

### 5b. `$table_prefix` is in scope

`wp-config.php` carries two shapes. Connection settings are `define()` constants;
the table prefix is a **variable assignment** — `$table_prefix = 'wp_';` — which the
current define-only regex cannot read. `l3io-wp-database` needs it to report a
WordPress version at all, since a non-default prefix means the version is not in
`wp_options`. Handle simple scalar variable assignments at file scope as well as
`define()`. This is a bounded extension to a second known shape; it is **not** a
licence to parse PHP generally, and ADR-0010's limits still bind.

### 6. CI

Copy the shape from `/home/ravenwolf.org/sanderson/source/git/ravensorb/wordpress/py-wordpress-backup/.github/workflows/ci.yml`, minus the
database services and WP-CLI — this package needs neither. Keep the Python
matrix, the clean-install verification, `.actrc`, `.act.*.example`, `Makefile`
and `.gitignore` entries. Copy `publish.yml` as-is apart from the package name
and URLs.

## Explicitly out of scope

- Rewriting the parser to handle more PHP. ADR-0010 decided against that and
  named the condition that would reopen it.
- Adding any runtime dependency, for any reason.
- Publishing. Hand back when the artifact builds and verifies; a human releases.

## Done when

Everything in the shared context's definition of done, plus: `from l3io.wp import
config` works from the installed wheel; read-back verification has tests covering
all four documented limits; and the README states the parser's scope and credits
upstream.
