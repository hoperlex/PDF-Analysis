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
