# Task W56A-INT-RECORDED-EXECUTOR-01 — preflight for recorded AR v2 execution

task_id: W56A-INT-RECORDED-EXECUTOR-01

## Outcome

An executor-side preflight accepts only a saved run matching independently
registered AR v2 profile and bundle identities with recorded run, adapter and
provider configuration. Mismatches fail before provider, blob or DB effects.
The existing v1 `execute_run` path stays unchanged.

## Depends on

- `CFB-INT-RECORDED-AND-NORM-04` — completed at `e4cf264b`;
- `W56A-INT-RECORDED-V2-CHAIN-PREP-01` — completed recorded response chain.

## Frozen inputs

- base commit and `origin/dev`: `e4cf264bc71375f85625d9ab3ad110316815d046`;
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

- premise: the executor still builds only a v1 request and selects the v1
  terminal path, while recorded AR v2 publication is unconnected.

### P-01 — current runtime boundary

- captured_at: 2026-10-15
- command: `rg -n 'profile=AR_TEXT_PROFILE|required_stages=PC01_STAGES|publish_gate_result\(|def publish_recorded_v2_response|def resolve_profile|RECORDINGS_RELPATH' src/auditmanager/runs/executor.py src/auditmanager/findings/v2_recorded.py src/auditmanager/analysis/text/profile.py src/auditmanager/analysis/text/recorded.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/recorded.py:52:RECORDINGS_RELPATH: Final[str] = "fixtures/recorded/text_analysis"
  src/auditmanager/analysis/text/recorded.py:57:    return _REPO_ROOT / RECORDINGS_RELPATH
  src/auditmanager/analysis/text/profile.py:81:def resolve_profile(analysis_profile_id: AnalysisProfileId | str = ANALYSIS_PROFILE_ID) -> AnalysisProfile:
  src/auditmanager/runs/executor.py:589:            profile=AR_TEXT_PROFILE,
  src/auditmanager/runs/executor.py:702:    publication = publish_gate_result(
  src/auditmanager/runs/executor.py:1011:            required_stages=PC01_STAGES,
  src/auditmanager/findings/v2_recorded.py:36:def publish_recorded_v2_response(
  ```
- interpretation: no registered v2 profile, request/artifact stage or
  executor publication switch exists; this task cannot activate v2 safely.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/executor.py`
- `tests/integration/runs/test_v2_recorded_executor.py`
- `docs/program/tasks/W56A-INT-RECORDED-EXECUTOR-01.md`
- `docs/program/W56A-INT-RECORDED-EXECUTOR-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, findings and analysis code,
existing run repository/commands, composition root, root dependencies/locks,
global styles, `CURRENT_STATE.md`, `origin/dev`, `origin/main` and tags.

## Non-goals

No v2 request, recorded lookup, model call, StageResult, finding publication,
run state change, API switch, provider activation, baseline, full gate or beta
claim. No unverified profile or model identity is treated as authorized.

## Deliverables

Additive recorded-only executor preflight, focused no-DB tests and result
report. The test profile and bundle identities are fixtures, not registration.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v2_recorded_executor.py`;
- Python compilation, direct task governance, `git diff --check` and exact
  owned-path check;
- database acceptance and complete `make gate` deferred under R-135.

## Integration contract

`plan_recorded_v2_execution` takes a persisted `RunRow`, adapter and provider
configuration plus identities from a later immutable profile registry. It
returns an inert intent only when all values agree and are recorded. It rejects
the v1 profile even if supplied as the purported v2 registration. The current
`execute_run` does not call it. Runtime integration must first register an AR
v2 profile/bundle and request/stage path, then connect recorded publication
through a public findings boundary with durable call provenance and run-level
idempotency.

## Failure/idempotency/security cases

Mismatched identity, live mode, terminal run or malformed registration raises
`analysis_input_invalid` before effects. This helper neither reads nor writes
DB state, cannot authenticate arbitrary caller-supplied registration, and
cannot prove a recording's request checksum. The trusted runtime caller must
source registered identities independently from the run row.

## Rollback / feature flag

Remove the additive preflight and test; no behavior was activated, so no data
rollback or feature flag is needed.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrate on the exact dev candidate, then grant the profile/stage and
  public findings boundary owners separately before runtime activation.
