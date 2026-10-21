# W56A-INT-RESPONSE-PIPELINE-PREP-01 — AR v2 response finish prepared

## Result

`ar_v2/response_pipeline.py` connects the existing response parser, PDF quote
grounding and deterministic merge-input adapter for one typed `ModelResponse`.
It preserves the response digest, explicit truncation status, malformed count,
every rejected quote diagnostic and the accepted source-to-dense ordinal map.
Only fully PDF-grounded proposals enter merge. It performs no provider or
database I/O and creates no expert decision.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_response_pipeline.py tests/integration/analysis/test_ar_v2_merge_input.py tests/integration/analysis/test_ar_v2_proposal_grounding.py`:
  **10 passed**.
- Python `compileall` for the two new Python files: passed.
- Direct `governance_findings` on the task: `[]`.
- `ruff` is absent from the repository venv; formatting reviewed manually.
  Full `make gate` deferred under R-135.
- Staged whitespace and exact-path proof: see Git commit evidence below.

## Contracts and limits

No contract, migration, provider, existing parser/grounding/merge or runtime
interface changed. The stage is not wired into a run, and v2 recordings are
not yet present. MODEL-PIN, provider activation, report persistence and UI
remain separate gates. A typed response alone does not establish provider
identity, provenance or acceptance.

## Integration instruction

The future AR v2 runtime owner obtains a `ModelResponse` from an authorized
adapter and calls `finish_response` with the pinned PDF text layer and selected
OCR context. Persist `grounding.rejected` diagnostics and the original parser
ordinals. Send only `merge.source_proposal_ordinals` and `merge.artifact`'s
dense ordinals onward; never create a finding from a rejected proposal.

## Ownership proof

Only the five allowed paths changed. `contracts/**`, migrations, provider
lock, existing parsing/grounding/merge implementations, composition roots,
global styles, recordings, production stand and `origin/main` were untouched.
Development target: `origin/dev`.
