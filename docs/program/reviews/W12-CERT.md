# `W12-CERT` — re-certification of PC-01 after waves 11 and 12

Session `W12-CERT`, wave 12 stage B. Worktree `/root/w12cert`, branch `agent/w12-cert`,
logs `/root/w12cert-logs/`, instance `gate-w12b` (55660 / 59260 / 59261, `audit_w12b`,
`auditmanager-gate-w12b`).

**`HEAD` on arrival: `e6eae1e1a8a5a7c7bca8075ab9511e9c75a2d6f2`** — `merge: stage B's brief,
with the real base`, the tip of `origin/dev`. The dispatch names base `2be71b9`; `e6eae1e`
is two commits later on the same line (`3f49385` and the merge `e6eae1e`, both docs-only).

**Started: 2026-09-17T12:31:24+05:00.**

Status: in progress.

---

## 0. Command log

| # | command | exit |
|---|---|---|
| 1 | `git worktree add /root/w12cert -b agent/w12-cert origin/dev` | 0 |
| 2 | `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | 0 (`bootstrap OK`) |
| 3 | `npm --prefix web ci` | 0 (184 packages) |
| 4 | `make gate` (arrival, `e6eae1e`) | 0 — `GATE OK` |

## 1. The gate at arrival

| component | expected by the brief | measured at `e6eae1e` |
|---|---|---|
| foundation | 35 | **35 passed** in 28.40 s, three `FOUNDATION-CHECK OK` sentinels |
| battery | 1505 passed / 5 skipped / 167 subtests | **1505 passed, 5 skipped, 167 subtests** in 182.38 s |
| frontend | 440 passed | **440 passed / 35 files** in 3.27 s |
| whitespace | — | clean |

`GATE OK`, exit 0. Log: `/root/w12cert-logs/gate-arrival.log`. Every figure the brief
quotes is exact.

## 2. The surface since `c0d7daf`, checked rather than taken

`git diff --stat c0d7daf..HEAD -- src/ db/` → **9 files, 232 insertions, 33 deletions**
(exit 0). `DEBT_REGISTER.md` D-1 says 8 files / 126 lines; it was measured at `5c84f43`,
before `ingest/reconciliation.py` moved in stage A, and the ninth file is that one. Not a
false premise — a figure that predates the stream it does not include.

Every row of the brief's table was read as a diff, not taken:

| File | Brief says | Verdict |
|---|---|---|
| `exports/service.py` | `CsvExport.filename` and `_FILENAME_TEMPLATE` removed | **true** — the `@property` and the module constant are both gone, `Final` no longer imported |
| `ingest/service.py` | `read_source_bytes` hashes returned bytes against the manifest digest | **true** — `sha256_of(data) != entry.sha256` → `STORAGE_INTEGRITY_ERROR` |
| `storage/s3.py` | `read(verify=True)` refuses an object with no recorded digest | **true** — `recorded is None` → `BlobMetadataInvalidError`; the old guard was `recorded is not None and recorded != actual` |
| `analysis/text/stage.py` | `cost_basis` added to the success path's metrics | **true** — added beside `cost_usd` in the success metrics dict |
| `ingest/reconciliation.py` | `verify_version` hashes bytes, after a declaration check, with an unstamped object refused first | **true** — three ordered questions, exactly as described |
| `shared/errors/envelope.py` | docstring only, six shapes named | **true** — docstring only |
| `multipart.py`, `projects.py`, `executor.py` | comments only, zero code lines | **true** — every changed line in all three is a comment |

## 3. Method

- Recorded journey: `env -u AUDITMANAGER_PROVIDER_MODE PYTHONPATH=src .venv/bin/pytest -q tests/e2e/pc01` → **49 passed, 5 skipped**, exit 0. This suite drives the composed application through its router.
- Mutation copy: `make mutation-copy MUT=/root/w12cert-mut` → exit 0. The unmutated copy was baselined **49 passed / 5 skipped** before any red was trusted, and `auditmanager.__file__` was printed and resolves to `/root/w12cert-mut/src/auditmanager/__init__.py`.
- **Liveness control**, before any real mutation: `raise RuntimeError("MUT-LIVE-CONTROL")` at the top of `build_application` in the copy → **2 failed, 47 errors**. The copy is what pytest imports.
- Every mutation was applied by `/root/w12cert-logs/mut.py`, which refuses a literal that is absent, ambiguous or a no-op, and **prints the changed line back** so it is read for meaning. Transcripts: `/root/w12cert-logs/mut-*.log`.
- No expectation in any probe is imported from the module it tests; every digest, count and constraint below is read out of the live database, the live object store or the frozen contract.

## 4. The ten criteria

Each row: what established it, and **what would have made it fail**. "Red" figures are from the
mutation copy against the whole acceptance suite, so a mutation that reddened only one test is
shown to have reddened only that one.

### Criterion 1 — services and a composed application, from documented commands

**Evidence.** `make bootstrap` exit 0 twice-idempotent by the gate's own check; `make foundation`
35 passed with three `FOUNDATION-CHECK OK` sentinels; `PYTHONPATH=src .venv/bin/python -m
auditmanager.api.app` prints `wired, provider_mode=proxy` and `operations=12`, exit 0, and makes
no provider call. The complete set of input names the twelve operations accept was expanded from
the frozen `openapi.json` (§6.1) — 12 operations, exactly.

**Able to fail — three ways, all measured.**

| | change | result |
|---|---|---|
| live | `unset DATABASE_URL` | exit **2**, naming `DATABASE_URL` |
| live | `unset S3_BUCKET` | exit **2**, naming `S3_BUCKET` |
| M-C1a | `settings._require`: `if not value:` → `if False:` | **1 failed / 48 passed** — `test_c1_a_misconfigured_dependency_fails_at_construction_not_at_first_use` |
| M-C1b | the `listProjects` route commented out | **4 failed / 45 passed**, including `test_c1_the_twelve_operations_are_exactly_the_frozen_contract` |

**Holds.**

### Criterion 2 — migrate an empty database

**Evidence.** A scratch database was created and **verified empty first** (`\d` → `Did not find
any relations`), then migrated: `alembic upgrade head` exit 0, running 0001→0002→0003→0004→0005.
Head `0005_truncated_call_status`. **16 base tables (including `alembic_version`) and 1 view
(`finding_current_verdict`)** — see §7, defect W12CERT-OBS-1, on the "17 tables" of the previous
record.

**Able to fail.** `alembic downgrade -1` on that scratch database → `make check-db` exits **2**:
`FOUNDATION-CHECK FAIL check-db: the database is at 0004_cost_basis, expected head
0005_truncated_call_status`.

**Holds — but not on the strength of the acceptance suite.** See §7, W12CERT-DEF-1: the acceptance
test named for this criterion **cannot fail on a wrong head**, measured.

### Criterion 3 — an immutable version and a verified private S3 object

**Evidence.** `uploadDocument` → 201, `version_ordinal` 1, `sha256` `6d53674f…`, `byte_size`
58978. `streamDocumentVersionContent` returns 58978 bytes hashing to the declared digest.
Exactly one manifest entry, role `source.document`, `sha256` `6d53674f…`, `size_bytes` 58978.
The surface declares no operation that can mutate a version (§6.1: the twelve accept
13 distinct input names and none is a digest).

**Able to fail.** M-C3 — `_version_view` reports the digest with its last nibble flipped:
**4 failed / 45 passed**, `test_c3_the_upload_publishes_the_corpus_baseline_with_its_declared_bytes`,
`…a_second_upload_publishes_a_new_identity…`, plus the criterion-6 and criterion-8 tests that
resolve through the same view.

**Holds.**

### Criterion 4 — the deterministic path, one live `text_analysis`, the states and the mode

**Evidence — live, not recorded.** Run `run_01M2Q5C0WRKRBX5SK3S4RCHGB8`: `state=published`,
`provider_mode=live`, `terminal_reason=NULL`, `degradation_set=[]`, four stages
(`source_preparation`, `page_geometry_extraction`, `document_context_build`, `text_analysis`)
all `succeeded`. Read from `audit_run` and `stage_result`, not from the test's print.

**`cost_basis` on the success path — the wave-11 change, certified against a real success.**
`stage_result.metrics` for `text_analysis` on the published live run carries
`"cost_basis": "measured"` beside `"cost_usd": 0.0387`. Before wave 11 this key existed on the
overrun branch only, so it answered on the run that failed its budget and raised `KeyError` on
the run that succeeded. Measured on the success path here.

**Able to fail.** M-C4 — the adapter's refusal `if provider_mode is not None and provider_mode !=
self._provider_mode:` → `if False:`: **1 failed / 48 passed**,
`test_c4_a_caller_cannot_talk_a_recorded_deployment_into_reporting_live`.

**Holds for the API. Named exception for the UI clause** — see §7, W12CERT-DEF-3.

### Criterion 5 — seeded issues located, every quotation on its declared page

**Evidence — live.** **3 of 3** seeded issues located (`SI-01`, `SI-02`, `SI-03`); **0 of 6**
near-miss controls flagged, compared against 5 published quotations; 3 observations, 5 evidence
rows; every published quotation verified present on its declared page against the corpus's own
extractor.

**Able to fail — two ways.**

| | change | result |
|---|---|---|
| M-C5a | `resolve_anchor` resolves nothing (`for candidate in ():`) | the run publishes **0 findings** rather than misattributed evidence; the journey fixture errors, 40 errors. Findings collapse rather than degrade |
| M-C5b | the API reports evidence one page later (`page_number=e.page_number + 1`) | **1 failed / 48 passed** — `test_c5_every_published_quotation_exists_on_its_declared_page` |

**Holds.** M-C5b also exposes W12CERT-DEF-2 (§7): of the three criterion-5 tests, only one can
tell a systematic page shift from a correct one.

### Criterion 6 — open the page, accept, reject, comment without overwriting history

**Evidence.** Accept 201, reject 201, a later comment 201 appending without altering the verdict.
The ledger's append-only rule established **directly against the live database**, not inferred:

```
UPDATE expert_decision_event ... -> refused, SQLSTATE=AM002, "append-only ledger; UPDATE is refused"
DELETE FROM expert_decision_event -> refused, SQLSTATE=AM002, "append-only ledger; DELETE is refused"
ledger rows before 41, after 41
```

**Able to fail.** M-C6 — `decision_history` returns only its last row: **1 failed / 48 passed**,
`test_c6_a_later_comment_appends_without_overwriting_the_history`.

**Holds.** Note W12CERT-DEF-4 (§7): the acceptance test named for the append-only rule asserts the
*route set*, not the trigger; the trigger is held by `tests/integration/decisions/**`, which the
gate runs.

### Criterion 7 — a UTF-8 CSV resolving to the exact aggregates

**Evidence — measured on the live run's export, independently of the suite.** 17 columns in the
frozen order; **5 data rows**, one per published evidence item; 3 distinct `finding_uid`;
`run_id` single-valued and equal to the live run; `provider_mode` = `live` on every row;
UTF-8 BOM present; **6 CRLF and 0 bare LF**; `content-type: text/csv; charset=utf-8`; two
exports byte-identical.

**The one source-compatible break, checked.** `CsvExport.filename` and `_FILENAME_TEMPLATE` are
gone. `grep` over `src/`, `tests/`, `tools/` and `web/src` finds **no surviving reference** to
either. The served name is built at the transport: `Content-Disposition: attachment;
filename="run_01M2Q5C0WRKRBX5SK3S4RCHGB8.csv"`. The frozen `openapi.json` declares that header on
`exportRunCsv`'s 200 as `type: string` with **no enum, no pattern and no example**, and its
description says the name "is presentation only and is never an identity" — so the frontend's
different suggestion (`${runId}-findings.csv`) contradicts nothing. The removal breaks no
consumer in this tree and no clause of the contract.

**Able to fail.** M-C7 — `latest_comment` dropped from `COLUMNS`: **1 failed / 48 passed**,
`test_c7_the_export_is_utf8_with_the_frozen_column_set`.

**Holds.**

### Criterion 8 — restart without losing canonical state

**Evidence — a real `make down` / `make up`, not a second look at the same objects.** A census of
all 15 domain tables plus the live-call figures was taken before and after; `diff` of the two
JSON censuses exits **0**, identical, including `_live_model_calls: 1` and
`_live_cost_micros: 38700`. After the restart, a **fresh composition root** reports the live run
`published` / `live` / `degradation_set []`, lists its 3 findings, streams the stored object back
at 58978 bytes hashing to the declared `6d53674f…`, and exports byte-identically twice.

**Able to fail.** With the services down, `make check-services` exits **2**. M-C3 also reddens
`test_c8_a_freshly_composed_application_reports_the_same_canonical_state`.

**Holds.**

### Criterion 9 — idempotent replay creates no duplicates

**Evidence.** Replaying `createProject`, `uploadDocument`, `startRun` and `appendDecision` under
identical keys creates nothing new (the four `c9` replay tests, green). A write with no
`Idempotency-Key` is refused 422 `validation_failed` — the router never invents one.

**Able to fail.** M-C9 — `CommandRepository.find` always answers `None`, so every replay looks
like a fresh command: **4 failed / 45 passed**, all four replay tests.

**Holds.**

### Criterion 10 — explicit failures, no fallback and no fake success

**Evidence — the five refusals measured directly, because the suite pins only the error-code
class** (`test_c10_unsupported_input_is_refused_with_a_typed_code` accepts any of
`validation_failed`, `analysis_input_invalid`, `storage_integrity_error` and asserts nothing
about which rule refused):

| fixture | status | error_code | details |
|---|---|---|---|
| `not_a_pdf.txt` | 422 | `validation_failed` | `field=content`, `constraint=pdf_magic_bytes` |
| `encrypted.pdf` | 422 | `validation_failed` | `field=content`, `constraint=not_encrypted` |
| `image_only.pdf` | 422 | `validation_failed` | `field=page_text`, `constraint=every_page_has_extractable_text` |
| `too_many_pages.pdf` | 422 | `validation_failed` | `field=page_count`, `constraint=1 <= page_count <= 30` |
| `oversize.pdf` | 422 | `validation_failed` | `field=file`, `constraint=max_bytes` |

**5 distinct constraints out of 5.** No refusal is a 500 and none leaves a version behind.

**The unavailable provider** fails the run explicitly: `state=failed`,
`terminal_reason=dependency_unavailable`, `degradation_set=["text_analysis"]`, the failed stage
carrying `error_code=dependency_unavailable`, the three deterministic stages still `succeeded`,
0 findings published. `W6CERT-DEF-1` — the docstring that *recorded* rather than asserted those
two values, and went stale for three waves — **is repaired**: they are assertions now and cannot
drift again without failing.

**Able to fail.** M-C10 — `MAX_PAGES` 30 → 300: **1 failed / 48 passed**, the
`too_many_pages.pdf` case. The fixture is 31 pages and is a file, not a value derived from the
constant, so raising it admits the fixture instead of allocating anything.

**Holds, with the two accepted limits below and the UI exception in §7.**

## 5. The two accepted limits, re-established

### 5.1 `checksum_mismatch` — **STILL NOT INDUCIBLE** through the twelve operations

This is the limit the brief says to look hardest at, because waves 11 and 12 changed precisely
the code that decides when bytes and their declarations disagree. `W11-RD` and `W12-RCN` each
reported finding no way to induce their new faults, and each said it was an observation by the
session that wrote the code. **This is my own verdict, established four ways.**

**First — the name.** There is no `checksum_mismatch` code in the catalog. `error-codes.json`
declares **20** codes and `checksum_mismatch` is not among them; the internal
`ChecksumMismatchError` carries `code = storage_integrity_error`. The limit is therefore about
criterion 10's *checksum failure*, not about an error code, and I read it that way below.

**Second — the surface.** Every one of the twelve operations was expanded from the frozen
`openapi.json`, following every `$ref` through `components`, into the complete set of input names
it accepts:

```
getFinding                     X-Correlation-Id
appendDecision                 Idempotency-Key, X-Correlation-Id, comment, event_type, finding_observation_id
listDecisionHistory            X-Correlation-Id, cursor, limit
createProject                  Idempotency-Key, X-Correlation-Id, name
listProjects                   X-Correlation-Id, cursor, limit
uploadDocument                 Idempotency-Key, X-Correlation-Id, display_title, file
startRun                       Idempotency-Key, X-Correlation-Id, provider_mode, version_uid
getRunStatus                   X-Correlation-Id
exportRunCsv                   X-Correlation-Id
listRunFindings                X-Correlation-Id, category, cursor, limit, verdict
getDocumentVersion             X-Correlation-Id
streamDocumentVersionContent   Range, X-Correlation-Id
operations examined: 12
```

Thirteen distinct names across the whole surface. **None is digest-shaped** (no `sha`, `digest`,
`checksum`, `hash`, `md5`, `etag` or `crc`). The only digest in the system is computed by the
server from the bytes it received, so there is nothing to disagree with.

**Third — the routers enforce it independently of the document.** Measured, not read:

| attempt | answer |
|---|---|
| an extra multipart part named `sha256` alongside the file | **422 `validation_failed`**, `field=body`, `constraint=additionalProperties`, "The upload carries a part the schema does not declare." |
| a part named `content-sha256` | **422 `validation_failed`**, same details |
| `startRun` with an extra `"sha256"` JSON property | **422 `validation_failed`**, "The request body carries a property the schema does not declare." |

**Fourth — the guard is alive, shown able to fail, against live MinIO.** Green half first, then
each red, then every object purged by exact identity. Bytes built in-process; **no byte added to
any frozen corpus**.

| | probe | result |
|---|---|---|
| green | publish, then `read(verify=True)` | 62 bytes returned, identical |
| R1 | `verify_temporary` with a false declared digest | `ChecksumMismatchError` (`storage_integrity_error`), and the temporary object is **gone** — nothing canonical, nothing staged |
| R2 | `verify_temporary` with a false declared size | `SizeMismatchError` (`storage_integrity_error`) |
| R3 | bytes replaced out of band, **same length**, metadata copied verbatim | `inspect()` — head only — still reports it **sound**; `read(verify=True)` raises `ChecksumMismatchError` with both digests |
| R4 | the `content-sha256` metadata stripped, bytes correct | `BlobMetadataInvalidError`, **`validation_failed`**, `field=content-sha256` — not the integrity verdict |

**And the same fault, through the front door.** A document was uploaded through `uploadDocument`,
its canonical object replaced out of band with a same-length body under verbatim metadata, and
the twelve operations asked again:

```
streamDocumentVersionContent  -> 422  storage_integrity_error, expected_sha256 6d53674f...
getDocumentVersion            -> 200  still reports the declared digest (a declaration, not the bytes)
```

then the bytes were restored and the same call returned 200 with the original 58978 bytes.

**Verdict.** A checksum failure **cannot be induced through the twelve operations** — the surface
offers no way to hand the store bytes that disagree with a declaration, and the routers refuse the
attempt with a typed envelope. What changed in waves 11 and 12 is that the same failure, arriving
from *outside* the twelve, is now **detected and refused** by them rather than served. The limit
holds, and it is a narrower limit than it was: what was "proved only at the storage layer" in
`W6-CERT`'s pass is now also refused at the read path an operator actually calls.

**D-2 and D-4, checked behaviourally over one live version.** `verify_version` was run against a
real published version whose object was manipulated three ways in turn, with the object proved
sound before the probe and restored sound after:

| state of the object | `verify_version` says |
|---|---|
| healthy | **SOUND** (returns) |
| replaced, same length, metadata verbatim — **D-2's exact scenario** | `storage_integrity_error`, `expected_sha256=6d53674f…`, `actual_sha256=612a113c…` — **the body's digest**, not the record's |
| recording no digest — **D-4's exact scenario** | `validation_failed`, `aggregate_type=Blob`, `field=sha256`, `constraint=recorded on every published object` — **no `actual_sha256` key, no empty string** |
| restored | **SOUND** |

Both D-2 and D-4 are genuinely closed, measured rather than read off the diff. The brief's claim
that **nothing in `src/` calls `verify_version`** was checked and is true: `grep -rn verify_version
src/` returns one `def` and four docstring mentions, and no construction of `Reconciler` outside
the module.

### 5.2 `ungrounded_model_item` — **STILL UNREACHABLE BY DESIGN**, proved by mutation

**Baseline, from the live database.** `finding_observation` holds **110 rows with
`grounded = true` and 0 with `grounded = false`**, and the live run added 3 grounded observations
and 0 ungrounded ones.

**Mutation A — nothing resolves.** `resolve_anchor`'s candidate loop emptied (`for candidate in
():`), read back as a loop over nothing:

- the journey publishes **0 findings**;
- `finding_observation` is **110 before and 110 after** — **no row was written at all**, so the
  drop happens before anything reaches the database;
- `grounded = false` rows: **0**.

**Mutation B — the drop removed as well**, so evidence-free observations must reach the gate.
`_ground`'s `if not anchors: dropped += 1; continue` became `if False:`, read back as the literal
`False`:

- the run **FAILED** with `terminal_reason = analysis_input_invalid`;
- `finding_observation` still **110**, `grounded = false` rows still **0**.

**Verdict.** Even with the drop-before-the-gate removed, no ungrounded row is written: the gate
refuses the run instead of recording a diagnostic. The limit is re-established by mutation, not
inherited.

## 6. Where a number came from, and what a test actually asserts

### 6.1 The gate figures
`1505 / 5 / 167` and frontend `440` are counts I reproduced exactly at `e6eae1e`. The `440` is
`289 + 151`, and the `289 → 440` rise is `W12-WEB`'s eleven new suites. The `1505` is
`1492 + 3 (W12-RCN) + 10 (W12-DEC)`; the three stage-A reviews' own arithmetic reconciles.

### 6.2 The 18% frontend coverage gap, re-measured here rather than inherited
`W12-WEB` reports that 34 of 110 modules under `web/src` are imported by no test. I ran the
reachability closure myself from `web/`:

```
src modules: 110   reachable: 76   unreached: 34   unreached lines: 1352
```

Identical to `W12-WEB`'s figure. `terminal_reason` reaches a user in exactly one place —
`src/widgets/run-progress/ui/run-progress.tsx:112`, the `failed` arm's
`<code data-terminal-reason=…>` — and no test imports that file. `W12-WEB`'s `U-01` made that line
print a constant with all 440 tests green, and I did not need to re-run it: the module is outside
the import closure, so nothing could have observed it.

### 6.3 Tests read rather than trusted
Four acceptance tests were read and judged against what the criterion requires rather than
against their names. Three of them assert less than their name promises; each is in §7.
