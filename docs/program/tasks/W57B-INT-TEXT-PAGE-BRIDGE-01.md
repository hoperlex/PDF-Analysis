# Task W57B-INT-TEXT-PAGE-BRIDGE-01 — Version-bound PDF text pages for normative references

task_id: W57B-INT-TEXT-PAGE-BRIDGE-01

## Outcome

One pure, unserved mapper converts a validated `analysis.public.TextLayer` to
`ReferencePage` values without losing page or Unicode code-point offsets. It
refuses a text layer that disagrees with the caller's independently pinned
Version UID or page count, or whose pages/document text are inconsistent.

## Depends on

- `W57B-INT-REFERENCE-OBSERVATION-PREP-01` — completed page/global-offset evidence plan.
- `W57B-INT-REFERENCE-PIPELINE-PREP-01` — completed one-page-source resolver pipeline.
- `CFB-INT-STATE-59` — completed live-state refresh on this exact development base.

## Frozen inputs

- base commit: `2b0a8a04a7ef2ce050e3ec3df9dd5414c68651be`
- API v1 SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `analysis.public.TextLayer`, `prepared.text_layer` v1.0.0, existing `ReferencePage` and pipeline;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: caller supplies independent Version page count; mapper checks exact 1..N pages.

## Captured premise evidence

- premise: The prepared text layer is the one document-global Unicode sequence, while the W57b pipeline takes `ReferencePage` values. No production mapper exists on this base.

### P-01 — exact base and absent owned paths

- captured_at: 2026-10-16
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/norms/references/text_pages.py tests/integration/norms/references/test_text_pages.py docs/program/tasks/W57B-INT-TEXT-PAGE-BRIDGE-01.md docs/program/W57B-INT-TEXT-PAGE-BRIDGE-01.md`
- captured_output:
  ```text
  2b0a8a04a7ef2ce050e3ec3df9dd5414c68651be
  ```
- interpretation: The bridge is additive and shares no active hotspot.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/references/text_pages.py`
- `tests/integration/norms/references/test_text_pages.py`
- `docs/program/tasks/W57B-INT-TEXT-PAGE-BRIDGE-01.md`
- `docs/program/W57B-INT-TEXT-PAGE-BRIDGE-01.md`

## Forbidden hotspots

Existing analysis internals/public facade, reference resolver/planner/pipeline,
`contracts/**`, `db/migrations/**`, root dependencies/locks, composition
root/global styles, API/routes, served stages, corpus, `CURRENT_STATE.md`,
remote refs, tags and checkpoint files.

## Non-goals

No PDF parsing, OCR substitution, alternative content source, text
normalization, catalogue or Blob read, DB/S3 write, served caller, rule
publication, severity, 0024 seal or beta acceptance.

## Deliverables

Additive pure bridge, meaningful focused tests, task report and clean source
commit for integrator review.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_text_pages.py tests/integration/norms/references/test_reference_pipeline.py` — pass;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program/test_wave_governance.py` — pass;
- compile owned Python, `git diff --check`, exact allowed-path and frozen-hash proof;
- no full `make gate` under R-135.

## Integration contract

The future W57b caller obtains a checksum-verified, validated
`prepared.text_layer` for the current Version and independently supplies that
Version UID and page count. `reference_pages_from_text_layer` returns exactly
one ordered `ReferencePage` per Version page with decimal page-number labels;
an empty page is unread (`text=None`) and retains its zero-width offset.
Nonempty page text and global starts are copied without modification. The
caller can pass the tuple to `run_reference_pipeline` and retains all
authorization, custody, Attempt fencing and publication duties.

## Failure/idempotency/security cases

Wrong Version/count, missing/duplicate/out-of-order pages, byte-based or
discontiguous offsets, altered page/document text and malformed inputs refuse
before pipeline use. Same validated input gives identical immutable pages.
No content or secret enters Git.

## Rollback / feature flag

Revert these additive unserved files before activation; no data rollback or
runtime flag applies.
