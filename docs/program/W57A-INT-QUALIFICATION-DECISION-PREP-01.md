# W57A-INT-QUALIFICATION-DECISION-PREP-01 — pure digest comparison

## Result

`qualification_decision.py` joins W57a's SELECT-only stored facts with a
candidate retrieval set and independently supplied source, embedding and
expected artifact digests. It refuses incomplete document/PDF-custody,
chunk/embedding/window counts, identity or proof drift, and altered candidate
bytes. After those checks it records a deterministic `matched` or `rejected`
comparison, including expected and observed SHA-256 values and exactly which
artifact digests differ. It performs no DB, S3 or runtime action.

## Checks

- Focused pure suite: **19 passed**; combined candidate, qualification reader
  and decision suite: **46 passed**.
- Direct task governance: `[]`.
- Python compilation and frozen W57/code-first/analysis contract SHA-256 checks
  passed. Whitespace and exact-path proof completed on the four owned files.
- Complete `make gate` deferred under R-135.

## Contracts and limits

No shared contract, migration, public API, dependency, composition, runtime
or provider path changed. The caller must independently verify the source PDF
bytes and complete BGE stream, obtain owner map approval, and supply committed
expected set/catalogue SHA-256 values from outside the current candidate.
Matching stored and caller-supplied digests cannot prove that provenance.
`matched` is a comparison result only; it creates no `verified` row, custody
binding or pinnable retrieval set. A mismatch is a rejected comparison plan,
not a persisted `rejected` row.

## Integration instruction

Under one consistent source transaction, read snapshot/build facts and the
candidate's source/windows with the same reviewed map identity. Compare using
independently checked digests. Only a later owned transaction may persist a
rejected row or perform the custody admissions, dispatch and verified-row
publication specified in W57 §A3.2.

## Ownership proof

Only the four new task-owned files were written. Existing retrieval modules,
`contracts/**`, migration head, norms repository, public boundary, root
dependencies, composition, global styles, corpus and `CURRENT_STATE.md` were
untouched. Stage only the four exact paths for integration.
