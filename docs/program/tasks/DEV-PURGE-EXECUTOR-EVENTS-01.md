# Task DEV-PURGE-EXECUTOR-EVENTS-01 — the product purge keeps the executor audit events its documents say to keep

task_id: DEV-PURGE-EXECUTOR-EVENTS-01
status: completed in development candidate

## Outcome

`scripts/recovery/product_purge.py` builds the `audit_event` keep and delete predicates from `KEEP_EVENT_PREFIXES` (`norm_custody.` and `executor.`), so the apply step no longer deletes `executor.*` events. After a purge the executor tables, their command receipts and the append-only trail of who set a secret or a route, and when, are all still there; the `keep-unchanged` and `product-emptied` guards measure the same set the tool keeps. Before this task `DELETE FROM audit_event WHERE NOT starts_with(event_type, 'norm_custody.')` removed every `executor.*` event and no guard could notice, because the guards use the same predicate.

## Depends on

- `STAND-PURGE-TOOL-01` — completed purge tool whose predicates this task corrects.
- `EXEC-SEAL-01` — completed; declared `executor.` events KEEP (`docs/program/EXEC-SEAL-01.md`, changed-files table) and wrote `executor.connection_created`, `executor.secret_set` and the other `executor.*` events.
- `EXEC-HTTP-01` — completed; restates it (`docs/program/EXEC-HTTP-01.md`, "Both fall under the existing product-purge prefixes (`audit_run.` PRODUCT, `executor.` KEEP)").
- `DEV-PURGE-INVENTORY-01` — completed; the tool at the base already classifies migration `0032`.

## Frozen inputs

- base: `integration/ar-close-1026` tip `37da1176e7ee4ed56577f1631e33a25ece5527c2`.
- migration head `0032_ar_v3_run_group`, unchanged; contract family/API unchanged; product `0.8.1`.
- the tool's guard markers (26 blocks), exit codes (`0` done, `2` usage, `3` refused, `4` failed), lock order, table classification (`PRODUCT_TABLES`, `KEEP_TABLES`, `MIXED_TABLES`) and command-type classification are unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `KEEP_EVENT_PREFIXES` names `executor.` but the SQL predicates of `audit_event` name `norm_custody.` only, so the apply step deletes the executor events

### P-01 — the predicates at the base, no database needed

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python <script> <base copy of product_purge.py>` where the script imports the module by path with `importlib.util.spec_from_file_location`, then prints `tool.KEEP_EVENT_PREFIXES` and `tool._predicates([])['audit_event']`; the base copy is `git show 37da1176:scripts/recovery/product_purge.py`
- captured_output:
  ```text
  KEEP_EVENT_PREFIXES = ('norm_custody.', 'executor.')
  keep   : starts_with(t.event_type, 'norm_custody.')
  delete : NOT starts_with(t.event_type, 'norm_custody.')
  ```
- interpretation: the tuple and the SQL disagree. The delete predicate is the one the apply step runs (`DELETE FROM public.audit_event AS t WHERE {predicates['audit_event'][1]}`), so an `executor.*` row is in the delete set. The same pair feeds the plan counts, the plan digest, `keep_fingerprints` and the `keep-unchanged` / `product-emptied` guards, which is why none of them can see it.

### P-02 — where the base builds the predicates

- captured_at: 2026-10-26
- command: `rg -n "norm_custody\.|KEEP_EVENT_PREFIXES|_EVENT_KEEP" <base copy of product_purge.py>`
- captured_output:
  ```text
  26:* ``audit_event``: ``norm_custody.*`` events are the custody ledger's history and stay; the run,
  124:#: ``audit_event.event_type`` families. ``norm_custody.`` is the custody ledger's.
  125:KEEP_EVENT_PREFIXES = ("norm_custody.", "executor.")
  374:    unknown = sorted(e for e in events if not e.startswith(KEEP_EVENT_PREFIXES + PRODUCT_EVENT_PREFIXES))
  394:_EVENT_KEEP = "starts_with(t.event_type, 'norm_custody.')"
  427:        "audit_event": (_EVENT_KEEP, f"NOT {_EVENT_KEEP}"),
  ```
- interpretation: one place builds both predicates (`_EVENT_KEEP`, line 394, used by `_predicates`, line 427); the apply step (line 879) and the fingerprints only consume them. Line 374 (the `event-types-classified` guard) already uses the tuple, so an `executor.*` event is "classified" and passes the refusal, then is deleted. No other site in `scripts/recovery` names `norm_custody.` as an event family.

### P-03 — no test seeded an executor event at the base

- captured_at: 2026-10-26
- command: `rg -n "executor\." tests/integration/recovery/test_product_purge.py tests/integration/recovery/purge_seed.py`
- captured_output:
  ```text
  tests/integration/recovery/test_product_purge.py:593:    assert "executor." in tool.KEEP_EVENT_PREFIXES
  tests/integration/recovery/test_product_purge.py:594:    assert not any("executor." .startswith(prefix) for prefix in tool.PRODUCT_EVENT_PREFIXES)
  ```
- interpretation: the only assertion about the family is that the prefix is in the tuple; `purge_seed.py` writes `norm_custody.*` events only. Nothing could fail on the delete.

### P-04 — the base tool deletes the executor event (red proof of the new test)

- captured_at: 2026-10-26
- command: `git show 37da1176:scripts/recovery/product_purge.py > scripts/recovery/product_purge.py` then `pytest tests/integration/recovery/test_product_purge_executor_events.py` on the existing integration stack; the file was restored with `git checkout -- scripts/recovery/product_purge.py`
- captured_output:
  ```text
  E       assert "starts_with(t.event_type, 'executor.')" in "starts_with(t.event_type, 'norm_custody.')"
  E       AssertionError: assert '  audit_event  (delete 25 rows, keep 5 rows)' in 'purge-product-data: database purge_clone_... [the base tool prints 'audit_event  (delete 26 rows, keep 4 rows)': the executor event counted as a row to delete]
  E       AssertionError: the executor.secret_set event was deleted by the purge
  FAILED tests/integration/recovery/test_product_purge_executor_events.py::test_the_audit_event_predicates_are_built_from_every_keep_prefix
  FAILED tests/integration/recovery/test_product_purge_executor_events.py::test_a_dry_run_counts_the_executor_event_as_a_row_that_stays
  FAILED tests/integration/recovery/test_product_purge_executor_events.py::test_the_purge_keeps_the_executor_and_custody_events_and_deletes_the_run_event
  3 failed in 5.92s
  ```
- interpretation: on the unfixed tool the real `apply` and `delete-objects` exit `0` (the steps assertion before the survival assertion passes) and the `executor.secret_set` event is gone: the premise is a real data loss, not a documentation drift.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/product_purge.py`
- `tests/integration/recovery/test_product_purge.py`
- `tests/integration/recovery/test_product_purge_executor_events.py`
- `docs/program/tasks/DEV-PURGE-EXECUTOR-EVENTS-01.md`
- `docs/program/DEV-PURGE-EXECUTOR-EVENTS-01.md`

## Forbidden hotspots

`contracts/**`, `db/**`, `infra/**` (including the shell entry point `infra/deploy/purge-product-data.sh`), `Makefile`, other `scripts/**` (including `schema_coverage.py`), `src/**`, `web/**`, the composition root, global styles, root dependency and lock files, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `origin/main`, tags and the deployment host.

## Non-goals

No change to which tables or command types are classified, to any refusal, lock, ordering or guard text, to an exit code or to the shell wrapper; no new migration; no change to what the executor commands write. `RUNNING_STATES` is not changed (see the report: a claimed standalone probe task is not covered; proposed as a register note). No purge against a real stand and no `make gate` (`R-135`).

## Deliverables

- `_event_keep()` in `product_purge.py`: `(starts_with(t.event_type, 'norm_custody.') OR starts_with(t.event_type, 'executor.'))`, built from `KEEP_EVENT_PREFIXES` at call time; the delete predicate is `NOT` of it; `keep_fingerprints`, the plan counts and the plan digest read the same pair. The module docstring and the comment above the tuple say so.
- New `tests/integration/recovery/test_product_purge_executor_events.py` (3 tests): a no-database test that every prefix of the tuple is in the keep predicate, the delete predicate is its exact negation and a prefix added to the tuple alone reaches both; a dry run on a real database that counts the executor event as a row that stays; a real plan, snapshot, apply and delete with one `executor.secret_set` (written by the product's journal writer with the payload `set_secret` writes), one `norm_custody.bound` and one `audit_run.created`, asserting the executor and custody events survive, the run event is gone, and the keep fingerprint of `audit_event` is equal before and after (the tool's `keep_fingerprints` and the test's own digest).
- `test_product_purge.py`: the existing declaration test also asserts the keep predicate contains `executor.` (one line) and points to the new module.
- Report `docs/program/DEV-PURGE-EXECUTOR-EVENTS-01.md` with the before and after of `tests/integration/recovery`, the quoted mutations and the `RUNNING_STATES` observation.

## Verification

- `tests/integration/recovery/test_product_purge_executor_events.py` on the existing integration stack: `3 passed`; the same file on the base tool: `3 failed` (P-04).
- `tests/integration/recovery` whole directory (the regression net for this tool): expected `0 failed`.
- every new test shown red under one quoted mutation (report).
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/DEV-PURGE-EXECUTOR-EVENTS-01.md',encoding='utf-8').read())))"` prints `[]`.
- `git diff --check` and the exact allowed-path inventory. No full gate (`R-135`).

## Integration contract

Merge before any stand step that runs `product_purge` (the activation runbook's purge step) on a stand that has configured an executor connection. The change touches no shared contract, migration, fixture module or composition root. The next event family that must survive a purge is added to `KEEP_EVENT_PREFIXES` alone; `test_the_audit_event_predicates_are_built_from_every_keep_prefix` fails by name if the SQL stops following the tuple.

## Failure/idempotency/security cases

An event type nobody classified still stops the tool before it touches anything (`event-types-classified`). If the keep and delete predicates ever disagree again, the `keep-unchanged` guard refuses and rolls back (shown in the report: mutation M2). A second run after the purge reports `nothing-to-purge: yes` and counts the executor events as rows that stay. The purge never uses CASCADE.

## Rollback / feature flag

Forward-revert of the commits. Reverting restores the deletion of `executor.*` audit events by a purge, which loses the trail of who set a secret or a route and when (only a dump restores it); revert only with that in view.

## Handoff

- changed files: `scripts/recovery/product_purge.py`, `tests/integration/recovery/test_product_purge_executor_events.py` (new), `tests/integration/recovery/test_product_purge.py`, task and report.
- commands/results: see the report; the new module goes from 3 failed (base tool) to 3 passed, the recovery directory stays at 0 failed.
- known limits: no purge was run against a real stand; `RUNNING_STATES` does not include `executor_task` (report).
- integration notes: none beyond merge order; a `DEBT_REGISTER.md` note is proposed in the report.
