# Task W56A-INT-RECORDED-STAGE-RESULT-01 — seal complete recorded text stage

task_id: W56A-INT-RECORDED-STAGE-RESULT-01

## Outcome

A pure seal produces one registry-versioned, schema-valid `StageResult` for a
complete recorded AR v2 response only after matching its canonical artifact
bytes, published Blob reference, call facts, verified `RecordedV2Input`,
run/version/profile provenance, full source page coverage and ordered timestamps.
Truncated responses fail closed
until a separate coverage and partial-status policy exists.

## Depends on

- `W56A-INT-RECORDED-ARTIFACT-PREP-01` — completed canonical AR v2 observation bytes.
- `W56A-INT-RECORDED-CALL-FACTS-01` — completed exact recorded response/usage binding.
- `W56A-INT-AR-V2-RECORDED-PROFILE-01` — completed immutable recorded descriptor.

## Frozen inputs

- base commit: `8fad351330bb27a8e462424f09c2274a9f3f5ae0`;
- `origin/dev` at task read: `8f113f6b8987f2fb702872435f61999e143bdc50`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- StageResult schema SHA-256 `09947aa4417c1f129efc0e7538463da72cbd4c517422bf0b31f5c85a85cda418`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W56a has artifact bytes and exact call facts, while the frozen
  registry requires a `text_analysis` output and no recorded AR v2 producer
  binds them into a `StageResult`.

### P-01 — no owned seal on exact base

- captured_at: 2026-10-16
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py tests/integration/analysis/test_ar_v2_recorded_stage_result.py docs/program/tasks/W56A-INT-RECORDED-STAGE-RESULT-01.md docs/program/W56A-INT-RECORDED-STAGE-RESULT-01.md && git show HEAD:src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py | rg -n 'class BuiltRecordedArtifact|def build_recorded_observation_artifact' && git show HEAD:contracts/analysis/v1/stage-registry.json | sed -n '403,409p;430,452p'`
- captured_output:
  ```text
  8fad351330bb27a8e462424f09c2274a9f3f5ae0
  41:class BuiltRecordedArtifact:
  103:def build_recorded_observation_artifact(
      },
      {
        "stage_id": "text_analysis",
        "title": "Text analysis",
        "stage_version": "1.0.0",
        "purpose": "Produce text-derived finding observations from the extracted text layer and the shared document context.",
        "depends_on": [
        }
      ],
      "produced_outputs": [
        {
          "role": "analysis.text_observations",
          "media_type": "application/json",
          "required": true,
          "description": "Text finding observations with evidence anchors into the text layer."
        }
      ],
      "execution": {
        "scope": "remote_eligible",
        "scope_rationale": "Consumes derived artifacts by blob_id and checksum and writes no canonical metadata.",
        "model_routed": true,
        "mandatory": true
      },
      "status_policy": {
        "skip_allowed": false,
        "partial_allowed": true,
        "retryable": true,
        "succeeded_requires_all_required_outputs": true
      },
      "evidence": {
  ```
- interpretation: the source builder exists, but a matching Blob reference
  and coverage against verified source input still need proof before a
  success result is formed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py`
- `tests/integration/analysis/test_ar_v2_recorded_stage_result.py`
- `docs/program/tasks/W56A-INT-RECORDED-STAGE-RESULT-01.md`
- `docs/program/W56A-INT-RECORDED-STAGE-RESULT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing v1 text stage,
`analysis.public`, executor, journal/repository, findings, API, recordings,
root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`,
Git refs, tags and remote branches.

## Non-goals

No Blob write/readback, DB/journal write, partial-result policy, provider
call, monetary cost, finding publication, runtime activation, full gate or
beta acceptance. A matching `ArtifactRef` is not proof that Blob exists.

## Deliverables

Additive stage seal, focused real replay/artifact and refusal tests, schema
validation against the frozen StageResult contract, task and report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_recorded_stage_result.py tests/integration/analysis/test_ar_v2_recorded_call.py tests/integration/analysis/test_ar_v2_recorded_artifact.py` — pass;
- one produced StageResult through `tests/contract/analysis_packages/stage_result_schema_check.py` under the governance interpreter — valid;
- Python compilation, direct task governance, frozen hashes, whitespace and
  exact allowed-path proof — pass;
- full `make gate` deferred under R-135.

## Integration contract

The future durable stage publishes `BuiltRecordedArtifact.payload` through
BlobStore and supplies the actual returned `ArtifactRef`, corresponding
`RecordedCallFacts` and verified `RecordedV2Input`, run/version IDs and stage
timestamps. The seal checks the exact source artifact references,
`textless_pages`, source page intervals, all page numbers, recomputed source
binding and request identity in addition to output metadata. It returns a
`StageResult` whose version comes from
the frozen registry. The caller still verifies Blob availability, persists
the model-call record with approved provider/cost policy, enforces one call
per run, and commits the call, artifact and stage result coherently.

## Failure/idempotency/security cases

Wrong bytes/digest/role/MIME, forged reference, profile/run/version/call
mismatch, jointly trimmed page lists, source-reference or textless-page
drift, truncated/salvaged reply, wrong usage or
invalid time fails before result construction. Equal inputs yield an equal
result. No model proposal becomes an expert decision.

## Rollback / feature flag

Remove the additive module and test before runtime wiring; no data rollback
or flag is needed.

## Handoff

- changed paths, checks and limits: accompanying report;
- contracts: none;
- next: integrate only four owned paths; the durable stage/journal and
  truncated coverage policy need separate grants.
