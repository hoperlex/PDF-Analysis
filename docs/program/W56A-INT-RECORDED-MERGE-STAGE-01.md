# W56A-INT-RECORDED-MERGE-STAGE-01 — saved AR v2 merge stage

## Result

`run_recorded_v2_merge_stage` is an unactivated durable port for a saved,
running recorded AR v2 run. It consumes the single successful text-stage
observation Blob and confirms that its declared text/OCR source references
equal the saved `source_preparation` result. A v2-specific reader checks exact
Blob bytes, canonical JSON, profile and run provenance, request/source
binding, complete coverage, dense observation and source ordinals, diagnostic
partition, page spans and required PDF citation shape. The generic v1
`read_artifact` stays unchanged.

The port calls the existing pure `merge_grounded` rule over the accepted
observations, publishes `findings.merged` through the existing durable Blob
intent and reconciliation flow, reads back the exact bytes, and commits a
registry-bound successful `finding_merge` StageResult with its Blob binding.
Zero accepted observations produce a valid empty-group artifact. The model
recording is absent during the port test and is never read by this code.

## Changed files

- `src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py` — strict
  saved-v2 reader and typed merge input;
- `src/auditmanager/analysis/public.py` — additive public exports for that
  reader, result and deterministic merge core;
- `src/auditmanager/runs/recorded_v2_merge.py` — unactivated durable merge port;
- `tests/integration/runs/test_v2_recorded_merge_stage.py` — saved Blob,
  no-recording, empty, duplicate, source mismatch, truncated/sparse and
  readback-failure cases;
- `docs/program/tasks/W56A-INT-RECORDED-MERGE-STAGE-01.md`;
- this report.

The existing `tests/integration/analysis/test_ar_v2_recorded_artifact.py`
remains unchanged and is included in the focused regression command.

## Checks

- Focused merge port, durable text stage, recorded artifact and pure merge
  suites: **49 passed**. Pytest emitted five warnings while cleaning unrelated
  old `/tmp/pytest-of-root/garbage-*` directories; no test failed.
- Program governance suite: **16 passed**; direct task governance: `[]`.
- Python compilation and `git diff --check`: passed.
- Frozen W56 plan, code-first order, API, error catalog, analysis registry and
  provider lock SHA-256 values match the task file.
- Real PostgreSQL/S3 acceptance and the full beta gate were not run under
  R-135 during the separate W55b release gate.

## Contracts and limits

No contract, migration, provider lock, executor, finding publisher,
JobRepository, run repository, composition root, recording, dependency file,
global style, remote ref or tag changed. The input reader uses the prior
text-stage success seal as the authority for actual PDF quote content; it
checks saved page boundaries and quote spans but does not reread the PDF text
Blob. This port does not select a terminal or write finding/diagnostic rows.
The test exercises fake session and Blob boundaries, so DB/S3 ordering and
reconciliation remain an integration acceptance item.

## Integration instruction

Cherry-pick the local task commit onto the current code-first dev candidate
after exact frozen-input and allowed-path review. A later executor task may
call this port only after the recorded text StageResult has committed under a
current Attempt, then separately publish findings and select a terminal from
persisted stages. On failure after Blob intent, reconcile the content-addressed
publication before retry; no second model call is required for merge. Keep the
v1 executor path unchanged until that later task passes real DB/S3 acceptance.
