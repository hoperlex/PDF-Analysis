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
