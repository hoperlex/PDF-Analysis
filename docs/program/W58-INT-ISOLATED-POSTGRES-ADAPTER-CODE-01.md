# W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01 — guarded PostgreSQL callback

**Base:** published `origin/dev=3d131d2966e0efeea7b53d9662785f253165a9a4`.
**Status:** unactivated operator code; no PostgreSQL or S3 service drill.

## Result

`restore_isolated_postgres` implements the callback consumed by the W58
DB-plus-Blob coordinator. It accepts the Engine made by the owned application
factory, an explicit disposable PostgreSQL target and a private `db.dump`.
The target must be numeric loopback, use a nondefault port and have an
`auditmanager_w58_*` database name. The Engine URL must use
`postgresql+psycopg`, have no query override and match the CLI target;
`current_database()`, `current_user` and PostgreSQL major 17 are checked
through SQL. The adapter refuses any preexisting user relation before it
invokes `pg_restore` with `--exit-on-error --single-transaction`.

The dump is opened without following a symlink and must be an owned private
regular file. It is passed as stdin, so its path and credentials are not
placed in process arguments. The CLI receives only explicit `PGHOST`,
`PGPORT`, `PGDATABASE`, `PGUSER` and a checked optional `PGPASSFILE`; inherited
`PG*` variables do not redirect it. The adapter extracts the exact
`stand-fingerprint-v1` SQL block from `infra/deploy/copy-serve.sh`, checks its
frozen SHA-256, runs it through `psql`, validates ordered table lines and
computes the digest expected by W54. It yields `RestoredDatabase` with a
repeatable-read, read-only Session and rolls the transaction back on exit.

An operator can pass `functools.partial(restore_isolated_postgres,
engine=engine, target=target)` as the coordinator's `restore_database` callback.
The coordinator compares its fingerprint digest to the frozen copy record
before any target-object write.

## Checks

- **24 targeted container-free tests passed.** They use fake Engine,
  connection, Session and process runner. Cases cover target/Engine mismatch,
  hidden URL redirect, nonempty DB, unsafe dump/passfile, restore failure or
  timeout, changed dump, wrong fingerprint source/output, wrong PostgreSQL
  version, and failure to establish read-only repeatable-read mode.
- Task parser/governance findings: **none**. Python compile and
  `git diff --check`: passed.
- The broader recovery suite and full gate were not run while the W55b full
  gate owned the host resource lane. No Docker, PostgreSQL, S3, source stand,
  network or remote ref was touched in this task.

## Limits and integration

The tests establish argument and refusal behavior only. A loopback port can
still be a tunnel to another host, and the empty-target check is not atomic
with an external writer. The operator must prove isolation and exclusive
ownership of the disposable target, keep the private copy fixed, provide a
matching Blob bucket and run a real service drill before any W58/B6 claim.
This task does not create or destroy a database. A failed attempt must be
investigated; retry uses a newly empty target. The existing coordinator
still performs the copy SHA-256 preflight and post-restore recheck.

No API/domain/stage contract, migration, dependency, composition root or
served behavior changed. The only input contract added is the offline W58
adapter function and target value object. Its runtime use remains disabled
until an isolated operator lane is scheduled.

## Containment and rollback

Exactly four task-owned files changed:

- `scripts/recovery/isolated_postgres_restore.py`
- `tests/integration/recovery/test_isolated_postgres_restore.py`
- `docs/program/tasks/W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01.md`
- `docs/program/W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01.md`

No forbidden hotspot was edited. Revert those four files to remove the
unactivated adapter. The integrator may cherry-pick its exact commit, run
the deferred broader recovery checks after the W55b resource lane releases,
then schedule separate PostgreSQL/MinIO acceptance.
