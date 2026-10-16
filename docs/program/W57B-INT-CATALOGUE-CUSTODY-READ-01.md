# W57B-INT-CATALOGUE-CUSTODY-READ-01 — unserved catalogue custody result

## Result

`load_verified_catalogue` now returns exact bounded catalogue bytes and
`CatalogueExpectation` for one current Run/Attempt. Its read-only SQL pin
requires a verified retrieval set, the matching snapshot and document count,
exactly two confirmed custody bindings (set and catalogue), and available
Blobs whose metadata matches the set and admission declarations. The object
is fully read with expected size/SHA-256, independently hashed, then the
current Attempt and SQL pin are rechecked. No runtime caller was activated.

The returned bytes and facts can be passed to the existing pure
`load_pinned_catalogue` validator together with a separately reviewed
unparsed-slug tuple. This reader does not supply or approve that tuple.

## Changed files

- `src/auditmanager/norms/references/catalogue_input.py`
- `tests/integration/norms/references/test_catalogue_input.py`
- `docs/program/tasks/W57B-INT-CATALOGUE-CUSTODY-READ-01.md`
- `docs/program/W57B-INT-CATALOGUE-CUSTODY-READ-01.md`

## Verification

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_catalogue_input.py tests/integration/norms/references/test_catalogue_query.py` — **31 passed**. A canonical catalogue built from `CatalogueDocument` passes the existing byte validator after the reader; offline refusals cover absent/duplicate/terminal pins, incomplete binding or document counts, invalid caps, short/long/corrupt objects, missing object, changed pin and stale Attempt. Fake Session, JobRepository and BlobStore ports prove the control flow and byte checking only.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program/test_wave_governance.py` — **16 passed**, with five concurrent `/tmp/pytest-of-root` cleanup warnings.
- `python3 -m py_compile src/auditmanager/norms/references/catalogue_input.py tests/integration/norms/references/test_catalogue_input.py` — **PASS**.
- Frozen API, stage, domain IDs, errors, migration 0023 and catalogue-query SHA-256 values match the task. `git diff --check` — **PASS**.

## Integration and limits

Integrate only this four-file additive commit after dev55. A future authorized
W57b caller must supply a consistent short transaction, current
`AttemptAuthority` and public `BlobStore`, then pass `.data` and `.expectation`
to `load_pinned_catalogue`. It must independently choose a reviewed
`listed_unparsed_slugs` tuple, authorize the requested use and recheck
authority before publication. The reader itself has no route, effect or
canonical expert decision.

These fake-port tests do **not** prove that the SQL runs against real 0023
PostgreSQL, that Blob bytes exist in S3, or that the W54 source is a qualified
published corpus. Real DB/S3 acceptance remains for an isolated integration
lane. W57b 0024 and B3.5 remain open. No PostgreSQL, S3, Docker,
LibreOffice, full gate or remote publication was run here.

No contract, migration, existing pipeline/query/public module, root
dependency, composition root, API or global style was changed. The four
changed paths exactly match the task grant. Rollback is a revert of the
additive commit; there is no data rollback or runtime flag.
