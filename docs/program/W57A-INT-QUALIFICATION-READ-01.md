# W57A-INT-QUALIFICATION-READ-01 — stored facts for qualification

`qualification_reader.py` adds two SELECTs under a caller-owned consistent
transaction. It binds a stored snapshot to the exact reviewed content key,
counts its documents and `norm_source` PDF bindings, then reads the chosen
reliability-aware chunk and embedding completion rows with actual stored
chunk/window counts. Absent build rows remain explicit `None`; count drift is
returned as evidence rather than being called qualified.

## Checks

- Focused fake-session suite: **22 passed**; combined qualification,
  candidate, window and source-reader suite: **42 passed**. It checks exact
  SQL inputs, missing completion rows, changed keys, invalid scalar facts
  and drifted counts. The SELECTs do not write or infer an accepted set.
- Python compilation passed; direct task governance returned `[]`; the three
  frozen W57/code-first/API hashes, whitespace and exact four-path staging
  proof passed. Full `make gate` is deferred under R-135; no live DB/S3
  check has run for this slice.

## Contracts and limits

No contract, migration, existing retrieval/custody module, public API,
composition root, dependency, global style or runtime path changes. Counts
and a stored `embedding_set_sha256` are not an independent recomputation of
the source row digest or vector stream. A `norm_source` binding row is not a
readback of the PDF bytes. The owner must compare these facts with separate
manifest, byte, map, vector, digest and custody evidence before creating a
verified set. No normative corpus or beta acceptance follows from this
reader.

## Integration instruction

Integrate only the four new task paths. Use the DTO under the same snapshot
transaction as source/window reads, reject any mismatched counts or missing
completion row in the later qualification workflow, then compare independent
expected digests. No remote ref or tag was changed by this source task.
