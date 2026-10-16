# Task W56A-INT-RECORDED-ACTIVATION-01 — explicit recorded executor bridge

task_id: W56A-INT-RECORDED-ACTIVATION-01

## Outcome

An explicitly supplied, persisted AR v2 recorded Run can traverse the five
registered stages and saved publication gate through `execute_run`. A missing
fixture identity, live configuration, or non-concrete recorded adapter is
refused before any Run, Job or Blob effect. Existing v1 execution is preserved.
This is an executor bridge, not serving composition activation.

## Depends on

- `W56A-INT-RECORDED-EXECUTOR-01` — completed preflight;
- `W56A-INT-DURABLE-RECORDED-STAGE-01` — completed recorded text stage;
- `W56A-INT-RECORDED-MERGE-STAGE-01` — completed saved merge stage;
- `W56A-INT-RECORDED-PUBLICATION-GATE-01` — completed and service tested;
- `CFB-INT-DEV-PUBLISH-17` — published and read back at base SHA.

## Frozen inputs

- base commit: `b9f1c149f004851de89a2fcc615618068e794bde` (`origin/dev` at task start);
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed stage and publication ports are not called by the executor;
  composition still resolves the v1 profile and provider lock.

### P-01 — bridge seam

- captured_at: 2026-10-16
- command: `git rev-parse HEAD && rg -n '^def (_execute_run_body|plan_recorded_v2_execution|run_recorded_v2_stage|run_recorded_v2_merge_stage|publish_recorded_v2_run|_build_provider)' src/auditmanager/runs/executor.py src/auditmanager/runs/recorded_v2_stage.py src/auditmanager/runs/recorded_v2_merge.py src/auditmanager/runs/recorded_v2_publication.py src/auditmanager/bootstrap/composition.py && rg -n '^STAGE_PLAN|^PROFILE_ID|^PROMPT_BUNDLE_ID' src/auditmanager/analysis/profiles/ar_v2/registered.py`
- captured_output:
  ```text
  b9f1c149f004851de89a2fcc615618068e794bde
  src/auditmanager/bootstrap/composition.py:312:def _build_provider(
  src/auditmanager/runs/recorded_v2_publication.py:107:def publish_recorded_v2_run(
  src/auditmanager/runs/recorded_v2_merge.py:95:def run_recorded_v2_merge_stage(
  src/auditmanager/runs/executor.py:227:def plan_recorded_v2_execution(
  src/auditmanager/runs/executor.py:716:def _execute_run_body(
  src/auditmanager/runs/recorded_v2_stage.py:54:def run_recorded_v2_stage(
  24:PROFILE_ID: Final[AnalysisProfileId] = AnalysisProfileId.parse(
  27:PROMPT_BUNDLE_ID: Final[PromptBundleId] = PromptBundleId.parse(
  32:STAGE_PLAN: Final[tuple[str, ...]] = (
  ```
- interpretation: the recorded ports and immutable profile exist independently;
  their normal worker/API wiring is outside this task.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/executor.py`
- `tests/integration/runs/test_v2_recorded_executor_bridge.py`
- `docs/program/tasks/W56A-INT-RECORDED-ACTIVATION-01.md`
- `docs/program/W56A-INT-RECORDED-ACTIVATION-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, recordings, analysis and findings
modules, repositories, composition root, API/router, root dependencies/locks,
global styles, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No model/price pin, live provider, recorded fixture generation, serving profile
selection, API/worker config, contract or migration change, full gate, main
publication or beta acceptance. This task does not select a fixture by guessing.

## Deliverables

Additive explicit executor branch; focused container-free route, refusal and
v1-preservation tests; result report with service-acceptance boundary.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v2_recorded_executor.py tests/integration/runs/test_v2_recorded_executor_bridge.py tests/integration/runs/test_v2_recorded_durable_stage.py tests/integration/runs/test_v2_recorded_merge_stage.py`;
- Python compilation, direct task governance, frozen hashes, `git diff --check`,
  exact owned-path check;
- no PostgreSQL/MinIO while the integrator's W55b full gate owns services.

## Integration contract

Only a persisted Run with the registered v2 profile and bundle, a concrete
offline `RecordedAdapter`, recorded provider configuration without a credential,
and an explicit fixture model plus generation settings can enter the bridge.
The executor commits Run/Attempt authority before deterministic stages, uses
the already durable text and merge ports, then calls the saved publication gate.
The caller commits the gate once or rolls it back. A deterministic halt lets the
gate terminalize a missing-stage Run without fixture replay. The v1 branch keeps
its existing stage and publication path.

## Failure/idempotency/security cases

Missing/malformed fixture parameters, profile mismatch and live mode fail before
effects. Each recorded stage and the gate recheck Attempt and saved evidence.
Their existing terminal CAS prevents a second publication. An exception after
authority or call persistence follows the existing caller's rollback and crash
reconciliation path; it does not silently replay or call a live provider.

## Rollback / feature flag

The branch is selected only by the persisted v2 identity plus explicit fixture
inputs. Reverting this task's executor change removes the bridge; no schema or
data rollback is needed. No serving flag is introduced.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrator may cherry-pick after dev17; a separate owned composition,
  fixture configuration and model-pin task is needed before serving activation.
