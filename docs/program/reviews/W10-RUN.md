# `W10-RUN` — mutation sweep of `runs/`, `ingest/` and the migrations

Session `W10-RUN`, wave 10. Worktree `/root/w10run`, branch `agent/w10-run`,
instance `gate-w10d`.

## Provisioning

- **HEAD on arrival: `e08da85`** ("docs: the wave 10 dispatch — five parallel sweeps of
  the rule surface"), branch `agent/w10-run`, tree clean. The brief names base `fb30e96`;
  `e08da85` is one commit *later* on the same line (`fb30e96` is its parent), so the base
  premise holds with that correction.
- Worktree was already bootstrapped by the killed first attempt: `.venv/` present,
  `web/node_modules/` present, `.env` present and carrying exactly instance `gate-w10d`
  (`POSTGRES_PORT=55620`, `S3_API_PORT=59220`, `S3_CONSOLE_PORT=59221`,
  `POSTGRES_DB=audit_w10d`, `S3_BUCKET=auditmanager-gate-w10d`).

## Sweep table

_(appended as batches complete)_

### Harness

- Mutations applied to `/root/w10mut/src` (a copy of `src/`), with `contracts/`, `docs/`,
  `fixtures/` **and `db/`** symlinked in. `db/` is needed as well as the three the brief
  names: `auditmanager.shared.db.check` resolves `db/migrations/alembic.ini` from its own
  module's parents, so without it three `tests/integration/db` tests fail on
  `MigrationStateError` before reaching an assertion. **First correction to the brief.**
- Every run goes through `-o "pythonpath=/root/w10mut/src /root/w10mut" -p proveimport`.
  `proveimport` is a pytest plugin that imports `auditmanager` in `pytest_configure`,
  prints `auditmanager.__file__`, and `SystemExit`s the session unless the path starts
  with `/root/w10mut/src/`. Every result below carries that line in its log.
- Every mutation is diffed against the pristine file and the diff printed before the run;
  a mutation that produced no diff aborts as `!!! NO-OP MUTATION !!!` rather than running.
  That is the wave-10 `frozenset() or frozenset({...})` mistake, made impossible.
- Baselines through the copy: `tests/integration/runs tests/integration/ingest` = 123
  passed (35 s); `tests/integration/db` = 95 passed (59 s).

### Batch 1 — `src/auditmanager/ingest/reconciliation.py` (swept by nobody before this)

| # | rule mutated | mutation | `runs`+`ingest` | `api`+`e2e`+`composition`+`p02_journey`+`storage` | verdict |
|---|---|---|---|---|---|
| M1 | `verify_version`: a manifest entry whose bytes are present but whose **checksum or size disagrees** with the store is `storage_integrity_error` | `if published.sha256 != entry.sha256 or published.size != entry.size_bytes:` → `if False:` | 123 passed | no new failure | **UNREDDENED** |
| M2 | `report`: an `available` blob that **no manifest references** is an orphan (`_AVAILABLE_WITHOUT_MANIFEST`) | `WHERE b.state = 'available'` → `WHERE false AND b.state = 'available'` | 123 passed | no new failure | **UNREDDENED** |
| M4 | `_object_exists`: an **unreachable store** must raise, never be reported as "the object is gone" | `raise domain_error_from_storage(exc)` → `return False` | 123 passed | no new failure | **UNREDDENED** |
| M5 | `report`'s default `stale_command_age="1 hour"` | → `"9999 hours"` | 123 passed | not run | **UNREDDENED** (every call site in the suite passes the argument explicitly) |

The second-pass selection has four **pre-existing** failures in
`tests/integration/p02_journey/test_truncated_end_to_end.py` that are present in an
unmutated control run of the same selection and absent from `make gate`. They count rows
over the real `model_call` table and so depend on a lane database that the battery's own
ordering leaves in a particular state. Not caused by any mutation here, and not my tree.
