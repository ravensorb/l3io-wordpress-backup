# ADR-0014: Archives are encrypted with `age`, through `l3io-wp-database`

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Shawn Anderson
- **Epic:** E004 (story 4.3), E003 (story 3.3)
- **Supersedes:** [ADR-0006](0006-archive-format-and-encryption.md), its encryption half
- **Departs from spec:** _bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md#ad-6--the-archive-format-is-one-owned-contract
- **Also changes:** PRD FR-4's mechanism (not its requirement) and AD-26's passphrase handoff

## Context

ADR-0006 chose Argon2id key derivation with chunked AES-GCM, built by this package from
`cryptography` primitives. It was never accepted, and it left this package owning a
construction where chunking, nonce discipline, AAD framing and key commitment must all be
got right.

`l3io-wp-database` has since shipped `age` encryption through `pyrage` (its ADR-0003,
v0.1.0): streaming, with bounded memory, and decryptable by the stock `age` command line
without this family. Its dumps are already `age`. Two formats in one family, for the same
operator, protecting the same database content, would be two things to recover and two to
get right.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Keep ADR-0006 | No dependency on the database release | This package owns a crypto construction; a second format beside the dumps' |
| B. Call `pyrage` directly | One format | A second integration of the same library, outside the package that owns it |
| C. **`age` through `l3io-wp-database`** | One format and one implementation; stock `age -d` recovers any archive | The passphrase path waits on database 0.2.0 |

## Decision

**Option C.** Archive payloads are `age`, encrypted and decrypted by calling
`l3io-wp-database`'s stream functions. This package imports no `pyrage` and no
`cryptography` cipher for archive encryption.

- **Recipients and identities** (`age` or SSH public keys to encrypt; `age` identities,
  optionally passphrase-protected, to decrypt) build on database **v0.1.0**.
- **Passphrase** encryption — AD-26's chain — builds on database **0.2.0**, which adds
  `passphrase=` to `encrypt`/`decrypt`/`dump`/`load`, mutually exclusive with
  recipients/identities, emitting a sole scrypt recipient. It needs streaming
  `passphrase.encrypt_io`/`decrypt_io` in upstream `pyrage`, which 1.4.0 lacks (its
  passphrase calls are one-shot over whole bytes). Design: `l3io-wordpress-database`
  `_bmad-output/planning-artifacts/plans/2026-10-20-plan-4-passphrase-stream.md`.
  Buffering a whole archive, hand-rolled scrypt+STREAM and the `age` CLI were rejected.
- A wrong key or passphrase is database's `DecryptionError`; a truncated or damaged
  stream is `CorruptDumpError`. This package maps both into its own hierarchy (AD-14)
  and keeps them distinct.
- **The Manifest records no key material and no KDF parameters**: `age` carries its own
  header. The Manifest records whether each member is encrypted.
- **What ADR-0006 provided that `age` alone does not, and where it now comes from.**
  `age` authenticates each member against truncation and tampering, but nothing in it
  binds a member to *its* Archive, so an encrypted member could be swapped in from another
  Archive under the same key. AD-6's Manifest checksums over **bytes as stored** — the
  ciphertext — catch that, and Verification checks them before any key is needed. A wrong
  key is told apart from corruption by `age` itself, which replaces ADR-0006's key
  commitment.

## Kept from ADR-0006

- The Manifest stays the first, never-encrypted member, so an Archive can be identified,
  version-gated and verified without a key.
- That makes member names, sizes and the source Site's identity visible to anyone holding
  the Archive — the deliberate trade. An operator needing them hidden encrypts at the
  storage layer as well.
- Losing every key or the passphrase loses the Archive. Documentation says so plainly.
- Committed fixture Archives per format version, exercised in CI, including an encrypted
  one; the supported range is derived from that set.

## Consequences

- Any archive member decrypts with `age -d`, without this package.
- Encryption streams with bounded memory, as AD-21 requires; AD-21's CI assertion covers
  the encrypted path.
- The `database` extra gains database's `encryption` extra.
- Passphrase archives cannot ship before database 0.2.0, and that needs a pyrage release.
- **Revisit when:** database 0.2.0 cannot ship streaming passphrase IO without
  hand-rolling cryptography. That reopens AD-26, not this ADR's format choice.

## Amendment — 2026-10-27: how the passphrase path was delivered

Accepted by Shawn, 2026-10-27, superseding the passphrase bullet above where they differ.

- **The upstream `pyrage` route did not land.** PR woodruffw/pyrage#171 was closed by the
  maintainer, who asked for the problem in the author's own words; issue #172 is open
  and unanswered (checked 2026-10-27). It is not a refusal on the merits, so if it lands it
  is a candidate to replace the binder below.
- **`l3io-wordpress-database` now streams `passphrase=`** (commit `47384ba`, untagged,
  pushed to its `main`; 0.2.0 not cut). Two backends, chosen by
  `L3IO_AGE_PASSPHRASE_BACKEND=auto|binder|cli` (database ADR-0003, amended 2026-10-26):
  - **binder** (preferred): `l3io-age-passphrase` v0.1.0, a new family package — a PyO3
    binding over the Rust `age` crate's own streaming passphrase encryptor. It wraps the
    maintained implementation; it is not a hand-rolled construction. GitHub Release wheels
    only, not on PyPI.
  - **cli** (fallback): stock `age` ≥ 1.3 with `age-plugin-batchpass`, the secret on
    `AGE_PASSPHRASE_FD`, never in argv. Rejected on 2026-10-20, accepted now as a
    fallback where the binder wheel is not installed.
- **This package pins database by rev to `47384ba`** (2026-10-27) and re-pins to v0.2.0
  when it is tagged. It imports `encrypt`, `decrypt` and `check_passphrase` from the
  package root, which 47384ba exports.
- **The `encryption` extra is not taken yet.** It pulls the binder, and uv ignores a
  dependency's own `[tool.uv.sources]`, so it would build the Rust binder from source.
  Story E004-S01-003 adds it together with a source for the binder's release wheels.
- **For the CLI fallback, AD-7's invariant extends to the passphrase:** it never appears
  in an argument vector, environment or log. That is database's mechanism to assert, as
  for credentials (ADR-0015); this package asserts only what it emits.
- The consequence "passphrase archives cannot ship before database 0.2.0, and that needs a
  pyrage release" no longer holds: they need database 0.2.0 (or this rev) and either the
  binder wheel or `age` ≥ 1.3 present.
