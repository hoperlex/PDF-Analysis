# W57A-INT-RETRIEVAL-RANGE-BOUND-FIX-01 — bounded span validation

## Result

`select_prompt_part` now checks target and candidate-window span sizes and
endpoints against supplied canonical paragraphs before expanding ordinals.
An impossible large range fails with `RankingRefused` in bounded memory.
Valid ranking, reduction and rendered prompt bytes are unchanged.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_ranking.py tests/integration/norms/retrieval/test_targets.py`:
  **15 passed**.
- Python `compileall`: passed; direct task governance: `[]`.
- `ruff` is absent from the repository venv; formatting reviewed manually.
  Full `make gate` deferred under R-135.
- Staged whitespace and exact-path proof: see Git commit evidence below.

## Contracts, risks and integration

No contract, migration or runtime interface changed. The future set builder
must still supply a complete reviewed document paragraph set. The guard
rejects malformed spans before allocation; it does not establish source
custody, legal status or owner approval. Integration should retain this check
before any prompt or blob construction.

## Ownership proof

Only the five allowed paths changed. `contracts/**`, migrations, provider
lock, other retrieval files, composition roots, global styles, corpus files,
production stand and `origin/main` were untouched. Development target:
`origin/dev`.
