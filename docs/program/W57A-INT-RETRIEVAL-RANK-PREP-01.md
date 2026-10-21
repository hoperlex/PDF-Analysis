# W57A-INT-RETRIEVAL-RANK-PREP-01 — deterministic selection prepared

## Result

`norms/retrieval/ranking.py` selects W57a target paragraphs and up to three
ranked windows per item from reviewed span inputs. Float32 vectors are checked
for dimension, finiteness and unit norm; inner products use `math.fsum` and ties
sort by document, chunk and window ordinals. Only mapped documents compete.
Resolved paragraphs must exist, be reliable and be NFC. The output assigns
dense `N1…Nk` labels and renders canonical JSON with each text SHA-256. The
22,000-character check applies to that exact serialized prompt part; when
needed the selector drops windows wholly within targets, then reduces the
uniform per-item limit from three to zero without truncating paragraphs.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_ranking.py`:
  **7 passed**.
- Python `compileall` for the new package and test: passed.
- Direct `governance_findings` on the new task: `[]`.
- `ruff` is absent from the repository venv; formatting reviewed manually.
  Full `make gate` deferred under R-135.
- Staged whitespace and exact-path proof: see Git commit evidence below.

## Contracts and limits

No contract, migration, provider, custody or runtime interface changed. This
pure selector has no reviewed map, promoted snapshot or database input reader;
`BUILDER_VERSION` identifies only this preparation algorithm. W57A-RETRIEVAL
must bind the map and snapshot, build the catalogue, admit both blobs through
custody, prove replay and measure build time and memory. The later profile
must embed this exact prompt part without exceeding the budget.

## Integration instruction

Feed `select_prompt_part` only owner-reviewed target spans and complete BGE
float32 windows for the qualified `ns_`. The returned `prompt_part`, labels,
rows and builder version must be bound in the set identity. Refuse the build
if any input is missing, unreliable or non-NFC, or the target-only part still
exceeds the cap. Never substitute a similar document or edition.

## Ownership proof

Only the six allowed paths changed. `contracts/**`, migrations, provider lock,
existing embedding/storage modules, composition roots, global styles, corpus
files, production stand and `origin/main` were untouched. Development target:
`origin/dev`.
