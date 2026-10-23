# Task AR-V3-BETA-CITE-STAGE-CONTRACT-01 — profile-owned CITE stage

## Outcome
The AR v3 beta profile has a versioned, machine-checked citation-review stage declaration and a validator for its future StageResult, without changing the nine legacy canonical stages or the sealed analysis family version.

## Depends on
- `AR-V3-BETA-REVIEW-ARTIFACT-01`
- `AR-V3-BETA-SIX-RUN-02`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- canonical legacy registry: `contracts/analysis/v1/stage-registry.json`, nine stages, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `ed95bac634ba1a190ccf1415b732543d86b3e728`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/analysis/ar_v3_beta/v1/stage.json`
- enumerator_owner: `AR-V3-BETA-CITE-STAGE-CONTRACT-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/analysis_packages/test_ar_v3_cite_stage_extension.py`

## Captured premise evidence
- premise: the sealed legacy registry has nine evidence-bound stages and its normative stage requires a finding merge
### P-01 — exact canonical count and dependency
- captured_at: 2026-10-23
- command: `/root/projects/PDF-Analysis/.venv/bin/python -c "import json; d=json.load(open('contracts/analysis/v1/stage-registry.json')); print(len(d['stages'])); print(next(x['depends_on'] for x in d['stages'] if x['stage_id']=='norm_verification'))"`
- captured_output:
  ```text
  9
  ['finding_merge']
  ```
- interpretation: v3 review before finding publication must not impersonate the existing post-merge stage or fabricate legacy evidence for a tenth canonical legacy stage.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `contracts/analysis/ar_v3_beta/v1/stage.json`
- `src/auditmanager/runs/v3_cite_stage_contract.py`
- `tests/contract/analysis_packages/test_ar_v3_cite_stage_extension.py`
- `docs/program/tasks/AR-V3-BETA-CITE-STAGE-CONTRACT-01.md`
- `docs/program/AR-V3-BETA-CITE-STAGE-CONTRACT-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/analysis/v1/**` and all other sealed contract families
- migration head, root dependencies/lockfiles, composition root, active executor
- provider transports, global styles, normative maps/source/set data

## Non-goals
- Writing or serving a CITE StageResult or changing existing stage topology.
- Calling a model, publishing a Blob, creating a finding or expert decision.
- Bumping the global `1.2.0` family contract.

## Deliverables
- One profile-specific versioned stage manifest and strict runtime loader/StageResult validator.
- Focused mutation tests and result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/analysis_packages/test_ar_v3_cite_stage_extension.py tests/contract/analysis_packages/test_stage_result_contract.py tests/contract/api_v1/test_contract_seal.py -x --tb=short`
- expected: all passed; governance and exact changed-path checks clear.

## Integration contract
The CITE writer must call `load_v3_cite_stage_contract` and `require_v3_cite_stage_result` before persisting a successful result. Its single output is `analysis.v3_beta_review`; the reply Blob is a required input referenced inside those bytes and the canonical completed call. This profile extension does not change the legacy registry or grant normative authority.

## Failure/idempotency/security cases
- Unknown stage/version, changed output/input role, missing frozen stage dependency, extra keys or non-review-only policy refuse.
- Successful StageResult requires exactly one review artifact; failed StageResult carries no artifacts. Partial/skipped are disallowed in this beta extension.
- The stage validator checks shape only; caller must independently prove current Attempt, exact call/reply/set and artifact readback.

## Rollback / feature flag
Unserved profile extension. Remove this manifest and validator before writer activation without data migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: no writer, executor or approved set pack
- integration notes: keep canonical nine-stage registry unchanged
