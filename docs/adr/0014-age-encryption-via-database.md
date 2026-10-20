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
