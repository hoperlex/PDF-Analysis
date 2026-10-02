# W48-GUARDS — completion report

## Result

**DONE.** D-87, D-114 and D-116 now have executable failures. The accepted migration head is
inventoried only after applying the current migration bytes to an empty disposable PostgreSQL
database; dashboard fixtures use pairwise-distinct values; and the invalidation guard reads the
TypeScript syntax tree, where comments and string literals are not executable calls.

## Changed files

- `tests/integration/db/test_schema_invariant_inventory.py` — complete fresh-database inventory;
- `tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py` — distinct
  section, verdict and run-state counts;
- `web/tests/guards/dashboard-invalidation.guard.test.ts` — syntax-aware invalidation proof and
  comment mutations;
- `web/tests/unit/widgets/dashboard.test.ts` — distinct browser fixture and keyed assertions;
- `docs/program/W48-GUARDS.md` — this report.

## D-87 — fresh-migration invariant inventory

The inventory covers every schema-bearing family visible after a migration from empty state:

| family | members | observed from the fresh database |
| --- | ---: | --- |
| columns, types, bounds, collation, nullability, defaults and generation | 256 | `information_schema.columns` |
| tables, views, sequences, persistence and RLS flags | 32 | `pg_class` |
| primary/foreign/unique/check constraints | 261 | `pg_constraint` definitions |
| indexes and predicates/options | 57 | `pg_indexes` definitions |
| non-internal triggers, enabled state and event arms | 22 | `pg_trigger` definitions |
| repository-owned database functions | 6 | `pg_get_functiondef` |
| views | 1 | `pg_get_viewdef` |
| non-built-in extension/version | 1 | `pg_extension` |
| identity sequence parameters | 6 | `pg_sequence` |
| row-level security policies | 0 | `pg_policies` (the accepted head has none) |
| declared state-machine edges | 24 | `contract_state_transition` rows |

Each family pins both the member count and a SHA-256 over its sorted normalised definitions. A
separate assertion rejects `CHECK (true)` and `CHECK ((true))` explicitly. This complements the
existing behavioural DB suite: it catches an unexercised catalog change, while the existing tests
continue to prove important consequences and SQLSTATEs.

The following are explicitly non-schema invariants and are not hidden behind the inventory:

- repository query and aggregation meaning — composition/repository tests;
- API vocabulary and identity allocation — contract/boundary tests;
- object bytes, S3 addresses and bucket policy — storage integration tests;
- the random salt/digest of the bootstrap credential — behavioural migration tests.

Full-tree scratch mutations were freshly migrated and produced the expected red result:

- nullable embedding vector: `columns` digest changed;
- unexpected RLS enablement: `relations` digest changed;
- unit-norm `CHECK` replaced by `CHECK (true)`: `constraints` digest changed and the explicit
  tautology test failed;
- HNSW `m` weakened from 16 to 8: `indexes` digest changed;
- immutable trigger lost its UPDATE arm: `triggers` digest changed;
- append-only SQLSTATE changed: `functions` digest changed;
- latest-verdict ordering changed from descending to ascending: `views` digest changed;
- queued→failed changed to queued→published: `state_topology` digest changed;
- pgvector pin changed from 0.8.6 to 0.8.5: a fresh migration failed before the inventory could
  run, which is also a hard red result rather than evidence from an old database.
- identity sequence start changed from 1 to 100: `sequences` digest changed;
- an unexpected permissive policy was added: the accepted zero-member `policies` family changed.

The scratch tree was removed after the mutations. Every database was allocated a unique random
name by the fixture and dropped after its case.

## D-114 — row swaps are visible

The backend fresh-deployment fixture now seeds section counts 1–15, reachable verdict counts
1/2/3 with the unproducible `needs_manual_review` at 0, and run-state counts 1–8. The browser
fixture uses distinct 1–15, 16–19 and 31–38 ranges. Both sides assert exact values by row key and
assert pairwise distinctness before relying on them.

Scratch production mutations all failed the exact-count test:

- backend AR↔KM: observed 3/1 instead of 1/3;
- backend pending↔rejected: observed 3/1 instead of 1/3;
- backend queued↔running: observed 3/2 instead of 2/3;
- browser AR↔KM: two failures, including `AR: expected 3 to be 1`;
- browser pending↔rejected: `pending: expected 18 to be 16`;
- browser queued↔running: `queued: expected 33 to be 32`.

## D-116 — comments are not code

The guard parses TypeScript with the already locked `typescript` dependency and inspects call,
import, declaration and re-export nodes. It still follows only the repository's documented one
helper level; it does not introduce a generic import-graph framework.

The real `create-project` invalidation was commented out in the scratch tree while its full text
remained in the comment: the guard failed 1/9. After restoration, adding
`// queryKeys.dashboard.summary()` to the non-invalidating export hook left the guard correctly
green at 9/9. Equivalent in-memory cases remain in the committed test.

## Checks

- `.venv/bin/python -m pytest tests/integration/db -q` against the isolated W48 lane —
  **186 passed in 158.50s**;
- `.venv/bin/python -m pytest
  tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py -q` —
  **4 passed in 5.55s**;
- `npm --prefix web test -- dashboard-invalidation.guard.test.ts dashboard.test.ts` —
  **26 passed**;
- `npm --prefix web run typecheck` — exit 0;
- `npm --prefix web run lint -- --quiet` — exit 0;
- mutation results — recorded above; every required red/green direction observed;
- `git diff --check` and allowed-path-only diff — exit 0 after this report.

## Contracts, migrations and runtime

No contract, migration, generated client, dependency/lock file, production backend/frontend,
composition root, workflow, deployment behaviour or global style changed. Migration head remains
`0013_norm_embeddings`; API remains 17 paths / 20 operations / 61 schemas; error catalog remains
22 entries.

## Risks and known limitations

- The inventory is intentionally a reviewed frozen-schema snapshot. A legitimate migration must
  review the changed family and deliberately reseal its digest; blindly replacing hashes would
  defeat it.
- The catalog inventory proves installed shape and catches source mutations only through a fresh
  migration. Behavioural tests remain necessary for semantic consequences.
- `needs_manual_review` remains an intentionally unproducible PC-01 verdict and therefore uses the
  distinct value 0; the migration and dashboard comments already document that product boundary.
- This task ran its required focused gates, not the Stage-A integration `make gate`; the integrator
  and `W48-JUDGE-A` own the merged-tree gate.

## Integrator handoff

Integrate this commit after `W48-PROSE`, run both focused suites plus the full gate on the merged
Stage-A SHA, then dispatch `W48-JUDGE-A`. No feature flag or data rollback applies: this task is
tests and documentation only, so rollback is a revert of its commit.

## Forbidden-hotspot proof

The committed diff is restricted to the five paths listed under “Changed files”, all explicitly
owned by `W48-GUARDS`. `contracts/**`, `db/migrations/**`, production sources, root dependency and
lock files, `Makefile`, composition, workflow, deployment, global styles, programme state/register,
Git refs/tags, host state and credentials are untouched.
