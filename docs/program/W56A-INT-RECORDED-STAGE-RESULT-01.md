# W56A-INT-RECORDED-STAGE-RESULT-01 — complete recorded stage seal

`seal_recorded_v2_stage_result` checks canonical AR v2 observation bytes
against a caller-supplied published Blob reference, exact recorded call facts,
verified `RecordedV2Input`, registered profile and run/version identity. It
recomputes the source binding and checks the artifact's exact source refs,
page intervals, analysed pages and `textless_pages` against that input. It returns a
`text_analysis` `StageResult` with the stage version from the frozen registry,
one required artifact and scalar metrics. The result carries no cost claim.

The seal refuses truncated or salvaged responses. The current artifact builder
marks every source page in `pages_analysed` even on a truncated reply, so a
`partial` result would need a separate explicit coverage rule and typed error.
This refusal prevents an incomplete response from being reported as success.

## Changed files

- `src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py`;
- `tests/integration/analysis/test_ar_v2_recorded_stage_result.py`;
- `docs/program/tasks/W56A-INT-RECORDED-STAGE-RESULT-01.md`;
- this report.

## Checks

- Focused real-replay, artifact, call and seal tests: **25 passed**,
  including jointly trimmed page lists and source-reference drift.
- Produced result checked with the pinned Draft 2020-12 StageResult validator:
  `{"name":"recorded_v2","valid":true,"messages":[]}`.
- Python compilation passed; direct task governance returned `[]`; seven
  frozen SHA-256 values match; `git diff --check` and the exact four-path
  ownership check passed.
- No Docker, DB, Blob write/readback, network, provider call or full gate.

## Contracts and limits

No contract, migration, provider lock, v1 stage, public analysis boundary,
executor, journal, findings, API, dependency, composition root or global
style changed. This pure seal cannot prove the caller actually stored or
verified the Blob; it checks the `ArtifactRef` metadata returned by the
future publisher. A persisted model-call row, stage-result row and their
transaction remain separate work. It is not active runtime behavior or beta
acceptance.

## Integration instruction

Take exactly the four task-owned paths. After a separately owned durable
caller publishes the artifact bytes and verifies storage availability, pass
its returned reference, exact call facts and verified source input to this seal, then persist
the result in the caller-owned transaction. Keep truncated responses out of
the success path until partial coverage is defined and tested.
