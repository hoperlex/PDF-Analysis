# W57A-INT-RETRIEVAL-CANDIDATE-01 — pure set/catalogue candidate

## Result

`candidate.py` joins the existing W57a SELECT evidence DTOs, reviewed source
projection, deterministic ranking selector and canonical set/catalogue byte
builders. It refuses a changed snapshot/content key/build, foreign, duplicate
or missing mapped-document windows, and item ID/target-document drift. The
returned immutable candidate carries both canonical blobs, their SHA-256,
the selected prompt part and the stored embedding-set digest. It performs no
database, S3, provider or runtime action.

## Checks

- Focused pure suite: **5 passed**; combined candidate, bridge, window,
  artifact, catalogue and ranking suite: **31 passed**.
- Python compilation passed; direct task `governance_findings` returned `[]`;
  four owned files passed trailing-space and final-newline checks.
- Complete `make gate` deferred under R-135.

## Contracts and limits

No shared contract, migration, public API, dependency, composition or runtime
path changed. The map binds IDs and artifact identity; approval of its targets
and query-vector digest remains caller-owned because the current map interface
does not expose a verified vector digest to this assembler. `WindowEvidence`
does not retain content key, so the caller must pass the same reviewed key to
its SELECT reader. The window reader verifies that key against the DB before
returning; this pure candidate does not make a broader provenance claim.
It does not compare independently expected set/catalogue digests or create a
verified row. No corpus qualification, custody or beta claim follows.

## Integration instruction

After owner map/target/vector review and independent embedding qualification,
read source and windows under one consistent transaction with the same map
snapshot/content key/build and mapped IDs. Assemble the candidate, compare its
two SHA-256 values with independent expectations, then follow W57's rejected
or verified-row and custody workflow. Do not pin or publish these bytes alone.

## Ownership proof

Only four new task-owned paths were written. `contracts/**`, migration head,
existing retrieval modules, norms repository, provider lock, public boundary,
composition root, root dependencies, global styles, corpus, `CURRENT_STATE.md`,
runner, stand and Git refs were untouched by this task. Stage only these four
exact paths for integration.
