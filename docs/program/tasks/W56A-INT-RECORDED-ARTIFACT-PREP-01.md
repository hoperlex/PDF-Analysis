# Task W56A-INT-RECORDED-ARTIFACT-PREP-01 — deterministic AR v2 recorded observation bytes

task_id: W56A-INT-RECORDED-ARTIFACT-PREP-01

## Outcome

A pure builder turns a verified recorded AR v2 replay into canonical,
versioned `analysis.text_observations` bytes with complete available source,
request, model-call and response provenance. Only PDF-grounded accepted
proposals become dense observations; rejected evidence and parser diagnostics
stay separate. The existing grounding-gate artifact reader accepts the output.

## Depends on

- `W56A-INT-RECORDED-RESPONSE-BRIDGE-01` — completed replay/finish bridge at `1959b760`;
- `W56A-INT-AR-V2-RECORDED-INPUT-01` — completed verified source binder;
- `W56A-INT-RESPONSE-PIPELINE-PREP-01` — completed grounding/merge finish.

## Frozen inputs

- base commit: `8dac96f7c36fad3e3855ab6abeb180a2a503fd9a`;
- source branch: `integration/code-first-entry`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; `P02_SEAMS.md` §§4.1, 4.7–4.8 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `RecordedReplayResult` retains three checksums and grounding/merge,
  but no AR v2 builder produces the versioned observation artifact bytes.

### P-01 — four additive paths absent on frozen base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py tests/integration/analysis/test_ar_v2_recorded_artifact.py docs/program/tasks/W56A-INT-RECORDED-ARTIFACT-PREP-01.md docs/program/W56A-INT-RECORDED-ARTIFACT-PREP-01.md`
- captured_output:
  ```text
  8dac96f7c36fad3e3855ab6abeb180a2a503fd9a
  ```
- interpretation: the new paths were absent; the v1 artifact builder does not
  carry AR v2 severity, source proposal ordinals or replay provenance.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py`
- `tests/integration/analysis/test_ar_v2_recorded_artifact.py`
- `docs/program/tasks/W56A-INT-RECORDED-ARTIFACT-PREP-01.md`
- `docs/program/W56A-INT-RECORDED-ARTIFACT-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migration head, provider lock, existing v1 artifact/gate,
public boundary, run executor/repository, call journal, StageResult producer,
finding publisher, recordings, corpus, root dependency/lock files,
composition root, global styles, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No DB/Blob read or write, provider call, StageResult creation, model-call row,
finding or diagnostic DB row, run state, merge-stage artifact publication,
geometry block-index binding, live model/price pin, full gate or beta claim.
The caller must allocate and durably bind `RunId` and `ModelCallId`.

## Deliverables

Additive byte builder, focused gate-reader/registry/provenance/refusal tests,
this task and result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_recorded_artifact.py` — pass;
- Python compilation, direct task governance, frozen hashes,
  `git diff --check` and exact owned-path proof — pass;
- no full `make gate` under R-135.

## Integration contract

The later recorded stage supplies verified `RecordedV2Input`, exact
`RecordedReplayResult`, caller-allocated/saved run and model-call IDs, and
registered profile/bundle IDs. The builder rechecks replay/source/request
links, the reviewed profile, PDF offsets, dense merge preparation and
identities. It returns immutable canonical bytes, SHA-256, size, role, version
and MIME. A separate publisher must store these bytes as a Blob, create the
`ArtifactRef`, construct StageResult under the registry status policy and
persist the call record before any finding publication. The current gate
reader accepts the payload's accepted observations; this test is not an
end-to-end StageResult or database acceptance claim.

## Failure/idempotency/security cases

Wrong mode, checksums, source binding, request-source render, profile,
run/call identity, merge partition or PDF offset fails before bytes are
returned. Rejected proposals never become observations. The same complete
inputs, including run and call IDs, yield identical bytes. Truncation and
salvage remain diagnostics for the later StageResult policy; no fallback or
expert verdict is implied.

## Rollback / feature flag

Remove the additive builder before runtime wiring. No active behavior or data
migration changes, so no feature flag is needed.

## Handoff

- changed paths/checks/limits: accompanying report;
- contracts: none;
- next: stage owner must own Blob publication, model-call journal,
  StageResult status and idempotent executor wiring in a separate task.
