# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Every `## ` heading here is read as a release.** `release.yml` extracts the entry
for the version it is about to tag and refuses to create the tag when there is none,
so prose that is not a release belongs under a deeper heading or in `docs/`.

## [Unreleased]

## [1.0.0] - 2026-09-29

First release under the new distribution name. The package was `wpbackup2`; it is
now `l3io-wp-backup`, importable as `l3io.wp.backup`.

### Changed

- **Distribution renamed** from `wpbackup2` to `l3io-wp-backup` (ADR-0012). The
  import path is the PEP 420 native namespace `l3io.wp.backup`, shared with
  `l3io-wp-config` and `l3io-wp-database` (AD-27).
- **Version numbering restarts at 1.0.0** and is now derived from the git tag by
  `hatch-vcs`. There is no version literal in the repository, so there is nothing
  to keep in sync with the tag.
- **Build system moved from setuptools to hatchling**, managed with `uv`.
- Minimum Python is now 3.11.

### Added

- `wpbackup2` is still the console script name, and `python -m wpbackup2` still
  works, so existing cron jobs and systemd units keep running (AD-22).
- Structured logging via `structlog`, with OpenTelemetry tracing behind the `otel`
  extra.

### Fixed

Defects corrected in the rewrite, each preserving the flag's documented intent
rather than its behaviour:

- `--mode db` performs a database-only backup instead of silently backing up
  everything.
- `--cleanfirst` selects the clean restore mode instead of being ignored.
- `--force` overrides the non-empty-target refusal instead of being the only way
  to reach clean mode.
- Failures exit non-zero.
- Credentials reach `mysql` and `mysqldump` through a mode-0600 option file passed
  as `--defaults-file`, never in `argv` and never via `MYSQL_PWD`. `--defaults-file`
  replaces the option-file chain, where `--defaults-extra-file` only adds to it and
  leaves an ambient `~/.my.cnf` able to redirect a restore to another server.
- URL relocation goes through `wp search-replace`, which unserializes, replaces and
  re-serializes. A SQL `REPLACE` corrupts every PHP-serialized value, because
  serialized strings carry a byte-length prefix that a textual replacement does not
  recompute — widgets, menus and theme options silently reset to defaults.
- A database-level `GRANT` matches its database name as a LIKE pattern, so `_` is a
  wildcard and `` `wp_site` `` also grants on `wpXsite`. Grant targets are escaped;
  `CREATE DATABASE` and connection parameters keep the literal name.

### Removed

- `--only-appointed-in-asg` cannot work: it required a package that no longer
  exists on any index. The flag is still **accepted** and fails with an error naming
  the removal and the reason, rather than argparse's `unrecognized argument`, so an
  operator whose cron job carries it gets an explanation.

[Unreleased]: https://github.com/ravensorb/py-wordpress-backup/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ravensorb/py-wordpress-backup/releases/tag/v1.0.0
