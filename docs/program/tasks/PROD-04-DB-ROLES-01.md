# Task PROD-04-DB-ROLES-01 — api and worker connect as an application role that cannot change the schema; one idempotent step gives it its rights after every migrate and every restore

task_id: PROD-04-DB-ROLES-01
status: completed in development candidate (nothing run against a host or a real compose project; see the report)

## Outcome

`PROD-04` of `PRODUCTION-READINESS-PLAN-01` (`R-146n` item 1, `AD-02` confirmed by `R-146w`; `ADR-0021` section 3 and row 7): `api` and `worker` connect as an application role that cannot change the schema, cannot truncate and owns nothing; the migrator (the postgres image's bootstrap role) keeps ownership and is the only role that runs `migrate`, `release-notes` and the operator tools that need write-everything; the application role's rights are applied by ONE idempotent step, `infra/deploy/apply-grants.sh`, derived from a classification of every table, view, sequence and function at head (`scripts/recovery/grant_classification.py`, built on `schema_coverage`), after every `migrate`, every `reset.sh` and every `reset.sh --restore` and `copy-serve.sh restore-db`; the second password is the owner's to write on the host and its absence is a typed refusal. **No migration is added; the head stays at `0033_ar_v3_cite_stage_id`.**

## Depends on

- `PROD-03` / `PROD-02-03-DEPLOY-GATES-01` and `JUDGE-FIXES-F2-01` — merged into the base (`infra/**` files, the listener library, the restore paths' gate).
- `ADR-0021` section 3 and row 7; `ADR-0023` (the audit ledger is append-only); `R-146n` item 1, `R-146w`, `R-93`, `R-52`.
- Register rows `D-166` (memory limits, `PROD-05`, not this lane), `D-213` (hand-kept inventories drift: this lane derives, it does not copy), `D-216` (no drill at the current head).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.6.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged (`0033_ar_v3_cite_stage_id`)
- base commit: `cfbae64a` (`integration/ar-close-1026`), branch `agent/prod-04-db-roles-01`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: scripts/recovery/grant_classification.py
- enumerator_owner: PROD-04-DB-ROLES-01 (the lane owns `infra/**` and `DEPLOYMENT_RUNBOOK.md` in wave PW3; `tests/integration/recovery/test_grant_classification.py` pins the set against `schema_coverage` and a migrated database, and `deploy.sh`'s `test_every_guard_in_the_script_has_a_case_here` pins its guard set)
- totality_query: `PYTHONPATH=src:$BS .venv/bin/python -c "from scripts.recovery import grant_classification as g, schema_coverage as c; print(sorted(c.TABLES - (g.READ_WRITE | g.APPEND_ONLY | g.READ_ONLY | g.NONE)), g.classification_problems())"` prints `[] []`

The set is the grant classification: four disjoint classes that partition `schema_coverage.TABLES` (25 read-write, 36 append-only, 3 read-only, 0 none), two lock-only exceptions, two callable helper functions. `deploy.sh` goes from 31 to 36 marked guards, `reset.sh` from 14 to 16, `purge-product-data.sh` from 15 to 16, `copy-serve.sh` gains three, `readiness.sh` gains one check (7 to 8) and `apply-grants.sh` has ten.

## Captured premise evidence

- premise: the reads the plan and `ADR-0021` rely on, re-run against the base commit `cfbae64a`; all are present. The ones that changed the design are P-02 (the bootstrap role is a superuser and the pgvector in this stack is not trusted, so the migrator cannot be a plain owner), P-04 (the head is `0033`), P-07 (the two restore paths and the dump flags) and P-09 (`FOR UPDATE` on two immutable tables needs an `UPDATE` privilege).

### P-01 — the four services that read the database url, all from one variable
- captured_at: 2026-10-26
- command: `git show cfbae64a:infra/deploy/compose.server.yml | grep -n "DATABASE_URL"`
- captured_output:
  ```text
  55:  # (a `DATABASE_URL` here, a client dependency in `web/package-lock.json`) and a new
  159:      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset.}
  176:      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset.}
  203:      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset.}
  275:      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset.}
  ```
- interpretation: `migrate` (159), `release-notes` (176), `api` (203) and `worker` (275) all take the same variable, which `alpha.env` fills with the owner's url. Two urls need two variables; the owner's goes to the two one-shots only.

### P-02 — the bootstrap role is a superuser and pgvector 0.8.6 is neither trusted nor creatable by a plain owner
- captured_at: 2026-10-26
- command: `psql ... -d postgres -c "select rolname, rolsuper from pg_roles where rolname = current_user"` and `psql ... -c "select name, version, superuser, trusted from pg_available_extension_versions where name='vector'"` on the lane stack (the same image family as the deployed `postgres`)
- captured_output:
  ```text
  auditmanager_local|t
  vector|0.8.6|t|f
  ```
- interpretation: `POSTGRES_USER` is created by the image as a superuser. The extension is `superuser = t`, `trusted = f`, and migration `0013` runs `CREATE EXTENSION vector` (P-03), so no plain owner role can run `migrate` on a fresh database. **Decision (decided by the lane): the migrator is the bootstrap superuser, as `ADR-0021` section 3 says; the superuser is contained by never putting its url in an always-on service's environment.** `test_a_plain_owner_cannot_migrate_a_fresh_database` pins the premise.

### P-03 — the migration that needs the superuser
- captured_at: 2026-10-26
- command: `grep -n "CREATE EXTENSION" db/migrations/versions/20261001_0013_norm_embeddings.py`
- captured_output:
  ```text
  32:    op.execute(f"CREATE EXTENSION vector WITH VERSION '{PGVECTOR_VERSION}';")
  ```
- interpretation: the only `CREATE EXTENSION` in the chain; a migration is history and is not edited by this lane (`no migration`).

### P-04 — the head and the schema's own inventory
- captured_at: 2026-10-26
- command: `ls db/migrations/versions/*.py | tail -1; PYTHONPATH=src:$BS .venv/bin/python -c "from scripts.recovery import schema_coverage as c; print(c.HEAD, len(c.TABLES), len(c.VIEWS), len(c.SEQUENCES))"`
- captured_output:
  ```text
  db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py
  0033_ar_v3_cite_stage_id 64 5 7
  ```
- interpretation: 64 base tables, 5 views, 7 sequences at `0033`; `schema_coverage` is the one source of truth the classification reuses (`D-213`: a hand-kept second list is the class of defect that register row describes).

### P-05 — what the code does to each table (static scan of every SQL string under `src/auditmanager`)
- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -c "from pathlib import Path; from scripts.recovery import grant_classification as g; o=g.observed_statements(Path('src/auditmanager')); print(sorted(t for t,v in o.items() if 'DELETE' in v.verbs)); print(sorted(t for t,v in o.items() if 'LOCK' in v.verbs and t in g.APPEND_ONLY)); print(sorted(g.coverage.TABLES-set(o)))"`
- captured_output:
  ```text
  ['app_user', 'app_user_role']
  ['document_version_classification', 'work_assignment']
  ['alembic_version', 'contract_state_transition', 'norm_embedding_profile']
  ```
- interpretation: only two tables are ever deleted from by the code; two append-only tables are row-locked (`FOR UPDATE` / `FOR NO KEY UPDATE`, which PostgreSQL grants only with an `UPDATE` privilege on some column); three tables are never written. `INSERT ... ON CONFLICT DO UPDATE` is counted as an `UPDATE` (`account_release_mark`, `execution_control`, `stage_result`, `analysis_artifact_publication`). The scan is evidence, not the grant: `evidence_problems` fails when the code needs more than a class grants.

### P-06 — deploy.sh's coherence guard reads DATABASE_URL against the owner
- captured_at: 2026-10-26
- command: `git show cfbae64a:infra/deploy/deploy.sh | grep -n "configured DATABASE_URL\|DATABASE_URL's"`
- captured_output:
  ```text
  602:if [[ "$(configured DATABASE_URL)" =~ $DB_URL_RE ]]; then
  604:        "  DATABASE_URL's user is '${BASH_REMATCH[1]}' but POSTGRES_USER is '$DERIVED_PG_USER'")
  606:        "  DATABASE_URL's password does not match POSTGRES_PASSWORD")
  608:        "  DATABASE_URL's database is '${BASH_REMATCH[5]}' but POSTGRES_DB is '$DERIVED_PG_DB'")
  ```
- interpretation: after this lane `DATABASE_URL` is the application's; the owner-side check moves to `MIGRATOR_DATABASE_URL` and the application side is judged by `apply-grants.sh --config-only`.

### P-07 — the restore paths, and the dump flags that make the step necessary
- captured_at: 2026-10-26
- command: `git show cfbae64a:infra/deploy/copy-serve.sh | grep -n "DROP SCHEMA\|pg_restore --no-owner"; git show cfbae64a:infra/deploy/reset.sh | grep -n "pg_restore --clean\|DROP SCHEMA IF EXISTS\|pg_dump --format"`
- captured_output:
  ```text
  948:    psql_stand --command "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO \"$PG_USER\";" < /dev/null >&2
  949:    compose exec -T postgres pg_restore --no-owner --no-privileges --exit-on-error --single-transaction \
  298:    compose exec -T postgres pg_restore --clean --if-exists --no-owner \
  736:    --command "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO \"$CONFIGURED_USER\";"
  579:    compose exec -T postgres pg_dump --format=custom --no-owner --no-privileges \
  ```
- interpretation: every dump is `--no-owner --no-privileges`; `restore-db` and the `reset.sh` wipe drop and recreate schema `public` (a new schema has no `USAGE` for anyone), `reset.sh --restore` is `--clean --if-exists`. After any of them the application role has no rights: three places to run the step.

### P-08 — the purge wrapper runs the tool with the api's url, and the tool refuses a role that does not own
- captured_at: 2026-10-26
- command: `git show cfbae64a:infra/deploy/purge-product-data.sh | grep -n "^api_python\|--entrypoint python api -m scripts"; grep -n "guard: owner-may-write" scripts/recovery/product_purge.py`
- captured_output:
  ```text
  229:api_python() {
  232:        --entrypoint python api -m scripts.recovery.product_purge "$@"
  234:api_python_dump() {
  238:        --entrypoint python api -m scripts.recovery.product_purge "$@"
  353:    # >>> guard: owner-may-write
  367:    # <<< guard: owner-may-write
  ```
- interpretation: both helpers run in the `api` service, whose `DATABASE_URL` becomes the application's; the tool's `owner-may-write` guard (`pg_has_role(current_user, relowner, 'MEMBER')`) would refuse it. The wrapper hands the owner's url, through the environment of the `docker compose` process. `product_purge.py` is not changed: its message already names "the owning role (the one the migrations run as)".

### P-09 — the catalogue at head: relations, functions
- captured_at: 2026-10-26
- command: `psql ... -c "select relkind, count(*) from pg_class where relnamespace='public'::regnamespace and relkind in ('r','v','S') group by 1 order by 1"` and the trigger / non-trigger function counts outside extensions
- captured_output:
  ```text
  S|7
  r|64
  v|5
  30|2
  ```
- interpretation: 7 sequences, 64 tables, 5 views; 30 trigger functions (all named by `schema_coverage.TRIGGERS`) and 2 plain SQL helpers (`am_is_ascending_page_list`, `norm_designation_tokens`) outside the 118 functions pgvector installs. The audit refuses any other.

### P-10 — the plan item, and what it asks (read again at the base)
- captured_at: 2026-10-27
- command: `git show cfbae64a:docs/program/PRODUCTION-READINESS-PLAN-01.md | grep -n "^### PROD-04"`
- captured_output:
  ```text
  63:### PROD-04 — Database roles: migrator and application, grants as an idempotent step (`R-146n` item 1, `AD-02`)
  ```
- interpretation: the item names `apply-grants.sh`, `compose.server.yml`, `deploy.sh`, `alpha.env.example`, `reset.sh --restore`, `copy-serve.sh restore-db`, `purge-product-data.sh`, a grant-classification guard test, a restored-from-`--no-privileges`-dump test and the application-role run of the integration suites; every one is delivered. `scripts/recovery/product_purge.py` changes "only if the guard's message needs it": it does not.

### P-11 — the tests that pin the old shape of the environment (`DATABASE_URL` naming the owner)
- captured_at: 2026-10-27
- command: `git grep -n "DATABASE_URL=postgresql+psycopg" cfbae64a -- tests/integration/composition | sed "s#^cfbae64a:##" | cut -c1-110`
- captured_output:
  ```text
  tests/integration/composition/test_acme_deploy_guards.py:315:        f"DATABASE_URL=postgresql+psycopg://{PG_U
  tests/integration/composition/test_deploy_image_identity.py:300:        "DATABASE_URL=postgresql+psycopg://"
  tests/integration/composition/test_deploy_script_refusals.py:117:            "DATABASE_URL=postgresql+psycopg:
  tests/integration/composition/test_deploy_script_refusals.py:140:        "DATABASE_URL=postgresql+psycopg://"
  tests/integration/composition/test_proxy_config_follows_checkout.py:708:                    "DATABASE_URL=post
  tests/integration/composition/test_readiness_command.py:76:            "DATABASE_URL=postgresql+psycopg://"
  ```
- interpretation: six environment builders write the owner into `DATABASE_URL`; after the change `deploy.sh` refuses that shape (`[app_db_role_invalid]`), so each builder was updated, and `reset.sh`, `copy-serve.sh` and `purge-product-data.sh` fixtures gained the new names (the report, section 5, says per test what it asserted before and after).

### P-12 — the register rows the brief names, and the decision on sequences
- captured_at: 2026-10-27
- command: `git show cfbae64a:docs/program/DEBT_REGISTER.md | grep -n '^| \*\*D-166\*\*\|^| \*\*D-213\*\*\|^| \*\*D-216\*\*' | cut -c1-130; grep -rnE "currval|lastval|setval|last_value" src/auditmanager | wc -l`
- captured_output:
  ```text
  83:| **D-166** | the API and worker containers have no memory limit, so a runaway request is contained by the host, not by the ser
  130:| **D-213** | **Hand-kept table and constraint inventories drift with every migration.** `product_purge`'s PRODUCT/KEEP/MIXED sets, ...
  133:| **D-216** | `BETA-STATIC-MATRIX-02` (B6): the last recorded backup/restore drill is at migration head `0029`; none is recorded at `0032`, ...
  0
  ```
- interpretation: `D-166` belongs to `PROD-05`; `D-213` is why the classification derives from `schema_coverage` and a test partitions it against the catalogue instead of keeping a second list; `D-216` is untouched (the restore-path tests here are stubs plus a real-database restore of a `--no-privileges` dump, not the owner's drill). **Sequences get `USAGE` and no `SELECT`** (decided by the lane): `src/` never reads sequence state (`currval`, `lastval`, `setval`, `last_value`: 0 matches), `nextval` needs `USAGE` only, and a `SELECT` would let a role read what the next identity will be for nothing. The one thing that does want `SELECT` on sequences is `pg_dump` run as the application role (two `executors` tests do exactly that, section 6 of the report): the dump tools run in the postgres container as the owner, so that is a test harness choice and not a product path.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to `agent/prod-04-db-roles-01` and pushes nothing. `origin/main` triggers a deployment (`AGENTS.md` section 6) and is not touched.

## Allowed paths

- `infra/deploy/**`
- `scripts/recovery/grant_classification.py`
- `tests/integration/composition/**`
- `tests/integration/recovery/**`
- `tests/integration/db/**`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/tasks/PROD-04-DB-ROLES-01.md`
- `docs/program/PROD-04-DB-ROLES-01.md`

`scripts/recovery/**` is used only for the one new module that shares `schema_coverage`'s source of truth; `product_purge.py` and `schema_coverage.py` are not edited. `infra/deploy/**` covers `apply-grants.sh` (new), `compose.server.yml`, `deploy.sh`, `reset.sh`, `copy-serve.sh`, `purge-product-data.sh`, `readiness.sh`, `env/alpha.env.example` and `README.md`.

## Forbidden hotspots

- `.github/**`
- `contracts/**`
- `db/migrations/**` and the migration head
- `src/**` (nothing needed a change: the application runs under the restricted role as it is)
- the web
- lock files and dependency manifests
- `docs/program/DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals

- installing the second password, the copy key's new file or anything on a live host (owner steps, runbook sections 13 and 16)
- a third (plain-owner) role or ownership transfer: P-02 shows the job needs the superuser
- `ALTER DEFAULT PRIVILEGES` (fail-closed instead: a table nobody classified gets nothing and stops the deploy)
- memory and log limits (`PROD-05`, `D-166`), the project erase (`PROD-07`; it will pass the migrator url the same way)
- running the suites that need a docker daemon (`test_product_purge_script.py`, the two `docker compose config` renders, the opt-in proxy stand)

## Deliverables

- `scripts/recovery/grant_classification.py`: the classification, the evidence scan, the SQL generator and the catalogue audit (`audit_grant_classification`)
- `infra/deploy/apply-grants.sh`: apply / `--check` / `--config-only` / `--compose-file`; ten guards; the SQL embedded between generated markers
- `compose.server.yml`, `env/alpha.env.example`, `deploy.sh` (five guards), `reset.sh` (two guards, two follow-ups), `copy-serve.sh` (three guards), `purge-product-data.sh` (one guard, the owner's url), `readiness.sh` (`db-roles`), `README.md`
- `tests/integration/db/application_role_plugin.py`: a pytest plugin that runs a suite as the application role
- new tests: `test_application_role_grants.py` (real database), `test_application_role_plugin.py`, `test_grant_classification.py`, `test_apply_grants_script.py`, `test_db_roles_deploy_guards.py`; modified tests: the report lists, per test, what it asserted before and after
- `docs/program/DEPLOYMENT_RUNBOOK.md` sections 2, 3, 13 and the new 16
- the report `docs/program/PROD-04-DB-ROLES-01.md`

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/recovery/test_grant_classification.py tests/integration/db/test_application_role_grants.py tests/integration/db/test_application_role_plugin.py tests/integration/composition/test_apply_grants_script.py tests/integration/composition/test_db_roles_deploy_guards.py` (one pytest at a time, on the lane stack)
- expected: all pass; the counts are in the report
- command: the touched composition suites (`test_deploy_script_refusals`, `test_acme_deploy_guards`, `test_default_credential_gate`, `test_stand_copy_fresh`, `test_deploy_image_identity`, `test_proxy_config_follows_checkout`, `test_reset_script_refusals`, `test_stand_copy_refusals`, `test_purge_product_data_script`, `test_readiness_command`)
- expected: all pass (the report lists the counts)
- command: the application-role runs: `DATABASE_URL=<application url on a private database> pytest tests/integration/jobs tests/integration/runs ...` and `AM_TEST_AS_APPLICATION_ROLE=1 pytest -p tests.integration.db.application_role_plugin tests/integration/access ...`
- expected: the passes and the named exceptions in the report
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (after the last commit: one contract test refuses a dirty tree)
- expected: green

## Integration contract

What the integrator can rely on:

- `DATABASE_URL` is the application role's url and reaches `api` and `worker`; `MIGRATOR_DATABASE_URL` is the owner's and reaches `migrate` and `release-notes` only (`compose.server.yml`; pinned by `test_the_application_gets_its_url_and_only_the_one_shots_get_the_owners`). Both are new names in `alpha.env`, with `ALPHA_APP_DB_USER` and `ALPHA_APP_DB_PASSWORD`; the example ships the last with no value
- `deploy.sh` refuses (exit 3, before the build) an unset or malformed second password (`[app_db_password_unset]`, `[app_db_password_shape]`, `[app_db_password_is_owner_password]`), a role named like the owner (`[app_db_role_is_owner]`), a role that is not named (`[app_db_role_invalid]`) and urls that do not carry them (`[database_urls_incoherent]`); and between `migrate` and `up` it refuses `[migrate_failed]`, `[release_notes_failed]`, `[grants_not_applied]`
- `apply-grants.sh` exit codes: 0 applied and verified, 1 `--check` found a difference, 2 usage, 3 refused (`[grants_unclassified]` or a setting), 4 failed
- a migration that adds a table, view, sequence or function without a classification turns `test_grant_classification.py` red AND is refused at run time by the step (nothing granted, transaction rolled back)
- `reset.sh` exits 4 when a wipe left the role without rights and 6 when a restore did; `copy-serve.sh restore-db` refuses `grants-applied` with the writers stopped and the record open; `restore-db` needs `apply-grants.sh` installed beside `copy-serve.sh`: **the owner repeats the install of runbook section 13 after this merges** (the file list changed again)
- no file under `contracts/**`, `db/migrations/**`, `.github/**`, the web or `src/**` is touched

## Failure/idempotency/security cases

- the step is idempotent: a second run leaves every ACL, the schema and database ACLs, the helper functions' ACLs and the role's attributes as the first left them (the stored password verifier is re-salted by design: a rotated password must land)
- a restore from a `pg_dump --no-owner --no-privileges` dump has no rights until the step, in both shapes the repository produces (a fresh database; `DROP SCHEMA public CASCADE; CREATE SCHEMA public` in place), and exactly the classification's after it
- append-only tables refuse `UPDATE` and `DELETE` by privilege; with the privilege forced on, `audit_event`'s trigger still refuses (`AM002`)
- the password is never on a command line (stdin from a private temporary file), never printed, never echoed from a server message
- `--check` reports each kind of difference (a mutation table row each) and the step repairs every one it can; ownership taken by the role is reported and not repaired
- every refusal is shown able to fail by deleting its marked block; the mutation table is in the report

## Rollback / feature flag

No flag. Rolling the lane back is reverting its commits and restoring the previous `alpha.env` shape (`DATABASE_URL` naming the owner): the application role and its grants stay in the database harmlessly (`DROP OWNED BY <role>; DROP ROLE <role>` removes them). The behaviour is not optional on purpose: an unset second password is a refusal, and there is no fall-back to the owner role.

## Handoff

- changed files: see the report, section 2
- commands/results: see the report, section 6
- known limits: see the report, section 8
- integration notes: see the report, section 7
