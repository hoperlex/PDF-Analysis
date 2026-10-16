# Task W57B-INT-RUN-REFERENCE-CHAIN-01 — current Run reference read chain

task_id: W57B-INT-RUN-REFERENCE-CHAIN-01

## Outcome

One unserved read-only call composes the saved PDF text reader, verified catalogue custody reader, text-page bridge and pure reference pipeline under one caller-owned transaction. It returns exact Run/Version/set/snapshot provenance, all reference outcomes and grounded newer-edition candidates, without publication.

## Depends on

- `W57B-INT-SAVED-TEXT-SOURCE-01` — completed saved PDF text reader.
- `W57B-INT-CATALOGUE-CUSTODY-READ-01` — completed verified catalogue reader.
- `W57B-INT-TEXT-PAGE-BRIDGE-01` — completed text-layer page bridge.
- `W57B-INT-REFERENCE-PIPELINE-PREP-01` — completed pure catalogue/reference pipeline.
- `CFB-INT-DEV-PUBLISH-63` — completed development base `417123c729599cfa075d3461038c8dd15b86d4a3`.

## Frozen inputs

- base commit: `417123c729599cfa075d3461038c8dd15b86d4a3`
- API v1 SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain identifiers SHA-256 `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- errors SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- saved text reader SHA-256 `6625a22bb6148b720284b1215f72794d4bcaca63c5b883b4e98bbdc3db919ade`;
- catalogue reader SHA-256 `4600cd274615f233c889f473d69c00209f49b0dfbf0dd6647fa330bfa6728c57`;
- pure pipeline SHA-256 `e5e15a167e8328cd5cdbd0cfc03cf6d37669022f785830bad91370863e3131d2`;
- page bridge SHA-256 `c8ce59d436f1fab368e13b00a6c3bc4ae7ee7d376cc592dbf68d9ffba4d66912`;
- W57 plan §§B3.1–B3.4; R-76 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: all four ingredients are present on the exact base, while the composed Run reader and its test and task files are absent.

### P-01 — exact base and additive paths

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; git ls-tree -r --name-only HEAD src/auditmanager/runs/reference_pipeline.py tests/integration/runs/test_reference_pipeline.py docs/program/tasks/W57B-INT-RUN-REFERENCE-CHAIN-01.md docs/program/W57B-INT-RUN-REFERENCE-CHAIN-01.md`
- captured_output:
  ```text
  417123c729599cfa075d3461038c8dd15b86d4a3
  ```
- interpretation: the new use case, test and records are additive; the two public facades are this task's only existing code edits.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/reference_pipeline.py`
- `src/auditmanager/runs/public.py`
- `src/auditmanager/norms/public.py`
- `tests/integration/runs/test_reference_pipeline.py`
- `docs/program/tasks/W57B-INT-RUN-REFERENCE-CHAIN-01.md`
- `docs/program/W57B-INT-RUN-REFERENCE-CHAIN-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root/global styles, API/routes, provider, findings and observation publication, existing reader/pipeline internals, W54 corpus, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No served stage or route, 0024 seal, PDF/OCR parsing, default unparsed-slug list, model call, finding persistence, DB/S3 live drill, qualified corpus assertion or beta acceptance.

## Deliverables

One transaction-scoped Run reference read, public facade exports, focused offline tests and result report, with a clean local source commit.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_reference_pipeline.py tests/integration/runs/test_reference_text_input_offline.py tests/integration/norms/references/test_catalogue_input.py tests/integration/norms/references/test_reference_pipeline.py tests/integration/norms/references/test_text_pages.py` — pass;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program/test_wave_governance.py` — pass;
- compile owned Python, `git diff --check`, exact allowed-path and frozen-hash proof;
- no full `make gate` under R-135 for this intermediate code candidate.

## Integration contract

The authorized caller owns one consistent, short transaction and supplies its current `AttemptAuthority`, `BlobStore`, explicit Run/Version/set/snapshot pin tuple, reviewed unparsed-slug tuple and byte caps. The use case checks the Run pin before and after both bounded readers, uses their public boundaries and the pure page/reference pipeline, and rechecks the current Attempt before return. The returned result preserves the pin tuple, catalogue digest and report/candidates; it grants no later effect authority.

## Failure/idempotency/security cases

Wrong Run/Version/set/snapshot pins refuse before Blob read. Changed run pin or stale Attempt refuses after the reads. Reader, catalogue, page and pipeline refusals propagate; no OCR substitution or local-file fallback occurs. Equal pinned inputs return equal evidence; there are no writes.

## Rollback / feature flag

Revert the six owned paths before activation. The code is unserved and persists nothing, so there is no runtime flag or data rollback.
