# Task W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01 — persisted saved PDF text read

task_id: W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01

## Outcome

One targeted test proves that the unserved W57b saved-text reader and
reference-page bridge consume the exact `source_preparation` artifact saved by
the production executor on an isolated PostgreSQL 0023 and private S3 bucket.
An OCR-only page remains unread as PDF text; a forged Attempt token refuses
before any Blob read.

## Depends on

- `W57B-INT-SAVED-TEXT-SOURCE-01` — completed unserved reader and bridge.
- `CFB-INT-DEV-PUBLISH-61` — completed development integration base.
- `W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01` — completed executor acceptance pattern.

## Frozen inputs

- base commit: `8c0dc0e708332e73bd3dc5defdae9fa97665f4ac`
- API v1 SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- saved-text reader SHA-256 `6625a22bb6148b720284b1215f72794d4bcaca63c5b883b4e98bbdc3db919ade`;
- reference-page bridge SHA-256 `c8ce59d436f1fab368e13b00a6c3bc4ae7ee7d376cc592dbf68d9ffba4d66912`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the test reads one saved source stage and its text-layer ref; no registry member changes.

## Captured premise evidence

- premise: The completed W56b real-service acceptance test seeds the committed
  `image_only_with_block.zip` through public Blob and Document ports and stops
  the production executor after source and geometry are saved, before provider.

### P-01 — prior test and additive test path

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD tests/integration/runs/test_recognised_region_db_s3_accept.py tests/integration/runs/test_reference_text_input_db_s3_accept.py`
- captured_output:
  ```text
  tests/integration/runs/test_recognised_region_db_s3_accept.py
  ```
- interpretation: the reusable acceptance pattern is tracked on the base;
  this task's test path is absent and additive.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/integration/runs/test_reference_text_input_db_s3_accept.py`
- `docs/program/tasks/W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01.md`
- `docs/program/W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01.md`

## Lane resources

- foundation_instance: `auditmanager-w57b-text-accept-01`
- postgres_port: `55462`
- s3_api_port: `59064`
- s3_console_port: `59065`
- postgres_db: `auditmanager_w57b_text_accept_01`
- s3_bucket: `auditmanager-w57b-text-accept-01`

## Forbidden hotspots

`contracts/**`, migrations, runtime source, root dependencies/locks,
composition root/global styles, `CURRENT_STATE.md`, provider, remote refs and
tags.

## Non-goals

No served caller, paid provider, normative corpus import, catalogue fixture,
finding or reference publication, 0024 seal or beta acceptance.

## Deliverables

One real PostgreSQL/S3 test using committed synthetic bundle bytes, task and
result report, a clean source commit and local handoff.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_reference_text_input_db_s3_accept.py` — pass against only this task's disposable services;
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program/test_wave_governance.py` — pass;
- compile owned Python, `git diff --check`, exact-path and frozen-hash proof;
- no full `make gate` under R-135 for this intermediate code candidate.

## Integration contract

The test uses public Document and Blob ports to publish the committed
synthetic portal bundle, starts a recorded Run, lets the production executor
save and bind `source_preparation`, and intercepts the next stage before
provider dispatch. It calls `load_saved_reference_text` in the current
Attempt's transaction and maps the result through
`reference_pages_from_text_layer` without adding a served path.

## Failure/idempotency/security cases

The OCR-only PDF pages carry no text or readable reference even when the
recognised markdown is populated. A forged execution token fails before
`BlobStore.open_stream`. The test leaves no provider call or finding.

## Rollback / feature flag

Revert the three owned paths. The test adds no runtime behavior or persisted
product state, so no feature flag or data rollback applies. The disposable
service pair and volumes are removed after verification.
