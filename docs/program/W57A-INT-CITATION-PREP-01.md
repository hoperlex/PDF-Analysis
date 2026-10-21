# W57A-INT-CITATION-PREP-01 — pure normative grounding prepared

## Result

`src/auditmanager/norms/citation_prep.py` implements the W57 §A3.4 pure
normalisation and value rules. It maps normalized matches back to canonical
raw offsets, checks the 4,000-character span limit, binds only to reliable NFC
paragraphs of the same norm document and returns the first withhold reason.
The helper expects already grounded project-document evidence quotes. It
performs no I/O and makes no normative applicability or expert decision.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_citation_prep.py`:
  **17 passed**.
- Python `compileall` for both new Python files: passed.
- Direct `governance_findings` on the new task: `[]`.
- `ruff` executable is absent from the repository venv; formatting reviewed
  manually. Full `make gate` deferred under R-135.
- Staged whitespace and exact-path checks: see Git commit evidence below.

## Contracts and limits

No contract, migration or runtime interface changed. The helper is additive
and not wired to the active analysis stage. Production acceptance still needs
the W57a map and verified retrieval set, CITE runtime integration, gate-time
measurement at budget size, persistence/API/UI and the complete beta gate.

## Integration instruction

The W57A-CITE owner passes set labels plus all reliable paragraphs of each
mapped document, calls `ground_norm_observation` after W56a evidence grounding
and before merge, and persists `raw_quote` and `raw_offset` only for an accepted
result. `reason` withholds the whole observation. Non-NFC paragraph IDs in
`skipped_non_nfc` must be counted in set preparation. No fallback to another
edition or document is allowed.

## Ownership proof

Only the task's five allowed paths changed. `contracts/**`, migrations, provider
lock, composition roots, global styles, corpus files, production stand and
`origin/main` were untouched. The task's development target is `origin/dev`.
