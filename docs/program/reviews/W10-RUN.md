# `W10-RUN` — mutation sweep of `runs/`, `ingest/` and the migrations

Session `W10-RUN`, wave 10. Worktree `/root/w10run`, branch `agent/w10-run`,
instance `gate-w10d`.

## Provisioning

- **HEAD on arrival: `e08da85`** ("docs: the wave 10 dispatch — five parallel sweeps of
  the rule surface"), branch `agent/w10-run`, tree clean. The brief names base `fb30e96`;
  `e08da85` is one commit *later* on the same line (`fb30e96` is its parent), so the base
  premise holds with that correction.
- Worktree was already bootstrapped by the killed first attempt: `.venv/` present,
  `web/node_modules/` present, `.env` present and carrying exactly instance `gate-w10d`
  (`POSTGRES_PORT=55620`, `S3_API_PORT=59220`, `S3_CONSOLE_PORT=59221`,
  `POSTGRES_DB=audit_w10d`, `S3_BUCKET=auditmanager-gate-w10d`).

## Sweep table

_(appended as batches complete)_

### Harness

- Mutations applied to `/root/w10mut/src` (a copy of `src/`), with `contracts/`, `docs/`,
  `fixtures/` **and `db/`** symlinked in. `db/` is needed as well as the three the brief
  names: `auditmanager.shared.db.check` resolves `db/migrations/alembic.ini` from its own
  module's parents, so without it three `tests/integration/db` tests fail on
  `MigrationStateError` before reaching an assertion. **First correction to the brief.**
- Every run goes through `-o "pythonpath=/root/w10mut/src /root/w10mut" -p proveimport`.
  `proveimport` is a pytest plugin that imports `auditmanager` in `pytest_configure`,
  prints `auditmanager.__file__`, and `SystemExit`s the session unless the path starts
  with `/root/w10mut/src/`. Every result below carries that line in its log.
- Every mutation is diffed against the pristine file and the diff printed before the run;
  a mutation that produced no diff aborts as `!!! NO-OP MUTATION !!!` rather than running.
  That is the wave-10 `frozenset() or frozenset({...})` mistake, made impossible.
- Baselines through the copy: `tests/integration/runs tests/integration/ingest` = 123
  passed (35 s); `tests/integration/db` = 95 passed (59 s).

### Batch 1 — `src/auditmanager/ingest/reconciliation.py` (swept by nobody before this)

| # | rule mutated | mutation | `runs`+`ingest` | `api`+`e2e`+`composition`+`p02_journey`+`storage` | verdict |
|---|---|---|---|---|---|
| M1 | `verify_version`: a manifest entry whose bytes are present but whose **checksum or size disagrees** with the store is `storage_integrity_error` | `if published.sha256 != entry.sha256 or published.size != entry.size_bytes:` → `if False:` | 123 passed | no new failure | **UNREDDENED** |
| M2 | `report`: an `available` blob that **no manifest references** is an orphan (`_AVAILABLE_WITHOUT_MANIFEST`) | `WHERE b.state = 'available'` → `WHERE false AND b.state = 'available'` | 123 passed | no new failure | **UNREDDENED** |
| M4 | `_object_exists`: an **unreachable store** must raise, never be reported as "the object is gone" | `raise domain_error_from_storage(exc)` → `return False` | 123 passed | no new failure | **UNREDDENED** |
| M5 | `report`'s default `stale_command_age="1 hour"` | → `"9999 hours"` | 123 passed | not run | **UNREDDENED** (every call site in the suite passes the argument explicitly) |

**Correction, mid-wave.** The second-pass selection above showed four failures in
`tests/integration/p02_journey/test_truncated_end_to_end.py`. I ran an unmutated control
of the same selection, saw the same four, and correctly concluded they were not caused by
any mutation — but my explanation (accumulated rows in the lane database) was wrong. The
integrator relayed `W10-FND`'s finding that the mutation copy also resolves **`tools/`**
from its own root, and those four tests are what a copy without `tools/` breaks. With
`tools/` symlinked in, the same selection is **321 passed, 5 skipped, 0 failed**. Batch 1
and batch 2 were re-run against the corrected copy; see "Re-verification" below.

### Batch 2 — `src/auditmanager/ingest/service.py` (swept by nobody before this)

Suites: `tests/integration/runs tests/integration/ingest` (baseline 123 passed).

| # | rule mutated | mutation | result | verdict |
|---|---|---|---|---|
| M6 | a `document_uid` belonging to **another project** is `not_found` | `if owner != project_uid:` → `if False:` | 123 passed | **UNREDDENED** |
| M7 | an upload replay whose stored outcome names no `version_uid` is `idempotency_key_stale` | `if not isinstance(raw, str):` → `if False:` | 123 passed | **UNREDDENED** |
| M8 | a `createProject` replay whose stored outcome names no `project_uid` is `idempotency_key_stale` | same shape | 123 passed | **UNREDDENED** |
| M9 | a `StorageError` escaping the upload becomes its mapped catalog code, not `internal_error` | `if isinstance(exc, StorageError):` → `if False:` | 1 failed, 3 errors | reddened — `test_a_checksum_mismatch_leaves_no_available_blob_and_no_version` |
| M10 | a published version whose manifest has no `source.document` entry is `storage_integrity_error` | code → `not_found` | 123 passed | **UNREDDENED** |
| M11 | staged temporary bytes are discarded on every failure path | `if temporary is not None:` → `if False:` | 123 passed | **UNREDDENED** |
| M12 | `source_filename` is part of the payload fingerprint | field removed from the fingerprint | 1 failed | reddened — `test_the_file_name_is_part_of_the_payload_fingerprint` |
| M13 | the target project is proved to exist **before** the key is claimed | `get_project` call removed | 1 failed | reddened — `test_unknown_project_is_refused_before_anything_is_published` |

M11 leaves real residue: with the discard disabled, the interrupted-publication tests
leave a `temporary/...` object in the lane bucket, and `tests/integration/storage`'s two
"leaves no temporary object" tests then fail on the *next* run. I deleted the one object
(`temporary/f0cbc1c98270803cbe7b6ae0e6b5b55d`) and re-ran `tests/integration/storage`
clean (44 passed) before continuing. That is `OPERATING_CONSTRAINTS.md` §6 residue from
my own mutation, not another lane.

### Batch 3 — `src/auditmanager/runs/retry.py`

Suites: `tests/integration/runs tests/integration/ingest` (baseline 123 passed).

| # | rule mutated | mutation | result | verdict |
|---|---|---|---|---|
| M14 | `RetryPolicy` refuses a budget below 1 | `if self.attempt_budget < 1:` → `if False:` | 123 passed | **UNREDDENED** |
| M15 | `RetryPolicy` refuses a ladder whose length ≠ `budget - 1` | `if len(...) != ...:` → `if False:` | 123 passed | **UNREDDENED** |
| M16 | `RetryPolicy` refuses a negative backoff | `if any(wait < 0 ...):` → `if False:` | 123 passed | **UNREDDENED** |
| M17 | `backoff_before_attempt` refuses an attempt past the budget | `raise ValueError(...)` → `return 0.0` | 123 passed | **UNREDDENED** |
| M18 | `retries(None)` is `False` — a stage that did not fail is never retried | → `return True` | 3 failed | reddened — three `test_retry_policy` cases |
| M19 | `budget_exhausted`'s `bool(self.records)` clause | empty records → `True` | 123 passed | **unreddenable by construction** (argument below) |
| M20 | `close()` reads `records[-2]` for `retried_on_error_code` | → `records[0]` | 123 passed | **unreddenable by construction** (argument below) |
| M21 | `not_attempted` reports `attempts: 0`, not one failed attempt | `attempts=0` → `attempts=1` | 123 passed | **UNREDDENED** |
| M22 | `retry_waited_seconds` is rounded to 6 places | → `round(..., 0)` | 123 passed | **UNREDDENED** |

**M19, unreddenable by construction.** `AttemptSummary.attempts` is only ever
`len(records)` (`AttemptLedger.close`) or `0` (`not_attempted`). `budget_exhausted`
returns `False` before reaching the clause whenever `attempts < attempt_budget`, so the
clause is reached only when `len(records) >= attempt_budget`. For `records` to be empty
there the budget would have to be `<= 0`, which `__post_init__` refuses. The clause is
dead for every policy the constructor admits — it is defence against M14's refusal being
removed, not a rule of its own. Guarding M14 is the useful move, and I did.

**M20, unreddenable by construction.** `retried_on_error_code` is "the code of the last
attempt that was retried". An attempt is retried only if `policy.retries(error)` is true,
and `RETRYABLE_STAGE_ERRORS` has exactly **one** member. Every retried attempt in any
admissible policy therefore carries the identical code `dependency_unavailable`, so
`records[0]`, `records[-2]` and every other retried index are indistinguishable by value.
Making them distinguishable would mean widening `RETRYABLE_STAGE_ERRORS`, which is a
product decision and not mine. Not faked as a test.

### Batch 4 — `src/auditmanager/runs/executor.py`

First pass `tests/integration/runs tests/integration/ingest` (154 with this wave's new
tests); second pass `api`, `e2e`, `composition`, `p02_journey`, `storage`, `exports`,
`db`, `findings`, `decisions` (498 passed, 5 skipped).

| # | rule mutated | mutation | first | second | verdict |
|---|---|---|---|---|---|
| E1 | a stage that never ran is recorded failed-by-absence, so the run reaches a terminal | `missing = [...]` → `missing = []` | green | green | **UNREDDENED** |
| E2 | a failed preparation stage halts the chain | `if result.status is not StageStatus.SUCCEEDED:` → `if False:` | green | green | **UNREDDENED** |
| E4 | the run's declared `provider_mode` is cross-checked against the adapter | `if False:` | 2 failed | — | reddened — `test_mode_crosscheck_is_reachable` |
| E5 | `cost_basis` defaults to `estimated`, not to the flattering value | `.get(..., "measured")` | green | green | **unreddenable by construction** |
| E6 | a `failed` model call records `analysis_failed` as its `error_code` | → always `None` | green | green | **unreddenable by construction** |
| E7 | the `metrics` scalar filter, which the frozen stage-result schema requires | filter removed | green | green | **unreddenable by construction** |
| E9 | `_run_text_analysis_stage` refuses a missing required input | `if False:` | green | green | **unreddenable by construction** |
| E10 | `parameters.call_status` is still written for pre-`0005` legibility | key removed | 3 failed | — | reddened — `test_call_status_and_output_tokens` |

**E5.** `ModelCallRecord.as_dict()` always emits a `"cost_basis"` key, and `cost_basis` is
a dataclass field whose own default is `"estimated"`. `document.get("cost_basis",
"estimated")` therefore never falls back — the `.get` default is dead code. The live
default is in `analysis/text/provenance.py`, another tree, and it is set from the response
(`"measured" if response.reported_cost_usd is not None else "estimated"`).

**E6.** No code path in `src/` ever constructs a `ModelCallRecord` with `status="failed"`.
`CALL_FAILED` is defined in `provenance.py` and appears only in the `CALL_STATUSES` set;
every `status=` site in `analysis/text/stage.py` is the *stage* status, a different
vocabulary. The executor's own comment says why: a transport failure raises out of
`complete()`, "so there is no response to record one from", and `model_call_rows: 0` is
exactly the evidence `P4_CLOSURE.md` §1 cites. The branch is reachable only by a stage that
does not exist. Not faked as a test.

**E7.** Every value `analysis/text/stage.py` puts in `metrics` is a `str`, `int`, `float`
or `bool`. The filter is prospective defence for a stage that returns a structured metric —
the wave-3 "removing it makes something *unspecified* rather than wrong" shape. Writing
such a stage is product code in another tree.

**E9.** Unreachable through `execute_run`. The branch fires when `ROLE_TEXT_LAYER` or
`ROLE_DOCUMENT_GRAPH` is absent, but `_run_text_analysis_stage` is called only when
`halted` is `False`, which means all three deterministic stages succeeded, which means the
runner's required-output guard already published both roles. It is defence behind E2's
halt, and E2 is now guarded, which is the useful move.

### Batch 5 — `src/auditmanager/runs/reconciliation.py` and `scope.py`

| # | rule mutated | mutation | result | verdict |
|---|---|---|---|---|
| R30 | `RECONCILIATION_TERMINAL` is the declared terminal `failed` | → `"cancelled"` | 3 failed | reddened — `test_reconciliation_and_terminals` |
| R31 | `INTERRUPTED_REASON` is `executor_process_ended_before_terminal` | → `"something_went_wrong"` | 154 passed | **UNREDDENED** |
| R32 | `INTERRUPTED_TERMINAL_REASON` is `analysis_failed` | → `internal_error` | 154 passed | **UNREDDENED** |

### Batch 6 — `db/migrations/**`

Mutated on a **full copy of the tree** at `/root/w10mutdb`, not on a copy of `src/` alone:
`tests/integration/db` applies migrations by running the literal `alembic` command as a
subprocess with `cwd` set to the repository root *derived from the test file*, so a
`src/`-only copy never reaches the mutated migration. `auditmanager.__file__` was checked
to resolve under `/root/w10mutdb/src` on every run. Clean-copy baseline: 95 passed.

| # | rule mutated | mutation | `tests/integration/db` | verdict |
|---|---|---|---|---|
| D1 | `model_call` carries the immutability trigger | dropped from the table list | 1 failed | reddened — `test_exactly_the_declared_tables_are_immutable` |
| D2 | the append-only trigger fires on UPDATE as well as DELETE | template → `BEFORE DELETE` | 1 failed | reddened — `test_the_decision_ledger_refuses_update_and_delete` |
| D3 | `am_append_only` raises `AM002` | → `AM001` | 2 failed | reddened |
| D4 | `am_immutable_row` raises `AM003` | → `AM001` | 7 failed | reddened |
| D5 | the write-once guard refuses a rewrite of a non-NULL column | `IF false THEN` | 1 failed | reddened |
| D6 | the state guard refuses an INSERT in a non-initial state | `IF false AND NOT EXISTS` | 1 failed | reddened |
| D7 | the frozen-column guard refuses an edit | `IF false THEN` | 1 failed | reddened |
| D8 | **`model_call`'s trigger fires on UPDATE** | re-declared `BEFORE DELETE` only | green | **UNREDDENED** |
| D9 | **`finding_evidence`'s trigger fires on DELETE** | re-declared `BEFORE UPDATE` only | green | **UNREDDENED** |
| D10 | **`audit_event`'s trigger fires on UPDATE** | re-declared `BEFORE DELETE` only | green | **UNREDDENED** |

D8/D9/D10 were run against `tests/integration/db`, `findings`, `decisions` and `runs`
together — 235 passed under each. **The SQLSTATEs themselves are well guarded; the gap is
per-table, per-arm reachability**, which `test_schema_shape.py` cannot see because it reads
`pg_trigger` for the attached *function name* and never asks what the trigger fires on.

Of the eight tables carrying one of these triggers, `model_call` had **no** write attempt
anywhere in the repository. `finding_evidence` had UPDATE only (the grounding-gate suite's
nudged anchor); `audit_event` had DELETE only.

A wide (whole-battery) second pass of D8/D9/D10 was started and had to be discarded: I was
running two mutation streams at once against one MinIO bucket and one PostgreSQL instance,
and the results were full of unrelated failures. Everything above was re-run serially. The
lesson is the one already on record — never measure during a fan-out — and it applies to a
session's own parallelism, not only to subagents.

---

## The guards written

Fifteen rules, five files, 45 new tests. Every one was watched red under its own mutation
and green without it, on the corrected copy, serially.

`tests/integration/runs/test_retry_policy_refusals.py` — 18 tests

| rule | literal pinned | authority | red under |
|---|---|---|---|
| `RetryPolicy` refuses a budget below 1 | `"at least one attempt"`, budgets `0` and `-1` | the constructor's stated contract | M14 (2 failed) |
| a ladder of length ≠ `budget - 1` does not construct | the message's three numbers, at four budget/ladder pairs | the module's "exactly `ATTEMPT_BUDGET - 1` entries, checked at construction" | M15 (4 failed) |
| a negative wait does not construct | `"a backoff cannot be negative"`; `0.0` is accepted | the boundary is `< 0`, not `<= 0` | M16 (2 failed) |
| an attempt past the budget is refused | `"attempt 4 is past a budget of 3"` (full equality) | `ATTEMPT_BUDGET == 3`, re-pinned in the same file | M17 (3 failed) |
| `not_attempted` reports `attempts: 0` | the whole `metrics()` mapping, every value written out | "a stage that never reached the provider" | M21 (1 failed) |
| `retry_waited_seconds` keeps sub-second precision | waits `0.0 / 0.25 / 0.125`, total `0.375` | — | M22 (1 failed) |

`tests/integration/ingest/test_reconciliation_rules_with_no_guard.py` — 6 tests

| rule | literal pinned | authority | red under |
|---|---|---|---|
| a stored digest disagreeing with the manifest is refused | both digests, computed from bytes the test built; impostor is the **same length** so only the digest half can fire | the manifest row, which is immutable | M1 (2 failed) |
| a stored **size** disagreeing is refused | digests asserted *equal*, so the refusal is the size comparison alone | same | M1 (2 failed) |
| an `available` blob no manifest references is an orphan | `recorded_state == "available"`, `describe()` string in full | the `blob` state machine's declared edges | M2 (1 failed) |
| an unreachable store is an outage, not missing bytes | `dependency_unavailable` + `retryable is True`, against `storage_integrity_error` + `False` | the frozen catalog, read off the envelope | M4 (1 failed) |
| `report()`'s default threshold is one hour | 59 minutes not stale, 61 minutes stale | — | M5 (1 failed) |
| `abandon_stale_commands()` carries the same default | same boundary, plus the resulting states | — | M5 |

`tests/integration/ingest/test_service_refusals_with_no_guard.py` — 7 tests

| rule | literal pinned | authority | red under |
|---|---|---|---|
| a document owned by another project is `not_found` | `details["aggregate_type"] == "Document"` | distinguishes it from the unknown-*project* refusal three lines above | M6 (1 failed) |
| an upload replay naming no `version_uid` is `idempotency_key_stale` | `details["command_type"] == "upload_source_document"` | the catalog's meaning of the code | M7 (1 failed) |
| the same on `createProject` | `"create_project"` | same | M8 (1 failed) |
| a version with no source manifest entry is `storage_integrity_error` | `details["role"] == ROLE_SOURCE_DOCUMENT`, and **no** `blob_id` key | the blob-role spelling, which differs from the manifest-entry spelling and so names this fault and not the other two | M10 (1 failed) |
| a failure after staging discards the staged bytes | the `temporary/` prefix is empty before and after | the same prefix `tests/integration/storage` asserts on | M11 (1 failed) |

`tests/integration/db/test_every_immutable_table_refuses_a_write.py` — 7 tests

| rule | literal pinned | authority | red under |
|---|---|---|---|
| `model_call` refuses UPDATE and DELETE | `AM003`, and the row's `provider_mode`/`cost_micros`/`input_tokens` unchanged | `SQLSTATE_IMMUTABLE_ROW_VIOLATION` from the shared kernel | D8 (3 failed) |
| `finding_evidence` refuses DELETE as well as UPDATE | `AM003` | same | D9 (1 failed) |
| `audit_event` refuses UPDATE as well as DELETE | `AM002`, and `"append-only ledger"` in the message | `SQLSTATE_APPEND_ONLY_VIOLATION` | D10 (1 failed) |

`test_schema_shape.py` stayed **green** under all three, which is the finding.

`tests/integration/runs/test_the_interruption_vocabulary_is_pinned.py` — 4 tests

| rule | literal pinned | authority | red under |
|---|---|---|---|
| the interrupted reason | `"executor_process_ended_before_terminal"`, written out | `OD-10`; also asserted *not* to be a declared state, with the eight-name `audit_run` vocabulary written out | R31 (2 failed), R30 (2 failed) |
| the terminal reason | `"analysis_failed"`, written out | cross-checked against `ErrorCode`, generated from `contracts/domain/v1/error-codes.json` | R32 (2 failed) |

`tests/integration/runs/test_a_halted_chain_reaches_a_terminal.py` — 3 tests

| rule | literal pinned | authority | red under |
|---|---|---|---|
| a failed preparation stage halts the chain | exactly one `stage_result` row, zero `model_call` rows, provider never asked | the executor's own stated reason | E2 (2 failed) |
| the stages that never ran are named | the three stage names written out, in the result *and* in `audit_run.degradation_set` | `PC01_STAGES` re-spelled as a literal | E1 (3 errored: `select_terminal` raises `validation_failed` and the run is left `running`) |

## Rules unreddenable by construction

| rule | argument |
|---|---|
| `AttemptSummary.budget_exhausted`'s `bool(self.records)` | `attempts` is `len(records)` or `0`; the clause is reached only when `len(records) >= attempt_budget`, which needs `attempt_budget <= 0`, which `__post_init__` refuses. Dead for every admissible policy. Guarding M14 is the useful move. |
| `AttemptLedger.close`'s `records[-2]` | `RETRYABLE_STAGE_ERRORS` has exactly one member, so every retried attempt carries the identical code. `records[0]`, `records[-2]` and every other retried index are indistinguishable by value. Making them distinguishable is a product decision. |
| `executor._record_model_calls`' `error_code` for a `failed` call | nothing in `src/` ever builds a `ModelCallRecord` with `status="failed"`. A transport failure raises out of `complete()` and records no row — `model_call_rows: 0`, which is `P4_CLOSURE.md` §1's own evidence. |
| `executor`'s `cost_basis` `.get(..., "estimated")` fallback | `ModelCallRecord.as_dict()` always emits the key. The live default is a dataclass field in another tree. |
| `_text_stage_result`'s scalar filter | every value `analysis/text/stage.py` puts in `metrics` is already a scalar. Prospective defence for a stage that does not exist. |
| `_run_text_analysis_stage`'s missing-required-input refusal | called only when `halted` is `False`, which means all three deterministic stages succeeded, which means the runner's required-output guard already published both roles. Defence behind E2's halt, which is now guarded. |

## Product defects, left unrepaired

**1. `read_source_bytes` returns bytes the manifest does not describe, silently.**
Owning trees: `src/auditmanager/storage/s3.py` (`S3BlobStore.read`) and
`src/auditmanager/ingest/service.py` (`IngestService.read_source_bytes`). Not repaired.

`read(blob_id, verify=True)` re-hashes what it read and compares the hash to the **object's
own** recorded `content-sha256` metadata. An object whose bytes and whose recorded digest
were both replaced is internally consistent, so the read succeeds. `read_source_bytes`
already holds the `ManifestEntry` — it calls `require_source_entry(version_uid)` to get the
`blob_id` — and never compares `entry.sha256` to what came back.

Consequence: for the exact fault `Reconciler.verify_version` exists to detect, the read path
returns the wrong document with no error. A reviewer opening the source of a published
version sees the impostor; reconciliation over the same version raises
`storage_integrity_error`. The two disagree about the same row.

Reproduced in
`tests/integration/ingest/test_reconciliation_rules_with_no_guard.py::test_a_version_whose_stored_checksum_disagrees_with_its_manifest_is_refused`,
which pins the behaviour **as it is** with a comment pointing here, so the defect cannot be
closed silently: if the read starts refusing, that assertion fails and names this note.

Suggested shape of the fix, for the owning tree and not applied here: `read_source_bytes`
compares `sha256_of(returned)` — or the store's recorded digest — against `entry.sha256`
and raises `storage_integrity_error` with `expected_sha256`/`actual_sha256`, which is what
`verify_version` already does.

**2. Three dead branches**, listed in the table above (`bool(self.records)`, the
`failed`-call `error_code`, the `cost_basis` `.get` default). Not defects — each is
defence — but each is currently unreachable, so none of them is doing anything today, and a
reader could take any of them for a live rule. Owning trees: `src/auditmanager/runs/`.

## Existing assertions encoding the implementation rather than the contract

1. **`tests/integration/runs/test_reconciliation_and_terminals.py:297`** —
   `assert row["interrupted_reason"] == INTERRUPTED_REASON`, with the constant imported
   from the module under test at line 29. Both sides move together; the constant was
   changed to `"something_went_wrong"` and 154 tests passed. Now covered by literals in
   `test_the_interruption_vocabulary_is_pinned.py`. **The original line is left as it is —
   it is not wrong, it is just not evidence — and changing it is not this session's to do.**
2. **`tests/integration/runs/test_reconciliation_and_terminals.py:298`** —
   `assert row["terminal_reason"] is not None`. Field, not reason: any of the catalog's
   codes satisfies it. Now covered.
3. **`tests/integration/db/test_schema_shape.py:127,145`** —
   `test_exactly_the_declared_tables_are_append_only` and `..._are_immutable` read
   `pg_trigger` for the attached *function name*. That is a catalog claim standing where a
   reachability claim is needed: three trigger arms could be removed with both tests green.
   Now covered by `test_every_immutable_table_refuses_a_write.py`.
4. **`tests/integration/runs/test_retry_policy.py`** and
   **`test_exhausted_budget_run_row.py`** — fourteen assertions of the form
   `adapter.calls == ATTEMPT_BUDGET`, `waits == list(BACKOFF_SECONDS)`. These import the
   constants and so move with them. **They are safe, and the reason is worth recording:**
   `test_retry_policy.py::test_the_attempt_budget_and_backoff_are_pinned_and_agree` pins
   `3` and `(2.0, 8.0)` as literals, so a drift in either constant reddens there. The
   pattern is load-bearing on that one test, and `test_retry_policy_refusals.py` now
   re-pins both independently.
5. **`tests/integration/ingest/test_publication.py:61,70,83`** —
   `== ACCEPTED_MEDIA_TYPE`, imported from `ingest.envelope`. Also safe, and checked rather
   than assumed: mutating `ACCEPTED_MEDIA_TYPE` to `"application/x-pdf"` reddens 23 tests,
   because the migration's `ck_document_version_media_type CHECK (media_type =
   'application/pdf')` is an independent authority and refuses the row. The database is
   doing the pinning.

## Anything false in the brief

1. **The symlink list is incomplete.** The brief says to symlink `contracts/`, `docs/` and
   `fixtures/`. `db/` is also needed — `auditmanager.shared.db.check` resolves
   `db/migrations/alembic.ini` from its own module's parents, and without it three
   `tests/integration/db` tests fail on `MigrationStateError` against an *unmutated* copy.
   `tools/` is also needed; the integrator relayed that mid-wave from `W10-FND` and it
   accounts for four `tests/integration/p02_journey` failures I had initially and wrongly
   attributed to database population. With `db/` and `tools/` both present the clean copy
   is green everywhere. **My first-pass reds for batches 1 and 2 were all re-run against
   the corrected copy and are unchanged (416 passed, 0 failed under every mutation).**
2. **A `src/`-only copy cannot mutate the migrations at all.**
   `tests/integration/db` applies them by running the literal `alembic` command as a
   subprocess with `cwd` set to the repository root derived from *the test file*, so the
   real `db/` is always used no matter what `pythonpath` says. Batch 6 needed a full copy
   of the tree at `/root/w10mutdb`. The brief's method section does not mention this and it
   is the difference between measuring the migrations and appearing to.
3. **Base commit.** The brief names `fb30e96`. `HEAD` on arrival was `e08da85`, one commit
   later on the same line (`fb30e96` is its parent) — the dispatch commit itself. Not an
   error, but the stated base is not what a correctly-seeded worktree lands on.
4. **The baseline count.** `816 passed / 5 skipped / 116 subtests` was exactly right, and
   `make gate` returned `GATE OK` before any change.
5. **Everything else held**: the instance and ports were free and correct, `make gate` runs
   as described, `npm --prefix web ci` was already done by the killed first attempt, and no
   live provider was needed.

## Two things about the environment, for whoever runs the next wave

1. **The scratchpad log path is shared between the wave-10 sessions.** My first
   `make gate` log, written to this session's own scratchpad directory, came back
   interleaved with `rootdir: /root/w10anl` and `/root/w10api/web` — other streams' output
   in my file. `ps` showed `/root/w10api/.venv/bin/python -m pytest -o
   pythonpath=/root/w10api-mut/src …` running in the same container. The parallel streams
   are not as isolated as "disjoint trees on their own instances" suggests. Every
   measurement in this report was re-taken with logs under `/root/w10mut/logs/`.
2. **Two mutation streams at once corrupt each other even on one instance**, because
   `tests/integration/ingest` and `tests/integration/storage` share one MinIO bucket and
   `make foundation` needs the lane's own database. I did this to myself once and threw the
   results away. Everything reported here was measured serially.

## Gate

```
make gate  →  GATE OK: battery, foundation, frontend and whitespace all pass
861 passed, 5 skipped, 116 subtests passed in 267.84s
```

Baseline was 816 / 5 / 116; this wave adds **45 tests** and removes none.

**Elapsed wall-clock: 2 h 27 min** (14:40:30 to 17:07:17, 2026-09-16), including the
killed first attempt's bootstrap, which this session inherited rather than repeated.
