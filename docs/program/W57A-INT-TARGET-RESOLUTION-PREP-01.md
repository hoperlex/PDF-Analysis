# W57A-INT-TARGET-RESOLUTION-PREP-01 — target spans prepared

## Result

`norms/retrieval/targets.py` resolves owner-specified numeric clauses, table
captions and explicit `npar_` endpoint ranges over a complete canonical
document paragraph sequence. Clause resolution includes descendants and
unnumbered continuation until the next heading or unrelated numbered clause.
Table resolution includes rows and notes until the next heading or clause.
Leading `**`, `__` and `#` markers are stripped for anchor detection.
Unreliable paragraphs are listed and excluded by splitting the result into
contiguous spans. Missing, ambiguous or unreliable anchors are refused.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_targets.py tests/integration/norms/retrieval/test_ranking.py`:
  **14 passed**, including a resolver-to-ranking integration check.
- Python `compileall` for the two new Python files: passed.
- Direct `governance_findings` on the task: `[]`.
- `ruff` is absent from the repository venv; formatting reviewed manually.
  Full `make gate` deferred under R-135.
- Staged whitespace and exact-path proof: see Git commit evidence below.

## Contracts and limits

No contract, migration, existing parser or runtime interface changed. This
resolver does not choose editions, inspect legal status or read the promotion
database. It consumes paragraph metadata supplied by the future W57A-MAP
owner; exact canonical text and target scope still require owner review.

## Integration instruction

Choose the document edition and qualified snapshot first. Pass all canonical
paragraphs of that `ndoc_` in ordinal order; review the selected texts and
`excluded_unreliable` IDs. Record only the resulting spans as reviewed map
targets and pass them unchanged to ranking. An absent/ambiguous clause or
caption should be resolved by an owner-picked explicit range, never by an
automatic nearest match.

## Ownership proof

Only the five allowed paths changed. `contracts/**`, migrations, provider
lock, segmentation/ranking implementations, composition roots, global styles,
corpus files, production stand and `origin/main` were untouched. Development
target: `origin/dev`.
