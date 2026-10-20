# GATE-FIX-DB-01 — repair the database-suite reds before the complete gate

**Base:** `7bdb254e` (`origin/dev` = the night candidate `8697baea` plus the three frozen
pre-gate task files; `db/` is byte-identical between the two). Branch `agent/gate-fix-db-01`,
isolated worktree `gate-fix-db`, lane PostgreSQL 17.11 on 57620, MinIO 61220/61221, database
`auditmanager_gate_fix_db`. **Status:** complete. Development candidate under `R-135`: no
push, no merge into another branch, no tag.

## Result

`tests/integration/db` on the lane's own containers:

| | command | outcome |
|---|---|---|
| before | `pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/db` | **24 failed, 491 passed** in 330.6 s |
| after  | the same command on the repaired tree (commit `61d955d2`, clean, nothing edited during the run) | **526 passed** in 366.2 s |

526 = 491 + the 24 repaired + 11 new tests. The suite ran with `PYTHONPATH=src` and the lane's
`DATABASE_URL`; the tree was not edited while either run measured it.

## The 24 reds, their cause and the decision

### Twenty-three: one defect in `0022_findings_v2.downgrade()` (real product defect)

Every one of them downgrades a database from the head to a revision at or below `0021`, and so
passes through `0022`. `0022.upgrade()` appends `decided_severity` to `finding_current_verdict`
with `CREATE OR REPLACE VIEW`, which PostgreSQL allows for a trailing column. Its
`downgrade()` rebuilt the view with the same helper and **one column fewer**, which
`CREATE OR REPLACE VIEW` never allows: `cannot drop columns from view`
(`sqlalche.me/e/20/f405`). The `0022` downgrade therefore failed on every database that did
not hold findings (a database that holds them is refused first, by design), and nothing in
the suite exercised the `0022` downgrade on its own: the only `0022` downgrade test is the
refusal with retained data.

The tests whose subject is an *earlier* revision's refusal (`0015`, `0020`, `0021`, `0012`)
failed on the wrong message: the chain died at `0022` before reaching the refusal they assert.

| file | tests |
|---|---|
| `test_accounts_migration.py` | `TestTheDowngrade`: `test_it_refuses_while_anything_the_0014_shape_cannot_hold_exists[a-name]`, `[an-email-login]`, `[a-request]`, `test_it_refuses_while_the_backfill_is_there`, `test_on_an_empty_tree_it_runs_and_upgrades_back` |
| `test_app_user_migration.py` | `TestTheDowngradeRefusesToDeleteTheOnlyCopy`: `test_it_drops_the_table_when_only_the_untouched_seed_is_there`, `test_it_refuses_when_a_real_account_would_be_lost` |
| `test_downgrade_never_loses_a_measurement.py` | `test_a_database_with_no_measurements_still_downgrades`, `test_a_measured_call_makes_the_downgrade_refuse` |
| `test_durable_analysis_effects.py` | `test_empty_0014_downgrades_to_0013_and_upgrades_back`, `test_occupied_0014_downgrade_refuses_without_moving_the_head` |
| `test_execution_queue_migration.py` | `test_empty_0017_downgrades_and_restores_old_frozen_guard` |
| `test_execution_workers_migration.py` | `test_an_empty_0019_downgrades_and_restores_the_lease_guard` |
| `test_norm_embeddings_migration.py` | `test_downgrade_refuses_to_drop_a_complete_retained_build` |
| `test_norms_search_migration.py` | `test_an_empty_0020_downgrades_and_upgrades_again`, `test_a_retained_current_snapshot_and_history_refuse_the_downgrade` |
| `test_portal_bundles_migration.py` | `test_an_empty_0021_downgrades_to_the_old_ceiling_and_upgrades_again`, `test_a_retained_count_alone_refuses_the_downgrade`, `test_a_retained_large_version_or_count_refuses_the_downgrade` |
| `test_release_notes_migration.py` | `test_downgrade_is_only_allowed_before_release_history_exists` |
| `test_reviewer_display_name.py` | `TestTheRollback`: `test_it_downgrades_and_upgrades_again`, `test_the_downgrade_names_the_accounts_whose_names_it_destroys` |
| `test_run_terminal_detail_schema.py` | `TestTheRollback`: `test_it_downgrades_and_upgrades_again` |

**Decision: fix the code**, in the downgrade only. `0022` is not on `origin/main`
(`git cat-file -e origin/main:db/migrations/versions/20261015_0022_findings_v2.py` fails), so
its downgrade may be edited; its upgrade SQL is untouched. The new helper
`_downgrade_verdict_view()`:

1. reads the view's comment from the catalog (`obj_description`, formatted with `%L` by the
   server) — `DROP VIEW` discards it, and the comment (`0002`'s) is part of the projection's
   contract;
2. `DROP VIEW finding_current_verdict` **without `CASCADE`**: a reader that came to depend on
   the view stops the downgrade instead of being dropped with it;
3. creates the view again with the unchanged upgrade helper `_current_verdict_view(with_severity=False)`
   (the nine `0021` columns, same text as `0002`);
4. sets the comment again (colons escaped so a `:name` inside it is not read as a bind
   parameter).

The helper is named `_downgrade_*` so the upgrade-surface digest (below) ignores it.

### One: `test_norms_corpus_migration` (stale pin)

`test_the_migration_creates_the_canonical_and_rebuildable_topology` pins the set of tables whose
name starts with `norm`. `norm_retrieval_set` is a real table created by
`0023_norm_citations` (W57a; the verified retrieval set a Run pins) and is already listed by
`test_migration_lifecycle.EXPECTED_TABLES` and counted in
`test_schema_invariant_inventory` (relations 63). Nothing about the migration is wrong; the pin
was never updated when `0023` arrived. **Decision: fix the test**, adding the table with its
migration named, as the other entries do. No guard was weakened: the assertion is still exact
set equality.

## Later migrations: no further defect

The task asks that any later migration whose downgrade breaks the chain be repaired too. None
does. `0023`…`0027` downgrade in sequence and each step restores the exact schema it left (proof
below). Their upgrade and downgrade text is unchanged.

## Proof

### (a) head → `0021` → head on a database that holds rows

`tests/integration/db/test_downgrade_chain_round_trip.py::test_every_step_down_restores_the_schema_and_head_upgrades_again`:

1. upgrade an empty database to `0021`; write a project, a document, a version, a run and a
   command record (tables no downgrade may touch);
2. upgrade one revision at a time to head, taking a catalog inventory after each and checking
   the five released row counts are unchanged;
3. at head, write rows in tables the chain drops by design: a version classification (`0024`),
   a work assignment with its `assigned` event (`0025`);
4. downgrade **one revision at a time** back to `0021`; after each step the inventory equals the
   one taken on the way up at that revision, the released rows are still there, and
   `0025`'s "exist nowhere else and are dropped" warning is emitted;
5. upgrade to head again; the inventory equals both the one from the way up and a database
   upgraded straight to head by the literal `make migrate` command; the dropped tables are empty.

The refusal with retained findings is untouched and still green
(`test_findings_v2_migration.py::test_populated_0021_backfills_the_sole_observation_and_refuses_downgrade`).

### (b) the upgrade SQL of every touched migration is byte-identical to `origin/dev`

`test_the_upgrade_surface_of_every_touched_migration_is_the_one_on_origin_dev` (six
parametrisations, `0022`…`0027`) pins a sha256 of each file's *upgrade surface*: the exact lines
of every top-level statement (imports, constants, helpers, `upgrade()`) except the module
docstring, `downgrade()` and the `_downgrade_*` helpers. The digests were computed from
`git show 7bdb254e:<path>`:

| migration | upgrade-surface sha256 |
|---|---|
| `0022_findings_v2` | `cf8b4f7c66c5663ddd0ccb54cea24fa6a3dc4d00cc03a4a5ab72739e969de493` |
| `0023_norm_citations` | `00a125b1e2f235aec9a42dc85a16e7d1d9da4f80bb8844c25a55369a20b7c3c6` |
| `0024_version_classification` | `2887367bcaa5546cb0e7cd92d46a5f419f37b9c333a6cf98d256c25955286c3a` |
| `0025_work_assignments` | `7061fccf5c5dafa35d911ab9b913c39050bfaa8d0505833541c2724ce919d0e3` |
| `0026_price_lists` | `6b21a92cb743436230093aee86bd826699207cabaa331deae4102f312a6fae6d` |
| `0027_optimisation_proposals` | `5cbe94b32de47e8d62c3639680096027ff049adac5fd31618d6b5a644042e93f` |

`git diff 7bdb254e -- db/` removes exactly one line, `_current_verdict_view(with_severity=False)`
inside `downgrade()`; nothing inside `upgrade()` or the code it calls moves. Only `0022` is
edited; `0023`…`0027` are byte-for-byte the base.

### (c) the schema after the round trip equals the schema after a straight upgrade

The same test compares the head inventory of the round-tripped database with a clone of the
suite's template (a straight `alembic upgrade head`). The inventory is the catalog families of
`test_schema_invariant_inventory.py` (columns, relations, constraints with validation state,
indexes, triggers, functions, views, sequences, extensions, state topology) plus user types,
comments on relations, columns, functions and constraints, relation ACLs and owners, and the
stamped revision, compared **row by row**, so a failure names the object.

One deliberate difference from the digest helper in that file: a column's position is its
rank among the table's live columns, not `ordinal_position` (`attnum`). Dropping and re-adding
a column keeps the table identical for every reader but moves the dropped column's `attnum`
for ever, so comparing `ordinal_position` after any column downgrade can never be equal and
would assert something no downgrade can satisfy.

### Mutation probes (each guard shown failing)

| mutation, applied to the repaired tree and then undone | result |
|---|---|
| revert `0022` to the base bytes (the original defect) | the chain test and the view test fail on `cannot drop columns from view`; the other nine pass |
| drop the comment re-set in `_downgrade_verdict_view` | chain test fails: `missing comments: ('relation', 'finding_current_verdict', '', 'The PD-01 projection, …')` |
| recreate the view with `with_severity=True` | chain test fails: `cannot drop column severity of table expert_decision_event because other objects depend on it` |
| `0027.downgrade()` stops dropping `am_check_optimisation_pass_scope()` | chain test fails: `surplus functions: ('am_check_optimisation_pass_scope', …)` |
| remove the colon escape on the restored comment | `test_the_0022_downgrade_returns_the_nine_columns_and_keeps_the_views_comment` fails |
| change `_SEVERITIES` in `0022` (an upgrade constant) | the `0022` upgrade-surface parametrisation fails |

Two further tests prove the guards themselves can fail without touching a migration:
`test_the_upgrade_surface_digest_can_fail` (a downgrade-only change leaves the digest alone,
four kinds of upgrade change move it) and `test_the_inventory_can_fail` (a dropped column and a
changed view comment both show in the difference).

## Files changed

- `db/migrations/versions/20261015_0022_findings_v2.py` — `downgrade()` only (new
  `_downgrade_verdict_view()`, one call site);
- `tests/integration/db/test_norms_corpus_migration.py` — the stale table pin;
- `tests/integration/db/test_downgrade_chain_round_trip.py` — new, 11 tests;
- `docs/program/GATE-FIX-DB-01.md` — this report.

## Contracts

None changed: no `contracts/**`, no migration head (`0027_optimisation_proposals`), no schema
(the schema after the walk is identical), no API count (71 / 81 / 235 untouched).

## Risks and known limitations

- The walk test seeds rows in `0024` and `0025` tables. `0026`/`0027` tables are empty during
  the walk; their populated single-step downgrades remain covered by their own tests
  (`test_the_downgrade_drops_only_this_revision_and_the_head_upgrades_again`).
- The `0022` downgrade still refuses when any finding, observation, decision event or v2 error
  code exists. That is its designed guard and is unchanged; a downgrade of a database that
  holds findings is not a supported path.
- `DROP VIEW` without `CASCADE` makes the `0022` downgrade fail loudly if a future migration
  adds an object that depends on `finding_current_verdict` before `0022` is reached on the way
  down. That migration's own downgrade must drop its dependent first, which is the correct
  order; the walk test would show it.
- The walk test follows `revision_walk()` from `0021` to the head, so a future revision joins
  the chain automatically. The upgrade-surface digests cover `0022`…`0027` only.
- The inventory test uses its own copy of the catalog queries rather than importing
  `test_schema_invariant_inventory._inventory` (suite directories carry no `__init__.py`, and
  the repository forbids `sys.path` workarounds), and it differs from it on purpose in the
  column position and the extra families above.

## Instructions for the integrator

1. Merge `agent/gate-fix-db-01` (a real merge) into `integration/night-1020`.
2. On the merged tree run `tests/integration/db` on a lane stack; expect 526 passed (or 526 +
   whatever the merged tree adds). The three named checks are
   `tests/integration/db/test_downgrade_chain_round_trip.py`,
   `tests/integration/db/test_norms_corpus_migration.py` and the twenty-three tests above.
3. No reseal is needed: the schema, `EXPECTED_INVENTORY` and the migration head are unchanged.
4. This lane touches `db/migrations/**` and so belongs to the complete-gate case of §8; under
   `R-135` that gate is the separate integration task, not this lane.

## Forbidden hotspots

`git diff --name-only 7bdb254e` lists exactly the four paths above. `0001`…`0021`, `0023`…`0027`,
`contracts/**`, `src/**`, `web/**`, dependency and lock files, `CURRENT_STATE.md`, refs, tags
and the stand are untouched; all four paths are in the task's `allowed_paths`.
