# DEBT-EFFECT-GUARDS-0033 — D-148 and D-142 were already closed; no migration written

The lane was dispatched to add `0033_effect_state_guards` for `D-148` (the effect-table state guards fire on UPDATE only) and, if small, `D-142` (no settlement state for an interrupted artifact intent). Both rows in `DEBT_REGISTER.md` are stale. `0018_norm_custody` (`W54-SEAL-01`, `6f4a2dae`) recreated both guards `BEFORE INSERT OR UPDATE` with an INSERT arm that refuses any state but `prepared`, and added `analysis_artifact_publication.abandoned` with `prepared -> abandoned`. `W54-CUSTODY-01` settles it from `JobRepository.settle_terminal_provider_effects`, which `reconcile_at_startup` calls. A `0033` would recreate identical triggers, move the head, and force a re-pin across the status documents, so none was written. The lane added two tests for what the existing suite does not cover, and the closing evidence.

## Measurement (private stack `auditmanager-debt-effects`, PostgreSQL, one database walked 0017 to 0032)

A one-off probe (not committed) inserted terminal rows directly and tried the legal edges. At `0017` the database held the rows below; `alembic upgrade head` then ran over them without error and kept every row.

| statement | at `0017` | at `0032` (head) |
|---|---|---|
| INSERT `provider_call_effect` state `outcome_unknown` | accepted | refused `AM001`, "may not be created in state outcome_unknown" |
| INSERT `provider_call_effect` state `abandoned` | accepted | refused `AM001` |
| INSERT `analysis_artifact_publication` state `bound` | accepted | refused `AM001` |
| INSERT `analysis_artifact_publication` state `abandoned` | no such column (`42703`) | refused `AM001` |
| INSERT either table `prepared` | accepted | accepted |
| `provider_call_effect` prepared to response_received | accepted | accepted |
| publication prepared to abandoned | no such column | accepted |
| publication abandoned to bound | no such column | refused `AM001` |

Trigger text: `BEFORE UPDATE ON` for both tables at `0017`; `BEFORE INSERT OR UPDATE ON` for both at the head. Round trip on a second scratch database with a `prepared` effect, a `prepared` publication and a `bound` publication: `0018 -> 0017` exit 0, guards back to `BEFORE UPDATE`, 1 effect and 2 publications retained; `-> head` exit 0, guards `BEFORE INSERT OR UPDATE`, rows retained as `prepared` and `bound`. That scratch database was dropped.

## Verification

- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/db/test_effect_state_guards_0033.py tests/integration/db/test_durable_analysis_effects.py tests/integration/db/test_norm_custody_migration.py tests/integration/db/test_schema_invariant_inventory.py tests/integration/db/test_downgrade_chain_round_trip.py tests/integration/ingest/test_reconciliation.py tests/integration/ingest/test_reconciliation_custody_blobs.py tests/integration/storage/test_repeated_publication.py` with the lane's `.env` exported: **71 passed**, exit 0 (2 of them new).
- `pytest ... tests/integration/runs/test_durable_effect_boundaries.py -k d142`: **2 passed** (crash, rerun, clean report; a live Attempt's intent stays `prepared`).
- Task governance findings for this task: `[]`. The wider `tests/contract/program` run is 27 passed, 1 failed; the failure is `test_every_task_added_after_governance_activation_satisfies_the_rules` naming other, pre-existing task files (for example `AR-V3-BETA-GROUP-REVIEW-01.md`, `PREMISE_OUTPUT_REQUIRED`), not this one.
- No `db/migrations/**` changed, so AGENTS section 8 case 3 does not apply and the `R-135` deferral of the full gate is not even needed here.

## Mutations (each reverted with `git checkout --`, tree clean afterwards)

New tests, against `db/migrations/versions/20261012_0018_norm_custody.py`:

- M-A, `_effect_triggers("INSERT OR UPDATE")` in `upgrade` changed to `_effect_triggers("UPDATE")`: both new tests red ("2 failed"); the guard-text assertion shows `BEFORE UPDATE ON public.provider_call_effect`.
- M-B, `_effect_triggers("UPDATE")` in `downgrade` changed to `("INSERT OR UPDATE")`: the round-trip test red, the boundary test green ("1 failed, 1 passed").
- M-C, the effect guard's INSERT arm condition `IF NEW.state IS DISTINCT FROM 'prepared' THEN` changed to `IF false THEN`: the boundary test red with `DID NOT RAISE DBAPIError` ("1 failed, 1 passed").

Existing guards, to show they were never vacuous: M-A against `test_a_fresh_upgrade_creates_the_custody_tables_and_guards_inserts` and `test_an_effect_row_inserted_in_a_non_initial_state_is_refused` ("2 failed"); the abandoned arm widened to `OLD.state IN ('prepared', 'bound')` reddens `test_a_bound_publication_is_never_abandoned`; deleting the `settle_terminal_artifact_publications` call in `src/auditmanager/jobs/repository.py` reddens `test_d142_a_crashed_publication_is_settled_and_the_report_is_clean_after_a_rerun` (`('prepared', False) == ('abandoned', True)`).

## Findings and limits

- D-142 design as shipped, for the record: `prepared -> abandoned`, written only by `settle_terminal_artifact_publications` for an intent whose Attempt is in a terminal state (`succeeded`, `failed`, `superseded`, `lost`, `cancelled`) and older than the pass's threshold (`0 seconds` at startup), journalled as `artifact.abandoned`; the trigger forbids `bound -> abandoned` and `abandoned -> bound`, and the blob row is never touched. Settlement is therefore not inferred from time alone and cannot hide a bound object.
- Rows created at `0017` with a terminal state by a direct INSERT survive the upgrade; the guard cannot and should not rewrite them. No production writer ever created one, so this is a note, not a defect.
- `D-143` ("with D-142") is untouched: W54 resolved it as a report plus a refusal (`rejected` stays terminal); its row text is the integrator's to read.
- The lane did not run the full gate, the live journey, or any test outside the list above.

## Proposed register text (the integrator applies it; `DEBT_REGISTER.md` and `CURRENT_STATE.md` were not edited)

Summary table rows:

```text
| ~~D-142~~ | artifact publication intents have no settlement state, so reconciliation never becomes clean after an interrupted publication | **closed in code by `W54-SEAL-01` (`0018_norm_custody`, `6f4a2dae`) and `W54-CUSTODY-01`**, found stale and re-proved 2026-10-26 by `DEBT-EFFECT-GUARDS-0033`: `prepared -> abandoned` once the Attempt is terminal; check `tests/integration/runs/test_durable_effect_boundaries.py -k d142` and `tests/integration/db/test_norm_custody_migration.py -k abandoned` |
| ~~D-148~~ | the effect tables' state triggers guard UPDATE only | **closed in code by `W54-SEAL-01` (`0018_norm_custody`, `6f4a2dae`)**, found stale and re-proved 2026-10-26 by `DEBT-EFFECT-GUARDS-0033`: both guards are `BEFORE INSERT OR UPDATE` and an insert must be `prepared`; check `SELECT tgrelid::regclass, pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname IN ('trg_provider_call_effect_state_guard','trg_analysis_artifact_state_guard')` prints `BEFORE INSERT OR UPDATE` twice, and `tests/integration/db/test_effect_state_guards_0033.py` |
```

Detail sections (`### D-148` and `### D-142`): replace each **Check:** line with the one in its row above, and append one sentence: "Closed 2026-10-26: the opening text describes `0014`/`0017`; `0018_norm_custody` is the closure."
