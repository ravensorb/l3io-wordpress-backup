# Handoff 4 — legacy pointer releases and defensive registrations

**Read `00-SHARED-CONTEXT.md` first.** Small task, easy to get wrong, and it is
the one users actually feel.

**Do this LAST** — after all three `l3io-wp-*` packages are live on PyPI.

## The problem being solved

`pip install wpbackup2` fails **today** with `ResolutionImpossible`: version
0.2.21 requires `chesney` and `wpconfigr`, both removed from PyPI. Anyone who
installed before 2020 cannot reinstall, and anyone finding it now gets an error
with no explanation. **PyPI has no rename, redirect or alias mechanism**, so a
final pointer release is the only migration path that exists.

## Part 1 — pointer releases for the two owned names

`wpbackup2` and `wpdatabase2` are owned by this project (PyPI author "Shawn
Anderson"). Publish one final version of each:

- its **only** runtime dependency is the corresponding `l3io-wp-*` package
- importing it emits a `DeprecationWarning` naming the replacement and the
  import path
- the PyPI description explains the rename, links the new package, and states
  that the old name is not maintained further
- version above the current published one (0.2.21 / 0.0.15) — remember PyPI
  burns filenames permanently, so a version already uploaded can never be reused

Whether it re-exports anything is a judgement call: the Python API is explicitly
**not** compatibility-bound across this rewrite (AD-22), so a faithful re-export
is likely impossible. Prefer an honest warning plus working install over a shim
that half-works.

## Part 2 — defensive registrations

Register `wpbackup`, `wpdatabase` and `wpconfigr` as thin packages pointing at
the `l3io-wp-*` family. Two reasons, both real:

1. **Discoverability.** ADR-0012 chose a vendor prefix, which trades away search
   visibility — nobody looking for "wordpress backup" finds `l3io-wp-backup`.
   These are the names a stranger actually searches.
2. **Supply chain.** All three are currently unregistered and are referenced by
   this project's own history and documentation. An unregistered name that your
   docs point at is available for revival hijack.

Each should be a minimal package that installs the real one and says so.

## Caution specific to `wpconfigr`

That name has history that is not ours — it was the original author's, who
deleted it, failed to republish (almost certainly because PyPI burns filenames,
not because names are reserved), and renamed to `wpconfigger`. Registering it as
a pointer is defensible; presenting it as *our* project is not. The description
must credit the original and point at both `wpconfigger` and `l3io-wp-config`.

If registration is refused for any reason, **stop and report** — do not work
around it.

## Done when

`pip install wpbackup2` succeeds and pulls `l3io-wp-backup`; the same for
`wpdatabase2`; the three defensive names resolve to informative pointer packages;
and `RELEASING.md` in each repository reflects what was actually published.
