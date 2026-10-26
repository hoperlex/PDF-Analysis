# PROD-04-DB-ROLES-01 — api and worker connect as an application role; one idempotent step gives it its rights after every migrate and every restore

Task: `docs/program/tasks/PROD-04-DB-ROLES-01.md`. Branch `agent/prod-04-db-roles-01`, base `cfbae64a` (`integration/ar-close-1026`), lane of wave `PW3`. Rulings: `R-146n` item 1, `R-146w` (`AD-02` as written at `83600aed`), `R-93`, `R-52`; `ADR-0021` section 3 and row 7; register rows `D-166`, `D-213`, `D-216` (read; none is changed here).

**Status.** Built and verified in the tree against the lane's real PostgreSQL 17.11 (private databases only) and stubbed `docker`; **no docker command was run, nothing was run against a host or a real compose project**. The first real run of `docker compose run migrate` + `apply-grants.sh` on the VPS, and the cutover of its `alpha.env`, are the owner's (runbook section 16). **No migration was added; the head stays at `0033_ar_v3_cite_stage_id`.** `src/**`, `contracts/**`, `db/migrations/**`, the web and `.github/**` are untouched.

## 1. What was built, and what the lane decided

| piece | what it is |
|---|---|
| `scripts/recovery/grant_classification.py` | **the classification**, built on `schema_coverage` (its `TABLES`, `VIEWS`, `SEQUENCES`, `TRIGGERS`, `GUARD_FUNCTIONS` are the universe; no second list of the schema). Four disjoint sets partition the 64 tables: 25 read-write, 36 append-only, 3 read-only, 0 none; two lock-only exceptions; two callable helper functions; 30 trigger functions derived. Also: the evidence scan (`observed_statements`: every SQL string under `src/auditmanager`, `INSERT ... ON CONFLICT DO UPDATE` counted as an `UPDATE`, row locks resolved through aliases), the SQL generator for `apply` and `check`, the catalogue audit (`audit_grant_classification`) and a CLI (`--print`, `--verify-script`, `--write-script`) |
| `infra/deploy/apply-grants.sh` | **the one step.** Creates the application role if absent and sets its attributes and password every run; `CONNECT` on the database, `USAGE` (no `CREATE`) on `public`; revokes everything it holds, then grants exactly the classification (tables, column-level `UPDATE` on the key of the two lock-only tables, `USAGE` on the sequences of insertable tables, `EXECUTE` on the two helpers); revokes any role membership; refuses (`[grants_unclassified]`) any relation it has no row for before granting anything; then verifies what it applied (`grants-ok: ...`). `--check` verifies only; `--config-only` judges the settings; `--compose-file` is for the copy key's installed-apart copy. Ten guards. The SQL is embedded between generated markers and a test fails when it is stale |
| `compose.server.yml`, `alpha.env.example` | `DATABASE_URL` (application) reaches `api` and `worker`; the new `MIGRATOR_DATABASE_URL` (owner) reaches `migrate` and `release-notes` only. New names `ALPHA_APP_DB_USER` and `ALPHA_APP_DB_PASSWORD`; the example ships the password **with no value** and the application url with a placeholder, never a password |
| `deploy.sh` | five guards: `grants-script-present`, `app-db-role-configured` (before the build; it asks `apply-grants.sh --config-only`) and `owner-migrated`, `release-notes-loaded`, `grants-applied` (before `up`). The order is now build, owner `migrate`, owner `release-notes`, the step, `up`. `derived-secrets-coherent` reads the owner's url as `MIGRATOR_DATABASE_URL` |
| `reset.sh` | two guards (script present, roles configured) before either destructive mode changes anything; the wipe and `--restore` end with the step, after the migrations and before the worker; exit 4 (wipe) and 6 (restore) when it fails |
| `copy-serve.sh` | `restore-db`: `grants-script-present` and `app-db-role-configured` before anything is stopped, `grants-applied` right after `pg_restore` (a refusal with the writers stopped and the record open); `status` prints `grants: <digest>` |
| `purge-product-data.sh` | guard `migrator-url-configured`; both helpers run the python half with `DATABASE_URL="$MIGRATOR_URL"` in the environment of the `docker compose` process (no url on a command line; an ambient `DATABASE_URL` is overridden) |
| `readiness.sh` | check `db-roles` (eight checks now): which role each running service connects as (user only), the `ADR-0021` row 7 query (`f|f|f|t`), and `apply-grants.sh --check` |
| `tests/integration/db/application_role_plugin.py` | a pytest plugin (opt-in: `AM_TEST_AS_APPLICATION_ROLE=1`) that runs a suite as the application role; it is how access, releases, dispatch, optimisation, documents, norms and the AR v3 group suites were run as the role (section 6) |
| runbook section 16 (and 2, 3, 13) | the procedure with the expected output of each step, when the step runs, the words a refusal carries, and what this does not do |

**Decided by the lane** (the window asked for no questions; each is small and reversible):

1. **The migrator stays the bootstrap superuser (P-02).** The image's `POSTGRES_USER` is a superuser, and a plain owner role cannot do the job: migration `0013` runs `CREATE EXTENSION vector` and the pgvector of this stack is `superuser = t, trusted = f`. `test_a_plain_owner_cannot_migrate_a_fresh_database` pins the premise (it creates a plain owner of a fresh database and watches `CREATE EXTENSION` fail); if it ever goes red the decision is open again. What contains the superuser: its url reaches no always-on service (`test_the_application_gets_its_url_and_only_the_one_shots_get_the_owners`).
2. **Fail closed, no `ALTER DEFAULT PRIVILEGES`.** `ADR-0021` section 3 lists default privileges "for later tables"; the lane did not follow that sentence: a table a later migration creates gets **no** rights until classified, the step refuses it by name before anything is granted, and `test_grant_classification.py` is red from the migration on. That is the discipline the task asked for ("a new migration that adds a table without a classification turns the test red"), and default privileges would make the new table silently read-write.
3. **Append-only is what the schema declares, plus the code's evidence.** A table with a guard trigger that refuses `UPDATE` (`am_immutable_row`, `am_append_only`, `am_guard_release_append_only`, `am_norm_chunk_no_update`) is append-only unless the code needs more (nothing does); `project` has no trigger but the code only inserts, so it is the one entry of `APPEND_ONLY_BY_CODE_EVIDENCE`. A table the code upserts into (`account_release_mark`, `execution_control`, `stage_result`, `analysis_artifact_publication`) is read-write. Three tables the code never writes are read-only: `alembic_version` (only the migrator moves the head), `contract_state_transition`, `norm_embedding_profile`. **Only two tables are ever deleted from by the code** (`app_user` of an archived account, `app_user_role` on revoke); read-write still includes `DELETE` for the others because the ADR says so and the schema does not forbid it.
4. **Two exceptions, each with its reason.** `work_assignment` and `document_version_classification` are append-only but the code takes a row lock on them (`SELECT ... FOR UPDATE`, `FOR NO KEY UPDATE`), which PostgreSQL allows only with an `UPDATE` privilege on at least one column. The role gets `UPDATE` on the **first primary-key column only**; every other column is refused by privilege and the immutability trigger fires on a row update and not on a lock. Reasons are in `LOCK_ONLY_UPDATE` and the evidence test pins that nothing else needs it.
5. **The step is bash plus generated SQL, not Python.** The host is promised bash, docker, curl, sed and git (runbook section 1). The classification stays in Python (so it reuses `schema_coverage` and is testable), generates the SQL, and the SQL is embedded in the script; `script_drift` fails when they differ, and `--write-script` regenerates. One file to install beside `copy-serve.sh`.
6. **Explicit order in `deploy.sh` rather than a compose service.** Compose gives the script no point between `migrate` and `api`, and whether a one-shot `grants` service would re-run when only the schema changed depends on compose's recreate rules, which cannot be observed without docker. So `deploy.sh` runs `compose run --rm -T migrate`, `compose run --rm --no-deps -T release-notes` and the step before `up`; `up` may run both one-shots again (no-ops at the head). A failure leaves the running containers serving.
7. **The password never appears in a command line.** It is restricted to 20 to 128 characters of `A-Z a-z 0-9 . _ ~ -`, written as `\set app_password '...'` on `psql`'s standard input from a private temporary file (a file, not a pipe: a `docker` that exits before reading cannot hand the script a SIGPIPE), and a server message is filtered of any line that mentions it. The second password must differ from the owner's.
8. **The role is created by the step, with the password every run.** `ALTER ROLE ... PASSWORD` re-salts the stored verifier on every run; the idempotence test compares every ACL and attribute but not that verifier, and says why. Rotation is: change two lines, deploy.
9. **`reset.sh` exits 4 after a wipe and 6 after a restore** when the step failed: the schema is recreated or restored, the worker stays stopped, the message says the one command to run. `restore-db` refuses instead (its writers are still stopped, so nothing is exposed) and `resume` must not follow.
10. **A dry run asks nothing about the roles.** `reset.sh --dry-run` changes nothing and the guards skip it.
11. **`product_purge.py` is not edited.** The `owner-may-write` guard's message already names "the owning role (the one the migrations run as)".
12. **The harness plugin lives in `tests/integration/db/`** (allowed for the grant tests) so no existing conftest and no harness file outside the allowed paths was touched; it wraps the database layer's one engine factory and says in its summary how many engines ran as which role.

**Not decided by this copy of the lane, and observed:** a second copy of the lane wrote in the same worktree between about 23:33 and 23:55 (the integrator removed it at 00:43). It merged `integration/ar-close-1026` (tip `9a28f09f`, which contains `PROD-07a`) into this branch (`936518bc`, a clean merge) and left material in `scratchpad/p04/` (a 28-row mutation table, premise outputs, a run log); nothing of it conflicts with this lane, and what is correct in it is folded into sections 4 and 6 and into the task file (P-10 to P-12). `scripts/recovery/project_erase.py`, `test_project_erase*.py` and the one-line `KEEP_EVENT_PREFIXES` change in `product_purge.py` are therefore in `git diff cfbae64a..HEAD` but are not this lane's: the lane's own changes are `git diff 9a28f09f..HEAD` (section 2).

13. **Sequences get `USAGE` and no `SELECT`.** `src/` never reads sequence state (`currval`, `lastval`, `setval`, `last_value`: 0 matches) and `nextval` needs `USAGE` only. The one reader that wants `SELECT` on a sequence is `pg_dump` run **as the application role**, which two `executors` tests do (section 6); the dump tools run in the postgres container as the owner, so that is a harness choice and not a product path, and the role was not widened for it.

## 2. Files

`git diff --name-status 9a28f09f..HEAD` (the integration tip the merge brought in; every path is inside the task's allowed list):

```
M  docs/program/DEPLOYMENT_RUNBOOK.md                              sections 2, 3, 13 and the new 16
A  docs/program/tasks/PROD-04-DB-ROLES-01.md
A  docs/program/PROD-04-DB-ROLES-01.md
M  infra/deploy/README.md                                          two file-table rows
A  infra/deploy/apply-grants.sh
M  infra/deploy/compose.server.yml                                 two urls
M  infra/deploy/copy-serve.sh                                      restore-db: 3 guards; status
M  infra/deploy/deploy.sh                                          5 guards; the owner migrate/notes/step before up
M  infra/deploy/env/alpha.env.example                              ALPHA_APP_DB_*, MIGRATOR_DATABASE_URL
M  infra/deploy/purge-product-data.sh                              1 guard; the owner's url
M  infra/deploy/readiness.sh                                       db-roles
M  infra/deploy/reset.sh                                           2 guards; the step in both paths
A  scripts/recovery/grant_classification.py
A  tests/integration/composition/test_apply_grants_script.py
A  tests/integration/composition/test_db_roles_deploy_guards.py
A  tests/integration/db/application_role_plugin.py
A  tests/integration/db/test_application_role_grants.py
A  tests/integration/db/test_application_role_plugin.py
A  tests/integration/recovery/test_grant_classification.py
M  tests/integration/composition/test_acme_deploy_guards.py
M  tests/integration/composition/test_deploy_image_identity.py
M  tests/integration/composition/test_deploy_script_refusals.py
M  tests/integration/composition/test_proxy_config_follows_checkout.py
M  tests/integration/composition/test_purge_product_data_script.py
M  tests/integration/composition/test_readiness_command.py
M  tests/integration/composition/test_reset_script_refusals.py
M  tests/integration/composition/test_stand_copy_refusals.py
M  tests/integration/recovery/test_product_purge_script.py
```

## 3. Premise

Twelve reads, printed into the task file (P-01 to P-12) against `cfbae64a`. All present. The ones that changed the design: **P-02/P-03** (the bootstrap role is a superuser, pgvector is not trusted, `CREATE EXTENSION vector` is in `0013`: the migrator cannot be a plain owner), **P-05** (only two tables are deleted from; two append-only tables are row-locked; three are never written; upserts need `UPDATE`) and **P-07** (every dump is `--no-owner --no-privileges`; `restore-db` and the wipe recreate schema `public`, which also removes `USAGE` for everyone: the unqualified table name then answers "relation does not exist", measured in `test_the_copy_serve_restore_shape_...`). The plan's `0033_ar_v3_cite_stage_id` head is right (the PW2B text says `0032`).

## 4. Mutation tables

**Table 1 — this session's 13 mutations.** Each row: the mutation was applied to the committed file, the named tests were run `-x`, the first red test is the one named, and the file was restored (the helper asserts it; `git status` was clean after). Helper outside the repository (`scratchpad/mut.py`); the table is the record. SQL mutations are made in the generator and the script is regenerated, so the drift test is not what catches them.

| # | commitment, and the mutation that removes it | first red test |
|---|---|---|
| G1 | clean slate before granting: the `REVOKE ALL ON ALL TABLES` line removed | `test_the_step_repairs_whatever_was_changed_by_hand` |
| G2 | no `TRUNCATE`: `TRUNCATE` added to the read-write class | `test_the_application_role_cannot_truncate_any_table` (the classification is the mutated side of the privilege matrix, so only the independent test sees it) |
| G3 | the schema is never creatable through `PUBLIC`: `REVOKE CREATE ON SCHEMA public FROM PUBLIC` removed | `test_check_reports_each_kind_of_difference_and_the_step_repairs_it[CREATE on the schema through PUBLIC]` |
| G4 | the role is a member of nothing: the membership revoke removed | `...[a membership]` |
| G5 | sequences: `USAGE` becomes `SELECT` | `test_the_application_role_does_the_crud_the_contexts_do` (the step's own verification refuses first: the fixture errors) |
| G6 | the lock-only column grants skipped | `test_the_application_role_does_the_crud_the_contexts_do` (same) |
| G7 | an unclassified relation is refused: `IF unknown IS NOT NULL` becomes `IF false` | `test_a_migration_that_adds_a_table_is_refused_by_the_step_and_by_the_guard` |
| G8 | attributes reset every run: `NOSUPERUSER` dropped from the `ALTER ROLE` | `...[superuser]` |
| G9 | `USAGE` on the schema: the grant removed | `test_the_copy_serve_restore_shape_drop_schema_create_schema_then_restore` |
| G10 | an immutable table is never read-write: `audit_event` added to the read-write set | `test_the_declaration_is_consistent` |
| G11 | `EXECUTE` on the helper functions: the grant skipped | `...[a lost helper]` |
| G12 | the script carries the classification's SQL: `project` moved to read-write without regenerating | `test_the_script_embeds_the_sql_generated_from_the_classification` |
| G13 | append-only twice: the clean slate removed, so a privilege forced on `audit_event` survives | `test_a_second_wall_the_trigger_refuses_even_a_privilege_forced_on` |

**Table 2 — the second copy's 28 mutations** (`scratchpad/p04/MUT_TABLE.md`, run 23:4x to 23:52 against the same test files; each file mutated alone and reverted; the SQL rows regenerate the script). This session did not re-run them: the `Q` rows are database-backed and the integrator's 00:43 note stopped database-backed runs; it checked that every named test exists in the tree (28 of 28) and that the `C`, `A`, `D`, `R`, `S`, `P`, `K`, `Y` suites are green unmutated (section 6). Where they overlap table 1 they agree (`Q4` = `G3`, `Q5` = `G1`/`G13`, `Q6` = `G4`, `Q7` = `G7`, `Q9` = `G9`, `Q10` = `G11`, `Q13` = `G12`, `C2` = `G10`).

| # | file mutated | mutation | first red test |
|---|---|---|---|
| C1 | `scripts/recovery/grant_classification.py` | omit one table (project) from every class | `recovery/test_grant_classification.py::test_the_declaration_is_consistent` |
| C2 | `scripts/recovery/grant_classification.py` | mark an append-only table (audit_event) read-write | `recovery/test_grant_classification.py::test_the_declaration_is_consistent` |
| C3 | `scripts/recovery/grant_classification.py` | drop the lock exception of work_assignment | `recovery/test_grant_classification.py::test_the_repository_code_needs_nothing_the_classification_withholds` |
| C4 | `scripts/recovery/grant_classification.py` | drop the written evidence for the one append-only table no trigger guards (project) | `recovery/test_grant_classification.py::test_the_declaration_is_consistent` |
| Q1 | `grant_classification.py (SQL regenerated)` | grant TRUNCATE with every table's privileges | `db/test_application_role_grants.py::test_the_adr_row_7_query_prints_f_f_f_t` (fixture error: the step's own verification exits 4) |
| Q2 | `grant_classification.py (SQL regenerated)` | drop the sequence grant | `db/test_application_role_grants.py::test_the_adr_row_7_query_prints_f_f_f_t` (fixture error: the step's own verification exits 4) |
| Q3 | `grant_classification.py (SQL regenerated)` | drop the lock-column UPDATE grant | `db/test_application_role_grants.py::test_the_adr_row_7_query_prints_f_f_f_t` (fixture error: the step's own verification exits 4) |
| Q4 | `grant_classification.py (SQL regenerated)` | drop REVOKE CREATE ON SCHEMA public FROM PUBLIC | `db/test_application_role_grants.py::test_check_reports_each_kind_of_difference_and_the_step_repairs_it[CREATE` |
| Q5 | `grant_classification.py (SQL regenerated)` | drop the clean slate (REVOKE ALL ON ALL TABLES ... FROM the role) | `db/test_application_role_grants.py::test_a_second_wall_the_trigger_refuses_even_a_privilege_forced_on` |
| Q6 | `grant_classification.py (SQL regenerated)` | drop the revocation of role memberships | `db/test_application_role_grants.py::test_the_step_repairs_whatever_was_changed_by_hand` |
| Q7 | `grant_classification.py (SQL regenerated)` | drop the fail-closed refusal of an unclassified relation | `db/test_application_role_grants.py::test_check_reports_each_kind_of_difference_and_the_step_repairs_it[a` |
| Q8 | `grant_classification.py (SQL regenerated)` | do not set the password on the role | `db/test_application_role_grants.py::test_the_application_role_does_the_crud_the_contexts_do` |
| Q9 | `grant_classification.py (SQL regenerated)` | drop GRANT USAGE ON SCHEMA public | `db/test_application_role_grants.py::test_the_step_repairs_whatever_was_changed_by_hand` |
| Q10 | `grant_classification.py (SQL regenerated)` | drop the EXECUTE grant on the two SQL helpers | `db/test_application_role_grants.py::test_check_reports_each_kind_of_difference_and_the_step_repairs_it[a` |
| Q11 | `grant_classification.py (SQL regenerated)` | verification ignores ownership (relations) | `db/test_application_role_grants.py::test_check_reports_each_kind_of_difference_and_the_step_repairs_it[a` |
| Q12 | `grant_classification.py (SQL regenerated)` | verification does not ask about TRUNCATE | `db/test_application_role_grants.py::test_check_reports_each_kind_of_difference_and_the_step_repairs_it[a` |
| Q13 | `infra/deploy/apply-grants.sh` | the embedded SQL is hand-edited in the script (GRANT ALL on the schema), not regenerated | `recovery/test_grant_classification.py::test_the_script_embeds_the_sql_generated_from_the_classification` |
| A1 | `infra/deploy/apply-grants.sh` | the password goes on the psql command line | `composition/test_apply_grants_script.py::test_apply_speaks_the_protocol_the_comment_promises` |
| A2 | `infra/deploy/apply-grants.sh` | no verification after the apply | `composition/test_apply_grants_script.py::test_apply_speaks_the_protocol_the_comment_promises` |
| D1 | `infra/deploy/deploy.sh` | deploy.sh does not run apply-grants.sh between migrate and up | `composition/test_db_roles_deploy_guards.py::TestTheOneShotsAndTheStepRunBeforeUp::test_the_order_is_build_then_owner_migrate_then_notes_then_apply_then_verify_then_up` |
| D2 | `infra/deploy/deploy.sh` | deploy.sh does not run migrate as the owner before the step | `composition/test_db_roles_deploy_guards.py::TestTheOneShotsAndTheStepRunBeforeUp::test_the_order_is_build_then_owner_migrate_then_notes_then_apply_then_verify_then_up` |
| R1 | `infra/deploy/reset.sh` | reset.sh --restore does not re-apply the rights | `composition/test_reset_script_refusals.py::TestTheApplicationRoleIsGivenItsRightsBack::test_the_restore_gives_the_rights_back_after_the_migrations_and_before_anything_connects_as_the_application` |
| R2 | `infra/deploy/reset.sh` | reset.sh (the wipe) does not re-apply the rights | `composition/test_reset_script_refusals.py::TestTheApplicationRoleIsGivenItsRightsBack::test_the_wipe_gives_the_rights_back_after_the_migrations_and_before_the_worker_starts` |
| S1 | `infra/deploy/copy-serve.sh` | copy-serve.sh restore-db does not re-apply the rights | `composition/test_stand_copy_refusals.py::test_each_guard_refuses_and_its_deletion_stops_the_refusal[copy-serve.sh:grants-applied]` |
| P1 | `infra/deploy/purge-product-data.sh` | purge-product-data.sh does not hand the owner URL to the python half | `composition/test_purge_product_data_script.py::test_the_python_half_is_handed_the_owners_url_at_every_step_and_never_the_applications` |
| K1 | `infra/deploy/compose.server.yml` | api is handed the owner's URL | `composition/test_db_roles_deploy_guards.py::test_the_application_gets_its_url_and_only_the_one_shots_get_the_owners` |
| K2 | `infra/deploy/compose.server.yml` | migrate is handed the application's URL | `composition/test_db_roles_deploy_guards.py::test_the_application_gets_its_url_and_only_the_one_shots_get_the_owners` |
| Y1 | `infra/deploy/readiness.sh` | readiness does not notice a service on the owner role | `composition/test_readiness_command.py::TestDbRoles::test_a_service_still_on_the_owner_role_is_a_finding[API]` |

The guards of the scripts are held by the repository's own form, **deleting the marked block from a copy and showing the refusal gone**, and each such test is in the suites below: `apply-grants.sh` 10 of 10 (`test_each_guard_is_shown_able_to_fail_by_deleting_it`), `deploy.sh` 5 of 5 (`TestEachWayTheTwoRolesCanBeMisconfigured`, `test_each_pre_up_guard_is_shown_able_to_fail_by_deleting_it`, `test_that_guard_is_shown_able_to_fail`), `reset.sh` 2 of 2, `copy-serve.sh` 3 of 3 (the guard-case table), `purge-product-data.sh` 1 of 1, `readiness.sh` `db-roles` (`test_the_check_is_shown_able_to_fail`). The classification guard: a table, view, sequence, identity column, trigger function, plain function, dropped table and another-schema relation each created in a clone are refused by name; the literal "migration copy" (a copy of `db/migrations` with a revision that adds a table, applied to a clone) is refused by the step (exit 3, nothing granted, the role's old rights untouched) and by the audit. The evidence scan is shown able to fail on a crafted source tree (an `UPDATE` of an append-only table, a `DELETE`, an upsert, a row lock, a write to a read-only table, and a class that takes away what the code does).

## 5. Modified tests: what each asserted before and after

No assertion was weakened. Fixtures changed because the environment now names the application role and the owner's url moved.

- `test_deploy_script_refusals.py`: `_env_text` / `_d103_env_text` — before: `DATABASE_URL` carried the owner; after: `DATABASE_URL` is the application's, `MIGRATOR_DATABASE_URL` the owner's, plus `ALPHA_APP_DB_*` (every non-guard case stays coherent). `_stage` also copies `apply-grants.sh` (`with_grants`). `TestD103...::test_rotating_only_the_four_names...` — before/after: the same refusal, now naming `MIGRATOR_DATABASE_URL's password does not match POSTGRES_PASSWORD`. `test_the_guard_is_shown_able_to_fail` (D-103) — before: the reproduction with the stale owner url sails through to the build when `derived-secrets-coherent` is deleted; after: the same, with the stale part being the two S3 values, because the stale owner url is now **also** refused by `app-db-role-configured` (a new case, `test_a_stale_owner_url_is_still_refused_before_any_build_with_that_guard_deleted`, states that defence in depth). `test_every_guard_in_the_script_has_a_case_here` — 31 markers to 36, the five named in `DB_ROLE_GUARDS` and required to appear in `test_db_roles_deploy_guards.py`.
- `test_acme_deploy_guards.py`, `test_deploy_image_identity.py`, `test_proxy_config_follows_checkout.py`: the env builders and the staging gain the application role / the step (the opt-in docker stand gets stand-in `migrate`, `release-notes` and `apply-grants.sh`); assertions unchanged.
- `test_reset_script_refusals.py`: `ENV_FILE` gains the roles; `_staged`, `_mutant` and the hand-staged `test_an_unreadable_dump_stops_the_wipe` copy the step; marker count 14 to 16 and two names added to the covered set; assertions unchanged.
- `test_stand_copy_refusals.py`: `ENV_TEXT` gains the roles; the installed set gains `apply-grants.sh`; three entries in the guard-case table; assertions unchanged (`listeners:` is still a prefix of the `status` line).
- `test_purge_product_data_script.py`: `ENV_FILE` gains both urls; the stub also records the `DATABASE_URL` it was given; marker count 15 to 16; assertions unchanged.
- `test_readiness_command.py`: `_alpha_env` names the roles; the stub answers the `db-roles` calls (clean by default); the clean-run test also asserts the new OK line and "8 checks" (it said 7 checks implicitly); the marker set gains `db-roles`.
- `tests/integration/recovery/test_product_purge_script.py`: the env file gains a well-formed `MIGRATOR_DATABASE_URL` (the file needs docker; not run here).

## 6. Commands and counts

Common method. From the worktree, one pytest at a time, `env $(grep -v '^#' .env | grep -v '^$' | xargs) PATH=<a directory whose `docker` exits 125>:$PATH PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <files>`, so that no real `docker` could be reached by a test that does not stub it. `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)`.

**(a) Not database-backed — run after the integrator's 00:43 note, on HEAD `31625cee` (the lane's code; the two docs were untracked), sequentially.**

| file | tests | result |
|---|---|---|
| `composition/test_deploy_script_refusals.py` | 89 | passed |
| `composition/test_acme_deploy_guards.py` | 99 | passed |
| `composition/test_readiness_command.py` | 64 | passed |
| `composition/test_db_roles_deploy_guards.py` (new) | 36 | passed |
| `composition/test_apply_grants_script.py` (new) | 34 | passed |
| `composition/test_reset_script_refusals.py` | 77 | passed |
| `composition/test_stand_copy_refusals.py` | 167 | 166 passed, 1 skipped (the real-docker fingerprint case, skipped before this lane too) |
| `composition/test_purge_product_data_script.py` | 47 | passed |
| `composition/test_default_credential_gate.py` | 106 | passed |
| `composition/test_deploy_image_identity.py` | 23 | passed |
| `composition/test_stand_copy_fresh.py` | 35 | passed |
| `composition/test_proxy_config_follows_checkout.py` | 17 | 16 passed, 1 skipped (the opt-in docker stand) |

Two runs: the first four files, **288 passed in 170 s**; the other eight, **504 passed, 2 skipped in 227 s**. The directory-wide run of 23:46 was killed at 49 % and is not claimed.

**(b) Database-backed — private databases of the lane's PostgreSQL 17.11 cluster, run earlier in the session (before the 00:43 instruction), not re-run since; the integrator re-runs them.**

| file | tests | result |
|---|---|---|
| `recovery/test_grant_classification.py` (new) | 33 | passed (a table, view, sequence, identity column, trigger function, plain function, dropped table and another-schema relation each created in a clone are refused by name; the evidence scan is shown failing on crafted trees) |
| `db/test_application_role_grants.py` (new) | 89 | passed (123 passed together with the 34 of `test_apply_grants_script.py`): (a) CRUD, (b) no `CREATE`, `DROP`, `ALTER`, `COMMENT`, `SET ROLE`, role changes (31 statements) and no `TRUNCATE` on any of the 64 tables, nor any privilege change (8 statements), (c) append-only refuses `UPDATE` and `DELETE` twice, (d) idempotence by ACL snapshot, (e) restore from a `--no-privileges` dump in both repository shapes, 30 tamper cases, the migration-copy case, the superuser/pgvector premise, rotation |
| `db/test_application_role_plugin.py` (new) | 3 | passed |

**(c) The suites run as the application role** (method: a private migrated database given its rights by the step; either `DATABASE_URL` = the role's url on it, or the plugin with the owner's url). Every number is from this session's logs.

| suite | how | passed | not passed, and why (the role was not relaxed) |
|---|---|---|---|
| `tests/integration/jobs` | role url | 93 | none |
| `tests/integration/runs` | role url | 746 | 88 errors in `test_v3_group_start_queues_the_runs`, `test_v3_recorded_group_over_http`, `test_v3_saved_text_layer_probe`: each builds its own database with `CREATE DATABASE` (needs `CREATEDB`); **with the plugin the same three files: 90 passed** (a second run of the other copy: 744 passed, 90 deselected) |
| `tests/integration/access` | plugin | 277 | 2 failed, both test setup that needs the owner: `ALTER TABLE app_user_role DROP CONSTRAINT ...` (DDL, to seed a stored unknown role) and `SET LOCAL session_replication_role = replica` (a superuser setting, to seed a row without its parents) |
| `releases`, `dispatch` | plugin | 59, 46 | none |
| `optimisation` | plugin | 96 | 6 failed: `test_stored_rows_are_never_updated_or_deleted` asserts the trigger's `AM003`; the role now meets the privilege error (`42501`) first, the layer above and stronger |
| `decisions`, `findings`, `executors`, `workers`, `storage`, `ingest`, `documents` | role url | 1161 | 6 failed: 4 assert the trigger's `AM002`/`AM003` (`42501` first, as above); 2 `executors` tests run `pg_dump` **as the role** and meet `permission denied for sequence audit_event_sequence_no_seq` (decision 13); 205 errors: `documents` (40) and `ingest` (165) fixtures `CREATE DATABASE`. With the plugin `documents` passes; `ingest` was not run with it because its conftest `TRUNCATE`s the domain tables between tests, which is owner-only |
| `tests/integration/norms` | role url, then plugin | 1076, then 1120 | 166 / 165 errors: the self-provisioning fixtures (`CREATE DATABASE`; with the plugin: `ALTER TABLE norm_current_snapshot DISABLE TRIGGER` ×128 and seeding writes to `norm_repair_call` ×37, owner set-up); 1 failure unrelated to roles (`test_every_relevance_anchor_resolves_to_the_exact_real_corpus` needs the real corpus) |

What the table says: **every statement of the product code that was executed ran as the restricted role and was granted**; the failures and errors are test set-up that needs the owner, assertions about the trigger layer, or `pg_dump` as the role. Not exercised as the role: `ingest` (set-up truncates), the `norms` custody/repair/bundle/search database suites (set-up DDL), and anything needing a docker daemon.

**(d) Governance, prose guards and whitespace** (after the last commit): see the end of this section.

## 7. Integration notes (for the integrator)

1. **The owner steps, in order** (runbook section 16): choose the second password; edit `alpha.env` (four lines; the existing `DATABASE_URL` becomes `MIGRATOR_DATABASE_URL`); deploy; check with `readiness.sh` (`db-roles`), `apply-grants.sh --check` and the `ADR-0021` row 7 query; **re-install the copy key's files** (runbook section 13 step 2: five files now, `apply-grants.sh` beside `copy-serve.sh`, plus the existing ones) — until then `restore-db` refuses before it stops anything and the other verbs are unaffected.
2. **Do not merge this to `origin/main` before the second password is on the host.** `deploy-auto` runs `deploy.sh`, which refuses (exit 3, `[app_db_password_unset]` or `[app_db_role_invalid]`, before it builds) an `alpha.env` of the old shape, so the workflow would be red at the guard until the owner's edit. `origin/dev` is unaffected. `AGENTS.md` section 6 applies.
3. **Every future migration that adds a table, view or sequence** must classify it in `grant_classification.py` and regenerate the script (`python -m scripts.recovery.grant_classification --write-script infra/deploy/apply-grants.sh`), or `test_grant_classification.py` is red and the step refuses at deploy time. This is the same lane discipline as `schema_coverage.py` (`D-213`); a migration lane's checklist should say so.
4. **`PROD-07`'s erase wrapper** passes `MIGRATOR_DATABASE_URL` exactly as `purge-product-data.sh` now does (`DATABASE_URL="$MIGRATOR_URL" compose run ...`, and a guard `migrator-url-configured`); `PROD-07a`'s report asks for the same.
5. **`PROD-05`** edits `compose.server.yml` next: the two `DATABASE_URL` lines and the header comment are this lane's.
6. The branch contains a merge of `integration/ar-close-1026` made by another session (section 1); merging it back is trivial, and `git diff 9a28f09f..HEAD` is the lane.
7. The application-role runs need nothing from the integrator: `AM_TEST_AS_APPLICATION_ROLE=1 python -m pytest -p tests.integration.db.application_role_plugin <suites>` with `DATABASE_URL` = the owner's, on the lane stack.

## 8. Limits

- **Not run, and why:** anything needing a docker daemon — `tests/integration/recovery/test_product_purge_script.py` (it execs into the lane's postgres container), the two `docker compose config` renders in `test_real_client_address_at_the_edge.py`, the opt-in real-container proxy stand (`AUDITMANAGER_PROXY_STAND=1`; its stand compose, env and a stand-in `apply-grants.sh` were edited blind). The example now carries `MIGRATOR_DATABASE_URL`, and `test_every_variable_the_compose_file_requires_is_in_the_example` is the static half of the render. `docker compose run migrate` before `up`, the real `exec -T postgres psql` with stdin from a file, and `up` re-running the one-shots are modelled by stubs and by the lane's host `psql`, not observed.
- **The postgres under test is the lane's 17.11 cluster, not the repository's built image**: the same major and minor, the same pgvector flags (P-02), but not the same container. `docker compose exec -T postgres psql` over the unix socket without a password is what `reset.sh` already relies on.
- **Suites that need the owner, and why** (the role was not relaxed): section 6 lists them. They are test setup — `CREATE DATABASE`, `TRUNCATE` between tests, `ALTER TABLE ... DISABLE TRIGGER`, `SET session_replication_role`, an `ALTER TABLE ... DROP CONSTRAINT` to seed a bad row — and tests that assert the **trigger's** error (`AM002`/`AM003`) where the role now gets the privilege error (`42501`) first, which is the layer above and stronger. None is a product statement the role was refused.
- **The password can reach the server log** if an `ALTER ROLE ... PASSWORD` statement fails (at `log_min_error_statement = error`, the default, the failing statement is logged); nothing the script prints contains it. A SCRAM verifier computed on the host would avoid it and needs a tool the host is not promised.
- **The role keeps the `PUBLIC` defaults**: `CONNECT`, session-local temporary tables, the functions an extension installs. It cannot create a permanent object.
- **Ownership is reported, not repaired**: an object the role came to own makes `--check` fail and the apply exit 4; the operator moves it back.
- **`restore-db` runs the step after the restore of a dump older than the checkout** by skipping classified tables that do not exist; a dump with a table the checkout does not know is refused (`[grants_unclassified]`), which after a restore is the rollback case the plan calls a forward fix.
- **`D-166`, `D-213`, `D-216` are not closed by this lane** (limits are `PROD-05`; this lane adds one more derived inventory instead of a hand-kept one; no drill at `0033` was run).
