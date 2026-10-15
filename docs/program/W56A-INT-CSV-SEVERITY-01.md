# W56A-INT-CSV-SEVERITY-01 — CSV severity projection

## Result

The CSV keeps OD-11's first seventeen columns and appends `severity` (the
current expert decision) and `severity_proposed` (the exported canonical
observation). When `finding.canonical_observation_id` is set, member evidence
does not create extra CSV rows. A NULL canonical identity keeps the legacy
pre-merge export behavior; the v2 publisher must set canonical identity in its
own transaction. Empty optional severity values serialize as empty cells.
The frontend's declared column list matches the server.

## Checks

- Focused no-DB CSV pins and serializer: **5 passed**.
- Python compilation and direct task governance: passed (`[]`).
- `git diff --check`: passed.
- The DB integration test for canonical row filtering and accept→reject
  severity changes was added but **could not run**: this worktree has no
  `DATABASE_URL`; the integration harness fails setup rather than skips.
- Full `make gate` deferred under R-135.

## Contracts and limits

No API/domain/analysis contract, migration, provider lock, root dependency or
composition root changed. The two appended columns implement W56 §A3.2's
amendment to OD-11; the first seventeen and byte format stay fixed. The
query still excludes ungrounded observations through its inner joins.
The proposed value remains model output and is never substituted for the
expert's value. This task does not activate AR v2 or prove a DB migration
upgrade; the DB test must be run when an isolated PostgreSQL is available.

## Integration instruction

Run `tests/integration/exports/test_v2_csv_severity.py` on an isolated
migrated PostgreSQL with `DATABASE_URL`, then integrate with the ledger's
decided-severity change. The later AR v2 publisher must assign
`finding.canonical_observation_id` before the run is exportable; otherwise
the explicit legacy path remains active.

## Ownership proof

Only the paths in this task's `Allowed paths` were changed. `contracts/**`,
migrations, decision ledger, finding query, bootstrap adapters, provider lock,
root dependency/lock files, composition root, global styles, stand and Git
refs were untouched by this task.
