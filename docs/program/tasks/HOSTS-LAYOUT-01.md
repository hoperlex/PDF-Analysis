# Task HOSTS-LAYOUT-01 — the stage layout, the frozen stage plan and per-cell model binding

## Outcome
An administrator can store, revise and enable a stage layout of six rows; a run started with the layout enabled freezes a `stage_plan` of cells (model, effort, answer limit, timeout, access) and calls each model through `binding_for(cell)` with its own `CallBinding`. The identity check `R-133` is exact per catalogue (`accepted_reported`). Consent v2, the readiness read and the three start commands work from the plan. With the switch off nothing changes.

## Depends on
- HOSTS-SEAL-1

## Frozen inputs
- domain contract: 1.45.0, owned by `HOSTS-SEAL-1`; frozen here
- API contract: 1.45.0 (layout, catalogue and readiness operations; consent v2; the three start commands); frozen here
- analysis/comparison/event contract: 1.45.0, including `contracts/analysis/v1/model-catalogue.json`
- migration head: `0062_hosts_stage_models`; this task adds none
- base commit: `8f76b4ed6daadad95f9c001e2c2c0dca717aad2d`
- the dispatcher replaces the base by the tip carrying `HOSTS-SEAL-1` at dispatch
- architecture: `docs/architecture/adr/ADR-0028-hosts-and-stage-models.md` decisions 5–8, 10–14, 18; the tables of rows, phases and sets in the ADR are the specification; rulings `R-153a`, `R-153e`
- the seam with `HOSTS-BACKEND-01`: the cell binding exists before the first model call and is read from `audit_run_cell_binding`; `stage_key` is passed to `prepare_provider_call`, which `HOSTS-SEAL-1` plumbed; the stub modules `bootstrap/stage_plan_adapter.py` and `bootstrap/stage_plan_providers.py` are filled here
- the pins: seven models in `docs/program/P02_LOCK.json`; the catalogue file is read-only here

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/runs/` (the six rows of the stage layout, one module)
- enumerator_owner: HOSTS-LAYOUT-01
- totality_query: `git grep -n "STAGE_ROWS" -- src`

## Captured premise evidence
- premise: where the model is read from the single binding, and the three exact comparisons

### P-01 — `config.model_id` is read at 32 lines
- captured_at: 2026-11-09
- command: `git grep -c "config\.model_id" -- src`
- captured_output:
  ```text
  src/auditmanager/analysis/text/stage.py:3
  src/auditmanager/analysis/text/windowed.py:4
  src/auditmanager/bootstrap/adapters.py:1
  src/auditmanager/bootstrap/composition.py:1
  src/auditmanager/runs/executor.py:1
  src/auditmanager/runs/extended_review.py:17
  src/auditmanager/runs/preflight.py:1
  src/auditmanager/runs/v3_provider_call.py:4
  ```
- interpretation: every site in `runs/` and `analysis/` is driven by the cell. The two in `bootstrap/` are the integrator's (`adapters.py`, `composition.py:932`).

### P-02 — the exact comparisons of the reported model
- captured_at: 2026-11-09
- command: `git grep -n "response.model != binding.call.expected_model\|model != task.expected_model\|reported != expected" -- src`
- captured_output:
  ```text
  src/auditmanager/analysis/text/stage.py:327:    elif not isinstance(reported, str) or reported != expected:
  src/auditmanager/executors/runner.py:606:    if model != task.expected_model:
  src/auditmanager/runs/extended_review.py:142:            and response.model != binding.call.expected_model):
  ```
- interpretation: two are this task's; `executors/runner.py:606` is `HOSTS-BACKEND-01`'s file, and the integrator swaps that line at `HOSTS-INT-1` to the function this task exports from `analysis.public`.

The integrator re-runs the premise commands on the dispatch base and corrects line numbers.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/**`
- `src/auditmanager/analysis/text/**`
- `src/auditmanager/analysis/extended/**`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/bootstrap/stage_plan_adapter.py`
- `src/auditmanager/bootstrap/stage_plan_providers.py`
- `tests/unit/runs/**`
- `tests/unit/analysis/**`
- `tests/unit/analysis_extended/**`
- `tests/integration/runs/**`
- `tests/integration/analysis/**`
- `tests/integration/analysis_text/**`

## Forbidden hotspots
- `src/auditmanager/runs/stage_facts.py`: the stub of `RUN-STAGES-01`
- `src/auditmanager/bootstrap/providers.py`, `composition.py`, `adapters.py` and `src/auditmanager/api/routers/ports.py`: the integrator's; this task exports functions and fills the two stubs
- `src/auditmanager/executors/**`, `src/auditmanager/jobs/**`: `HOSTS-BACKEND-01`'s
- `contracts/**`, `db/migrations/**`, `docs/program/P02_LOCK.json`
- the blocks region of `src/auditmanager/runs/extended_review.py` is later reworked by `HOSTS-ENSEMBLE-01`; this task changes it only to read the cell and does not add legs or a judge

## Non-goals
- no ensemble (`blocks:N:leg1`, `leg2`, `judge`); the blocks row is a single cell in this wave and the set is named «Только Claude (блоки без судьи)»
- no run screen, no `getRunStages`
- no hosts, groups or availability (`HOSTS-BACKEND-01`)
- no routing of comparisons
- no reserve set (`R-153e`)
- no PostgreSQL or S3 started by the lane

## Deliverables
- **Layout store.** Revisions `slr_<ULID>` with the author, the journalled enable switch (valid only with `AUDITMANAGER_PROVIDER_SOURCE=database`, read only when a run starts), the sets «Только Claude», «Только Codex» and «Свой набор» with the exact model · effort of the ADR table, and the default set chosen at the switch. Only an administrator revises; the catalogue limits models and efforts (Opus medium and high; Sonnet and Codex low, medium and high; never Haiku, `xhigh`, `max`, Opus low).
- **Rows and phases.** One module defines the closed tuple `STAGE_ROWS`: `text`, `blocks`, `cross_check`, `norms`, `review`, `correction`, mapped to the code phases of the ADR table; the phases without a model stay without one. Labels come from one phase dictionary exported for the web.
- **Frozen plan.** At run start the plan freezes each cell's model, effort, answer limit, timeout and access (subscription when a subscription agent is online now, otherwise API); nothing changes mid-run and nothing is substituted.
- **`binding_for(cell)`.** One adapter and one `CallBinding(expected_model)` per call, through `stage_plan_providers.py`; a call without a `CallBinding` is refused; semantic repair of a reply uses the cell of the phase it repairs.
- **Per-cell settings** at every hard-coded value: effort `high` (`analysis/extended/workflow.py:95`, `analysis/text/prompt.py:304`), answer limits 16000 (`analysis/text/prompt.py:230`), 6000 (`workflow.py:93`, `core.py:258`, `cross_window_review.py:120`) and 12000 (`workflow.py:143`). The defaults stay today's constants.
- **`accepted_reported`.** A function exported from `analysis.public` reads the catalogue; the two sites in `runs/extended_review.py:142` and `analysis/text/stage.py:327` use it. No prefix match, no case folding.
- **Idempotency key.** (source, phase, `request_sha256`, model): no host and no connection revision.
- **Consent v2 and readiness.** `getRunStartReadiness` returns the digest, the access per cell and the total; the three commands (`startRun`, `reauditRun`, `startRunFromStage`) validate consent v2 and reject explicit executor selectors with `validation_failed`; `require_approved_model` checks membership; a changed access answers with the existing cost-preflight refusal (`reason: cost_estimate_binding_changed`). A start from a stage takes today's plan and reuses only PC-01 stages without a model. `estimateRunCost` is by model.
- **Stub adapters** `StageLayoutAdapter` and `stage_plan_providers.py` filled; the functions the integrator's wrappers call are exported.

## Required tests
- command: with the project's Python (`FOUNDATION_PYTHON` in the `Makefile`, the venv), `-m pytest tests/unit/runs tests/unit/analysis tests/unit/analysis_extended -q`, plus the touched files of `tests/integration/analysis_text` that need no service; database-marked tests under `tests/integration/runs` are written and not run by the lane
- expected: pass. Cases: each row maps to its phases; a catalogue-forbidden effort or model is refused; a frozen plan does not change when the layout is revised; `R-133` (another model refused, no `CallBinding` refused, `accepted_reported` exact: an alias outside the list is refused); the idempotency key has no host; consent v2 (another model or a changed access refused; subscription is 0 $ with `confirmed`); an explicit selector under the layout is `validation_failed`; with the switch off a run is bound exactly as before

## Integration contract
- The integrator wires `stage_plan_adapter.py` and `stage_plan_providers.py` in `composition.py`/`providers.py`, replaces the single `CallBinding` at `composition.py:932` for a `stage_plan` run, and swaps `executors/runner.py:606` for the exported `accepted_reported`.
- `RUN-START-ONE-01`, `RUN-SCREEN-01` and `HOSTS-ENSEMBLE-01` rely on the plan's cell identities, the phase dictionary and `binding_for(cell)`.

## Failure/idempotency/security cases
- the layout switch off, or the provider source not `database`, leaves every run on the legacy route
- a viewer cannot read the layout; an expert cannot revise it
- no LLM output decides a model or an effort
- each guard has a test that fails without it

## Rollback / feature flag
The database switch is the flag. Turning it off stops new runs from freezing a plan; runs already started finish on theirs.

## Handoff
- changed files: the lane lists them; it does not run git
- commands/results: the unit tests above; no database, container or model run
- known limits: database-marked tests unexecuted; the blocks row has no judge until `HOSTS-ENSEMBLE-01`
- integration notes: exported function names; the wiring list for the integrator
