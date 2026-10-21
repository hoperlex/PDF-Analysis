# GATE-REPAIR-01 — the named reds, reproduced, classified and repaired

Task: `docs/program/tasks/GATE-REPAIR-01.md`. Branch `agent/gate-repair-01`, based on `54ec23eb`
(`origin/dev` at the freeze of the task file). Debt `D-187`, `D-189`, `D-190` (`D-181` read where a
named file is still red). Lane `auditmanager-gate-repair`: PostgreSQL 17 on 57600, MinIO 61400/61401,
database `auditmanager_gate_repair`, `W55B_QA_API_PORT=28500`.

## Result

**No product defect.** Four reds were reproduced on the unchanged base; all four are test-side and
all four are repaired. Two of them (`documents` stand-in, the P02 table list) are **not on the
debt register**: they were found by running the files that the brief's `grep -rln DecisionAdapter`
and the survey below name, and both come from lanes that, under `R-126`, wrote database tests
without running them. Every other red that `D-187` names was already repaired on the base by
`GATE-FIX-DB-01`, `GATE-FIX-API-01` and `GATE-FIX-CONTRACT-01` and is green here, so the row is
stale in its text (the integrator closes it; `DEBT_REGISTER.md` is a forbidden hotspot here).

| red | on the register | class | repair |
|---|---|---|---|
| `composition/test_every_port_implementation_is_whole.py::test_every_wired_implementation_carries_the_whole_port[documents]` | no (new since `D-176`) | stand-in too narrow for its guard | `_Documents` in `api/test_upload_door_revocation_is_wired.py` answers every other `DocumentPort` method with an `AssertionError` |
| `p02_journey/test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete` | no (new since `0028`) | stale pin | `P02_TABLES` counts `document_version_classification_correction` |
| `qa_w55b/test_p3_input_budget.py`, one test of the file at each run | `D-189` | environmental, two causes | the harness: default ports below the ephemeral range, bind probe, readiness of both planes |
| `jobs/test_d141_final_transaction_keeps_the_lease.py` | `D-190` | environmental (host stall) | lease 8 s instead of 2 s, gate 12 s instead of 4 s |

## Measured before (base `54ec23eb`, nothing edited)

Every row: `set -a; . ./.env; set +a; .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q
-p no:cacheprovider <paths> -rf > log; rc=$?`, one pytest process at a time, the status read from
`$?` after the redirect. Host: 8 CPUs, 11.8 GB, load 1.5 to 9 (the latter only under the burners of
`D-190`), disk free 5.4 to 6.7 GB before each run (`df -B1M /`), RAM available 2.5 to 5.9 GB.

| id | paths | rc | counts |
|---|---|---|---|
| m1 | `tests/integration/db/test_downgrade_chain_round_trip.py` | 0 | 13 passed |
| m2 | the thirteen `tests/integration/db` files whose downgrade passes through `0022_findings_v2` (`test_accounts_migration`, `test_app_user_migration`, `test_downgrade_never_loses_a_measurement`, `test_durable_analysis_effects`, `test_execution_queue_migration`, `test_execution_workers_migration`, `test_norm_citations_migration`, `test_norm_embeddings_migration`, `test_norms_search_migration`, `test_portal_bundles_migration`, `test_release_notes_migration`, `test_reviewer_display_name`, `test_run_terminal_detail_schema`) | 0 | 173 passed |
| m3 | the rest of `grep -rl 0022_findings_v2 tests` on the integration side: `analysis/test_ungrounded_reason_vocabulary.py`, `recovery/test_{blob_object_binding,copy_record_binding,offline_restore_audit,offline_restore_preflight}.py` | 0 | 57 passed |
| m4 | `db/test_norms_corpus_migration.py` | 0 | 20 passed |
| m5 | `api/test_query_surface.py`, `p02_journey/test_query_surface_over_the_corpus.py` | 0 | 46 passed |
| m6 | the files `grep -rln DecisionAdapter tests` names: `api/test_decision_authorship`, `test_decision_journal`, `test_listing_surface`, `test_absent_and_empty_are_not_the_same_answer`, `composition/test_every_port_implementation_is_whole`, `composition/test_router_answers`, `p02_journey/test_truncated_end_to_end` | **1** | **1 failed**, 106 passed, 1 skipped (673 s): `test_every_wired_implementation_carries_the_whole_port[documents]` |
| m7 | `contract/shared_kernel/test_error_kernel.py`, `contract/fixtures_seeded/test_ar_v2_seeded.py`, `integration/evaluation/`, `db/test_routing_refusal_codes_migration.py`, `runs/test_the_interruption_vocabulary_is_pinned.py` | 0 | 124 passed, 32 subtests |
| m8 | `W55B_QA_API_PORT=28500`, `tests/integration/qa_w55b` | **1** | **1 failed**, 66 passed (376 s): `test_p3_input_budget.py::test_a_document_exactly_at_the_budget_starts_and_one_character_less_refuses`, `ConnectionRefusedError` |
| m9 | the same, no override | **1** | **1 failed**, 66 passed (376 s): `test_p3_input_budget.py::test_at_a_low_ceiling_a_start_and_a_reaudit_over_the_budget_are_refused_with_both_figures`, `ConnectionRefusedError` |
| m10 | `jobs/test_d141_final_transaction_keeps_the_lease.py` | 0 | 1 passed (6.9 s) |
| m19 | `tests/characterization` (`D-181`) | 0 | 69 passed |

A survey of the integration files changed since the last gate-fix merge (`049f2fcb`), because
`R-126` meant their lanes never ran them (every command as above):

| id | paths | rc | counts |
|---|---|---|---|
| s1 | 17 files of `access`, `analysis`, `api` (incl. `qa_w49`), `auth`, `dashboard`, `documents`, `findings` | 0 | 237 passed |
| s2 | 21 files of `ingest`, `jobs`, `norms`, `optimisation`, `qa_w52`, `releases`, `runs`, `sections` | 0 | 254 passed |
| s3 | `tests/integration/recovery` | 0 | 308 passed |
| s4 | `tests/integration/p02_journey` | **1** | **1 failed**, 59 passed (285 s): `test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete` |
| s5 | `tests/integration/optimisation` | 0 | 102 passed |
| s6 | `db/test_{classification_corrections_migration,migration_lifecycle,schema_invariant_inventory,schema_shape,routing_refusal_codes_migration}.py` | 0 | 37 passed |
| s7 | `tests/unit tests/replay` | 0 | 912 passed |
| s8 | `tests/integration/composition` without `test_every_port_implementation_is_whole.py` and `test_router_answers.py` (both in m6) | 0 | 920 passed, 2 skipped (503 s) |

## The reds

### 1. `documents` stand-in (`a87a704a`)

`D-74`'s guard parses every `build_router(...)` in `src/` and `tests/`, resolves the class behind
each port argument and requires it to carry the whole protocol, **except** a class with
`__getattr__` (a stand-in that answers every attribute cannot be caught out by a missing method).
`tests/integration/api/test_upload_door_revocation_is_wired.py` (`d4000aca`, `D-176`) wires
`documents=_Documents()`, a class with `upload_document` only. Failure, verbatim:
`tests/integration/api/test_upload_door_revocation_is_wired.py:194 _Documents lacks
['get_version', 'list_documents', 'list_versions', 'read_content', 'stream_content',
'upload_document_version']`. **Class: stand-in too narrow for a guard that has a defined form
for it.** The guard is not touched. `_Documents.__getattr__` raises `AssertionError("the D-176
wiring test does not drive DocumentPort.<name>")`, the form `test_listing_surface._Unused` and many
other stand-ins use; a request that reached another operation now fails loudly where it
was an `AttributeError` behind a `500`.

### 2. `P02_TABLES` (`3bd13e26`)

`assert_table_list_is_complete` read the live schema and found
`['document_version_classification_correction']`, created by `0028_classification_corrections`
(`CLASSIFICATION-CORRECTION-01`, which also made `0028`'s two views, not base tables and so not
listed). **Class: stale pin**, the same one `GATE-FIX-P02-01` repaired for `0022`..`0027`. The
table is added with a comment: a journey writes no correction, so its count is expected unchanged
across a replay. The completeness guard is the guard, unchanged.

### 3. `D-189` (`83a47650`): two causes, and the second one was not on the register

The register names the ephemeral range and the `connect_ex` probe. Both are real and both are
repaired. **Neither is what failed the runs above**: with the override `28500`, outside the range,
`test_p3_input_budget` still failed (m8). That file restarts the served child at each cost
ceiling, and its failures are `ConnectionRefusedError` on the first call after `ensure()`.

* **Readiness was the health plane's.** `infra/deploy/serve.py` starts the health plane on a
  thread and the API in the main thread, so `/readyz` answers before the API port is bound. The
  harness polls `/readyz` every 0.5 s and declared the child ready at the first 200. Measured by
  polling both ports every 2 ms over 12 starts of the real `serve.py` (`gr-order-probe.py`): the
  API accepted 19 to 26 ms after the health plane in 12 of 12. A poll that landed in that window
  sent the first call to a closed port. Measured on the harness itself (`gr-race-rate.py`: start,
  call at once, stop, 60 times, ports 28500/28501): **old harness 8 of 60 first calls refused,
  repaired harness 0 of 60**. `ensure()` now also requires an HTTP answer (any status) from the
  API port. An HTTP answer rather than a connect, because a connection that connected to itself
  accepts and then answers with the request line it sent.
* **The ephemeral range.** The default pair was 57500/57501 inside `ip_local_port_range`
  32768-60999, where a connect to an unused port can connect to itself (a simultaneous open,
  built deterministically by the new test) and the child then cannot bind. The default is now
  `DEFAULT_API_PORT = 28500` (health 28501).
* **The probe.** `_port_is_free` connected; a connect sees only that nothing *listens*. It now
  binds, with `SO_REUSEADDR` because `uvicorn` sets it (a `TIME_WAIT` leftover of the previous
  child, which this harness stops and replaces at each ceiling, is free to the server; a stricter
  probe would refuse a start the server can make).

`tests/integration/qa_w55b/test_harness_ports.py` (11 tests) pins each, and each asserts its
premise (`connect_ex` calls a held silent port free; a socket bound to P connects to P; a
`TIME_WAIT` leftover is there and a plain bind refuses it).

### 4. `D-190` (`3522ada6`)

The lease is stamped on PostgreSQL's clock (`statement_timestamp()` in `jobs/repository.py`), so
there is **no clock to drive**; the knobs are `JobRepository.lease_seconds` and
`jobs.lease.HEARTBEAT_SECONDS` and they are the whole margin. The tolerance of a heartbeat stall
was `2.0 - 0.25 = 1.75 s`. Now `LEASE_SECONDS = 8.0`, `GATE_SECONDS = 12.0`, heartbeat unchanged:
tolerance 7.75 s, and the gate still runs 4 s past the lease so a heartbeat that never ran is seen
by the reclaimer before the gate ends. The file takes 15 s instead of 7. A second test pins the
numbers (tolerance at least three times the observed stall, gate at least 2 s past the lease).
Classified environmental, not flaky-by-rate: it passes on every rerun (m10) and reproduces only
under an injected stall (below).

## Measured after (the repaired tree, nothing edited while a run measured it)

| id | paths | rc | counts |
|---|---|---|---|
| m12 | `api/test_upload_door_revocation_is_wired.py`, `composition/test_every_port_implementation_is_whole.py` | 0 | 34 passed (482 s); the first file alone before the edit (m11, by `git stash`): 5 passed |
| m13/m14 | `qa_w55b/test_harness_ports.py` | 1, then 0 | the first run: 10 passed, 1 failed (my own helper held a port that still had a `TIME_WAIT` leftover; `_free_pair` now demands a strictly free pair); the second: 11 passed |
| m15 | `W55B_QA_API_PORT=28500`, `tests/integration/qa_w55b` | 0 | **78 passed** (406 s) |
| m16 | the same, no override | 0 | **78 passed** (422 s) |
| m17 | `28500` held by a listener of mine, one real qa test | 1 | `Failed: port 28500 is already in use`, in 0.4 s, no child started |
| m18 | `jobs/test_d141_final_transaction_keeps_the_lease.py` | 0 | 2 passed (14.9 s) |
| loop | the same file, 20 sequential runs, six CPU burners started and killed by PID (load average 3.9 rising to 9.5 on 8 CPUs) | 20 of 20 rc 0 | 2 passed each, 15.0 to 17.4 s |
| m20 | `p02_journey/test_whole_journey_idempotency.py` | 0 | 2 passed |
| m21 | `tests/integration/p02_journey` | 0 | 60 passed (282 s) |

## Mutation probes

The copy is `make mutation-copy MUT=/root/gate-repair-01-mut`; before any mutation a whereami test
printed `QA_SUPPORT_FILE /root/gate-repair-01-mut/tests/integration/qa_w55b/qa_support.py` and, for
`D-190`, `LEASE_FILE /root/gate-repair-01-mut/src/auditmanager/jobs/lease.py` and
`EXECUTOR_FILE .../runs/executor.py`; the unmutated copy was green first (11 passed; 2 passed).
`PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared between cases.

`D-189`, `tests/integration/qa_w55b/test_harness_ports.py` against a mutated `qa_support.py`:

| mutation | result |
|---|---|
| M1 `_port_is_free` back to `connect_ex(...) != 0` | 3 failed: `test_a_port_held_without_listening_is_not_free`, `test_a_port_that_connected_to_itself_is_not_free`, `test_the_harness_refuses_to_start_on_a_port_something_holds` |
| M2 the probe binds without `SO_REUSEADDR` | 1 failed: `test_the_leftover_of_a_stopped_child_does_not_make_the_port_busy` |
| M3 `if ready and _api_answers():` -> `if ready:` (health-only readiness) | 1 failed: `test_the_child_is_ready_only_when_the_api_port_answers` |
| M4 `_api_answers` a bare `create_connection` | 1 failed: `test_the_api_probe_wants_an_http_answer_and_not_a_connection` |
| M5 `DEFAULT_API_PORT = 57500` | 1 failed: `test_the_default_port_pair_is_below_the_ephemeral_range` |
| restored | 11 passed |

The occupying-the-port mutation of the register row is M1's third test and m17 (a real listener
on 28500 and a real qa test).

`D-190`, `jobs/test_d141_final_transaction_keeps_the_lease.py` against a mutated copy:

| mutation | result |
|---|---|
| A: the `session.commit()` after the text artifacts' binding (the `D-141` repair) replaced by `pass`, new parameters | 1 failed in 14.8 s: the proof still bites at 8 s / 12 s |
| B0: heartbeat thread stall injected in `lease.py` (`D190_STALL`), stall 0, new parameters | 1 passed |
| B1: stall 5 s, new parameters (tolerance 7.75 s) | 1 passed |
| B3: stall 9 s, new parameters | 1 failed: the tolerance is finite and measured |
| B0old: stall 0, the old 2 s / 4 s | 1 passed |
| B2: stall 5 s, the old 2 s / 4 s | 1 failed in 5.4 s: the old margin could not take a 5 s stall |
| D: the margin test under the old numbers | 1 failed: `test_the_margin_outlasts_the_stall_that_failed_the_battery_and_the_gate_outlasts_the_lease` |

The `_Documents` stand-in: before the edit the guard failed (m6, quoted above), after it passes
(m12); `_Documents().list_documents`, `.get_version`, `.read_content` each raise the
`AssertionError` above and `upload_document` still answers (`DomainError`, `calls = 1`).
`P02_TABLES`: the completeness guard is the existing one, and s4 is its failure on the base (the
list without the new entry); a name in the list that is not a table would fail `table_counts` with
`UndefinedTable`.

## Commands that close the task

| command | rc | result |
|---|---|---|
| `git diff --check` | 0 | clean |
| `pytest tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | 0 | 983 passed, 19283 subtests passed, measured on the clean committed tree of the report's own commit (a dirty tree makes `test_alpha_acceptance_command` fail by design: an earlier run with this report uncommitted was 982 passed and that one refusal) |

## Not exercised, and what to watch

* No complete `make gate`, no whole `tests/integration` directory (`R-135`, this host). The
  integration files not named above were not run; those unchanged since `049f2fcb` are taken as
  green on the strength of `GATE-FIX-DB-01` and `GATE-FIX-API-01`, not measured here. `tests/e2e` and the live journey were not run (forbidden hotspots, no stand).
* `test_cp00_candidate.py` pins a stage-registry hash that is stale; the complete gate ignores the
  file (Makefile lines 541-543), so it was left alone, as the brief said.
* `D-189`: `serve.py`'s `/readyz` answers about 25 ms before its API socket is bound. That is
  `infra/deploy/serve.py` and was not touched; the harness now waits for both planes. A deployment
  probe that sends traffic on `/readyz` alone has the same 25 ms window (a reverse proxy retries
  it); worth a line in whatever owns that file.
* `D-190`: the loop used six CPU burners, not memory pressure. The stall that failed the battery
  was most likely the swap pressure of the host (10 GB of swap in use during this task); the
  injected stalls (heartbeat thread only) are a proxy, not the same event.
* The 8 of 60 / 0 of 60 figures are one sample each on a loaded host (load 1.5 to 3); they are
  evidence of the mechanism and of the repair, not a rate.
* The first `make up` was started from a command of mine that also redirected its output to a path
  outside the worktree (`/root/projects/tmp_unused`); the file was removed at once and nothing else
  was written outside the worktree and the session scratchpad.

## Integrator notes

* Merge as a real merge into `integration/night-1020`; every group is a commit. Nothing outside the
  allowed paths changed (`git diff --name-only 54ec23eb..HEAD` below).
* `D-187`'s row can be closed as stale: all its named reds were green on the base (`m1`..`m7`),
  and the two unnamed ones found here are repaired. `D-189` and `D-190` are repaired as specified
  (`m15`/`m16`, the 20-run loop).
* The new `qa_w55b` default pair 28500/28501 is outside the kernel's ephemeral range but another
  lane may use it; set `W55B_QA_API_PORT` per lane as before.

## Changed files

- `docs/program/GATE-REPAIR-01.md`
- `tests/integration/api/test_upload_door_revocation_is_wired.py`
- `tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py`
- `tests/integration/p02_journey/journey.py`
- `tests/integration/qa_w55b/qa_support.py`
- `tests/integration/qa_w55b/test_harness_ports.py`

Nothing under `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, `tests/support/**`, `tests/conftest.py`, `tests/e2e/**`, `web/**`, `docs/program/CURRENT_STATE.md` or `docs/program/DEBT_REGISTER.md`; no ref, tag or stand touched. `git diff --name-only 54ec23eb..HEAD` is exactly the list above.
