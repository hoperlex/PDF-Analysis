# Task W56A-INT-RECORDED-SAVED-PUBLICATION-PLAN-01 — plan findings from saved recorded artifacts

task_id: W56A-INT-RECORDED-SAVED-PUBLICATION-PLAN-01

## Outcome

An unactivated read-only bridge reconstructs complete recorded AR v2 grounding
and a deterministic publication plan from exact saved observation and merge
Blobs. It binds run, version, registered profile, model call, source references
and both StageResult artifact references, without reading the recording again.

## Depends on

- `W56A-INT-RECORDED-ARTIFACT-PREP-01` — completed v2 observation artifact;
- `W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01` — completed pure publication rule;
- `W56A-INT-DURABLE-RECORDED-STAGE-01` — completed durable text stage;
- `W56A-INT-RECORDED-MERGE-STAGE-01` — completed durable merge stage.

## Frozen inputs

- base commit: `08055ca094a9c3e4676a5907a0b3020f0bee4fb8`
- `origin/dev` at dispatch: `08055ca094a9c3e4676a5907a0b3020f0bee4fb8`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; StageResult v1, observation artifact v2,
  merge artifact v1.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: saved observation reading projects only merge fields and no saved
  publication-plan bridge exists at the base.

### P-01 — missing saved-plan bridge

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD src/auditmanager/findings/recorded_saved_plan.py tests/integration/findings/test_v2_recorded_saved_plan.py && rg -n 'class RecordedMergeInput|def read_recorded_merge_input|def plan_v2_merge_publication|def publish_v2_merge_plan' src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py src/auditmanager/findings/merge_publication_plan.py src/auditmanager/findings/v2_publication.py`
- captured_output:
  ```text
  src/auditmanager/findings/v2_publication.py:161:def publish_v2_merge_plan(
  src/auditmanager/findings/merge_publication_plan.py:56:def plan_v2_merge_publication(
  src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py:62:class RecordedMergeInput:
  src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py:143:def read_recorded_merge_input(
  ```
- interpretation: the bridge is additive; the existing merge reader needs a
  complete typed projection before the saved artifact can feed the pure planner.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/findings/recorded_saved_plan.py`
- `tests/integration/analysis/test_ar_v2_recorded_artifact.py`
- `tests/integration/findings/test_v2_recorded_saved_plan.py`
- `docs/program/tasks/W56A-INT-RECORDED-SAVED-PUBLICATION-PLAN-01.md`
- `docs/program/W56A-INT-RECORDED-SAVED-PUBLICATION-PLAN-01.md`

## Forbidden hotspots

Executor, run/job/findings repositories, active publication and terminal code,
`contracts/**`, migrations, provider lock, recordings, composition root, API,
root dependencies/locks, global styles, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No provider/recording read, finding or diagnostic DB row, run terminal,
executor activation, migration, live model/price claim, DB/S3 acceptance,
complete gate or beta verdict.

## Deliverables

Strict complete saved observation projection, analysis public export, pure
saved-plan bridge, focused tests and result report.

## Required tests

- focused saved artifact and publication plan tests — pass;
- relevant existing merge/publication tests — pass;
- Python compilation, direct task governance, frozen hashes, whitespace and
  exact allowed-path proof — pass;
- service-backed PostgreSQL/S3 and complete gate deferred under R-135 while
  the separate W55 release gate runs.

## Integration contract

The later run-side publisher supplies the saved successful text and merge
artifact references, matching StageResult bindings, and persisted run
identity. This bridge reads each Blob exactly once, checks exact bytes and
cross-artifact source/call provenance, reconstructs every accepted proposal and
rejected diagnostic, and invokes `plan_v2_merge_publication`. It returns a
trusted pure plan and context facts, not a DB write or authorization to publish.

## Failure/idempotency/security cases

Changed bytes, missing/wrong refs or roles, different run/version/profile,
model call or source binding, nullable/incomplete rejection diagnostics,
forged merge grouping and non-canonical bytes fail closed. Repeated input
returns the same plan without effects. A later transactional gate must still
fence the Attempt and prevent duplicate findings including zero-finding runs.

## Rollback / feature flag

Revert the seven task-owned paths before runtime wiring. This bridge is
unactivated and has no data rollback or user-facing flag.

## Handoff

- changed paths/checks/limits: accompanying result report;
- contracts: none;
- next: integrator grants a separate durable finding/terminal gate with real
  PostgreSQL/S3 acceptance before executor activation.
