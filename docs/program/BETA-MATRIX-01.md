# BETA-MATRIX-01 — static coverage matrix B1–B12 for the closed beta on test data

**Base:** `origin/dev` `fc8455f6`. **Branch:** `agent/beta-matrix-01`. **Asked for by:** `CODE-FIRST-TO-BETA.md` §3.
**Rulings:** `R-135`, `R-139`, `R-140`, `R-141`. Documentation only. No stand, container or test suite was run; the one program
executed was the read-only `tools/plan/pin_sweep.py contract-version` (exit 0). Paths and test names were read on the tree above;
anything not seen there is marked UNVERIFIED.

**Scope** (`R-141c`, `OWNER_RULINGS_2026-09-17.md` §3.41): a closed beta on test data. Accepted B1, B2, B4, B6 (local drill), B7,
B8, B9, B12; deferred by the owner, text unweakened, B3, B5, B10, B11. `R-141a` orders the publication of `59a1be91` (the `R-125`
gate completion accepted for that SHA only), `R-141b` the wipe before it. Stand state is unverified: main is `ec3ebf07`, `D-188`
says the host verifier was not run, the norms corpus is not on the stand; every stand step waits for that publication, and
evidence must name its tree (`CODE-FIRST-TO-BETA.md` §5).

**This matrix sets no PASS.** `ROADMAP-TO-BETA.md` §9 defines B1–B12 as measurements on a deployed stand; a test green on a lane
proves code, not the criterion. Verdicts: **READY-TO-ACCEPT-ON-STAND** = code and automated checks exist and the missing evidence
is a run or an owner decision named in the row; **NEEDS-CODE** = a named gap; **DEFERRED-BY-OWNER**.

## Summary

| B | Criterion | Verdict | What stands between it and acceptance |
| --- | --- | --- | --- |
| B1 | accounts, roles, registration, shell | READY-TO-ACCEPT-ON-STAND | `D-137`: identity continuation and A13–A20 never ran on a built stand |
| B2 | corpus, S3 bindings, embeddings, cited search | READY-TO-ACCEPT-ON-STAND | stand import not run (`STAND-NORMS-IMPORT-RUNBOOK-01.md` written, never executed); local proof only |
| B3 | full AR pipeline, grounded, quality | DEFERRED-BY-OWNER | — |
| B4 | durable execution, retry, resume, journal | READY-TO-ACCEPT-ON-STAND | no stand observation; a provider failure cannot be induced live |
| B5 | real AR documents end to end | DEFERRED-BY-OWNER | — |
| B6 | backup and restore drill (local) | READY-TO-ACCEPT-ON-STAND | the one synthetic drill ran at head `0023` with one Blob; repeat on the candidate head |
| B7 | deploy bound to gate, version, release history | READY-TO-ACCEPT-ON-STAND | `59a1be91` on neither dev nor main yet (`R-141a`); `D-120`; `0.5.1` history row |
| B8 | exposure review | READY-TO-ACCEPT-ON-STAND | `EXPOSURE-REVIEW-01.md` says not clean: owner decisions E-1 to E-6; fixes in `infra/**` need the gate |
| B9 | contract `1.0.0` and error catalog frozen | NEEDS-CODE | the seal itself plus `D-179` dedicated codes (§B9) |
| B10 | expert smoke sessions | DEFERRED-BY-OWNER | — |
| B11 | retained-data policy | DEFERRED-BY-OWNER | — |
| B12 | every menu destination acts, result, live acceptance | NEEDS-CODE | journey steps for the uncovered destinations (§B12), `D-180`, stale `r66.mjs` |

## B1 — accounts, roles, registration, shell

- **Code:** `src/auditmanager/access/{accounts,registrations,grant,revoke,passwords,policy,profile,unlock}.py`;
  `src/auditmanager/api/security.py` (`UNAUTHENTICATED_OPERATIONS`, `OPERATION_ROLES`); routers `auth.py`, `users.py`,
  `registrations.py`, `me.py`; web `features/{sign-in,register,decide-registration,manage-user,edit-profile,change-password}`.
- **Tests:** `tests/integration/api/test_registration_flow.py::test_the_pair_proves_a_pending_application`,
  `tests/integration/api/test_role_register.py::test_a_roleless_account_reads_no_product_data`,
  `tests/integration/access/test_registrations.py::test_approval_creates_the_account_from_the_request_in_one_transaction`,
  `tests/integration/auth/test_revocation.py::test_a_credential_stops_being_accepted_the_moment_the_account_is_revoked`;
  `web/tests/unit/shell/{screen-decision,navigation}.test.ts`, `web/tests/guards/screen-registry.guard.test.ts`.
- **Missing:** a live run of the W51 continuation and the human A13–A20 pass (`D-137`); needs a stand, an administrator
  credential and a read-only host path to the web tier's session register (`identity.mjs` fails without it, by design). After an
  `R-140` wipe only the seeded `admin` exists: its password must change before the push (`EXPOSURE-REVIEW-01.md` E-1). The live
  origin issues the cookie without `Secure` and sends no HSTS (E-2, `D-191`).
- **Command:** `E2E_PC01_LOGIN=<admin> E2E_PC01_PASSWORD=<pw> npm --prefix web run e2e:pc01 -- --origin <o> --phase all --out <d>`,
  then `E2E_PC01_SESSION_STORE_PATH=<ro-path> node tests/e2e/pc01/journey/identity.mjs --origin <o> --journey <d>/journey.json
  --out <d>/identity`; by hand A01 and A12–A20 of `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`.

## B2 — corpus, bindings, embeddings, cited search

- **Code:** `src/auditmanager/norms/{bundle,custody,embedding,search,catalogue,current_snapshot}`, router `norms.py`; web
  `_pages/norms`, `widgets/{norm-search,norm-snapshots,norm-catalogue,norm-document}`; stand verbs
  `infra/deploy/{copy-serve,receive-bundle,push-bundle,pull-copy}.sh`, `scripts/stand-copy/restore-test.sh`.
- **Tests** (under `tests/integration/norms/`): `bundle/test_bundle_postgres.py::test_postgres_an_exact_replay_is_a_no_op`,
  `custody/test_two_phase_custody.py::test_a_process_lost_at_each_interruption_point_converges`,
  `embedding/test_digest.py::test_the_digest_is_the_documented_canonical_serialisation`,
  `search/test_norm_pdf_window.py::test_the_pdf_is_served_only_through_a_confirmed_binding`.
- **Evidence in hand (local only):** `W54-LOCAL-IMPORT-01.md` — 674 documents, 61,573 embedding windows, 28,920 admissions
  confirmed and bound, 0 incidents, digests `match`; search, document and ranged PDF served from an isolated stack.
- **Missing:** the same on the stand: the owner's instruction naming the bundle digest, the two owner-installed keys, about 22 GB
  of disk if staging and Docker share a filesystem (stand free space UNVERIFIED), the 0.7.0 deployment first, then an
  administrator designates the snapshot. The runbook's section 9: no document records `receive`, `import`, `report` or `attest
  --test-data` on any stand, and the bundle was last imported at head `0023`, not `0027`. Weakeners: `D-124`, `D-127`, `D-158`.
  Project crops (the other half of "every crop") exist only after a run; custody test
  `tests/integration/ingest/test_reconciliation_custody_blobs.py`, not seen on a stand.
- **Command:** `STAND-NORMS-IMPORT-RUNBOOK-01.md` §0–§6: `push-bundle.sh`, `copy attest --test-data`, `inbound import`, `inbound
  report` (exit 0, `full match`), `copy resume`, `setCurrentNormSnapshot`, the §6 probe table («ГОСТ 10140», «СП 54 п. 7.1» not
  «п. 7.1.4», «открыть» answering `206`), `copy verify-objects 100`.

## B3, B5, B10, B11 — deferred by the owner (what exists, so the deferral stays visible)

- **B3:** recorded-only AR v2 chain (`src/auditmanager/runs/recorded_v2_*.py`, `tests/integration/findings/test_v2_recorded_chain.py`);
  13 section profiles are `draft` (`D-178`, `D-183`); the live model pin is stopped (`W56A-MODEL-PIN-01`); `D-167` is in-sample.
- **B5:** the 500-page / 250 MiB envelope and the input-budget refusal are tested (`tests/integration/ingest/test_size_guard_boundary.py`,
  `tests/integration/runs/test_input_budget.py`); no real document was run; `D-162`, `D-171`, `D-175` open. **B10:** protocol
  `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`, experts `OD-18`. **B11:** `infra/deploy/reset.sh`, `R-109`, `R-110`; `U-04`, `D-156` open.

## B4 — durable execution

- **Code:** `src/auditmanager/jobs/{repository,lease,commands,events}.py`; `src/auditmanager/runs/{executor,retry,reconciliation}.py`
  (`ATTEMPT_BUDGET`, backoff; the loop re-asks only a call the provider did not process); `src/auditmanager/workers/{service,registry}.py`;
  `src/auditmanager/execution/public.py` (journal projection); web `widgets/execution-journal`,
  `entities/execution/model/presentation.ts` (labels such as «Вызов не обработан»).
- **Tests:** `tests/integration/runs/test_retry_policy.py::test_an_unreachable_provider_is_retried_and_the_run_still_publishes`,
  `tests/integration/workers/test_worker_service.py::test_a_killed_workers_run_is_reclaimed_and_finished_by_another_worker`,
  `tests/integration/jobs/test_d150_and_worker_claims.py::test_a_live_prepared_effect_still_fails_the_run`,
  `tests/integration/qa_w53/test_queue_and_effect_journal.py::test_lease_reclaim_journals_the_effect_outcome`;
  `web/tests/unit/execution/execution-screens.test.ts`.
- **Missing:** (a) any stand observation. (b) By design a live worker killed during a provider call ends the run as
  `provider_outcome_unknown`; only a recorded call (`D-150`) or a stage boundary resumes (`infra/deploy/README.md`, "The worker
  service"), so «restart resumes» is shown by killing the worker in the deterministic stages. (c) A provider failure cannot be
  induced on the live stand; its evidence is the DB-backed tests or a local fault-injecting proxy. (d) That a retry shows on the
  Журнал screen live is UNVERIFIED (`provider.not_processed`, `attempt.*` are in its vocabulary). Open: `D-169`, `D-155`.
- **Command:** stand, host operator: start a run through the journey, then `docker compose --env-file infra/deploy/env/alpha.env
  -f infra/deploy/compose.server.yml kill -s KILL worker` in the deterministic stages; after the 60 s lease read `/workers` and
  `/logs` (a new `wrk_…` identity, a terminal run). Local: `scripts/rehearsal/w53/{process_recovery,proxy_faults}.py` on a
  disposable `w53_rehearsal*` database, written for head `0017`, UNVERIFIED at `0027`.

## B6 — backup and restore, local drill

- **Code:** `scripts/recovery/{synthetic_drill_fixture,synthetic_drill_runner,isolated_restore_drill,isolated_postgres_restore,
  target_object_restore,target_blob_readback,blob_reference_audit}.py`, `scripts/stand-copy/restore-test.sh`, `infra/deploy/reset.sh`.
- **Tests** (under `tests/integration/recovery/`): `test_synthetic_drill_runner.py::test_nonempty_bucket_refuses_before_engine_or_restore`,
  `test_isolated_restore_drill.py::test_coordinator_restores_db_before_target_write_then_reads_all_target_bytes`,
  `test_blob_reference_audit.py::test_healthy_database_returns_all_available_blob_facts_and_reads_only`.
- **Evidence in hand:** `W58-INT-RELATIONS-PLACEHOLDER-FIX-01.md` — one real synthetic run (head `0023`, one 58,978-byte Blob,
  fresh target-02): `target_objects 1`, `target_blobs 1`, equal byte counts. Its own limits: not an attested stand copy, not
  complete W58/B6; the W58 seal keeps no source-S3 role, media type or custom metadata.
- **Missing:** the drill on the candidate head `0027` (fingerprint block and emptiness query last driven at `0023`), and the owner's
  judgement whether one synthetic Blob is a B6 drill or a larger source (the W54 local stack held 28,920 objects) is wanted.
  `D-123` (stand MinIO never inventoried) stays outside a local drill.
- **Command:** the operator lane of `W58-INT-SYNTHETIC-DRILL-CLI-01.md` (source `make up check-services migrate check-db`, seed,
  `pg_dump`, `python -m scripts.recovery.synthetic_drill_fixture`, `offline_restore_preflight`, then `python -m
  scripts.recovery.synthetic_drill_runner --copy-dir … --objects-root … --target-env … --pg17-bin /usr/lib/postgresql/17/bin`);
  its candidate Postgres ports `57581/57582` lie in the range the common brief reserves, so pick a free pair with `ss -ltn`.

## B7 — deploy bound to gate, version endpoint, release history

- **Code:** `VERSION` (`0.6.0` on dev); `src/auditmanager/releases/{product_version,build_id,load,notes,versioning,repository}.py`;
  `src/auditmanager/api/routers/releases.py` (`getProductVersion` `GET /system/version`, `listReleases`, `markReleaseNotesRead`);
  `release-notes/{0.2.0,0.3.0,0.4.0,0.5.0,0.5.1,0.6.0}.json`; `docs/program/RELEASES.md` (ledger rows `v0.4.0`–`v0.6.0`);
  `.github/workflows/deploy-auto.yml`, `infra/deploy/verify-deployed.sh`; web `widgets/version-history`, `_app/release-notices.tsx`.
- **Tests:** `tests/integration/releases/test_release_loader.py::test_loader_is_idempotent_and_serves_the_highest_revision`,
  `tests/integration/api/test_release_routes.py::test_stage_c_adapter_serves_the_running_version_and_visible_history`,
  `tests/contract/release_notes/test_release_notes_form.py::test_authored_shape_and_form`,
  `tests/contract/test_deploy_auto_workflow.py::test_trigger_sha_is_selected_before_deploy_and_verified_afterwards`,
  `web/tests/unit/release/history.test.ts`.
- **Missing:** (1) `59a1be91` (`agent/release-0-7-0-notes-01`) is not an ancestor of dev; main is `ec3ebf07` (`D-188`); nothing
  serves `0.7.0` or a `v0.7.0` tag until `R-141a` is carried out. (2) "Bound to the gate" is a process rule (`D-120`, `R-73`), not a
  mechanism; for this SHA `R-141a` accepts the `R-125` completion (`NIGHT-1020-GATE-0-7-0-01.md`, `D-189`, `D-190`) instead of a
  literal `GATE OK`. (3) `release-notes/0.5.1.json` is served as a release but has no tag, no ledger row and no ruling like
  `R-86`'s (`0.3.0` only): the owner rules archive or accept. (4) `build_id` is a content digest, not a git revision (`D-121`).
- **Command:** after the owner's exact-SHA instruction, per `RELEASE-0-7-0-DEPLOY-STEPS-01.md`: workflow green,
  `infra/deploy/verify-deployed.sh` exit `0` on the host, `make alpha-acceptance` (its `apiBuild` phase reads `getProductVersion`
  and must say PASS), `git ls-remote origin 'refs/tags/v0.7.0^{}'` equals the deployed SHA, account menu «История версий» lists
  `0.1–0.2, 0.3.0, 0.4.0, 0.5.0, 0.5.1, 0.6.0, 0.7.0` and nothing invented.

## B8 — exposure review

- **Code and tests:** `src/auditmanager/api/security.py` (three unauthenticated operations: `issueToken`, `submitRegistration`,
  `readRegistrationStatus`), `infra/deploy/compose.server.yml` (only the proxy publishes a port), `infra/deploy/proxy/nginx.conf`,
  web `app/bff/**`; `tests/integration/api/test_authorization.py::test_the_open_surface_is_exactly_the_register`,
  `tests/integration/api/test_role_register.py::test_every_guarded_operation_is_in_the_role_register`,
  `tests/contract/test_proxy_security_headers.py`, `tests/contract/test_proxy_rate_limits.py`: all 81 operations.
- **Evidence in hand:** `EXPOSURE-REVIEW-01.md` (2026-10-21, read-only, 102 GET/HEAD/OPTIONS requests): no unintended port answers,
  no product data or API description without a credential, no CORS, no source maps. Its verdict is **not clean**; owner decisions:
  E-1 HIGH the seeded `admin`/`password` pair is public until changed (order now fixed in `RELEASE-0-7-0-DEPLOY-STEPS-01.md`);
  E-2 live cookie without `Secure`, no HSTS (`D-191`); E-3 one shared throttle bucket behind the host terminator (inference);
  E-4 `POST /api/v1/auth/token` unthrottled per address (`D-192`); E-5 260 MiB buffered before the 401 (`D-165`, `D-192`);
  E-6 the host also serves another application. E-7 (terminator and firewall not in the tree) and E-8 (stale text, `D-193`) are low.
- **Missing:** those decisions; the live `admin` password state (not probed); the same probe table re-run on the 0.7.0 stand;
  `D-176`, `D-166`, `D-122` still open. A fix that touches `infra/**` (`Secure` forwarding, the token throttle, upload buffering)
  is NEEDS-CODE with a full gate if the owner chooses to fix rather than accept.
- **Command:** the reproducible curl rows of `EXPOSURE-REVIEW-01.md` Part 2 against the 0.7.0 origin; `infra/deploy/readiness.sh`
  `default-credential` check on the host (expects `access-check OK no default credentials`); `./scripts/manual-alpha-check.sh
  --origin <o> --preflight-only`; host `ss -ltnp`.

## B9 — contract `1.0.0` and error catalog frozen

State now: `contracts/api/v1/openapi.json` `info.version` and every `contract_version` read `1.0.0-draft.1`; the catalog
`contracts/domain/v1/error-codes.json` is `status: draft_candidate`, `frozen: false`, revision 17, 25 codes; surface 71/81/235.

**What the seal changes** (one owner of contract, migration head, `FRONTEND_LOCK`, `tests/support/**`; one full gate, §8 case 3):

- `contracts/api/v1/openapi.json` (2 occurrences) and its byte-identical copy `web/openapi/openapi.json`;
  `contracts/domain/v1/{error-codes,identifiers,state-machines}.json`, their schemas and `error-envelope.schema.json`;
  `status`, `frozen`, `supersedes` in the catalog; `contracts/analysis/v1/*` (12 files) and `contracts/events/v1/*` only if those
  families move too (undecided, `ROADMAP-TO-BETA.md` §8.2; `contracts/comparison/v1` is a README only); 10 example files.
- Code literals: `src/auditmanager/api/schemas/models.py:631` (`ErrorEnvelope.contract_version`: every error body changes on the
  wire), `src/auditmanager/api/routers/__init__.py:194`, `src/auditmanager/analysis/engine/result.py:35`,
  `infra/deploy/proxy/nginx.conf:292` and `tls-server.conf` (the edge's `429` body), `web/src/shared/api/credentialed-forward.ts:212`.
- The four generated artifacts `web/src/shared/api/generated/{client.gen,index,operations.gen,types.gen}.ts` via
  `npm --prefix web run api:generate`, and the digests in `web/FRONTEND_LOCK.json` (check: `npm --prefix web run api:verify`).
- Pins: `tests/support/expected_facts.json` (`contract_version`; `api_codes` 25 and `stored_vocabulary` 23 if codes change); literals
  in `tests/contract/api_v1/test_openapi_conformance.py`, `tests/contract/test_{alpha_acceptance_command,cp00_candidate}.py`,
  `tests/e2e/pc01/test_acceptance.py` and five files under `tests/integration/`; 37 files under `web/tests`; the five `error_catalog`
  needles of `CONTRACT_PIN_REGISTRY.md`. `python3 tools/plan/pin_sweep.py contract-version` lists 66 consumer paths today. The
  literal is also in 16 records of `tests/characterization/w13_baseline/records`, 4 of `artifacts/validation/PC-02/baseline/runs`
  and `fixtures/golden` (3 files): assert what they pin before re-capturing them.
- If codes are added: a migration widening the four stored-error CHECKs (as `0022` did), so a new head and the `migration_head`
  pin; `shared/errors/codes.py`; the `ErrorCode` enum in `models.py`; web `shared/api/{catalog-message,errors}.ts` and
  `entities/audit-run/model/terminal-reason.ts` (Russian sentences under the rendered-language guard).

**Catalogue debts to resolve first:**

- `D-179`: run start for an unclassified version or a section without a profile reuses `required_norm_unavailable` with
  `details.reference_kind` `version_classification` / `analysis_profile`; the register assigns dedicated codes to the final seal.
- Contract follow-ups registered for "the next reseal": `D-151` (OpenAPI and `P02_SEAMS.md` prose describe product reads with no
  role, `R-80`), `D-161` (`blk_<32hex>` against identifier rule 1), `D-172` (a `304` for crops; the integer rule in
  `x-envelope-rules`), `D-163`, `D-145`. Each is done in the seal or carried on purpose.
- `model_identity_mismatch` is in the catalog, the enum and the stored CHECKs but has no raise site in `src` (no
  `ErrorCode.MODEL_IDENTITY_MISMATCH`); its check waits on `W56A-MODEL-PIN-01`. `rate_limited` (edge only) and
  `analysis_input_budget_exceeded` (before any run exists) sit outside the stored vocabulary by design, per their notes. No code is
  marked "reserved": `grep -i reserved contracts/domain/v1/error-codes.json` is empty; the "reserved" in `openapi.json`
  `info.description` is `contracts/optimization/v1`, a family that does not exist.
- `open_owner_decisions` holds `OPEN-RETENTION` (`U-04`, `not_decided`, affects `idempotency_key_stale`). B11 is deferred, so the
  seal states that no retention window is declared, or the owner decides one.
- **Evidence after the seal:** `pytest tests/contract`, `npm --prefix web run api:verify`, one `make gate` with literal `GATE OK`,
  `getProductVersion.contract_version` read live.

## B12 — every menu destination: action, result, live acceptance

Menu source: `web/src/shared/config/screen-registry.ts` (`inMenu: true`) through `web/src/_app/navigation.ts` and
`account-menu.tsx`. The manifest `tests/e2e/pc01/journey/manifest.json` holds 29 read routes (cold load, declared GETs asserted),
4 write steps (`create-project`, `upload-document`, `classify-version`, `start-run`), 6 upload refusals and the identity
continuation (register, approve, verdict, role change, archive, purge, reject; never run on a built stand, `D-137`). No menu
item renders a stub: `RoutePlaceholder` is used by no page and `/optimisation` redirects to the project tab.

| Destination (role) | Action and result in code | Live manifest coverage | Not covered live |
| --- | --- | --- | --- |
| Главная `/` (any) | role tiles, pending count (admin), «Мои задачи» panel | read route `root` | — |
| Проекты `/projects` | create project, list, open | read; `create-project`, `upload-document` | — |
| Дашборд `/dashboard` | aggregate panels, section panel | read | `D-180`: the section panel groups by the legacy field |
| Оптимизация разделов | Form-7 specification per section, per-project totals | read (`getSectionSpecification`) | priced data; `qa_w50/r66.mjs` still expects «не готов» (`D-186`) |
| Диспетчер (admin, expert) | assign, start, complete, return | read (`listAssignments`) | `createAssignment`, `transitionAssignment` |
| База знаний | decision ledger | read | — |
| Блоки | blocks, crops, recognised text | read (optional calls) | needs a version that has blocks |
| Нормы | search, catalogue, document, Excel, designation | read (snapshots, events) | search; `/norms/document` (declares no call); Excel; `setCurrentNormSnapshot` |
| Журнал выполнения | journal | read | — |
| Исполнители | worker list, intake switch (admin) | read | `setWorkerIntake` |
| Настройки анализа | profile list and details | read | — |
| Очередь | queue; pause, priority, cancel, re-audit | read | all four commands |
| Пользователи (admin) | list, detail, roles, archive, reset, purge | read; `updateUser`, `archiveUser`, `purgeUser` in the continuation | `resetUserPassword`, `restoreUser` |
| Заявки (admin) | approve, reject | read; both in the continuation | — |
| Профиль (account menu) | edit names and e-mail | read (`getMe`) | `updateMyProfile` (A15 by hand) |
| Сменить пароль (account menu) | change password | read, no call | `changePassword` (by hand) |
| История версий (account menu) | side panel of releases | none (optional `listReleases` only) | unit test only: `web/tests/unit/release/history.test.ts` |
| Выйти (account menu) | `POST` session close | none | A12 by hand; keys only in `qa_w50/keyboard.mjs` |

Reached from inside, uncovered live: `uploadDocumentVersion`, `compareDocumentVersions` (and the П→Р view), `carryOverDecision`, the
project «Оптимизация» tab (`uploadPriceList`, both vendor lists, `startOptimisationPass`, `decideOptimisationProposal`, the CSV),
`exportRunCsv`/`exportRunXlsx` (A07 by hand), `reauditRun`, `cancelRun`. `BETA-LIVE-JOURNEY-01` is a frozen task with no report yet.

- **Tests:** `tests/e2e/test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers`;
  `web/tests/guards/{screen-registry,screen-set,prepared-sections}.guard.test.ts`; per screen `web/tests/unit/{dispatcher,execution,
  norms,sections,section-specification,optimisation,optimisation-proposals,comparison,workers,release,session,shell}`; backend
  `tests/integration/{dispatch,optimisation,sections,comparison,exports}`.
- **Missing:** the live steps above; `D-180`; `r66.mjs`; and "the full АР function matrix is tested", which no document in the tree
  defines (UNVERIFIED). On the stand the write half starts a run, a credentialed live provider call under the `R-29` ceiling; a
  recorded local stack costs nothing but is not stand evidence.
- **Command:** `npm --prefix web run e2e:pc01 -- --origin <o> --phase all` once `BETA-LIVE-JOURNEY-01` has extended it, and
  `./scripts/manual-alpha-check.sh --origin <o> --interactive` for A01–A20 (A09: 27 screens at 780 × 900).
