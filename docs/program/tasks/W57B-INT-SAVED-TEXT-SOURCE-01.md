# Task W57B-INT-SAVED-TEXT-SOURCE-01 — current Attempt saved PDF text source

task_id: W57B-INT-SAVED-TEXT-SOURCE-01

## Outcome

One unserved, caller-transaction-owned Run read returns a validated
`analysis.public.TextLayer` from the exact saved `source_preparation` Blob, with
independently checked Version UID and page count. It fits the W57b
`reference_pages_from_text_layer` input without converting OCR to PDF text.

## Depends on

- `W56B-INT-RUN-TEXT-READ-01` — completed saved source read/fencing pattern.
- `W57B-INT-TEXT-PAGE-BRIDGE-01` — completed pure reference-page adapter.
- `CFB-INT-DEV-PUBLISH-60` — completed development integration base.

## Frozen inputs

- base commit: `2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab`
- API v1 SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W56b source validator SHA-256 `785fbffeb3069a304dfca150c7865b31948ad191aaed9e673d299b2731140761`;
- W57b text-page bridge SHA-256 `c8ce59d436f1fab368e13b00a6c3bc4ae7ee7d376cc592dbf68d9ffba4d66912`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the reader checks one saved stage, one text ref and every page against the independently loaded Version page count.

## Captured premise evidence

- premise: The W56b source validator couples canonical byte validation to a
  chunk budget, while W57b needs the same validation without model chunking.

### P-01 — base and additive reader paths

- captured_at: 2026-10-16
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/runs/reference_text_input.py tests/integration/runs/test_reference_text_input_offline.py docs/program/tasks/W57B-INT-SAVED-TEXT-SOURCE-01.md docs/program/W57B-INT-SAVED-TEXT-SOURCE-01.md`
- captured_output:
  ```text
  2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab
  ```
- interpretation: the four new paths are absent at freeze; the two existing
  analysis paths are this task's only shared-surface edits.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/reference_text_input.py`
- `src/auditmanager/analysis/text/source_bytes.py`
- `src/auditmanager/analysis/public.py`
- `tests/integration/runs/test_reference_text_input_offline.py`
- `docs/program/tasks/W57B-INT-SAVED-TEXT-SOURCE-01.md`
- `docs/program/W57B-INT-SAVED-TEXT-SOURCE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root/global
styles, API/routes, provider and finding publication, stage execution, W56b
window policy, catalogue resolver, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No PDF parse, OCR substitution, model dispatch, findings, normative resolution,
DB/S3 write, served caller, new profile policy, 0024 seal or beta acceptance.

## Deliverables

Factor pure canonical text-layer byte validation from W56b's existing window
source; expose it at the analysis public boundary; add an unserved bounded
Run/Attempt read and focused offline tests; deliver a clean source commit and
this report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_reference_text_input_offline.py tests/integration/runs/test_text_window_input.py tests/integration/analysis_text/test_source_bytes.py tests/integration/analysis_text/test_saved_window_custody.py tests/integration/norms/references/test_text_pages.py` — pass;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program/test_wave_governance.py` — pass;
- compile owned Python, `git diff --check`, exact-path and frozen-hash proof;
- no full `make gate` under R-135 for this intermediate code candidate.

## Integration contract

Call `load_saved_reference_text` inside the caller's transaction with a current
`AttemptAuthority` and explicit positive byte cap. The service locks the
current Attempt, reads Run/Version and one succeeded, registry-versioned
source stage, checks a complete saved artifact set, streams only the text ref
with expected SHA/size and a bounded buffer, validates canonical JSON and
ordered text pages, then repeats current Attempt/Run/Version/stage checks.
It returns `text_layer`, `version_uid` and `page_count` for the existing pure
reference-page bridge. The caller owns transaction commit/rollback and any
later provider or publication authorization.

## Failure/idempotency/security cases

Wrong stage/Version/page count/ref/digest/size, noncanonical payload, invalid
Unicode offsets, stale Attempt or changed rows refuse. Early termination
closes the Blob stream. A repeated unchanged read returns equivalent data;
no fallback to OCR, path or local files occurs.

## Rollback / feature flag

Revert the six owned paths before activation. This code is unserved, creates
no persistent state and needs no runtime flag or data rollback.
