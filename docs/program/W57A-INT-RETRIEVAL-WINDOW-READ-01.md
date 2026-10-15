# W57A-INT-RETRIEVAL-WINDOW-READ-01 — canonical embedding windows

## Result

`window_reader.py` adds a SELECT-only reader of one `norm_embedding_build`.
It matches the caller's exact snapshot content key and independent build
digest, checks complete canonical chunk/window totals, replays the full
`norm-embedding-set/2` metadata digest in stored order, and bounds mapped
candidate windows at 50,000. For mapped documents it reads pgvector text,
packs the exact 1,024 float32 values and checks the stored vector SHA before
returning existing `RetrievalWindow` inputs. No HNSW search or write runs.

## Checks

- Focused fake-session suite: **6 passed**; combined bridge/ranking suite:
  **19 passed**.
- Python compilation passed; direct task `governance_findings` returned `[]`;
  four owned files passed trailing-space and final-newline checks.
- Complete `make gate` deferred under R-135.

## Contracts and limits

No shared contract, migration, public API, dependency, composition or runtime
path changed. The build schema permits a full metadata count/digest check;
the reader performs it, while bounding its materialized result to mapped
windows. It does not independently regenerate tokenizer windows or confirm
that a human reviewed the map. Stored build validity and the caller's expected
digest are inputs to later W57a qualification, not a legal source verdict.
The caller must keep all SELECTs in one consistent transaction. No verified
retrieval-set row, custody admission, production DB/S3 publication or beta
claim follows.

## Integration instruction

After map approval and independent embedding-build qualification, pass the
same reviewed `ns_`, content key, build identity, expected set digest and mapped
document IDs used by `SnapshotEvidence`/its bridge. Use returned windows with
the pure ranking selector, compare the resulting set/catalogue artifacts to
independent expected digests, then follow W57 custody and verified-row steps.

## Ownership proof

Only four new task-owned paths were written. `contracts/**`, migration head,
existing retrieval modules, norms repository, provider lock, public boundary,
composition root, root dependencies, global styles, corpus, `CURRENT_STATE.md`,
runner, stand and Git refs were untouched by this task. Stage only these four
exact paths for integration.
