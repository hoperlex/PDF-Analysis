# Task W56A-INT-RESPONSE-PIPELINE-PREP-01 — pure AR v2 response finish

task_id: W56A-INT-RESPONSE-PIPELINE-PREP-01

## Outcome

A pure AR v2 response-finish function connects the parser, PDF quote grounding
and deterministic merge input for a typed `ModelResponse`. A focused test
shows rejected proposals never enter the merge artifact, while truncation and
all diagnostics remain visible. No provider or runtime stage is activated.

## Depends on

- `W56A-INT-PROPOSAL-GROUNDING-PREP-01` — completed pure PDF grounding.
- `W56A-INT-MERGE-INPUT-PREP-01` — completed at `97224aec7dad6916fafbb8108de899583db56c0e`;
  supplies dense artifact ordinals after filtering.

## Frozen inputs

- base commit and `origin/dev`: `0bcef49dc4e0dd0899a2d6bfc099c3f9d0e7cf9f`.
- W56 plan §A3.3–§A3.5; code-first order SHA-256
  `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`; no head movement.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: parser, proposal grounding and merge-input preparation are separate pure components on this base.

### P-01 — exact base and absent connecting module

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/response_pipeline.py`
- captured_output:
  ```text
  0bcef49dc4e0dd0899a2d6bfc099c3f9d0e7cf9f
  0bcef49dc4e0dd0899a2d6bfc099c3f9d0e7cf9f
  ```
- interpretation: the typed response can be processed offline without the unresolved gateway pin.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/response_pipeline.py`
- `tests/integration/analysis/test_ar_v2_response_pipeline.py`
- `docs/program/tasks/W56A-INT-RESPONSE-PIPELINE-PREP-01.md`
- `docs/program/W56A-INT-RESPONSE-PIPELINE-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing parser/grounding/merge
modules, runtime executor, public API, database publication, root dependencies,
composition root, global styles, recordings, stand, tags and `origin/main`.

## Non-goals

No provider call, active AR v2 stage, finding identity, expert decision,
recording generation, full local gate or beta acceptance.

## Deliverables

Pure response finish function, focused tests, report and development ref read-back.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_response_pipeline.py tests/integration/analysis/test_ar_v2_merge_input.py tests/integration/analysis/test_ar_v2_proposal_grounding.py` — pass;
- Python compilation, direct task governance, `git diff --check` and exact
  allowed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

A later AR v2 runtime stage passes the exact typed response, PDF text layer
and selected OCR context to `finish_response` after an authorized recorded
adapter call. It persists diagnostics and original proposal ordinals; only
accepted dense ordinals enter merge/publication. Provider identity and runtime
activation remain in their own slots.

## Failure/idempotency/security cases

Malformed untruncated response raises the parser's typed refusal. Truncated
JSON salvages only complete elements. A failed PDF quote rejects the whole
proposal, including any other resolved evidence. Repeated inputs yield the
same pure artifact without I/O. No recording or credential is committed.

## Rollback / feature flag

Revert the additive module before runtime wiring; no data rollback or flag.
