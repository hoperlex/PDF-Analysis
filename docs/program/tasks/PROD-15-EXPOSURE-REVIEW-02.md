# Task PROD-15-EXPOSURE-REVIEW-02 — a fresh exposure review of the system as it would be deployed to production

task_id: PROD-15-EXPOSURE-REVIEW-02
status: completed in development candidate (documents only; the review is `docs/program/EXPOSURE-REVIEW-02.md`)

## Outcome

`docs/program/EXPOSURE-REVIEW-02.md` exists and states, for each of the nine findings of `EXPOSURE-REVIEW-01.md`, what changed in the tree (with the file and line opened) and whether it is closed, narrowed, open or moved; reviews by reading the code the route groups and their authorization registers, the trust boundaries of the nginx layers, the secrets, the data egress, the upload and blob path, logging and audit, and the denial-of-service surfaces of one 4 GB host with one worker; classifies every new finding HIGH, MEDIUM or LOW with its evidence and the attacker position it needs; lists what could not be verified without a host; gives the recommended order of fixes with the plan items they belong to; and proposes debt-register rows. Plan item `PROD-15`, debt row `D-217`, owner ruling `R-29` clause 2. Nothing in the tree is changed.

## Depends on

- `PROD-01-TLS-ACME-01`, `PROD-02-03-DEPLOY-GATES-01`, `PROD-06-ACCESS-AUDIT-01` — completed, in the tree at the base commit (built, unobserved on a host).
- `PROD-04` (database roles) and `PROD-11` (removal of AR v1/v2) are named by the plan as dependencies of `PROD-15` and are **not** in the tree; the review says what the tree does today and lists what to re-check when they merge (section 7 of the review).
- `PROD-07A-PROJECT-ERASE-CORE-01`, `PROD-11D-V3-GROUP-QUEUE-01`, `JUDGE-FIXES-F2-01` — completed, in the tree at the base commit.

## Frozen inputs

- domain contract: not_applicable (read only)
- API contract: `contracts/api/v1/openapi.json`, 92 paths, 104 operations, version 1.6.0 (read only, not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id` (unchanged)
- base commit: `9a28f09fe81d48a39afd0e08c404de1f28bc0c70` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The review reads the sets that other files enumerate (the three authorization registers of `src/auditmanager/api/security.py`, the operations of the contract) and adds no member to any of them.

## Captured premise evidence

- premise: the base commit, the plan item and its check, the totality of the authorization registers over the contract, the nginx throttle zones, the secrets the compose file hands each service, the unused web functions, the thread-pool and database-pool sizes, a same-uid child reading its parent's environment, SQLAlchemy exception strings, the seed and the ACME pin, and the no-database tests that were run; all re-read at the base commit on 2026-10-26

### P-01 — the base commit is the tip of `integration/ar-close-1026`

- captured_at: 2026-10-26
- command: `git rev-parse integration/ar-close-1026 && git merge-base HEAD integration/ar-close-1026`
- captured_output:
  ```text
  9a28f09fe81d48a39afd0e08c404de1f28bc0c70
  9a28f09fe81d48a39afd0e08c404de1f28bc0c70
  ```
- interpretation: The lane branch started at the tip, and `git merge integration/ar-close-1026` (asked for after a session restart) answered "Already up to date": the tree already holds the PROD-02/03 gates, `JUDGE-FIXES-F2-01`, `scripts/recovery/project_erase.py` and the group-queue fix. It does not prove the tip is the integrator's later tip, only that nothing newer existed in this repository when the review ran.

### P-02 — what the plan says `PROD-15` is, and its check

- captured_at: 2026-10-26
- command: `grep -n "^### PROD-15" -A4 docs/program/PRODUCTION-READINESS-PLAN-01.md | cut -c1-220`
- captured_output:
  ```text
  162:### PROD-15 — The exposure re-review (`D-217`, `R-29` clause 2)
  163-- **Result:** `EXPOSURE-REVIEW-01.md` is followed by a review of the public origin that names `getExecutorTaskImage` and `getArV3BetaPackStatus`, the runner channel and the TLS terminator; any finding that changes wh
  164-  system stops for the owner.
  165-- **depends_on:** PROD-01, PROD-02, PROD-04, PROD-06, PROD-11 · **Hotspots:** none · **Size:** M (a read-only probe and a report) · **Executor:** Sonnet lane from a development host; owner decides.
  166-- **Check (documentation check only):** `grep -c "getExecutorTaskImage\|getArV3BetaPackStatus" docs/program/EXPOSURE-REVIEW-01.md` is at least 2 in the new review document.
  ```
- interpretation: The plan item asks for a report, names the two operations, and stops findings that change who can reach the system for the owner. Its `depends_on` includes `PROD-04` and `PROD-11`, which are not built; the plan's "read-only probe" (a request to the served origin) was not made because this lane has no network (`could not verify`, section 8 of the review). The check applies to the new document, not to `EXPOSURE-REVIEW-01.md`.

### P-03 — the three registers cover all 104 operations of the contract, with none unregistered

- captured_at: 2026-10-26
- command: `python3 -I -c "import json,sys;sys.path.insert(0,'src');from auditmanager.api.security import OPERATION_ROLES as R,RUNNER_OPERATIONS as N,UNAUTHENTICATED_OPERATIONS as U;d=json.load(open('contracts/api/v1/openapi.json'));M=('get','post','put','patch','delete');ops=[o['operationId'] for p in d['paths'].values() for m,o in p.items() if m in M];print(len(d['paths']),len(ops),'open',len(U),'runner',len(N),'roles',len(R),'unregistered',sorted(o for o in ops if o not in R and o not in N and o not in U),'security-empty',sorted(o['operationId'] for p in d['paths'].values() for m,o in p.items() if m in M and o.get('security')==[]))"`
- captured_output:
  ```text
  92 104 open 3 runner 5 roles 96 unregistered [] security-empty ['issueToken', 'readRegistrationStatus', 'submitRegistration']
  ```
- interpretation: 3 + 5 + 96 = 104; no operation is unregistered; the operations with `security: []` in the contract are exactly the three of `UNAUTHENTICATED_OPERATIONS`. This is a static sweep of the document against the registers; the served-application sweeps (`tests/integration/api/test_role_register.py`, `test_authorization.py`, `tests/integration/executors/test_runner_seam.py`) need PostgreSQL and were not run.

### P-04 — the throttle zones of the public proxy

- captured_at: 2026-10-26
- command: `grep -n "limit_req_zone" infra/deploy/proxy/nginx.conf`
- captured_output:
  ```text
  77:# `limit_req_zone` are http-level directives. With TLS on, nginx loads this file (mounted as
  123:limit_req_zone $guest_registration_client zone=guest_registration:1m rate=6r/m;
  150:limit_req_zone $token_exchange_client zone=token_exchange:1m rate=6r/m;
  193:limit_req_zone $runner_token_client zone=runner_channel:1m rate=60r/m;
  200:limit_req_zone $runner_address_client zone=runner_address:1m rate=300r/m;
  ```
- interpretation: Four zones, all keyed per address or per token prefix, none on `location /` (the web tier and the BFF sign-in door) and none a `limit_conn`. Basis of `F-06`, `F-10`, `F-18`.

### P-05 — which services receive the database URL, the signing key and the provider file

- captured_at: 2026-10-26
- command: `grep -n "DATABASE_URL: \|AUDITMANAGER_API_TOKEN: \|env_file\|AUDITMANAGER_WORKER_SLOTS: " infra/deploy/compose.server.yml | cut -c1-150`
- captured_output:
  ```text
  159:      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset.}
  176:      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset.}
  199:    # Named one by one rather than `env_file: alpha.env`, so this file states exactly what
  203:      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset.}
  224:      AUDITMANAGER_API_TOKEN: ${AUDITMANAGER_API_TOKEN:?AUDITMANAGER_API_TOKEN is unset. The seam is fail-closed; see infra/deploy/env/alpha.env.e
  275:      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is unset.}
  303:      AUDITMANAGER_WORKER_SLOTS: ${AUDITMANAGER_WORKER_SLOTS:-1}
  308:    env_file:
  342:      AUDITMANAGER_API_TOKEN: ${AUDITMANAGER_API_TOKEN:?AUDITMANAGER_API_TOKEN is unset. The web tier forwards it; without it every operation answ
  ```
- interpretation: One `DATABASE_URL` for `migrate`, `release-notes`, `api` and `worker`; the signing key goes to `api` (line 224) and to `web` (line 342); the provider file is the `worker`'s `env_file` only (line 308). Basis of `F-03`, `F-05` and the secrets table.

### P-06 — the web tier never calls the functions that read the signing key

- captured_at: 2026-10-26
- command: `grep -rn "getApiToken\|hasServerCredential" web/src`
- captured_output:
  ```text
  web/src/shared/config/server-env.ts:99:export function getApiToken(): string {
  web/src/shared/config/server-env.ts:112:export function hasServerCredential(): boolean {
  ```
- interpretation: Only the definitions occur under `web/src`; tests import them. No web module reads `AUDITMANAGER_API_TOKEN` at run time, so the variable in `compose.server.yml:342` is unused by the web code (`F-03`). It does not prove that Next itself or a dependency never reads the environment.

### P-07 — the thread pool and the database pool

- captured_at: 2026-10-26
- command: `/root/projects/PDF-Analysis/.venv/bin/python -I -c "import anyio,anyio.to_thread;exec('async def m(): print(anyio.to_thread.current_default_thread_limiter().total_tokens)');anyio.run(m)"`
- captured_output:
  ```text
  40
  ```
- interpretation: anyio's default pool for sync handlers, as installed (anyio 4.15.1, starlette 1.6.0, fastapi 0.141.1, uvicorn 0.53.0), is 40; `src/auditmanager/shared/db/config.py:40,42` sets `pool_size: int = 5` and `max_overflow: int = 5`. No `CapacityLimiter` or `total_tokens` is set anywhere in `src/` or `infra/deploy/`. Basis of `F-06`.

### P-08 — a child of the same uid reads its parent's environment through `/proc`

- captured_at: 2026-10-26
- command: `SENTINEL_SECRET=parent-secret-value python3 -I -c "import subprocess,sys;c='import os;print(b\"SENTINEL_SECRET=parent-secret-value\" in open(\"/proc/%d/environ\"%os.getppid(),\"rb\").read())';print(subprocess.run([sys.executable,'-I','-c',c],env={},capture_output=True,text=True).stdout.strip())"`
- captured_output:
  ```text
  True
  ```
- interpretation: On this host, a `python -I` child started with an empty environment (the shape of `ingest/envelope.py:470-477`, `env={"PATH": os.defpath}`) reads the environment its parent was started with. It was run on the development host, not in the `api` container; Docker's default profile does not forbid reading `/proc/<ppid>/environ` of the same uid, but that was not run (`could not verify`). Basis of `F-04`.

### P-09 — SQLAlchemy prints bound parameters unless the engine hides them

- captured_at: 2026-10-26
- command: `/root/projects/PDF-Analysis/.venv/bin/python -I -c "from sqlalchemy import create_engine,text;e=create_engine('sqlite://',future=True);c=e.connect();c.execute(text('create table t (a text check (a <> 0))'));exec('try: c.execute(text(\"insert into t(a) values (:a)\"),{\"a\":0})\nexcept Exception as x: print(str(x).splitlines()[0:3])')"`
- captured_output:
  ```text
  ['(sqlite3.IntegrityError) CHECK constraint failed: a <> 0', '[SQL: insert into t(a) values (?)]', '[parameters: (0,)]']
  ```
- interpretation: With the default engine arguments, the exception text carries `[parameters: ...]`. `src/auditmanager/shared/db/engine.py:29-38` passes no `hide_parameters`. SQLite is the stand-in for PostgreSQL's driver here: the behaviour is SQLAlchemy's, not the driver's. Whether a given failing statement in production carries client text depends on the statement; `D-225` was a CHECK refusing a `stage_result` insert. Basis of `F-12`.

### P-10 — the seed and the ACME client pin as they stand

- captured_at: 2026-10-26
- command: `grep -n "SEED_LOGIN\|SEED_PASSWORD" db/migrations/versions/20260922_0006_app_user.py | head -2 && grep -n "ACME_CLIENT_APK_VERSION" infra/acme/client.pin`
- captured_output:
  ```text
  99:SEED_LOGIN = "admin"
  100:SEED_PASSWORD = "password"  # noqa: S105 - the owner's deliberate default; see the docstring
  25:ACME_CLIENT_APK_VERSION=UNRESOLVED
  ```
- interpretation: The published pair is still seeded by migration `0006`; the gate (`check.py --gate`) controls the stack's own 443 listener, not the seed. The ACME client version is unresolved, so a deploy with a certificate name set refuses until someone with a network resolves it (`D-227` item 1). Basis of `F-01` and the `E-1`, `E-7` rows.

### P-11 — the superuser statement of the topology ADR

- captured_at: 2026-10-26
- command: `sed -n 41,42p docs/architecture/adr/ADR-0021-production-topology-and-operations.md`
- captured_output:
  ```text
    the official PostgreSQL image that bootstrap user is a superuser (assumption: the image's
    documented behaviour; the check is the query of row 7 below). Pool 5 plus 5 overflow
  ```
- interpretation: The ADR itself records that the application's database user is the image's bootstrap superuser and marks it an assumption to be checked by the row 7 query, which needs a running stack (`could not verify`). Basis of `F-05`.

### P-12 — the no-database tests that bear on the review, run

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/test_proxy_rate_limits.py tests/contract/test_proxy_security_headers.py tests/unit/access/test_access_check_gate.py`
- captured_output:
  ```text
  .........................................................................
  .............................
  101 passed in 1.06s
  ```
- interpretation: The static pins of the proxy throttles and security headers, and the 29 unit cases of the credential gate, hold at the base commit. This says nothing about the served application or a running proxy.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`EXPOSURE-REVIEW-01.md` is not rewritten: this review supersedes it by a new document that states the present status of each of its findings.

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits on `agent/prod-15-exposure-review-02` only; nothing is pushed, tagged or published (`AGENTS.md` sections 5 and 6).

## Allowed paths

- `docs/program/EXPOSURE-REVIEW-02.md`
- `docs/program/tasks/PROD-15-EXPOSURE-REVIEW-02.md`

## Forbidden hotspots

- everything else, in particular `contracts/**`, `src/**`, `db/migrations/**`, `infra/**`, `web/**`, `tests/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `docs/program/PRODUCTION-READINESS-PLAN-01.md`, the rulings and the ADRs
- root dependency/lock files, migration head, composition root, global styles

## Non-goals

- No fix. Every finding is a recommendation with a plan item; none is made here.
- No request to any host, no container, no database, no network, no push, no change of the debt register (the proposed rows are section 10 of the review).
- No repetition of the accepted risks `A-1` to `A-8` as findings; they are cited where a finding goes beyond them.
- No probe of the live origin (the plan item's "read-only probe"): this lane had no network. The review says what that leaves unverified.

## Deliverables

- `docs/program/EXPOSURE-REVIEW-02.md`: the status table of `E-1` to `E-9`, the review by theme, the table of 24 new findings with position and evidence, the findings that stop for the owner, what was found sound, what to re-check, what could not be verified, the order of fixes with plan items, and the proposed debt rows.
- This task file.

## Required tests

- command: `PYTHONPATH=src:/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: all pass on a committed tree (one contract test refuses a dirty tree)
- command: `git diff --check <base>..HEAD`
- expected: no output
- command: `grep -c "getExecutorTaskImage\|getArV3BetaPackStatus" docs/program/EXPOSURE-REVIEW-02.md`
- expected: at least 2 (the plan item's documentation check, applied to the new document)
- command: the governance one-liner of the wave file: `PYTHONPATH=src:$BS python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/PROD-15-EXPOSURE-REVIEW-02.md',encoding='utf-8').read())))"`
- expected: `[]`

## Integration contract

The integrator may rely on: (1) the document names every finding with an id (`F-01` to `F-24`), a severity, the position needed and the file and line read; (2) the four findings that change who can reach the system are listed together (section 5) for the owner's decision; (3) the proposed debt rows (section 10) carry a check command each and are not entered; (4) the review is repeated at `PROD-17`, and section 7 lists what to re-check when `PROD-04` and `PROD-11` merge; (5) no file outside the two allowed paths is changed (`git diff --name-only <base>..HEAD`).

## Failure/idempotency/security cases

- A line reference in the review that no longer matches after a later commit is a stale pointer, not a failure of the finding; the quoted text identifies the line.
- The review quotes no secret value: the only literal secrets named are the published `admin` / `password` pair, which are public by design.
- A statement that could not be verified without running it is in section 8, not in the findings table, except where the tree itself (a comment, a register, a test name) states the fact and the finding says so.

## Rollback / feature flag

Not applicable: documents only; revert the commit.

## Handoff

- changed files: `docs/program/EXPOSURE-REVIEW-02.md`, `docs/program/tasks/PROD-15-EXPOSURE-REVIEW-02.md`
- commands/results: the docs guards, `git diff --check` and the governance one-liner are in the lane's final report; the no-database tests of P-12 passed (101)
- known limits: nothing was run against a host; the live `admin` password, the host nginx, the firewall, IPv6 publishing, the exploitability of the `next` advisory and the cipher list of the pinned image are in section 8 of the review
- integration notes: the proposed debt rows use `D-233` onward as placeholders; the numbers are the integrator's. The task text named `E-1` to `E-7`; the predecessor also carries `E-8` and `E-9`, and the review covers all nine
