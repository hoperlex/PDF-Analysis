# Task W56A-INT-RECORDED-MERGE-STAGE-01 — durable recorded merge artifact

task_id: W56A-INT-RECORDED-MERGE-STAGE-01

## Outcome

An unactivated run-side port reads one saved, successful AR v2 text observation
Blob under a current Attempt, checks its exact bytes and run provenance, derives
the deterministic `findings.merged` artifact, reads back its published Blob and
commits the `finding_merge` StageResult with its binding. It never reads a model
recording or writes findings.

## Depends on

- `W56A-INT-DURABLE-RECORDED-STAGE-01` — completed durable text stage port;
- `W56A-INT-RECORDED-ARTIFACT-PREP-01` — completed AR v2 observation bytes;
- `W56A-INT-MERGE-CORE-01` — completed deterministic merge core.

## Frozen inputs

- base commit and `origin/dev`: `445efc5db8556ef5a5e13fa680f9f49eb9783954`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; StageResult contract v1; recorded
  observation artifact v2 and merge artifact v1.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the recorded text stage persists v2 observation bytes, while the
  generic artifact reader admits only v1 and no recorded merge port exists.

### P-01 — saved-text merge seam

- captured_at: 2026-10-16
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/runs/recorded_v2_merge.py tests/integration/runs/test_v2_recorded_merge_stage.py && rg -n 'ARTIFACT_VERSION: Final|def read_artifact|def merge_grounded' src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py src/auditmanager/analysis/ports/artifacts.py src/auditmanager/analysis/stages/finding_merge.py`
- captured_output:
  ```text
  445efc5db8556ef5a5e13fa680f9f49eb9783954
  src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py:32:ARTIFACT_VERSION: Final[str] = "2.0.0"
  src/auditmanager/analysis/ports/artifacts.py:50:ARTIFACT_VERSION: Final[str] = "1.0.0"
  src/auditmanager/analysis/ports/artifacts.py:98:def read_artifact(
  src/auditmanager/analysis/stages/finding_merge.py:61:def merge_grounded(observations: Sequence[MergeObservation]) -> dict[str, object]:
  ```
- interpretation: a v2-specific strict reader and an unactivated run port are
  needed; weakening the generic v1 reader would break its frozen boundary.

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
- `src/auditmanager/runs/recorded_v2_merge.py`
- `tests/integration/analysis/test_ar_v2_recorded_artifact.py`
- `tests/integration/runs/test_v2_recorded_merge_stage.py`
- `docs/program/tasks/W56A-INT-RECORDED-MERGE-STAGE-01.md`
- `docs/program/W56A-INT-RECORDED-MERGE-STAGE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, recordings, executor runtime,
findings, JobRepository, run repository, composition root, API, root
dependencies/locks, global styles, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No executor activation, fixture replay, provider call, finding/diagnostic DB
row, run terminal, live model/price claim, new schema, complete beta gate or
DB/S3 acceptance claim.

## Deliverables

Strict v2 observation Blob reader, analysis public exports for the merge input
and core, one run-side durable merge stage port, focused tests and result report.

## Required tests

- focused v2 observation reader and merge-stage tests — pass;
- existing recorded artifact, durable stage and pure merge tests — pass;
- Python compilation, direct task governance, frozen hashes, whitespace and
  exact allowed-path proof — pass;
- service-backed PostgreSQL/S3 and complete gate deferred under R-135 while
  the separate W55b release gate runs.

## Integration contract

The later executor supplies a saved running run and current Attempt after the
recorded text StageResult has committed. The port checks that StageResult's
single observation reference, reads exact Blob bytes once and derives grouping
from dense PDF-grounded observations. It may reuse the recorded artifact's
stored observations but may not read the recording again. The resulting
`findings.merged` Blob and successful StageResult are bound to the Attempt;
finding publication and terminal selection remain separate executor work.

## Failure/idempotency/security cases

Wrong run/profile/version, stage status/version/reference, changed bytes,
truncated or salvaged coverage, malformed or sparse observation ordinals,
stale Attempt, duplicate merge result or mismatched readback fails closed.
An upload may leave a truthful intent if a later step fails, but no success
StageResult is committed. Deterministic content-addressed bytes permit a new
Attempt to retry merge after reconciliation without another model call.

## Rollback / feature flag

Revert the seven task-owned paths before executor wiring. This is unactivated
and has no user-facing setting or data rollback.

## Handoff

- changed paths/checks/limits: accompanying report;
- contracts: none;
- next: integrator accepts these exact paths, then separately grants recorded
  executor activation, finding publication and real PostgreSQL/S3 acceptance.
