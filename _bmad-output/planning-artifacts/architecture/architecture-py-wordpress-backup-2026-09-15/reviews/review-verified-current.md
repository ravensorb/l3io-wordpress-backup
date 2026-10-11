# Review — "Verified current" lens

- **Target:** `_bmad-output/planning-artifacts/architecture/architecture-py-wordpress-backup-2026-09-15/ARCHITECTURE-SPINE.md` + `docs/adr/0001`–`0010`
- **Lens:** every committed decision must be web-researched or reality-checked, not asserted from training data
- **Reviewed:** 2026-09-15
- **Method:** every claim re-checked independently against the live PyPI JSON API, the GitHub REST API, and vendor documentation. Nothing was taken from the spine, and nothing was answered from model memory.

## Verdict

**The stack table is real.** Every pinned version resolves to the actual current release on PyPI today — including two (`uv 0.12.15`, `boto3 1.43.95`) uploaded on 2026-09-15 itself, which is only possible if someone looked. The ADR comparison tables are likewise checkable and check out: dates, licences, wheel matrices and quoted manual text all match the sources. This is not a training-data document.

Five claims are wrong or stated more confidently than their sources support. One is load-bearing on a cryptographic decision.

**Counts: 34 CONFIRMED · 5 WRONG/OVERSTATED · 2 UNVERIFIABLE.**

---

## 1. Spine Stack table

Queried `https://pypi.org/pypi/<name>/json` on 2026-09-15. "Latest" is `info.version`; date is the upload time of that release's first file.

| Claim | Live value | Verdict |
|---|---|---|
| Python floor `>=3.11` | policy, not a version — supporting facts below | CONFIRMED |
| uv 0.12.15 | 0.12.15, uploaded **2026-09-15T12:07Z** | CONFIRMED |
| ruff 0.16.7 | 0.16.7, 2026-09-10 | CONFIRMED |
| mypy 2.3.1 | 2.3.1, 2026-08-15, `requires_python >=3.10` | CONFIRMED |
| pytest 9.1.1 | 9.1.1, 2026-06-19 | CONFIRMED |
| pytest-cov 7.1.0 | 7.1.0, 2026-03-21 | CONFIRMED |
| structlog 26.1.0 | 26.1.0, 2026-06-06 | CONFIRMED |
| cryptography 50.0.1 | 50.0.1, 2026-08-25 | CONFIRMED |
| PyMySQL 1.2.0 | 1.2.0, 2026-05-19 | CONFIRMED |
| boto3 1.43.95 | 1.43.95, uploaded **2026-09-15T19:23Z** | CONFIRMED |
| WP-CLI 2.12.0 | `v2.12.0`, GitHub API, published 2025-05-07 | CONFIRMED |
| import-linter "verify before binding" | 2.15, 2026-09-04 | UNVERIFIABLE-as-written — see §7 |
| mysql client "8.0+" | MySQL 8.0 left Extended Support 2026-04-30 | **WRONG-ish — see F-5** |

"ruff … pinned exactly, pre-1.0" — CONFIRMED, 0.16.7 is pre-1.0. "uv is pre-1.0 — pin it" (ADR-0007) — CONFIRMED.

---

## 2. ADR-0004 — driver comparison table

Every cell independently re-derived from the PyPI JSON for each project and release.

| Cell | ADR says | Live | Verdict |
|---|---|---|---|
| PyMySQL version/date | 1.2.0, 2026-05-19 | 1.2.0, 2026-05-19T08:26Z | CONFIRMED |
| PyMySQL pure Python | yes | only files are `pymysql-1.2.0-py3-none-any.whl` + sdist | CONFIRMED |
| PyMySQL licence | **MIT** | `license_expression: MIT` | CONFIRMED |
| PyMySQL "one universal wheel" | yes | exactly one `py3-none-any` wheel | CONFIRMED |
| mysqlclient version/date | 2.3.0, 2026-09-14 | 2.3.0, 2026-09-14T15:38Z | CONFIRMED |
| mysqlclient not pure Python | correct | C extension, per-cpython-ABI wheels | CONFIRMED |
| mysqlclient licence | **GPL-2.0** | `license_expression: **GPL-2.0-or-later**` | **Imprecise — F-3** |
| mysqlclient "**Windows only**" wheels | yes | all 16 wheels are `win_amd64`/`win_arm64` (cp310→cp315, incl. free-threaded `t` builds); Linux/macOS get only `mysqlclient-2.3.0.tar.gz` | CONFIRMED |
| mysql-connector-python version/date | 26.7.0, 2026-07-29 | 26.7.0, 2026-07-29T10:17Z | CONFIRMED |
| m-c-p "hybrid" | yes | 26 files: 24 cpython-ABI wheels **plus** a `py2.py3-none-any` pure wheel | CONFIRMED |
| m-c-p licence | GPLv2 + FOSS Exception | `license: 'GNU GPLv2 (with FOSS License Exception)'` | CONFIRMED |
| m-c-p wheels "broad" | yes | manylinux_2_28 x86_64/aarch64, macOS 14 arm64/x86_64, win_amd64, cp310–cp314 | CONFIRMED |
| Context: `mysql-connector` 2.2.9 last released **2019-04-01** | yes | 2.2.9, uploaded 2019-04-01T14:40Z, GPLv2+FOSS | CONFIRMED |

**The licence claims that drove the rejection hold.** `mysqlclient` really is copyleft (in fact *or-later*, marginally stronger than stated) and really has no Linux/macOS wheel, so the two reasons given for rejecting it are both true and both checkable. The decision is sound.

---

## 3. ADR-0006 — cryptography claims

| Claim | Source | Verdict |
|---|---|---|
| Fernet: "the complete message contents must be available in memory" | cryptography docs, Fernet → Limitations: *"Fernet is ideal for encrypting data that easily fits in memory. As a design feature it does not expose unauthenticated bytes. This means that the complete message contents must be available in memory, making Fernet generally unsuitable for very large files at this time."* | CONFIRMED — near-verbatim |
| `Argon2id` exists in `cryptography` | KDF docs document `Argon2id` | CONFIRMED |
| available since **44.0.0** | docs carry *"Added in version 44.0.0"* | CONFIRMED |
| RFC 9106 first-choice KDF | docs: *"Argon2id should be used by most users, as recommended in RFC 9106."* | CONFIRMED |
| `length=32` | RFC 9106 §4: 256-bit tag size | CONFIRMED |
| "≥16-byte random salt" | RFC 9106 §4: 128-bit salt; cryptography docs: salt *"recommended to be 16 bytes or longer"* | CONFIRMED |
| "the memory-constrained profile where 2 GiB is unavailable" | RFC 9106 §4 FIRST RECOMMENDED = Argon2id t=1, p=4, m=2²¹ (2 GiB); SECOND RECOMMENDED = t=3, p=4, m=2¹⁶ (64 MiB) | CONFIRMED — the fallback profile exists and is described correctly |
| **"AES-GCM's 2³²−1 block cap per (key, nonce) makes chunking mandatory"** | see F-1 | **WRONG** |

---

## 4. ADR-0003 — MySQL claims

| Claim | Source | Verdict |
|---|---|---|
| `MYSQL_PWD` "must be considered extremely insecure" | MySQL 8.4 Reference Manual, *Environment Variables*: *"Use of `MYSQL_PWD` to specify a MySQL password must be considered extremely insecure and should not be used."* | CONFIRMED — the ADR's quotation marks are accurate |
| deprecated as of 8.4, removal expected | same page: *"`MYSQL_PWD` is deprecated as of MySQL 8.4; expect it to be removed in a future version of MySQL."* | CONFIRMED — verbatim |
| readable via `ps` in some configurations | same page: *"Some versions of ps include an option to display the environment of running processes."* | CONFIRMED |
| `--defaults-extra-file` recommended and not deprecated | 8.4 manual, *Option Files* / *Option-File Options* — documented, no deprecation notice | CONFIRMED |
| **"must be argv position 1"** / "MySQL requires it first" | see F-2 | **OVERSTATED** |

---

## 5. ADR-0005 — WP-CLI claims

| Claim | Source | Verdict |
|---|---|---|
| Current version 2.12.0 | GitHub API `wp-cli/wp-cli` + `wp-cli/wp-cli-bundle` releases: newest tag `v2.12.0` | CONFIRMED |
| Released **2025-05-07** | `published_at: 2025-05-07T02:26:51Z` | CONFIRMED |
| "no tagged release since 2025-05-07" / "~16 months" | tag list is v2.12.0, v2.11.0 (2024-08-08), v2.10.0, v2.9.0, v2.8.1 — nothing newer. 2025-05-07 → 2026-09-15 = 16.3 months | CONFIRMED, and the arithmetic is right |
| "`master` carries commits dated today" | latest commits on default branch: **2026-09-15T11:31Z**, 2026-09-14, 2026-09-14 | CONFIRMED — literally true on the day of writing |
| `wp search-replace` has **no credential flags** | full documented option list — `--dry-run --network --all-tables[-with-prefix] --export[_insert_size] --skip-tables --skip-columns --include-columns --precise --recurse-objects --verbose --regex[-flags/-delimiter/-limit] --format --report[-changed-only] --log --before_context --after_context` — contains **no** user/password/host option | CONFIRMED |
| bootstraps WordPress / reads `wp-config.php` via `$wpdb` | consistent with the absence of credential flags and WP-CLI's documented bootstrap model | CONFIRMED |
| pointed at a site with global `--path` | `--path=<path>` is listed under **Global Parameters**: *"Path to the WordPress files."* | CONFIRMED |
| serialization handling | docs: *"Search/replace intelligently handles PHP serialized data, and does not change primary key values."* | CONFIRMED |
| `--dry-run` maps onto FR-19 | docs: *"Run the entire search/replace operation and show report, but don't save changes to the database."* | CONFIRMED |

The ordering constraint the ADR derives from this — config rewrite *must* precede search-replace — follows correctly from the verified facts. It is a real forcing function, not a stylistic preference.

---

## 6. ADR-0009 — Python EOL dates

Checked against `devguide.python.org/versions/`.

| ADR claim | devguide | Verdict |
|---|---|---|
| 3.9 EOL 2025-10-31 | end-of-life, **2025-10-31** | CONFIRMED |
| 3.10 EOL **2026-10**, "roughly six weeks away" | security, EOL *2026-10* | CONFIRMED (≈2–6 weeks from 2026-09-15; "roughly six weeks" is the outer edge but honest) |
| 3.11 security-only to 2027-10 | security, *2027-10* | CONFIRMED |
| 3.12 to 2028-10 | security, *2028-10* | CONFIRMED |
| 3.13 and 3.14 in bugfix | bugfix (*2029-10*, *2030-10*) | CONFIRMED |
| "mypy 2.x requires ≥3.10 to run anyway" | mypy 2.3.1 `requires_python: >=3.10` | CONFIRMED |
| Option C: ≥3.14 gets `filter='data'` free | see §7 | CONFIRMED |

Note the devguide marks every date except 3.9's in italics as provisional. The ADR treats 3.10's as firm enough to act on; that is reasonable but the provisionality is not noted.

---

## 7. AD-11 / tarfile, and import-linter

### tarfile (`docs.python.org/3/library/tarfile.html`)

| Claim | Docs | Verdict |
|---|---|---|
| `filter='data'` is a valid value | values are `'fully_trusted'`, `'tar'`, `'data'`, `None`, or a callable | CONFIRMED |
| interpreter default is `fully_trusted` on 3.12/3.13 | *"Changed in version 3.14: The filter parameter now defaults to 'data'."* + *"Previously, the filter strategy was equivalent to fully_trusted."* | CONFIRMED |
| default changed in 3.14 | as above | CONFIRMED |
| on 3.11 it is "patch-level-dependent via backport" | *"Extraction filters were added to Python 3.12, but may be backported to older versions as security updates. To check whether the feature is available, use e.g. `hasattr(tarfile, 'data_filter')` rather than checking the Python version."* | CONFIRMED |

**Gap, not a factual error (F-4).** The docs' own guidance is to feature-detect with `hasattr(tarfile, 'data_filter')`. AD-11's rule as written — *"passes `filter='data'` explicitly on every call"* — will raise `TypeError` on a 3.11 patch level that predates the backport, which is precisely the situation ADR-0009 says exists. The rule correctly identifies the hazard and then specifies a mechanism that does not survive it. The fix is one `getattr`, per the docs' own example.

### import-linter

| Question | Answer | Verdict |
|---|---|---|
| Does it exist? | yes — `import-linter` on PyPI, *"Lint your Python architecture"* | CONFIRMED |
| Maintained? | 2.15 released **2026-09-04**; six releases in 2026 (2.10 Feb → 2.15 Sep); `Development Status :: 5 - Production/Stable` | CONFIRMED |
| Current version | **2.15** | CONFIRMED |
| Licence / Python support | BSD 2-Clause; `requires_python >=3.10`, classifiers through 3.14 — compatible with the 3.11 floor | CONFIRMED |
| Can it express "module X may not import module Y"? | yes — the `forbidden` contract type: *"Forbidden contracts check that one set of modules is not imported by another set of modules,"* configured with `source_modules` / `forbidden_modules`, checking descendants and **indirect** imports | CONFIRMED |
| Can it forbid *external* packages (e.g. `boto3`)? | yes — *"External packages may also be forbidden. (Be sure to configure Import Linter to include external packages)"*, requiring `include_external_packages = True` | CONFIRMED — but the spine never mentions this required setting |
| Can it forbid **stdlib** modules (`subprocess`, `shutil`, `tarfile`)? | the contract-type docs discuss internal and external third-party packages only; stdlib is not addressed | **UNVERIFIABLE** |

---

## Findings

### F-1 — ADR-0006's AES-GCM justification is wrong, and wrong in the direction that matters (load-bearing)

ADR-0006 states: *"AES-GCM's 2³²−1 block cap per (key, nonce) makes chunking mandatory, not stylistic."* Three problems:

1. **The number is wrong.** GCM's 32-bit counter yields a maximum of 2³²−2 blocks of plaintext per invocation (NIST SP 800-38D: 2³⁹−256 bits, ≈64 GiB). Not 2³²−1.
2. **It is not the binding constraint.** A 64 GiB ceiling does not make chunking mandatory for the "multi-gigabyte" archives the ADR's Context describes. If this were the only limit, single-shot encryption would be fine for the stated workload.
3. **The actual binding constraint is one the ADR does not mention — and it is the same objection used to reject Fernet.** `cryptography`'s AEAD docs state `AESGCM.encrypt()` raises for `data` larger than **2³¹−1 bytes** (≈2 GiB), and the API is one-shot: it takes the whole plaintext as a `bytes` argument, with no incremental `update()`. So the chosen primitive has *exactly* Fernet's "complete message must be in memory" property that Option A was rejected for. Chunking is what rescues Option B from Option A's fate — that is the real argument, and it is stronger than the one written down.

Suspicious detail: **2³²−1 is the documented limit for `AESGCMSIV`**, a different primitive on the same docs page. Getting AESGCM's cap by recalling the neighbouring row is the signature of training-data recall rather than a page read — and it is the one claim in ADR-0006 that was not verified, in an ADR whose header says *"Verified against `cryptography` 50.0.1 docs, 2026-09-15."*

The decision (Argon2id + chunked AES-GCM with per-chunk nonces and index/count in AAD) is still correct. Only the stated reason is wrong. **Rewrite the justification**; the correct one is available and cheaper to defend. Also worth noting: `Cipher` + `modes.GCM` in the same library *does* offer incremental `update()`, and the ADR does not say why chunked one-shot AEAD was preferred to it.

### F-2 — "`--defaults-extra-file` must be argv position 1" is stated harder than MySQL states it

AD-7 says *"passes it as `--defaults-extra-file` in argv position 1 (MySQL requires it first)"*; ADR-0003 repeats *"Must be argv position 1."*

The 8.4 manual (*Command-Line Options that Affect Option-File Handling*) actually says: **"each of these options must be given before other options,"** with documented exceptions (`--print-defaults` may follow `--defaults-file`/`--defaults-extra-file`/`--login-path`; on Windows `--install` must precede `--defaults-file`).

argv[1] satisfies "before other options", so the *implementation* is safe and the decision stands. But the *claim* is narrower and more absolute than its source, and a future reader who moves the flag to argv[2] behind another defaults-option will be told by this ADR that they broke a hard requirement they did not break. Restate as the manual does.

### F-3 — `mysqlclient` licence is GPL-2.0-**or-later**, not GPL-2.0

PyPI metadata for 2.3.0 gives `license_expression: GPL-2.0-or-later`. The ADR's table says `GPL-2.0`. This does not change the rejection — it slightly strengthens it — but a licence claim the ADR itself calls load-bearing should carry the exact SPDX expression from the index.

### F-4 — AD-1's "enforced by an import-linter contract in CI" overstates the guard's reach

AD-1's rule enumerates: *"no `subprocess`, `socket`, `shutil`, `tarfile`, `open`, `boto3`, no clock or RNG read,"* then asserts *"Enforced by an import-linter contract in CI, not by review."* Against what import-linter actually does:

- `boto3` — enforceable, **but only with `include_external_packages = True`**, which the spine never states. Without it the contract passes while checking nothing — a false green.
- `subprocess`/`socket`/`shutil`/`tarfile` — stdlib forbidding is undocumented for the `forbidden` contract type (UNVERIFIABLE above). Plausible via grimp's external-module handling, but the spine binds the enforcement mechanism without having established it.
- **`open`** — a builtin. **Not an import. Not expressible in import-linter at any configuration.**
- **"no clock or RNG read"** — import-linter sees the `import time` / `import random`, but a *read* through an already-imported module (or through `datetime.datetime.now`) is beyond an import graph.

So a rule with seven prohibitions is backed by a guard that reaches at most five of them, one of them only with an unstated config flag. This is the failure mode the project's own standards call out: prose that overstates its own coverage stops the next reader from looking. State what the contract covers and what remains review-only — and, when the contract is written, plant a violation of each clause to prove the scope, not just the rule.

Related and smaller: the spine's Stack table is headed *"Verified current 2026-09-15"* and then carries one row reading *"current at adoption — verify before binding."* That is honest, and it is also the only unverified row under a heading that promises otherwise. It is now verifiable: **import-linter 2.15**, BSD-2-Clause, released 2026-09-04, `requires-python >=3.10`.

### F-5 — the stack floor "mysql client 8.0+" is past EOL and undercuts ADR-0003's own premise

The Stack table sets the external client floor at "8.0+". Per endoflife.date, **MySQL 8.0 left Premier Support 2025-04-30 and Extended Support 2026-04-30** — as of today it is fully end-of-life; the supported LTS lines are 8.4 and 9.7.

Two consequences. First, this contradicts the Python overlay's own "supported, non-EOL runtime" rule that ADR-0009 applies rigorously to Python — the same test was not applied to the MySQL client. Second, ADR-0003's entire rejection of `MYSQL_PWD` rests on its deprecation **as of 8.4**; against an 8.0 client that deprecation does not exist. The decision is still right (the "extremely insecure" language predates 8.4 by many years), but the floor and the rationale are one version apart. Raise the floor to 8.4, or say explicitly that 8.0 clients are supported-but-EOL and that the `MYSQL_PWD` argument rests on the security text rather than the deprecation.

---

## Also confirmed (supporting claims outside the named scope)

- **ADR-0002:** `https://pypi.org/pypi/wpconfigr/json` returns **404** — the outage is real, today. `wpdatabase2` and `wpbackup2` both return 200, so the ADR's framing (dependents published, dependency missing) is exactly right.
- **ADR-0002:** `>=1.0.0,<=2.0.0` does admit 2.0.0 exactly — correct reading of PEP 440.
- **ADR-0007:** uv supports PEP 735 — *"uv uses the `[dependency-groups]` table (as defined in PEP 735)."* CONFIRMED.
- **ADR-0007:** `--locked` fails on a stale lockfile — *"Requires that the lockfile is up-to-date. If the lockfile is missing or needs to be updated, uv will exit with an error."* CONFIRMED verbatim.
- **AD-10:** `merge_contextvars` first — structlog docs: *"Use `structlog.configure()` with `structlog.contextvars.merge_contextvars()` as your **first processor**."* CONFIRMED.
- **ADR-0008:** `botocore` being outside boto3's stability guarantees — not independently checked; flagged only as unverified, not disputed.

## Recommended actions

1. **ADR-0006** — replace the AES-GCM justification with the verified one (`AESGCM.encrypt()` is one-shot and raises above 2³¹−1 bytes, so chunking is what avoids the memory property Fernet was rejected for). Add a line on why chunked AEAD over `Cipher`+`modes.GCM` streaming. *(F-1)*
2. **AD-1** — split the rule into "enforced by contract" and "review-only", name `include_external_packages = True`, and drop or relocate `open` and "no clock/RNG read". Bind import-linter **2.15**. *(F-4)*
3. **AD-11** — specify `hasattr(tarfile, 'data_filter')` feature detection, per the stdlib docs, so the 3.11 floor the project chose does not break the rule the project wrote. *(F-4, tarfile)*
4. **Stack table** — raise the MySQL client floor to 8.4, or record the EOL exception explicitly. *(F-5)*
5. **ADR-0003 / AD-7** — restate the constraint as the MySQL manual does ("before other options"). *(F-2)*
6. **ADR-0004** — correct the licence cell to `GPL-2.0-or-later`. *(F-3)*
