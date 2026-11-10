# HOSTS-CMP-01 — the comparison of versions on the stage layout (with HOSTS-SEAL-3)

- task_id: `HOSTS-CMP-01` (contract part `HOSTS-SEAL-3`, contract 1.47.0)
- owner: one Sonnet lane; integrator: the HOSTS integrator (`integration/combined-1`)
- base: `integration/combined-1` at the dispatch SHA named in the brief
- depends_on: `HOSTS-SEAL-1`, `HOSTS-SEAL-2`, `HOSTS-LAYOUT-01`, `HOSTS-BACKEND-01`, `HOSTS-ENSEMBLE-01` (all merged)
- closes: `D-541`
- facts: `.local/reports/hosts-cmp-facts-2026-11-10.md` (read-only census of 2026-11-10, `path:line` for every claim)

## Outcome

With the stage layout switched on, the four comparison kinds that call a model are served by the same system groups as the
analysis. Those kinds are `comparison_pair_check`, `comparison_sheet_changes`, `comparison_spec` and `comparison_report`.
Each kind gets one layout cell `<kind>:main` with model, effort, answer-token limit and timeout, as the original has per stage.
A comparison job freezes its cell at start. Its consent names the system group revision, as `EXEC2-GROUP-CMP-01` does for a rule.
With the switch off, comparisons are routed exactly as today: legacy or rules.

## Decisions (owner away; taken by the integrator, 2026-11-10)

1. **Kinds in scope.** `comparison_stage_review` stays out. It is an enum value with no handler and no call site (`CMP-SEAL-C4`).
2. **Contract shape (1.47.0).**
   - The analysis rows (`StageRowKey`, `StageLayoutCell`) are unchanged, so no existing reader changes.
   - The layout revision gains a separate optional list, `comparison_cells`. Each item is a `StageComparisonCell` with:
     - `work_kind`, one of the four kinds above (a new enum `ComparisonLayoutKind`);
     - `model_id`, `effort`, `max_output_tokens` (1..65536) and `timeout_seconds` (1..7200).
   - `ReviseStageModelLayoutRequest` accepts the list, and the views return it.
   - A kit fills it, and «Свой набор» may edit it.
   - An absent list on an old revision means "the kit's defaults".
3. **Storage.** The cells are stored in the revision's existing `cells` jsonb with the row equal to the kind. The cell-key pattern of `0062` already admits this, and no DB CHECK lists the rows.
   - A run's frozen `stage_plan` never contains them: `restricted_to` / `rows_in_use` keep the six analysis rows.
   - If the lane finds a reason for a column, migration `0063` is the integrator's slot and the lane may take it. The reason is then recorded.
4. **Routing.**
   - With the layout on and the provider source `database`, `comparison/ai_jobs/estimate.read_route` gets a third branch:
     1. take the kind's cell;
     2. choose its access as the stage-plan freezer does (subscription before api among the available members);
     3. resolve the system group `pair_group_name(model, access)`;
     4. return `route_of_group_revision(...)`.
   - The job freezes the group revision (`executor_group_revision_id`), so the existing group dispatch and the comparison spend mirror
     (pool lock) serve it unchanged.
   - A kind whose model has no available member is refused at start with the existing typed answer for an unavailable route. It is
     never routed somewhere else silently.
5. **Settings reach the call.**
   - The cell's effort replaces the module constants: `ai_pairs/prompt.py` `EFFORT`, the literal `"high"` in `ai_sheets/describe.py`
     and `report/plan.py`, and none today for spec.
   - Its `max_output_tokens` caps the module limits: `ai_pairs` 1200, `ai_sheets` 8192, `spec` 32000, `report` `MAX_TOKENS` per role.
     The cell value is a ceiling: `min(module limit, cell)`. For report, the cell caps each role's limit.
   - Its `timeout_seconds` is the host task window of the call.
   - A job admitted by legacy or rules keeps today's values exactly.
6. **Kit defaults.** They follow the original (`PDF-proverka` `version_comparison_ai`), mapped onto the catalogue.
   - The original's `gpt-6-luna` is not in the catalogue. Pinning a model is the owner's (`R-143g`), so it is mapped to `gpt-6-astra` and `D-667` records it.

   | kind | «Только Codex» | «Только Claude» | answer tokens | timeout |
   |---|---|---|---|---|
   | `comparison_pair_check` (original `sheet_match`: luna, high, 900 s) | `gpt-6-astra` high | `claude-sonnet-5-5` high | 1200 | 900 |
   | `comparison_sheet_changes` (original `VC_SC`: 6.1-sol, high, 1800 s) | `gpt-6.1-sol` high | `claude-sonnet-5-5` high | 8192 | 1800 |
   | `comparison_spec` (original whole-spec: luna, high, 900 s) | `gpt-6-astra` high | `claude-sonnet-5-5` high | 32000 | 900 |
   | `comparison_report` (original `VC_MR`: 6.1-sol, high, 2400 s) | `gpt-6.1-sol` high | `claude-sonnet-5-5` high | 8000 | 2400 |

## Allowed paths

- `contracts/api/v1/openapi.json`, `contracts/api/v1/README.md` (the 1.47.0 delta), `contracts/api/v1/CHANGELOG*` if present, and the
  contract census pins the version moves (`tests/contract/**`)
- `web/src/shared/api/generated/**`, regenerated only with the repository's generator; no other `web/**`
- `src/auditmanager/runs/stage_layout.py`, `runs/stage_layout_store.py`, `analysis/text/cell_settings.py`, `bootstrap/stage_plan_service.py`,
  `bootstrap/stage_plan_adapter.py`
- `src/auditmanager/comparison/**`
- `src/auditmanager/executors/public.py`: exports only
- `src/auditmanager/api/schemas/models.py`: the generated models of the new schemas
- tests under `tests/unit/**`, `tests/integration/comparison/**`, `tests/integration/runs/**`, `tests/contract/**`
- `docs/program/tasks/HOSTS-CMP-01.md` (this file, its report section)

## Forbidden hotspots

- `bootstrap/adapters.py`, `composition.py`, `providers.py`, `api/routers/ports.py`, `api/security.py`, `bootstrap/runner.py` and `executors/runner.py`,
  all held by `HOSTS-INT-WIRE-01`. The lane reports any wiring it needs there.
- `web/**` except the generated client
- `jobs/**`, `db/migrations/**` (unless decision 3 says otherwise), `VERSION`, `release-notes/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`

## Checks

- unit: `tests/unit/runs tests/unit/comparison tests/unit/executors tests/unit/bootstrap` and `tests/contract/api_v1`
- database, on a throwaway Postgres (tmpfs, own container name, started and stopped in one locked script):
  - `tests/integration/comparison` (the whole package; it pins legacy and rules routing, which must stay green);
  - one new end-to-end test: layout on, a host with a member of the kind's model, a comparison job started on the layout, its
    consent naming the system group revision, the call carrying the cell's effort and limit;
  - with the switch off, the same job routed as before.
- break-it-once: the end-to-end test fails when the third branch of `read_route` is removed.
- `web`: `npx tsc --noEmit` after regeneration. It must stay green, because the analysis rows are unchanged.

## Integration

The integrator merges after `HOSTS-INT-WIRE-01`. A web lane then adds the four comparison rows to «Модели по этапам»: one small
group «Сравнение версий», shown under «Свой набор» only, because a kit fills them.

## Rollback

The layout switch off returns every comparison to legacy or rules routing. Jobs already admitted finish on their frozen group revision
(`ADR-0026` decision 17).

## Report (lane HOSTS-CMP-01, 2026-11-10)

Base `54ba71bab`; merged `a4e040c4e` (`HOSTS-INT-WIRE-01`) at the integrator's word. No migration, no new column: the cells are stored in the revision's
`cells` array with the row equal to the kind (decision 3 needed no column; migration `0063` is not taken).

### What was built

- **Layout** (`runs/stage_layout.py`, `stage_layout_store.py`, `bootstrap/stage_plan_service.py`): `COMPARISON_KINDS` (the four), the two sets' tables of
  decision 6, `validate_comparison_cells` / `require_valid_comparison_cells` (catalogue pairs, limits, each kind once, a named kit keeps its table's models
  and efforts), `LayoutRevisionRow.comparison_cells` and `.comparison_cells_in_force` (stored list, else the kit's table, else none for `custom`). A run's plan
  never holds a kind: `LayoutRevisionRow.cells` stays the six rows.
- **Route** (`comparison/ai_jobs/layout_route.py`, third branch of `estimate.read_route`): the kind's cell, a subscription before an API key
  (`executors.public.evaluate_wait`; a member whose pool is full still counts), the system group's current revision, `route_of_group_revision(..., cell=)`.
  A kind whose model no server serves, a layout on under a source other than `database`, and a revision with no cell for the kind are all
  `503 dependency_unavailable` / `executor_route_missing`: the legacy connection and the rule are not read.
- **Frozen cell**: `AiRoute.cell` is in the route document, so the **estimate digest binds it** and the job stores it with its estimate
  (`AiJobRecord.cell`, no column). A resume, a retry or a finish re-estimates on the job's own cell (`read_job_route`). `Consent.cell` carries it to the wrapper.
- **Settings reach the call** (`comparison/spend/cell.py`, applied once in `ComparisonModelCaller.call`): the cell's effort replaces the request's, its limit is
  `min(module limit, cell limit)` in the body and in the priced estimate, the request is hashed and journalled as it goes out. `build_estimate` counts the answer at the same cap.
- **Dispatch**: a system member has no probe and no runner token of its own, so the generic `member_facts` finds no eligible member of a server's group.
  `comparison/spend/dispatch.member_facts_of` reads such a member by its server's facts (`member_reasons`, the server's slots of the provider).
- **Contract 1.47.0**: see the delta below.

### Decisions beyond this file

1. **One chokepoint instead of four builders.** The effort and the limit are applied in the spend wrapper from the consent's cell, not by editing `EFFORT`, the
   literal `"high"` of `describe.py` / `plan.py` and the limits of the four modules: no handler can forget the cell, a job with no cell is byte-identical, and the journal
   hashes the request that went out. The module constants stay as the legacy values.
2. **The cell lives in the estimate's route** (`ComparisonAiRoute.cell`), not in a column: the digest then binds what will run, and the stored job needs no migration.
3. **`custom` without comparison cells has none** and a comparison is refused; a revision made before this seal under a named kit follows the kit's table.
4. **Content keys are unchanged**: a stored answer is found by the model and the prompt, as before, not by the effort or the cell's limit (see the debts).
5. **The version sweep** (the pins of SEAL-2 moved to 1.47.0) touched files outside the allowed list because the contract census pins them: `contracts/{analysis,domain,events}`,
   `infra/deploy/proxy/*.conf`, `src/.../routers/__init__.py`, `analysis/engine/result.py`, `web/FRONTEND_LOCK.json`, `web/openapi`, `web/src/shared/api/credentialed-forward.ts` and the
   version fixtures of `web/tests/**`. Exports only were added to `runs/public.py` and `executors/public.py`.
6. `web/tests/unit/start-run/readiness.test.ts` said `1.45.0`: a `tsc` error already at the base (the client said `1.46.0`); moved with the sweep.
7. The prose of `startRun` (`409 conflict_reason` -> `422 analysis_input_invalid`, `details.reason`) is corrected at the integrator's request; no other contract wording of that reason says `409`.

### Contract delta (1.46.0 -> 1.47.0)

296 paths / 324 operations, **796 schemas** (+2). New: `ComparisonLayoutKind` (enum of the four kinds), `StageComparisonCell` (`work_kind`, `model_id`, `effort`,
`max_output_tokens` 1..65536, `timeout_seconds` 1..7200). Widened, all optional: `StageLayoutRevision.comparison_cells`, `ReviseStageModelLayoutRequest.comparison_cells`
(four items, each kind once), `ComparisonAiRoute.cell`. Domain catalogs at candidate revision 64. Generated client regenerated (`api:verify` OK), `FRONTEND_LOCK.json` resealed.

### Wiring the integrator must add (`bootstrap/composition.py`, held by `HOSTS-INT-WIRE-01`)

In `_ComparisonRoutes.route`, the pull adapter of a system member is built without a `HostCall`, so the host agent is not told the cell's effort, limit, window and key
(`payload.host`), and the cell's timeout is not the task's window. After `bound = bind_connection(...)` and before the `PublishedPullAdapter` wrapping:

```python
adapter = bound.adapter
cell = getattr(job, "cell", None)                                  # the cell the job froze
connection = bound.connection
if cell is not None and getattr(connection, "capacity_pool", None) is not None:   # a system member of a server
    from auditmanager.comparison.spend.cell import host_call_of
    from auditmanager.executors.public import access_of_billing, build_pull_adapter, split_pool
    _host, provider = split_pool(connection.capacity_pool)
    adapter = build_pull_adapter(
        session_factory=self._runtime.session_factory, revision=bound.revision, context=context, engine=self._runtime.engine,
        host_call=host_call_of(cell, provider=provider, access=access_of_billing(settings.billing)))
```

### Debts (check commands in the report of the lane)

- The attempt watchdog of a comparison item is 900 s (`comparison/work/model.ATTEMPT_WATCHDOG_SECONDS`): a call's window is `min(cell timeout, watchdog left - 60 s)`, so the
  1800 s of sheet changes and the 2400 s of the report cannot be reached until the watchdog is per kind.
- The module constants (`EFFORT`, the literal `"high"`, the four limits) are still in the modules, and the content keys of stored answers do not carry the effort or the cell's limit.
- The generic `executors.public.member_facts` is not host-aware; `comparison/spend/dispatch.member_facts_of` is the lane's reading until it is.
- The host payload carries the cell's limit as a ceiling (`HostCall.max_output_tokens`); the request body carries `min(module limit, cell limit)`.
- The web rows of the four kinds in «Модели по этапам» («Свой набор» only) are the web lane's.
