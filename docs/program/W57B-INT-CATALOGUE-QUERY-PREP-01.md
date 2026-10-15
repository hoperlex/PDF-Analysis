# W57B-INT-CATALOGUE-QUERY-PREP-01 — result

## Result

`catalogue_query.load_pinned_catalogue` accepts canonical W57a catalogue bytes
only against a caller-supplied expected SHA-256 and pinned snapshot identity,
content key, content digest and document count. It checks each document's
identity, stored SQL designation tokens, canonical order and a caller-supplied
reviewed list of unparsed slugs before returning `PinnedCatalogue`.

Migration head `0022` has no `norm_retrieval_set` table or `norm_catalogue`
custody role. The adapter therefore makes no DB query or verified-custody
claim. A future runtime reader must independently prove that expected facts
come from the run-pinned verified set and qualified snapshot, and that blob
bytes came through the confirmed catalogue binding. The local 57-slug
candidate remains unreviewed and cannot be passed as a runtime allowlist.

## Verification

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_catalogue_query.py tests/integration/norms/references/test_reference_resolution.py`: 34 passed.
- `compileall` of both new Python files: passed.
- Task governance, whitespace and exact owned-path check: passed.
- PostgreSQL/custody and full `make gate`: deferred; no schema or runtime path exists for this adapter under `0022`, and R-135 defers the complete gate.

## Changed files

- `src/auditmanager/norms/references/catalogue_query.py`
- `tests/integration/norms/references/test_catalogue_query.py`
- `docs/program/tasks/W57B-INT-CATALOGUE-QUERY-PREP-01.md`
- `docs/program/W57B-INT-CATALOGUE-QUERY-PREP-01.md`

## Contracts, risks and integration

No frozen contract, migration or public API changed. `CatalogueExpectation`
is an internal input contract; it does not itself certify the trustworthiness
of caller-provided facts. Once `0023` exists, the integrator should add a
database/custody reader in an owned task, supply only independently verified
facts to this adapter and test the real transaction and blob path. Revert this
additive file if that reader chooses a different serialization; no data change
needs rollback. Forbidden hotspots were not touched by this lane.
