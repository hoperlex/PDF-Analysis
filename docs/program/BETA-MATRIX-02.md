# BETA-MATRIX-02 — static coverage matrix B1–B12, refreshed to the tree `origin/dev` `d087c101`

**Base:** `origin/dev` `d087c101` (the freeze commit of the task; `git ls-remote origin refs/heads/dev`). **Branch:**
`agent/beta-matrix-02`. **Task:** `docs/program/tasks/BETA-MATRIX-02.md`. **Refreshes:** `BETA-MATRIX-01.md` (base `fc8455f6`,
2026-10-21), which stays as written, as the record of that day. **Asked for by:** `CODE-FIRST-TO-BETA.md` §3.
**Rulings:** `R-135`, `R-141c`, `R-141e`, `R-142`, `R-144d`, and the owner's standing order of 2026-10-22 «гони до беты без вопросов».
Documentation only. No stand, container, build or test suite was run. The commands that executed anything are quoted with their
results in §1: `git` reads (including `git ls-remote`, a read-only network call), `ls`/`grep`/`sed`/`wc`/`md5sum`, and read-only parses
of JSON files with `python3 -I`; the one test command is
`python3 -m pytest -q tests/contract/program` (result under "Hotspots and limits"). Every path and test name below was checked with `ls`/`grep`
on `d087c101`; anything not seen there is marked UNVERIFIED.

**Scope** (`R-141c`, `OWNER_RULINGS_2026-09-17.md` §3.41): a closed beta on test data. Accepted: B1, B2, B4, B6 (local drill), B7,
B8, B9, B12. Deferred by the owner, text unweakened: B3, B5, B10, B11. `R-141e` cancelled the `59a1be91` publication and the 0022
purge; the owner's own pull requests #2, #3 and #4 moved `origin/main` instead (§1). Stand state is not readable from the tree:
every statement about the stand is UNVERIFIED unless a record is named.

**This matrix sets no PASS.** `ROADMAP-TO-BETA.md` §9 defines B1–B12 as measurements on a deployed stand; a test green on a lane
proves code, not the criterion. Verdicts keep the classes of `BETA-MATRIX-01`: **READY-TO-ACCEPT-ON-STAND** = code and automated
checks exist and the missing evidence is a run, an expert, real documents, a policy or an owner decision named in the row;
**NEEDS-CODE** = a named gap in code or in the tests that guard it; **DEFERRED-BY-OWNER**.

## Summary

| B | Criterion | Verdict now | Was (01) | What stands between it and acceptance |
| --- | --- | --- | --- | --- |
| B1 | accounts, roles, registration, shell | READY-TO-ACCEPT-ON-STAND | same | `D-137`: the identity continuation and A13–A20 never ran on a built stand |
| B2 | corpus, S3 bindings, embeddings, cited search | READY-TO-ACCEPT-ON-STAND | same | the stand import has not run (runbook written, never executed; it still names `59a1be91` and head `0027`); local proof only |
| B3 | full AR pipeline, grounded, quality | DEFERRED-BY-OWNER | same | — |
| B4 | durable execution, retry, resume, journal | READY-TO-ACCEPT-ON-STAND | same | no stand observation; a provider failure cannot be induced live |
| B5 | real AR documents end to end | DEFERRED-BY-OWNER | same | — |
| B6 | backup and restore drill (local) | READY-TO-ACCEPT-ON-STAND | same | the real drill ran at head `0028` with 23 Blobs and again at head `0029` (`RECOVERY-DRILL-0029-01`: 23 of 23 objects and Blobs, 55 tables, 4 views, 72 triggers equal, independent compare no differences; recovery suite 308 passed); owner judges whether synthetic data is a B6 drill |
| B7 | deploy bound to gate, version, release history | READY-TO-ACCEPT-ON-STAND | same | main carries `0.7.0` at `44962e8d` but the ledger row names `48c8e34c`; host verifier pending; no `v0.7.0` tag; no literal `GATE OK`; `0.5.1` row unruled |
| B8 | exposure review | READY-TO-ACCEPT-ON-STAND | same | E-1, E-2, E-6 are owner decisions; E-3 needs an operator setting; E-4, E-5, E-8 are fixed in code and not re-probed on a stand |
| B9 | contract `1.0.0` and error catalogue frozen | READY-TO-ACCEPT-ON-STAND | NEEDS-CODE | sealed on dev and main; missing: `contract_version` read from a deployed stand and one complete gate (`R-135`) |
| B10 | expert smoke sessions | DEFERRED-BY-OWNER | same | — |
| B11 | retained-data policy | DEFERRED-BY-OWNER | same | — |
| B12 | every menu destination acts, result, live acceptance | READY-TO-ACCEPT-ON-STAND (integrator, 2026-10-22, after `PC01-JOURNEY-GAPS-01`) | NEEDS-CODE | 10 of 14 menu destinations and all four account-menu actions have walked write steps, on a recorded local stack only; «Заявки» acts only in the identity continuation, «База знаний» and «Журнал выполнения» are read-only, «Блоки» has a cold load and no action step; the stand's acceptance script runs the `core` phase only |

## 1. Measured on the tree

Tree: the worktree `.local/worktrees/lane-f` at `d087c101` (`git rev-parse HEAD`), clean before this document. Every row names its
command.

| Fact | Value | Command |
| --- | --- | --- |
| `origin/dev`, `origin/main` | `d087c101d6ee0e1d58a7e595a3f1dcb2989718b3`, `44962e8d9ba91f189a9d3d5bf6955c25b5612c34` ("Merge pull request #4 from hoperlex/dev") | `git ls-remote origin refs/heads/main refs/heads/dev` |
| main against dev | main is an ancestor of dev; the diff is 8 files, all under `docs/` (ADR-0002, `EXEC-ADR-01.md`, rulings, two dispatch plans, three task files) | `git merge-base --is-ancestor origin/main HEAD`; `git diff --name-only origin/main HEAD` |
| main's own facts | `VERSION` `0.7.0`; `openapi.json` `info.version` `1.0.0`; `expected_facts.json` head `0029_routing_refusal_codes`, `contract_version` `1.0.0` | `git show origin/main:VERSION`; `git show origin/main:contracts/api/v1/openapi.json`; `git show origin/main:tests/support/expected_facts.json` |
| main against `48c8e34c` (the SHA the ledger names) | PR #4 added 243 files, 16,895 insertions: the seal, the hardening, the purge tool, the recovery pin | `git diff --shortstat 48c8e34c origin/main` |
| deploy workflow on main | byte-identical to dev's, with `</dev/null` on both child scripts (`D-188`'s repair) | `git show origin/main:.github/workflows/deploy-auto.yml \| md5sum` against `md5sum .github/workflows/deploy-auto.yml` |
| `59a1be91` | exists as an object, is not an ancestor of dev; cancelled by `R-141e` | `git merge-base --is-ancestor 59a1be91 HEAD` (false) |
| tags on `origin` | `v0.4.0`, `v0.5.0`, `v0.6.0`; no `v0.7.0` | `git ls-remote --tags origin 'v0.7*'` (empty); `git ls-remote --tags origin` |
| `VERSION` | `0.7.0` | `cat VERSION` |
| release notes | `0.2.0, 0.3.0, 0.4.0, 0.5.0, 0.5.1, 0.6.0, 0.7.0` `.json` plus `dictionary.json`, `schema.json`; `0.7.0` is `revision` 2, dated 2026-10-21 | `ls release-notes`; JSON read of `release-notes/0.7.0.json` |
| API surface | 73 paths / 83 operations / 242 schemas; the same count in `openapi.json` itself | JSON read of `tests/support/expected_facts.json` (`surface.path_count`, `len(operations)`, `schema_names`) and of `contracts/api/v1/openapi.json` |
| error codes | 27 in the catalogue; `api_codes` 27, `stored_vocabulary` 25 | `len(codes)` of `contracts/domain/v1/error-codes.json`; `expected_facts.json` `error_catalog` |
| contract version | `contracts/api/v1/openapi.json` `info.version` `1.0.0`; catalogue `contract_version` `1.0.0`, `supersedes` `1.0.0-draft.1`, `candidate_revision` 19, `status` `frozen`, `frozen` true; `identifiers.json` and `state-machines.json` also `frozen` | JSON reads; `grep -m1 '"status"' contracts/domain/v1/*.json` |
| migration head | `0029_routing_refusal_codes` (`db/migrations/versions/20261021_0029_routing_refusal_codes.py`); `expected_facts.json` `migration_head` equal; `scripts/recovery/schema_coverage.py` `HEAD` equal | `ls db/migrations/versions \| tail`; `grep -n '^HEAD' scripts/recovery/schema_coverage.py` |
| PC-01 journey manifest | 29 read routes, 95 write steps, 6 upload-refusal cases, an identity continuation of 11 operations and 8 manual steps (A13–A20) | JSON read of `tests/e2e/pc01/journey/manifest.json` (`len(routes)`, `write.steps`, `refusals.cases`, `identity.operations`, `identity.manual_steps`) |
| journey conformance file | 118 test functions (counted, not run) | `grep -c '^def test_' tests/e2e/test_pc01_journey_conformance.py` |
| menu | 14 menu destinations (`inMenu: true`) and 16 screens outside it; the account menu offers «Профиль», «Сменить пароль», «История версий», «Выйти» | `grep -c "inMenu: true" web/src/shared/config/screen-registry.ts`; `sed -n 100,130p web/src/_app/account-menu.tsx` |
| stubs | `RoutePlaceholder` is defined and exported by `web/src/shared/ui` and rendered by no page; `/optimisation` is a pointer that redirects to the projects list | `grep -rn RoutePlaceholder web/src web/tests`; `sed -n 1,30p web/src/app/optimisation/page.tsx` |
| section profiles | 13 text profiles, every `profile.json` says `"status": "draft"`: `ai eom gp itp kj km ov pos ps pt ss tx vk`; AR is `analysis/profiles/{ar_v2,ar_v3}`; none for ПБ (`CURRENT_STATE.md`) | `ls src/auditmanager/analysis/text/profiles`; `grep -m1 '"status"' …/profiles/*/profile.json` |
| recordings | one JSON each under `fixtures/recorded/sections/{ai,pos,ps,tx,ar_specification}`; `fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json` and the variants `over_budget`, `truncated`, `ungrounded_quotation`; no recording for the other nine sections (`D-183`) | `find fixtures/recorded -maxdepth 2` |
| `model_identity_mismatch` | in the catalogue and both enums (`api/schemas/models.py:481`, `shared/errors/codes.py:48`); no raise site in `src` | `grep -rn model_identity_mismatch src` |
| executor line | no `src/auditmanager/executors/`; no `EXEC-*` code on the tree (`EXEC-ADR-01` is documentation) | `ls src/auditmanager/executors` (absent) |
| register rows read | `D-179`, `D-180`, `D-151`, `D-161`, `D-158`, `D-169`, `D-173`, `D-176`, `D-192`, `D-193` are struck through (closed) | `grep -n -E '^\| (~~)?D-(179\|180\|151\|161\|158\|169\|173\|176\|192\|193)' docs/program/DEBT_REGISTER.md` |

## 2. What changed since BETA-MATRIX-01

Each stale claim, with the old and the new value, and the command that shows the new one (§1 has the rest).

| # | Claim in `BETA-MATRIX-01` | Old | Now |
| --- | --- | --- | --- |
| 1 | base, API surface | `fc8455f6`; 71 paths / 81 operations / 235 schemas | `d087c101`; 73 / 83 / 242. Two operations were added and none removed: `getRunNormReferences` (`GET /runs/{run_id}/norm-references`) and `correctVersionClassification` (`POST …/classification/corrections`) (`git show fc8455f6:tests/support/expected_facts.json` against the tree) |
| 2 | migration head | `0027_optimisation_proposals`; B6 asks for a drill on "the candidate head `0027`" | `0029_routing_refusal_codes`; `0028` added `document_version_classification_correction`, `0029` widened four stored-error `CHECK`s |
| 3 | error catalogue | `status: draft_candidate`, `frozen: false`, revision 17, 25 codes | `status: frozen`, `frozen: true`, revision 19, 27 codes (`version_classification_required`, `section_profile_unavailable`); stored vocabulary 23 → 25 |
| 4 | contract version | `1.0.0-draft.1` in `openapi.json` and every `contract_version` | `1.0.0` everywhere it is declared; the one test that reads every holder is `tests/contract/api_v1/test_contract_seal.py` (`BETA-CONTRACT-SEAL-01.md`) |
| 5 | B9 verdict | NEEDS-CODE: "the seal itself plus `D-179`" | the seal is done (§B9); `D-179`, `D-151`, `D-161` are closed; `D-145`, `D-163`, `D-172` are carried on purpose past the seal |
| 6 | B12 verdict and the uncovered list | NEEDS-CODE; manifest of 4 write steps; uncovered: dispatcher commands, queue commands, `setWorkerIntake`, `setCurrentNormSnapshot`, `resetUserPassword`, `restoreUser`, `updateMyProfile`, `changePassword`, history panel, sign-out, uploads of versions, comparison, carry-over, the optimisation tab, exports, `reauditRun`, `cancelRun` | 95 write steps (`BETA-LIVE-JOURNEY-01.md`): every item in that list has a step, including the queue, the workers, the dispatcher, the password, the profile, the history panel, sign-out and the user acts; what is still unwalked is in §B12 |
| 7 | `D-180` (dashboard section panel groups by the legacy field) | open | closed by `CLASSIFICATION-CORRECTION-01` (`a2140f5d`); the journey step `dashboard-sections-panel` reads the confirmed count |
| 8 | `r66.mjs` "stale" (`D-186`) | expects «не готов» | retyped from `screen-registry.ts`, prints `R-66 OK`, two quoted mutations (`BETA-LIVE-JOURNEY-01.md`; `git log` of `tests/e2e/pc01/qa_w50/r66.mjs`) |
| 9 | `VERSION` and release notes | `0.6.0`; notes up to `0.6.0` | `0.7.0`; `release-notes/0.7.0.json` revision 2 |
| 10 | `59a1be91` | "the `R-125` gate completion accepted for that SHA only"; "on neither dev nor main yet" (`R-141a`) | superseded by `R-141d` and cancelled by `R-141e`; not an ancestor of dev; the owner merged `dev` into `main` through pull requests #2, #3 and #4 |
| 11 | main | `ec3ebf07`; `D-188`: host verifier not run | `44962e8d` (PR #4, 2026-10-22 09:32 +03:00), which carries `0.7.0`, the seal, head `0029` and the deploy workflow's stdin repair; whether its workflow ran green and whether `verify-deployed.sh` passed on the host is UNVERIFIED: no document in the tree records PR #4 |
| 12 | B6 evidence | one synthetic drill at head `0023`, one Blob | `RECOVERY-REBASE-01.md`: the drill rebased onto `0028`, run once: 23 objects = 23 Blobs, 271,413 bytes, 55 tables, 4 views, 72 triggers; `scripts/recovery/schema_coverage.py` `HEAD` then moved to `0029` (`345ac443`) |
| 13 | B8 weaknesses | E-4 (token unthrottled), E-5 (260 MiB buffered before the 401), E-8 (stale text) open | closed in code by `HARDEN-AUTH-EDGE-01` (`D-192`, `D-193`); E-3 has its code in `REAL-IP-EDGE-01` and waits for an operator setting; `D-165` stays open on the web tier side |
| 14 | `D-158` (search shares the API pool), `D-176` (revoked credential at the upload door), `D-169` (a killed run says nothing), `D-173` | open | closed by `ACCESS-STORAGE-HARDEN-01`, `API-FOLLOWUPS-01`, `RUN-ROBUSTNESS-01`, `WEB-FOLLOWUPS-01` (register rows) |
| 15 | the stand's acceptance script | "`manual-alpha-check.sh --origin <o> --interactive` for A01–A20" with `e2e:pc01 --phase all` | the script calls `--phase core` (`scripts/manual-alpha-check.sh:394`, `3cc12d46`); `--phase all` refuses an origin whose provider is not `recorded` unless `--allow-spend` is given (`tests/e2e/pc01/journey/README.md`, "Where it will not run") |
| 16 | the B2 runbook preconditions | head `0027`, main `59a1be91` | stale inside `STAND-NORMS-IMPORT-RUNBOOK-01.md` §0 item 1 and §9; the head is `0029` and the deployed SHA is whatever main's workflow deployed. The runbook is not edited by this slice |
| 17 | statements in `CURRENT_STATE.md` and `RELEASES.md` | "main still serves `1.0.0-draft.1`" (`CURRENT_STATE.md`); the `v0.7.0` ledger row: `48c8e34c`, head `0028`, contract `1.0.0-draft.1`, `build_id` `bbbab3c0dfb856a39` | main is `44962e8d`, serving `1.0.0` at head `0029`; the row and the sentence describe the tree of PR #3. Both belong to the integrator; reported, not edited |

## B1 — accounts, roles, registration, shell

- **Code:** `src/auditmanager/access/{accounts,registrations,grant,revoke,passwords,policy,profile,unlock}.py`;
  `src/auditmanager/api/security.py` (`UNAUTHENTICATED_OPERATIONS`, `OPERATION_ROLES`); routers `auth.py`, `users.py`,
  `registrations.py`, `me.py` under `src/auditmanager/api/routers/`; web `features/{sign-in,register,decide-registration,manage-user,
  edit-profile,change-password}`. New since 01: the per-app revocation memory at the upload door (`D-176`, closed).
- **Tests:** `tests/integration/api/test_registration_flow.py::test_the_pair_proves_a_pending_application`,
  `tests/integration/api/test_role_register.py::test_a_roleless_account_reads_no_product_data`,
  `tests/integration/access/test_registrations.py::test_approval_creates_the_account_from_the_request_in_one_transaction`,
  `tests/integration/auth/test_revocation.py::test_a_credential_stops_being_accepted_the_moment_the_account_is_revoked`;
  `web/tests/unit/shell/{screen-decision,navigation}.test.ts`, `web/tests/guards/screen-registry.guard.test.ts`.
  Browser steps on the recorded stack: `profile-update`, `password-change`, `user-archive`, `user-restore`, `user-password-reset`,
  `sign-out`, `signed-out-session-is-gone` of the manifest (§B12).
- **Missing:** a live run of the W51 identity continuation (`manifest.identity`: `submitRegistration`, `approveRegistration`,
  `updateUser`, `rejectRegistration`, `purgeUser`, a revoked request) and the human A13–A20 pass (`D-137`); needs a stand, an
  administrator credential and a read-only host path to the web tier's session register (`identity.mjs` fails without it, by design).
  The report of `BETA-LIVE-JOURNEY-01` does not record a run of `identity.mjs`: UNVERIFIED that it ever ran after W51. The seeded
  `admin`/`password` pair is public (E-1): `R-141d` records the owner's statement that the administrator's data "is already changed",
  and no tree record shows the live state, so it is UNVERIFIED. The live origin issued the cookie without `Secure` and sent no HSTS when
  `EXPOSURE-REVIEW-01.md` probed it on 2026-10-21 (E-2, `D-191` open); not re-probed.
- **Command:** `E2E_PC01_LOGIN=<admin> E2E_PC01_PASSWORD=<pw> npm --prefix web run e2e:pc01 -- --origin <o> --phase core --out <d>`, then
  `E2E_PC01_SESSION_STORE_PATH=<ro-path> node tests/e2e/pc01/journey/identity.mjs --origin <o> --journey <d>/journey.json --out
  <d>/identity` (whether a `core` envelope satisfies `identity.mjs` is UNVERIFIED; it requires `journey.write.ran` and a captured run);
  by hand A01 and A12–A20 of `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`.

## B2 — corpus, bindings, embeddings, cited search

- **Code:** `src/auditmanager/norms/{bundle,custody,embedding,search,catalogue,current_snapshot}`, router `norms.py`; web
  `_pages/norms`, `widgets/{norm-search,norm-snapshots,norm-catalogue,norm-document}`; stand verbs
  `infra/deploy/{copy-serve,receive-bundle,push-bundle,pull-copy}.sh`, `scripts/stand-copy/restore-test.sh`. New since 01: the search
  bulkhead (`src/auditmanager/norms/search/capacity.py`, `D-158` closed) and the catalogue with derived display designations
  (`tests/integration/norms/search/test_display_designation_window.py`).
- **Tests** (under `tests/integration/norms/`): `bundle/test_bundle_postgres.py::test_postgres_an_exact_replay_is_a_no_op`,
  `custody/test_two_phase_custody.py::test_a_process_lost_at_each_interruption_point_converges`,
  `embedding/test_digest.py::test_the_digest_is_the_documented_canonical_serialisation`,
  `search/test_norm_pdf_window.py::test_the_pdf_is_served_only_through_a_confirmed_binding`, `search/test_search_bulkhead.py`.
- **Evidence in hand (local only):** `W54-LOCAL-IMPORT-01.md` — 674 documents, 61,573 embedding windows, 28,920 admissions confirmed
  and bound, 0 incidents, digests `match`; search, document and ranged PDF served from an isolated stack at head `0023`
  (`W54-LOCAL-IMPORT-01.md` line 21).
- **Missing:** the same on the stand: the owner's instruction naming the bundle digest, the two owner-installed keys (`R-142d`: none
  installed), about 22 GB of disk if staging and Docker share a filesystem (stand free space UNVERIFIED), the deployment verified
  first, then an administrator designates the snapshot. The runbook's §9: no document records `receive`, `import`, `report` or `attest
  --test-data` on any stand. The runbook still carries the cancelled `59a1be91` and head `0027` in §0 and §9; the importer refuses a
  database not at head (`database_not_at_head`), so the first import runs at `0029` and no run at that head exists. Weakeners:
  `D-124`, `D-127`. Project crops (the other half of "every crop") exist only after a run; custody test
  `tests/integration/ingest/test_reconciliation_custody_blobs.py`, not seen on a stand.
- **Command:** `STAND-NORMS-IMPORT-RUNBOOK-01.md` §0–§6: `push-bundle.sh`, `copy attest --test-data`, `inbound import`, `inbound report`
  (exit 0, `full match`), `copy resume`, `setCurrentNormSnapshot`, the §6 probe table («ГОСТ 10140», «СП 54 п. 7.1» not «п. 7.1.4»,
  «открыть» answering `206`), `copy verify-objects 100`.

## B3, B5, B10, B11 — deferred by the owner (what exists, so the deferral stays visible)

- **B3:** recorded-only AR v2 chain (`src/auditmanager/runs/recorded_v2_{merge,publication,sources,stage}.py`,
  `tests/integration/findings/test_v2_recorded_chain.py`); the 13 section profiles are `draft` (`D-178`; §1), the recordings cover
  four of them with synthetic data only (`D-183`); the live model pin is stopped (`W56A-MODEL-PIN-01`) and `model_identity_mismatch` has
  no raise site (§1); `D-167` is in-sample.
- **B5:** the 500-page / 250 MiB envelope and the input-budget refusal are tested (`tests/integration/ingest/test_size_guard_boundary.py`,
  `tests/integration/runs/test_input_budget.py`); no real document was run; `D-162`, `D-171`, `D-175` open.
- **B10:** protocol `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`; experts `OD-18`.
- **B11:** `infra/deploy/reset.sh`, `R-109`, `R-110`; `U-04`, `D-156` open. New: the operator tool `infra/deploy/purge-product-data.sh`
  (`STAND-PURGE-TOOL-01.md`; `tests/integration/recovery/test_product_purge.py`, `test_product_purge_script.py`) keeps accounts and the
  corpus; it has not run on the stand, and `D-156` closes only when the operator has run it.

## B4 — durable execution

- **Code:** `src/auditmanager/jobs/{repository,lease,commands,events}.py`; `src/auditmanager/runs/{executor,retry,reconciliation}.py`
  (`ATTEMPT_BUDGET` is 3, backoff; the loop re-asks only a call the provider did not process); `src/auditmanager/workers/{service,
  registry}.py`; `src/auditmanager/execution/public.py` (journal projection); web `widgets/execution-journal`,
  `entities/execution/model/presentation.ts` (labels such as «Вызов не обработан» for `provider.not_processed`).
- **Tests:** `tests/integration/runs/test_retry_policy.py::test_an_unreachable_provider_is_retried_and_the_run_still_publishes`,
  `tests/integration/workers/test_worker_service.py::test_a_killed_workers_run_is_reclaimed_and_finished_by_another_worker`,
  `tests/integration/jobs/test_d150_and_worker_claims.py::test_a_live_prepared_effect_still_fails_the_run`,
  `tests/integration/qa_w53/test_queue_and_effect_journal.py::test_lease_reclaim_journals_the_effect_outcome`;
  `web/tests/unit/execution/execution-screens.test.ts`. New since 01: after repeated lost attempts in one stage the run names that
  stage (`D-169` closed by `RUN-ROBUSTNESS-01`; its repeated-kill tests under `tests/integration/runs`, named in the register row).
- **Missing:** (a) any stand observation. (b) By design a live worker killed during a provider call ends the run as
  `provider_outcome_unknown`; only a recorded call (`D-150`) or a stage boundary resumes (`infra/deploy/README.md`, "The worker
  service"), so «restart resumes» is shown by killing the worker in the deterministic stages. (c) A provider failure cannot be induced
  on the live stand; its evidence is the DB-backed tests or a local fault-injecting proxy. (d) That a retry shows on the Журнал screen
  live is UNVERIFIED: the route `logs` is walked cold and reads `listExecutionJournal` only. Open: `D-155`.
- **Command:** stand, host operator: start a run through the journey, then `docker compose --env-file infra/deploy/env/alpha.env -f
  infra/deploy/compose.server.yml kill -s KILL worker` in the deterministic stages; after the 60 s lease read `/workers` and `/logs`
  (a new `wrk_…` identity, a terminal run). Local: `scripts/rehearsal/w53/{process_recovery,proxy_faults}.py` on a disposable database,
  written for head `0017` (the file's own header), UNVERIFIED at `0029`.

## B6 — backup and restore, local drill

- **Code:** `scripts/recovery/{synthetic_drill_fixture,synthetic_drill_runner,isolated_restore_drill,isolated_postgres_restore,
  target_object_restore,target_blob_readback,blob_reference_audit}.py`; since 01 also `schema_coverage.py`, `synthetic_drill_seed.py`,
  `synthetic_drill_compare.py` and `product_purge.py` (`RECOVERY-REBASE-01.md` §3); `scripts/stand-copy/restore-test.sh`,
  `infra/deploy/reset.sh`.
- **Tests** (under `tests/integration/recovery/`): `test_synthetic_drill_runner.py::test_nonempty_bucket_refuses_before_engine_or_restore`,
  `test_isolated_restore_drill.py::test_coordinator_restores_db_before_target_write_then_reads_all_target_bytes`,
  `test_blob_reference_audit.py::test_healthy_database_returns_all_available_blob_facts_and_reads_only`, and the loud guard
  `test_schema_coverage.py::test_the_declared_head_is_the_alembic_head`, `::test_the_declared_schema_equals_the_migrated_schema`.
  The commit that moved the pin to `0029` (`345ac443`) says the recovery directory was 308 passed; not re-measured here.
- **Evidence in hand:** `RECOVERY-REBASE-01.md` — one real synthetic run at head `0028` on tree `a6d485cc`: a seeded dataset of 227 rows
  and 23 objects, 271,413 bytes, `target_objects 23`, `target_blobs 23`, equal bytes, 55 tables / 4 views / 72 triggers equal, an
  independent compare with no differences. Its limits (§8 there): one server with two databases, not two stacks; the `norm*` tables
  are empty; roles are not restored; not an attested stand copy; not W54-scale (28,920 objects). The older run
  (`W58-INT-RELATIONS-PLACEHOLDER-FIX-01.md`, head `0023`, one Blob) is superseded as the latest evidence.
- **Drill at `0029` (2026-10-22, `RECOVERY-DRILL-0029-01.md`, tree `c8a11c60`, lane stack, recorded provider):** exit 0 at every step, 23 of 23
  objects and 23 of 23 Blobs (271,413 bytes), 55 of 55 tables and 4 of 4 views equal (227 rows), 72 of 72 triggers equal, an independent compare with
  `differences: []`, 40 of 40 update/delete attempts refused on the 20 populated guarded tables, the four `CHECK`s that `0029` widened present on both
  sides; `tests/integration/recovery` 308 passed in 133 s; two negatives (an added and a dropped table) refused by the schema audit. Not claimed: a real stand
  backup, the stand's Blob store, `U-04`, a second compose stack, `norm*` data, roles, W54 scale.
- **Missing:** the owner's judgement whether 23 synthetic objects are a B6 drill or a larger source is wanted. `D-123` (stand MinIO never inventoried) stays outside a local drill.
- **Command:** `RECOVERY-REBASE-01.md` §9 (`make up check-services migrate check-db`, `synthetic_drill_seed`, `pg_dump`,
  `synthetic_drill_fixture --source-env`, `offline_restore_preflight`, `synthetic_drill_runner --pg17-bin /usr/lib/postgresql/17/bin`,
  `synthetic_drill_compare --probe-target-guards`); pick free ports with `ss -ltn`.

## B7 — deploy bound to gate, version endpoint, release history

- **Code:** `VERSION` (`0.7.0`); `src/auditmanager/releases/{product_version,build_id,load,notes,versioning,repository}.py`;
  `src/auditmanager/api/routers/releases.py` (`getProductVersion` `GET /system/version`, `listReleases`, `markReleaseNotesRead`);
  `release-notes/{0.2.0,0.3.0,0.4.0,0.5.0,0.5.1,0.6.0,0.7.0}.json`; `docs/program/RELEASES.md` (ledger rows `v0.4.0`–`v0.7.0`);
  `.github/workflows/deploy-auto.yml`, `infra/deploy/verify-deployed.sh`; web `widgets/version-history`, `_app/release-notices.tsx`.
- **Tests:** `tests/integration/releases/test_release_loader.py::test_loader_is_idempotent_and_serves_the_highest_revision`,
  `tests/integration/api/test_release_routes.py::test_stage_c_adapter_serves_the_running_version_and_visible_history`,
  `tests/contract/release_notes/test_release_notes_form.py::test_authored_shape_and_form`,
  `tests/contract/test_deploy_auto_workflow.py::test_trigger_sha_is_selected_before_deploy_and_verified_afterwards`,
  `web/tests/unit/release/history.test.ts`; the journey step `release-history-panel` (§B12).
- **Missing:** (1) main carries `0.7.0` since the owner's pull request #3 and now at `44962e8d` (PR #4); nothing is tagged `v0.7.0`
  (§1); host verification is pending (`RELEASES.md`, "Verification still owed" (3)); the workflow result for PR #4 is not recorded in
  the tree (UNVERIFIED). (2) The `v0.7.0` ledger row names `48c8e34c`, head `0028`, contract `1.0.0-draft.1`, `build_id`
  `bbbab3c0dfb856a39`: it describes PR #3's tree, not main's; the integrator updates it when the owner says which SHA is tagged.
  (3) "Bound to the gate" is a process rule (`D-120`, `R-73`), not a mechanism, and no literal `GATE OK` exists for either main tree
  (`RELEASES.md` says "none on this tree" for `48c8e34c`; nothing records one for `44962e8d`); a complete gate was running on this host
  as this was written and its result is not read here. (4) `release-notes/0.5.1.json` is served as a release but has no tag, no ledger
  row and no ruling like `R-86`'s (`0.3.0` only): `grep -rn '0\.5\.1' docs/program/RELEASES.md docs/program/OWNER_RULINGS_2026-09-17.md`
  finds nothing; the owner rules archive or accept. (5) `build_id` is a content digest, not a git revision (`D-121`).
- **Command:** after the owner's say-so naming the SHA: workflow green, `infra/deploy/verify-deployed.sh` exit `0` on the host,
  `make alpha-acceptance` (its `apiBuild` phase reads `getProductVersion` and must say PASS), `git ls-remote origin
  'refs/tags/v0.7.0^{}'` equals the deployed SHA, account menu «История версий» lists `0.1–0.2, 0.3.0, 0.4.0, 0.5.0, 0.5.1, 0.6.0,
  0.7.0` and nothing invented.

## B8 — exposure review

- **Code and tests:** `src/auditmanager/api/security.py` (three unauthenticated operations: `issueToken`, `submitRegistration`,
  `readRegistrationStatus`), `infra/deploy/compose.server.yml` (only the proxy publishes a port), `infra/deploy/proxy/nginx.conf`,
  `infra/deploy/proxy/trusted-proxies.sh`, web `app/bff/**`; `tests/integration/api/test_authorization.py::test_the_open_surface_is_exactly_the_register`,
  `tests/integration/api/test_role_register.py::test_every_guarded_operation_is_in_the_role_register`,
  `tests/contract/test_proxy_security_headers.py`, `tests/contract/test_proxy_rate_limits.py`; new since 01:
  `tests/integration/composition/test_edge_credential_gate.py`, `test_exposure_text_is_current.py`,
  `test_real_client_address_at_the_edge.py`, `tests/e2e/test_upload_limit_headroom.py`. The first two tests above pin that the open surface is exactly the three operations and that
  every other operation sits in the role register; the count is read from the contract, not written here.
- **Evidence in hand:** `EXPOSURE-REVIEW-01.md` (2026-10-21, read-only, 102 GET/HEAD/OPTIONS requests): no unintended port answers, no
  product data or API description without a credential, no CORS, no source maps. Its verdict was **not clean**. Since then:
  E-4 (`POST /api/v1/auth/token` unthrottled) and E-5 (260 MiB buffered before the 401) are fixed in the repository by
  `HARDEN-AUTH-EDGE-01` (`D-192`, `D-193`; zone `token_exchange`, `auth_request` before the upload body), E-8 is corrected, and E-3
  (one shared throttle bucket) has its mechanism in `REAL-IP-EDGE-01` (`ALPHA_TRUSTED_PROXY_CIDRS`, default none, so nothing changes
  until the operator sets it). These changes touched `infra/**` and are on `origin/main` by `44962e8d` at the latest; no record of a complete gate on those trees
  exists (`RELEASES.md` says "none on this tree" for `48c8e34c`; nothing records one for `44962e8d`).
- **Missing:** the owner's decisions E-1 (HIGH while the seeded pair is live; state unprobed), E-2 (cookie without `Secure`, no HSTS:
  the live TLS terminator is a host nginx outside the repository, `D-191`), E-6 (the host's default site is a different application, to confirm), E-7 (terminator
  and firewall not in the tree); the operator's `ALPHA_TRUSTED_PROXY_CIDRS` for E-3; the same probe table re-run against the deployed
  `44962e8d` stand (E-4 and E-5 are proved by tests, not by a probe); `D-122` (no dependency or image scan), `D-166` (no container
  memory limit) open. A fix that touches `infra/**` is NEEDS-CODE with a complete gate if the owner chooses to fix rather than accept.
- **Command:** the reproducible curl rows of `EXPOSURE-REVIEW-01.md` Part 2 against the deployed origin; `infra/deploy/readiness.sh`
  `default-credential` check on the host (expects `access-check OK no default credentials`); `./scripts/manual-alpha-check.sh --origin
  <o> --preflight-only`; host `ss -ltnp`.

## B9 — contract `1.0.0` and error catalogue frozen

State now (§1): `contracts/api/v1/openapi.json` `info.version` `1.0.0`; the three domain catalogues `frozen`; `error-codes.json`
`contract_version` `1.0.0`, `candidate_revision` 19, 27 codes; surface 73 / 83 / 242; head `0029`. The same values are on
`origin/main` (§1). This is what `BETA-CONTRACT-SEAL-01.md` reports; here it is re-read on the tree, not copied.

- **Code and tests that hold it:** `contracts/api/v1/openapi.json` and its byte-identical copy `web/openapi/openapi.json`;
  `contracts/domain/v1/*`; `contracts/analysis/v1/*` and `contracts/events/v1/*` (moved together, as the seal's report says);
  `src/auditmanager/shared/errors/codes.py`; migration `db/migrations/versions/20261021_0029_routing_refusal_codes.py`.
  `tests/contract/api_v1/test_contract_seal.py` (`test_the_facts_file_names_the_sealed_version`,
  `test_every_json_artifact_of_a_family_declares_only_the_sealed_version`, `test_the_application_constants_are_the_sealed_version`,
  `test_the_edge_answers_its_own_error_bodies_with_the_sealed_version`, `test_a_domain_catalog_is_frozen_at_the_sealed_round`,
  `test_a_domain_schema_refuses_a_catalog_that_is_not_frozen`, `test_the_catalog_is_frozen_with_all_twenty_seven_codes`,
  `test_the_retention_question_stays_undecided_and_declares_no_window`), `tests/contract/api_v1/test_routing_refusal_codes.py`,
  `tests/integration/db/test_routing_refusal_codes_migration.py`; `npm --prefix web run api:verify` guards the generated client and
  `web/FRONTEND_LOCK.json` (not run here).
- **Debts resolved or carried, each by its register row:** `D-179` closed (dedicated codes `version_classification_required` and
  `section_profile_unavailable`, 422); `D-151` and `D-161` closed (prose); `D-172`, `D-163`, `D-145` carried on purpose to the first
  minor version (`BETA-CONTRACT-SEAL-01.md` §4); `D-180` closed (not a contract matter).
- **Read on the tree, to keep honest:** `model_identity_mismatch` is in the frozen catalogue and both enums but nothing raises it
  (§1); its check waits on `W56A-MODEL-PIN-01`, so the freeze names a code the application cannot yet emit (a deliberate state
  of the seal, to be restated at any live-model enablement). `rate_limited` (edge only) and `analysis_input_budget_exceeded` (before a
  run exists) sit outside the stored vocabulary by design. `OPEN-RETENTION` (`U-04`) stays `not_decided` and the freeze declares no
  window; B11 is deferred, so that is consistent (test above). `grep -ci reserved contracts/domain/v1/error-codes.json` is `0`;
  `grep -n reserved contracts/api/v1/openapi.json` finds nothing (the "reserved family" sentence of 01 is gone).
- **Missing:** `getProductVersion.contract_version` read from a deployed stand (the `apiBuild` phase of `make alpha-acceptance`);
  one complete `make gate` with the literal `GATE OK` on the final candidate (`R-135`; `AGENTS.md` §8 case 3). A reseal after this one
  is a version change: any later code for a new error is outside this matrix.

## B12 — every menu destination: action, result, live acceptance

Menu source: `web/src/shared/config/screen-registry.ts` (`inMenu: true`, 14 destinations) through `web/src/_app/navigation.ts` and
`account-menu.tsx` (four account actions). Manifest: `tests/e2e/pc01/journey/manifest.json`, 29 read routes (cold load, declared GETs
asserted), 95 write steps (all but the first five carry `screen` and `case`, `action` or `refused`), the identity continuation (§B1). No menu item renders
a stub (§1). **Where the 95 steps ran:** on a recorded local stack, directly and through the production `nginx.conf`: exit `0`, 95/95,
29/29, 5 min 14 s (`BETA-LIVE-JOURNEY-01.md`, tested tree `93ff8900`; the envelope sits in an untracked `.local` of that lane's worktree and was not read here). On
a stand, `scripts/manual-alpha-check.sh` runs `--phase core`: the four original write steps (`create-project`, `upload-document`,
`classify-version`, `start-run`) and the 29 routes. The other 91 steps make accounts, pause dispatch, designate a snapshot and start
further runs, and `--phase all` refuses a non-recorded origin without `--allow-spend` (`D-186`).

| Destination (role) | Walked write steps (names in the manifest) | Read route | Not walked |
| --- | --- | --- | --- |
| Главная `/` (any) | `my-tasks-return-needs-a-reason`, `my-tasks-take-the-work`, `my-tasks-complete-the-work` | `root` | a successful «Вернуть» (only the empty-reason refusal is walked) |
| Проекты (any role) | `create-project`, `upload-document`, six upload refusals, `upload-next-version`, `classify-*`, `start-*-run`, `record-decision` | `projects`, `project`, `document`, `version`, `comparison`, `run`, `review` | `correctVersionClassification` (a correction of a confirmed classification: the form exists in `web/src/widgets/version-classification`, `web/tests/unit/sections/classification-correction.test.ts`; no journey step) |
| Дашборд | `dashboard-sections-panel` | `dashboard` | — |
| Оптимизация разделов | `section-form7`, `section-form7-without-members` | `section-optimisation` | priced real data (recorded set only) |
| Диспетчер (admin, expert) | `assign-work`, `dispatcher-admin-cannot-take-the-work`, `dispatcher-expert-sees-only-the-own-work`, `dispatcher-shows-the-finished-work` | `dispatcher` | `getAssignment` has no mention in the manifest |
| База знаний | — (read-only screen, `listDecisions`) | `knowledge-base` | — |
| Блоки | **none** | `blocks` (cold: `listProjects`; `listVersionPortalBlocks`, `streamVersionPortalBlockCrop`, `getVersionBlocks` only as optional calls) | choosing a version and reading its portal blocks, crops and text lines |
| Нормы | `norms-designate-the-current-snapshot`, `norms-search`, `norms-catalogue`; refusals `norms-snapshots-offer-only-what-qualifies`, `norms-designation-is-an-administrators-act`, `norms-search-needs-a-query`, `norms-catalogue-filter` | `norms` | `/norms/document` (`getNormDocument`, `listNormParagraphs`, `streamNormDocumentContent`): the route declares no call; the seeded PDFs have no object (`BETA-LIVE-JOURNEY-01.md`) |
| Журнал выполнения | — (read-only) | `logs` (`listExecutionJournal`) | a retry shown live (B4 (d)) |
| Исполнители | `workers-list-the-worker`, `worker-intake-is-an-administrators-act`, `worker-stops-taking-new-work`, `worker-takes-new-work-again` | `workers` | — |
| Настройки анализа | `analysis-settings-lists-the-profiles`, `analysis-settings-for-an-expert` | `analysis-settings` | read-only by design |
| Очередь | `queue-pause-dispatch`, `queue-lists-the-waiting-run`, `queue-priority-out-of-range-refused`, `queue-change-priority`, `queue-cancel-the-waiting-run`, `queue-reaudit-the-cancelled-run`, `queue-resume-dispatch` | `queue` | — |
| Пользователи (admin) | `user-archive`, `user-restore`, `user-password-reset`, `user-password-reset-must-match` | `admin-users`, `admin-user` | `updateUser` (role change) and `purgeUser` only in the identity continuation, which has no recorded run |
| Заявки (admin) | — | `admin-registrations` | `approveRegistration`, `rejectRegistration` only in the identity continuation |
| Профиль (account menu) | `profile-needs-a-surname`, `profile-update` | `account` | — |
| Сменить пароль (account menu) | `password-confirmation-must-match`, `password-current-must-be-right`, `password-change`, `old-pass-is-refused-after-the-password-change` | `change-password` | — |
| История версий (account menu) | `release-history-panel` | — | — |
| Выйти (account menu) | `sign-out`, `signed-out-session-is-gone` | — | — |

**Destinations without a walked write step (four of 14):** «Блоки» (a cold load only; it has an action, choosing a version, that no step
performs), «Заявки» (a route walk; it acts only in the identity continuation, which has no recorded run), and the read-only screens
«База знаний» and «Журнал выполнения», for which reading is the action and the route walk is the step. Operations of the 83
that the manifest does not name at all, read from its text: `getNormDocument`, `listNormParagraphs`, `streamNormDocumentContent`
(named in a comment), `correctVersionClassification`, `getAssignment`, `listPriceListPositions`, `listOptimisationPasses`,
`listProposalDecisions`, `getRunNormVerification` (no web caller: `grep -rn getRunNormVerification web/src` finds nothing outside the
generated client) and `getProductVersion` (read by the `apiBuild` phase of `make alpha-acceptance`, not by the journey);
`issueToken`, `changePassword`, `submitRegistration` are reached through the BFF's own doors and named in comments. For
`listPriceListPositions`, `listOptimisationPasses` and `listProposalDecisions` the web has hooks; whether a walked screen calls them is
UNVERIFIED.

- **Tests:** `tests/e2e/test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers` and
  `::test_the_night_window_steps_agree_with_the_contract_and_with_each_other`; `tests/e2e/pc01/journey/prove_the_guard_can_fail.py`
  (80 mutations, 80 red, per the report; not re-run); `web/tests/guards/{screen-registry,screen-set,prepared-sections}.guard.test.ts`;
  per screen `web/tests/unit/{dispatcher,execution,norms,sections,section-specification,optimisation,optimisation-proposals,
  comparison,workers,release,session,shell}`; backend `tests/integration/{dispatch,optimisation,sections,comparison,exports,dashboard}`.
- **Missing:** (1) the stand run: with the recorded provider on a test-data stand the 95 steps can run (`--phase all`); on the published
  stand only `core` runs unless `--allow-spend` is accepted, a credentialed live provider call under the `R-29` ceiling. (2) The walk
  gaps above: a step for «Блоки» (needs a version whose run reached layout), the norms document view (needs a snapshot whose PDFs have
  objects, so the real import first), a successful return of an assignment, `correctVersionClassification`, and a recorded run of the
  identity continuation. (3) `D-186`'s open point: `proposal-accept` sends two identical POSTs on a double press (one decision, both
  `201`); `D-195`: four more benign double POSTs. (4) "The full АР function matrix is tested" (B12's last clause): no document in the
  tree defines it (UNVERIFIED).
- **Command:** `npm --prefix web run e2e:pc01 -- --origin <o> --phase all` against a recorded-provider test-data origin, `--phase core`
  against the published stand, and `./scripts/manual-alpha-check.sh --origin <o> --interactive` for A01–A20 (A09: 27 screens at
  780 × 900).

## Decisions taken (no recorded decision blocks them; the conservative default applies)

1. **B9 is READY-TO-ACCEPT-ON-STAND.** Its text is "contract `1.0.0` and error catalogue frozen", which the tree satisfies on dev and
   on main; the evidence that remains is a live read and a complete gate, neither of which is code.
2. **B12 is READY-TO-ACCEPT-ON-STAND (integrator, 2026-10-22), reached in two steps.** The first draft of this matrix kept it NEEDS-CODE on the literal reading of `BETA-MATRIX-01`, because «Блоки», the norms document view, a successful «Вернуть», `correctVersionClassification` and the identity continuation had no journey step. `PC01-JOURNEY-GAPS-01` (lane G, merged) added them: the journey declares **109 write steps and 29 routes**; the live run on the recorded local stack of the full beta tree (`integration/beta-main` at `7a238a52`) exited `0`, 109/109 steps and 29/29 routes, 345 s (the first run had two findings, both test-side and fixed: a stale expectation after the PB profile and a norms seed with `paragraph_count` 0); the identity continuation passed (12 operations, 18 checks, exit `0`). Remaining un-walked, written out in `PC01-JOURNEY-GAPS-01.md`: a successful `purgeUser` (only its refusal `409 account_referenced`), what the browser's PDF viewer draws, a missing norm document (`404`), and everything on the published stand (a recorded local stack only; `manual-alpha-check.sh` runs `--phase core` on a stand, `--phase all` needs `--allow-spend`). The acceptance on the stand stays the owner's.
3. **B7 stays READY-TO-ACCEPT-ON-STAND although main carries `0.7.0` without a tag or a recorded host verification:** every item left
   is a run or an owner decision (`verify-deployed.sh`, the tag, the `0.5.1` ruling), and the ledger row is the integrator's to correct.
4. **Evidence of `RECOVERY-REBASE-01` is accepted as the latest B6 run, but only at head `0028`.** The `0029` pin move is code
   (`345ac443`); a drill at `0029` is listed as missing rather than inferred.
5. **Stand state is not inferred from tree records.** The state of the `admin` password, of PR #4's workflow, of the host verifier
   and of the stand's free disk are marked UNVERIFIED wherever a row needs them.
6. **The executor-connection line is not graded here.** `R-143d` moved remote executors into the beta scope and `R-144` made them
   the priority; no `EXEC-*` code is on this tree (§1), and B1–B12 are matrices of the criteria as `ROADMAP-TO-BETA.md` §9 states
   them. When an `EXEC-*` slice lands, the rows for B1 (a new «Исполнители» surface), B8 (a new inbound pull channel, `R-143c`) and
   B12 (new menu actions) need a refresh.

## What the owner or the stand must still do

Copied from `BETA-MATRIX-01` §"What stands between it and acceptance" and updated. "Owner" means a decision or an instruction;
"operator" means the host; "executor" means a coding session.

| # | Who | What | Criteria | Source |
| --- | --- | --- | --- | --- |
| 1 | operator | run `infra/deploy/verify-deployed.sh` on the host for the tree main deployed; report whether the workflow for `44962e8d` finished green | B7 | `D-188`, `RELEASES.md` "Verification still owed" |
| 2 | owner | name the SHA to tag `v0.7.0` (the ledger row names `48c8e34c`, main is `44962e8d`); then fill the row's SHA, head `0029`, contract `1.0.0`, `build_id` | B7 | `RELEASE-0-7-0-DEPLOY-STEPS-01.md` step 4 |
| 3 | owner | rule the `0.5.1` history entry (archive or bundled entry like `R-86`, or accept) | B7 | `release-notes/0.5.1.json`, no row, no tag |
| 4 | owner (optional) | `D-120` stays an accepted process control (`R-73`: a push to main deploys what it names; the workflow proves ancestry, not a gate); say so if a mechanism is wanted instead | B7 | `D-120` |
| 5 | operator | check the live `admin` credential: `infra/deploy/readiness.sh` `default-credential` check, expect `access-check OK no default credentials` | B1, B8 (E-1) | `EXPOSURE-REVIEW-01.md` E-1; `R-141d` says it was changed |
| 6 | owner | decide E-2 (host terminator: `Secure` cookie, HSTS), E-6 (the host's default site), E-7; operator sets `ALPHA_TRUSTED_PROXY_CIDRS` for E-3; then re-run the probe table | B8 | `D-191`, `REAL-IP-EDGE-01.md` |
| 7 | owner | install the two forced-command keys, name the window, check capacity (about 22 GB), name who designates the snapshot; run `STAND-NORMS-IMPORT-RUNBOOK-01.md`; its §0 and §9 name `59a1be91` and head `0027` and need the integrator's refresh first | B2 | `R-142c`, `R-142d` |
| 8 | operator | `infra/deploy/purge-product-data.sh --dry-run`, then the real run, if the stand's generated test data is to go before the beta (keeps accounts and the corpus) | B1, B2 hygiene | `D-156`, `STAND-PURGE-TOOL-01.md` |
| 9 | executor + operator | run the identity continuation and A13–A20 on a built stand | B1 | `D-137` |
| 10 | operator | run `e2e:pc01 --phase core` through `manual-alpha-check.sh` on the stand; for the 91 night-window steps either a recorded-provider test-data origin or an owner-accepted `--allow-spend` under `R-29` | B12 | `D-186` |
| 11 | executor (optional) | add journey steps for «Блоки», a successful assignment return, `correctVersionClassification`, and the norms document view once a real snapshot exists | B12 | §B12 |
| 12 | owner | define "the full АР function matrix" that B12's last clause asks to be tested | B12 | no definition in the tree |
| 13 | operator | kill the worker in a deterministic stage on the stand and read `/workers` and `/logs`; the provider-failure retry stays a test or a fault-injecting proxy | B4 | §B4 |
| 14 | executor + operator | repeat the B6 drill at head `0029`; owner judges whether 23 synthetic objects are a B6 drill or a larger source is wanted | B6 | `RECOVERY-REBASE-01.md` §8 |
| 15 | integrator | one complete `make gate` with the literal `GATE OK` on the final candidate; read the running gate's result when it ends | B9 and every B | `R-135`; `AGENTS.md` §8 |
| 16 | integrator | refresh the statements this slice found stale and may not edit: `CURRENT_STATE.md` ("main still serves `1.0.0-draft.1`"), the `v0.7.0` row of `RELEASES.md`, the runbook's `59a1be91` and `0027`, the `D-188` row (the workflow repair is on main) | B7, B9, B2 | §2 rows 11, 16, 17 |
| 17 | owner | B3, B5, B10, B11: deferred, text unweakened (`R-141c`): quality and real-document acceptance, expert smoke sessions, a retained-data policy (`U-04`) | B3, B5, B10, B11 | `R-141c` |

## Hotspots and limits

This slice changes `docs/program/BETA-MATRIX-02.md` only (`git diff --name-only d087c101..HEAD`). No `contracts/**`, migration,
lock file, composition root, global style, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, ref, tag or stand was touched. Nothing was pushed.
Required checks (the tests do not read this file; both ran with its text as committed except for this paragraph): `git diff --check` exit 0; `nice -n 10 python3 -m pytest -q tests/contract/program`
exit 0, 28 passed in 1.02 s (output in the executor's scratchpad). Limits: no other suite was run, so a row that says "tests exist" says the name is on the tree and nothing about its result; figures quoted
from reports (`BETA-LIVE-JOURNEY-01.md`, `RECOVERY-REBASE-01.md`, `BETA-CONTRACT-SEAL-01.md`) are theirs, on the trees they name.
