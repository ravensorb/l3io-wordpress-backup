# ADR-0006: Archive format: manifest member, chunked AES-GCM under Argon2id

- **Status:** Proposed
- **Date:** 2026-09-15
- **Deciders:** Sanderson
- **Epic:** n/a
- **Departs from spec:** PRD FR-3, FR-4, FR-10
- **Principle(s) in tension:** Core §1 never hand-roll cryptography, §3 design by contract

## Context

The Archive is the contract between backup and restore and the artifact operators hold for months (PRD §8). It must carry integrity metadata (FR-3), support a version gate (FR-10), and be encrypted at rest (FR-4, pulled into v1.0 because always-on Safety Snapshots would otherwise write unencrypted full-database copies to disk). Archives can be multi-gigabyte.

## Options considered — encryption

Verified against `cryptography` 50.0.1 docs, 2026-09-15.

| Option | Pros | Cons | Standards fit |
|---|---|---|---|
| A. Fernet | Simple, high-level, hard to misuse | **Wrong tool.** The docs state the complete message must be in memory; it exposes no unauthenticated bytes, so there is no streaming mode. Unusable for multi-GB archives | Fails on the actual requirement |
| B. **Argon2id KDF + chunked AES-GCM** | Streams; authenticated; RFC 9106 first-choice KDF; `Argon2id` available since `cryptography` 44.0.0 | Chunking, nonce discipline, AAD framing and key commitment must all be got right | §1 — uses the library's primitives rather than inventing a construction |
| C. Shell out to `age` or `gpg` | Nothing to own | Another external binary; key management becomes the operator's separate problem | Weaker than B for a library |

## Decision

**Option B.** The construction below is normative; AD-6 fixes the container layout it sits in.

**Why chunking is mandatory.** `AESGCM.encrypt()` is one-shot and raises above 2³¹−1 bytes — the same whole-message-in-memory property that disqualifies Fernet. (AES-GCM's per-(key, nonce) cap of 2³²−2 blocks, ~64 GiB, is a real limit but not the binding one here; 2³²−1 is `AESGCMSIV`'s, a different primitive.)

**Construction.**

- **Key derivation.** Argon2id, `length=32`, a **fresh 16-byte random salt per Archive** — never reused across Archives, never derived from the Site. RFC 9106 first-choice parameters (`iterations=1, lanes=4, memory_cost=2**21`), falling back to the memory-constrained profile (`iterations=3, memory_cost=2**16`) where 2 GiB is unavailable, with the chosen profile recorded.
- **Where the salt lives.** In `manifest.json`, which AD-6 places as the **first, never-encrypted member** of the container. A salt is not secret, and placing it inside the envelope it decrypts would be a bootstrap paradox.
- **Key commitment.** The Manifest carries `HMAC-SHA256(derived_key, "wpbackup2-kc-v1" || archive_id)`. A wrong passphrase is detected here and raises a **distinct, named error** — FR-4 requires exactly that, and without commitment a wrong passphrase is indistinguishable from a corrupt Archive.
- **Chunk framing.** Each chunk is sealed with AES-GCM under a unique nonce. AAD binds `archive_id` (a UUIDv4 minted per Archive and recorded in the Manifest), the member role and name, the chunk index, and an **`is_final` flag** — not a total chunk count, which a streaming writer does not know when it seals chunk zero. `is_final` gives truncation detection without requiring the length up front; `archive_id` prevents chunks being spliced between two Archives encrypted under the same passphrase; the index prevents reordering.
- **Nonce discipline.** Nonces are random per chunk, and a derived key is used for exactly one Archive. Argon2id at 2 GiB is expensive enough to tempt key caching across Archives, which with a counter nonce would be catastrophic GCM nonce reuse — so the salt-per-Archive rule above is a safety property, not hygiene.
- **Format.** The Manifest is a member of the container, not a sidecar: an operator moving one file must not be able to separate an Archive from its integrity data.

## Consequences

- Positive: streaming, authenticated, truncation- and splice-resistant, and recoverable by anyone holding the passphrase. Version-gating and Verification (FR-3, FR-10) work on an encrypted Archive without a key, because the Manifest is outside the envelope.
- Negative: losing the passphrase means total loss — a feature meant to protect causing the loss it protects against. Documentation must state this plainly.
- Negative: the Manifest is unencrypted, so member names, sizes and the source Site's identity are visible to anyone holding the Archive. That is the deliberate trade for being able to verify and version-gate without a key. Credentials never appear there (AD-6), and an operator needing the metadata hidden should encrypt the Archive at rest a second time at the storage layer.
- Follow-up: committed fixture Archives per format version, exercised in CI; the supported range is derived from that fixture set, never hand-listed (AD-6).
