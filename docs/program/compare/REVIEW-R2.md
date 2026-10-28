# COMPARE-MODULES-PLAN revision 1 — judging round 2 (feasibility against the repository)

Reviewer: independent round-2 judge, read-only. Tree: worktree `plan-compare-modules` at `128439bf`
(base `9e42c18a`); the live integration tip `integration/ar-close-1026` was also read (`05f4584d`),
and so were the two running PW5 lane worktrees `section-category-ocr-01` and `analysis-presets-01` (read-only).
Every claim below names the command or the file:line it rests on. No suite, docker, npm or build was run.

---

1. **R2-01 · BLOCKER · §4 «Seal» definition, §5 «Composition root», C4 note** — By design no lane can wire its
   own operations, so none of them can finish green.
   - Evidence: §4 makes the seal the owner of «the composition root» and says «the other lanes of the wave start
     after it merges». §5 says «a lane needing a port wiring lists it for the seal». So by the time a lane's
     service exists, the seal has already merged. Every operation a seal adds is a stub that answers
     `503 dependency_unavailable`, and the stub is registered in the shared enumerators
     `tests/integration/composition/test_router_answers.py:53` (`SEALED_STUB_GETS`) and
     `test_an_absent_parent_is_not_an_empty_page.py:182` (`SEALED_STUB_COLLECTIONS`) (`CONTRACT_PIN_REGISTRY.md`,
     event «sealed stub operation»). The lane that implements an operation has to edit
     `src/auditmanager/bootstrap/adapters.py` (4 992 lines), `api/routers/ports.py` and the router, and has to
     empty those enumerators. None of these files is in any lane's own paths. Wave C4 has no seal at all
     («C4 has no seal: SEAL-C3 sealed its operations»), so C4 has no owner of the composition root either.
     Earlier plans handled this with a serial chain (`W57-PLAN.md:689` «`bootstrap/adapters.py` SEAL → NORMREFS → XLSX»)
     or by splitting `adapters.py` by class (`W53-CLOSE-PLAN.md:66-68`). PW4 and PW5 gave each lane both the contract
     and `adapters.py` (`PRODUCTION-WAVE-PW4.md:31`, `PW5.md:9`).
   - Fix: give each implementing lane the adapter class(es) of its own ports in `adapters.py` and its rows in the
     two stub enumerators, serialised inside the wave (seal → lane A → lane B …, as in W57). Alternatively, end
     each wave with a WIRE slice that owns `bootstrap/**`, `api/routers/**` and the stub enumerators. Name the
     owner of `src/auditmanager/api/**` (routers, `schemas/models.py`, `ports.py`, `security.py` role register)
     for every wave, C4 included.

2. **R2-02 · BLOCKER · §3 A-4, CMP-JOBS-01 (C0, L, own paths `jobs/**`, `workers/**`)** — A typed job/spend
   subject cannot be built in one L lane inside those paths. It also breaks a frozen contract.
   - Evidence. A Job is a Run in the schema, in the domain contract and in about 180 code sites:
     - `db/migrations/versions/20261002_0014_durable_analysis_effects.py:140-168`: `job.run_id NOT NULL REFERENCES
       audit_run`, `uq_job_run_id UNIQUE (run_id)`.
     - Same file, `:238-321`: `provider_call_effect.run_id NOT NULL`, `ck_provider_effect_stage_id CHECK (stage_id =
       'text_analysis')`, `fk_provider_effect_job_belongs_to_run (run_id, job_id)` and
       `fk_provider_effect_final_call_belongs_to_run`.
     - `20260910_0002_pc01_schema.py:820-840`: `model_call.run_id NOT NULL` and `ck_model_call_stage_id` (enum).
     - `20261022_0031_executor_pull_channel.py`: `ck_executor_task_origin CHECK (origin IN ('run_call','probe'))`,
       where `run_call` requires `run_id`.
     - `contracts/domain/v1/state-machines.json` machine `job`: «Audit Jobs & Runs module»; it has no paused state.
     - `grep -c run_id`: `jobs/repository.py` 123, `execution/public.py` 17, `runs/carrier.py` 16,
       `runs/reconciliation.py` 10, `workers/service.py` 8, `executors/runner_repository.py` 6.
     - The claim locks Run → Job (`jobs/repository.py:873-876`), and `_NEXT_JOB` joins `audit_run`
       (`:79-99`). `reclaim_expired` calls `runs.public.fail_reclaimed_run` (`:680`, `:776`).
       `AttemptAuthority` and `AttemptContext` carry `run_id` (`jobs/lease.py:28-45`).
     - The EXEC-PAR one-active-Run-per-connection limit reads `audit_run.connection_revision_id`
       (`jobs/repository.py:46-50`, `:940-970`).
     - The per-run cost ceiling lives in `analysis/text/cost.py` (`BUDGET_SCOPE_RUN`). Spend sums are in
       `runs/repository.py` `_COST_SUMMARY` and `dashboard/repository.py` `_SPEND`.
     - The queue and journal read models require `run_id`: contract `ExecutionQueueItem.required` and
       `ExecutionJournalEntry.required` both include `run_id`, and `execution/public.py:60-90` reads
       `SELECT j.run_id FROM job`. Making it optional is a breaking change to a response (major version;
       `2.0.0` is reserved for `D-233`).
   - What breaks if comparison rows enter `job`: the «Очередь»/journal API and screens, reclaim (it fails a Run that
     does not exist), effect journals (the CHECK and FK refuse the row), the cost meter (scoped per run), EXEC-PAR
     (a comparison job on a pull connection escapes the limit), the global `execution_control` pause (it pauses
     comparison too) and recovery classification.
   - Recommendation (concrete): decide now, not in the ADR. Choose a **comparison-local durable queue** in
     `src/auditmanager/comparison/work/**` that copies the Lease pattern but not the tables:
     - `comparison_work` + `comparison_work_attempt` with `lease_expires_at` / heartbeat / attempt count,
       pause / cancel and an effect journal `comparison_model_call`. Its spend columns follow the precedent of
       `comparison_summary` (migration `0035:394-472`: `provider_mode`, `cost_basis`, `cost_micros` and the CHECKs).
     - The worker hosts it as a second loop, the way `probe_runner` is hosted (`workers/service.py:216-217`,
       `:286-287`, `:379-389`). That is one hook in `workers/service.py` plus wiring in `bootstrap/composition.py`.
     - `executor_task` gets an origin `comparison_call` with a nullable `comparison_attempt_id`, and
       `runner_repository._ATTEMPT_LIVE` gets an OR branch.
     - `_CONNECTION_HAS_OTHER_ACTIVE_RUN` also counts active comparison AI work, under the same advisory lock.
     - The R-29 dashboard sum UNIONs the two journals.
   - Cost: about two M slices (queue + spend journal), no contract break, no change to the domain state machine.
     The shared-subject route is at least XL, touches six contexts and a frozen contract field, and is the risk
     path W48 warns about. Re-size and re-path CMP-JOBS-01 accordingly. CMP-INGEST-02, SERIES, QUEUE and STAGE-RUN
     then depend on the comparison queue, not on `jobs`.

3. **R2-03 · BLOCKER · CMP-VC-UI-01 (C1), CMP-STAGE-PAIR-01 (C3), every web slice; CMP-JOURNEY-01 (C4)** — A new
   screen or a new module stylesheet turns two static guards red, and the plan gives the files that fix them only
   to C4.
   - Evidence: `tests/e2e/test_pc01_journey_conformance.py:15-19,459-463`: «Add a screen and this goes red until
     the journey walks it» (route tree under `web/src/app` vs `tests/e2e/pc01/journey/manifest.json`). This is
     part of light acceptance item 1 (AGENTS §8, «the journey manifest's conformance»).
     `web/tests/unit/styles/contrast.test.ts:334-349` «opens every screen web/src/app offers, derived rather than
     listed», and the next case requires every colour-bearing rule of every `*.module.css`
     (`import.meta.glob('../../../src/**/*.module.css')`, `:124`) to be reached by a screen in
     `web/tests/unit/styles/screens.ts`. The route-event pins (`python3 tools/plan/pin_sweep.py route`) add
     `web/src/shared/lib/routes.ts`, `web/tests/guards/screen-set.guard.test.ts`,
     `web/tests/guards/lazy-boundary.guard.test.ts`, `server-credential.guard.test.ts`,
     `dashboard-invalidation.guard.test.ts` and `web/tests/unit/shell/navigation.test.ts`. The plan gives
     `tests/e2e/` only to CMP-JOURNEY-01 in C4 and gives `screens.ts` to nobody. Six web slices add module CSS:
     VIEWER, VC-UI-01, VC-UI-02, STAGE-PAIR, STAGE-LINK and STAGE-REVIEW. In C3, PAIR ∥ LINK would both edit
     `screens.ts`.
   - Fix: each slice that adds a route owns its `manifest.json` routes entry and the route pins above. Each slice
     that adds a module stylesheet owns its block in `screens.ts`. These shared files are serialised inside the
     wave (enumerator ownership, `docs/templates/TASK_TEMPLATE.md` «Enumerator ownership»). CMP-JOURNEY-01 keeps
     only the walk itself.

4. **R2-04 · BLOCKER · CMP-EXEC-IMAGES-01 (C0), CMP-SEAL-C0 contents** — The image lane needs a contract change
   that SEAL-C0 does not seal, and a file in another context that a running PW5 lane is editing.
   - Evidence: `contracts/api/v1/openapi.json`: `ClaimedExecutorTask.images` has `"maxItems": 1`, and
     `RunnerImage.required` includes `portal_block_id` (`PortalBlockId` `^blk_[0-9a-f]{32}$`). The runner protocol
     `tools/executor-runner/RUNNER_API.md:83-96,229` says «at most one saved PNG». SEAL-C0's list (plain-PDF upload,
     batches, order, profile reads, job subject, error codes) does not name the runner schemas, so the probe will
     not surface them.
   - Evidence: the single image is a field of the analysis context, not of executors:
     `src/auditmanager/analysis/text/adapter.py:43` `image_bytes: bytes | None`. The slice that built the
     one-image channel edited this file (`git show --stat 994404a9`: `analysis/text/adapter.py | 16`). PW5's
     `SECTION-CATEGORY-OCR-01` is editing it now (`git diff --stat integration/ar-close-1026...HEAD` in
     `.local/worktrees/section-category-ocr-01`: `analysis/text/adapter.py | 14`).
   - Evidence: the hard-coded one-image or portal-block checks sit in `executors/image_input.py:38-53`,
     `pull.py:193-212`, `tools/executor-runner/codex_answer.py:52-63,140-150` (prompt text «the crop for portal
     block»), `claude_answer.py:75-77` (refuses every image) and `mcp_bridge.py:382-391`.
   - Fix: put `RunnerImage` (a crop reference without a portal block), `ClaimedExecutorTask.images.maxItems` and
     the `executor_task` origin for comparison work into SEAL-C0, and grant `analysis/text/adapter.py`
     (ModelRequest only) to CMP-EXEC-IMAGES-01 after SX merges. Add a compatibility rule for runners already
     deployed on remote hosts: an old runner fails the task with `image_input_unsupported` and never sends a
     subset of the images. M is credible once these grants exist (the one-image slice was 550 lines in 16 files).

5. **R2-05 · MAJOR · §5 «Entry», §4 C0** — The entry condition names only ANALYSIS-PRESETS-01. PW5's SX lane
   holds two files that C0 needs, and the base facts have moved.
   - Evidence: the SX worktree diff touches `src/auditmanager/analysis/public.py | 14` and
     `analysis/text/adapter.py | 14`. CMP-PROFILE-01 needs the first («rendering through `analysis/public.py`»)
     and CMP-EXEC-IMAGES-01 needs the second (R2-04). The integration tip `05f4584d` carries migration
     `0036_cite_partition_v3` (merge `eb5dcf1e`, contract still `1.8.0`). The PR lane has an uncommitted
     `db/migrations/versions/20261027_0037_analysis_presets.py` and edits `src/auditmanager/executors/public.py`
     plus new `executors/preset_*.py`, which is CMP-EXEC-IMAGES-01's directory.
   - Fix: the entry is «SX and PR merged». SEAL-C0 takes head `0038` or later; restate the base (tip, head,
     contract) in revision 2.

6. **R2-06 · MAJOR · §4 seals, §8 «Stop»** — The per-table pin family is neither named nor granted. Seals are
   sized M while each one adds many tables.
   - Evidence: the two-table migration `0035` had to edit `scripts/recovery/{schema_coverage,grant_classification,
     product_purge}.py`, `infra/deploy/apply-grants.sh` (two rows per table at `:255-256`, `:394-395`) and tests
     with literal counts: `tests/integration/db/test_application_role_grants.py:380` `len(refused) == 66` and
     `tests/integration/recovery/test_grant_classification.py:78` `len(coverage.TABLES) == 66`. It also edited
     `test_schema_shape.py`, `test_schema_invariant_inventory.py`, `test_migration_lifecycle.py`,
     `test_downgrade_chain_round_trip.py`, `test_product_purge.py`, `test_project_erase.py` and
     `test_synthetic_drill_{compare,seed}.py` (`git show --stat e3f18176`). The PR lane's working tree edits the
     same 15 files for one table (`git status` in `analysis-presets-01`).
   - Evidence: a table with a `*_blob_id` column must be listed in `scripts/recovery/blob_reference_audit.py:24-33`.
     `project_erase.py` derives the project scope by **foreign-key closure from `project`**
     (`project_erase.py:8-12,546-552`), so a table that is not reachable from `project` must be declared in
     `UNSCOPED_PRODUCT_TABLES` (`:98`). Content-keyed profile rows shared across projects (A-5, `cpr_`) and the
     «per-install AI queue» break that closure. An actor column needs `access/references.py` (D-244 limit 4).
     `pin_sweep.py table` lists none of the recovery scripts or grant tests, so the seal's probe will not surface
     them.
   - Scale: by the plan's own list the seals add about 30–40 tables (C0 ≈ 6, C1 ≈ 6, C2 ≈ 8, C3 ≈ 14). COMPARE-
     PERSISTED-SUMMARY-01 (3 operations, 2 tables) was an L lane of 85 files and 11 790 lines (`git diff --shortstat
     ca2e5df8 e3f18176`).
   - Fix: grant every seal `scripts/recovery/{schema_coverage,grant_classification,product_purge,project_erase,
     blob_reference_audit}.py`, `infra/deploy/apply-grants.sh`, `src/auditmanager/access/references.py` and the 12
     test files above. Make profiles per-version rows (no cross-project rows). Re-size SEAL-C1 and SEAL-C2 to L and
     SEAL-C3 to XL, or split SEAL-C3 into two seals.

7. **R2-07 · MAJOR · §4 seals (contract version), §8** — The contract-version literal family and the infra
   surface pins are not addressed.
   - Evidence: `VERSIONING_AND_FREEZE_POLICY.md:11` «backward-compatible optional addition → minor», and `R-146ar`
     moved `1.7.0 → 1.8.0` for three operations as «the mechanical rewrite of the literal» (D-244 limit 1: «111
     files»). `python3 tools/plan/pin_sweep.py contract-version` lists about 75 paths (≈ 50 of them
     `web/tests/unit/**`, plus `src/auditmanager/analysis/engine/result.py`, `api/routers/__init__.py`, `VERSION`,
     both contract READMEs, `identifiers.json`). The surface counts are also pinned in infra:
     `infra/deploy/proxy/nginx.conf:309` («107 operations»), `infra/deploy/serve.py:4`, `infra/deploy/README.md`,
     `web/src/shared/api/authorization.ts:24` and `web/src/app/bff/v1/[...path]/route.ts`
     (`rg -l "95 paths|107 operations|314 schemas"`). Under AGENTS §8 case 3, `infra/**` changes need a full gate
     (R-135 defers it).
   - Fix: state the version per seal (`1.9.0` … or one bump per module). Grant the contract-version and
     reseal-surface families to each seal from `pin_sweep.py`, and add `infra/deploy/{proxy/*.conf,serve.py,
     README.md}` to the seal grants.

8. **R2-08 · MAJOR · CMP-SEAL-C0 «new error codes (run-start refusal)», A-8** — A new error code is the most
   expensive way to say this, and the refusal it wants already exists.
   - Evidence: `runs/commands.py:385-395` already refuses a version without `source.document` with
     `analysis_input_invalid`, `reason="missing_required_input"`. The catalogue is 27 API / 25 stored codes
     (`tests/support/expected_facts.json`), and stored codes are DB CHECK vocabularies (`model_call`,
     `provider_call_effect` `ERROR_CODES`; migration `0029_routing_refusal_codes` had to widen them).
     `pin_sweep.py error-code` lists 30 paths, including `web/src/shared/api/catalog-message.ts` (Russian messages)
     and five web contract tests. Repository practice is a new classifier under an existing code
     (`error-codes.json:175-186`, `conflict_reason`).
   - Fix: reuse `analysis_input_invalid` with a new `reason` value (e.g. `comparison_only_version`) and its Russian
     sentence. Reserve a new code for a case no existing code fits, and then grant the error-code family.

9. **R2-09 · MAJOR · CMP-INGEST-01/02, §1.1 upload, §8 «Upload abuse»** — The edge refuses large bodies on any
   new path. The plan grants neither the proxy nor the BFF and does not fix a chunk size.
   - Evidence: `infra/deploy/proxy/nginx.conf:219` `client_max_body_size 32m` server-wide. Only
     `location ~ ^/api/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$` and its `/bff/v1` twin (`:391-417`; copy in
     `tls-server.conf:149-192`) take 260m, with `auth_request` before the body (`HARDEN-AUTH-EDGE-01`, E-5, D-192;
     «These are the only two locations that take a body of 260 MiB»). A plain-PDF upload on a new operation path is
     refused at 32 MiB, and drawings run up to 250 MiB (`ingest/envelope.py:153`). `uploadDocument` must keep
     refusing a bare PDF (A-8 «portal-bundle upload is unchanged»; `ingest/service.py:411-418`).
   - Fix: decide in SEAL-C0. Either chunk ≤ 30 MiB on the default location (state it, and test 10 000 small
     requests under the limit_req zones), or add two regex locations (api + bff) with the same auth-before-body
     and grant `infra/deploy/proxy/{nginx,tls-server}.conf` and the proxy tests (`tests/contract/test_proxy_rate_limits.py`,
     `tests/integration/composition/test_proxy_config_follows_checkout.py`) to CMP-INGEST-01. PW5's S1 owned these
     files and has now merged (`ea321784`).

10. **R2-10 · MAJOR · CMP-STAGE-PAIR-01 own paths, A-11, §5 «Shared web files»** — The planned web slices
    collide with slices that already exist.
    - Evidence: `web/src/_pages/stage-comparison/` exists. It is the **version-scoped** page
      (`stage-comparison-page.tsx:1-10`, route `web/src/app/projects/[project_uid]/versions/[version_uid]/comparison/page.tsx`),
      the one the plan says «stays». `web/src/widgets/stage-comparison/` is the W43 run comparison, and the slice
      name `stage-comparison` is pinned by `web/tests/guards/lazy-boundary.guard.test.ts:57-62,143,228,329,369`
      and `web/tests/unit/styles/screens.ts:23,1442`. CMP-STAGE-PAIR-01 lists `web/src/_pages/stage-comparison/**`
      as its own path without «(new)».
    - Evidence: CMP-STAGE-LINK-01 (C3, parallel with PAIR) and CMP-STAGE-REVIEW-01 (C4) build widgets that must be
      mounted in a page that PAIR owns. VC-UI-02 mounts into a page VC-UI-01 owned (different waves, so that is fine).
    - Fix: give the new module new slice names (e.g. `_pages/stage-pairs`, `app/stage-pairs`, or keep the URL
      `/stage-comparison` but rename the FSD slices). Grant each later web slice the one mount edit in the page
      file, serialised.

11. **R2-11 · MAJOR · C1 «ENGINE ∥ MATRIX ∥ VIEWER»** — Two parallel slices own the same directory.
    - Evidence: CMP-ENGINE-01 owns `comparison/engine/**`, and CMP-VIEWER-01 owns «tile reads in
      `comparison/engine/tiles*`». Both run in parallel by the order line.
    - Fix: give the tiles their own package (`comparison/tiles/**`) owned by VIEWER, with an interface fixed in
      SEAL-C1, or make VIEWER follow ENGINE.

12. **R2-12 · MAJOR · §2 «What stays», A-11, O-4, D-5** — Sheet pairing would have two canonical truths and two
    screens named the same. O-4 asks only about migrating the data.
    - Evidence: the version-scoped page keeps `widgets/version-comparison` («Сравнение версий» heading,
      `stage-comparison-page.tsx:7-11`), its pairing controls `entities/version-comparison/ui/sheet-pairing-controls.tsx`,
      the 0035 approvals (`comparison_sheet_link`, at most 32 active links, older→newer by **ordinal**, migration
      `0035` docstring) and the summary over them (`generateComparisonSummary`). Finding carry-over reads that
      service's sheet suggestions (`comparison/carryover.py:161-181`, `finding_match_suggestions.py:7-9`). The new
      matrix (`cmx_`/`cme_`) pairs the same pages under different rules, and its order (`cvo_`) may differ from the
      ordinal (D-5).
    - Fix: decide in the ADR, not in an end-of-plan poll:
      - which store is canonical for «page X of version A ≙ page Y of version B»;
      - whether the version-scoped pairing and summary are hidden while the module flag is on;
      - whether carry-over stays on its own proposals (state it);
      - what the version-scoped screen's heading is renamed to.
      Add the needed edits of `widgets/version-comparison` to a slice.

13. **R2-13 · MAJOR · A-11 flag, §8 «Rollback»** — The rollback depends on a flag mechanism that does not exist
    and that no slice owns.
    - Evidence: no feature-flag mechanism exists (`grep -rln "featureFlag|FEATURE_" web/src src/auditmanager` →
      nothing). `screen-registry.ts` is a static array that the guards enumerate. `web/src/shared/config` is «the
      only place in `web/` that reads `process.env`» (`proxy-trust.ts:20`). A «server setting» therefore means
      either a new contract read or a new web-container env in `infra/deploy/compose.server.yml` (infra, full-gate
      class). The guards that derive screens from `web/src/app` (R2-03) still see a hidden route.
    - Fix: put the flag mechanism in SEAL-C0, with its owner and grants (`web/src/shared/config/**` +
      `infra/deploy/compose.server.yml` env + `server-env.ts`, or an operation). State that a flagged-off route
      still exists in the tree and in the journey manifest.

14. **R2-14 · MAJOR · CMP-PROFILE-01 «byte cap and eviction», A-5, §8 «Disk»** — The planned eviction is a
    deletion that the storage boundary does not offer and that AGENTS §4 forbids without reconciliation.
    - Evidence: `src/auditmanager/storage/public.py` exports no delete or evict. Blobs are product data that only
      the operator tools delete (`project_erase.py` phases «plan … object deletion is an external side effect, so it
      is not a dual write»), and `blob_reference_audit.py` audits every `*_blob_id` column. Deleting a cached
      preview or tile that a row references, from a lane in `comparison/profile/**`, is a dual write DB + object
      store with no outbox.
    - Fix: for the beta, use a cap enforced by refusal (`needs_review`/`RENDER_FAILED`-style typed state) and no
      eviction. Otherwise add a storage-owned GC with a reconciliation journal as its own slice that owns
      `storage/**` and the recovery scripts. Keep tiles derivable on demand rather than stored.

15. **R2-15 · MAJOR · §1 upload/version marks, CMP-INGEST-01 own paths** — The existing screens and reads would
    show plain-PDF versions as ordinary analysable versions, and no slice owns changing that.
    - Evidence: Q-CMP-5 says «such a version is marked as uploaded without a portal bundle». The version detail,
      version list, document list, run-start control («Запустить», executor selector) and portal-blocks widget
      (`web/src/widgets/{version-list,version-history,document-list,portal-blocks,run-list}`,
      `_pages/version-detail`) are in no slice's paths. The `DocumentVersion` schema has no field for it, and a run
      start refusal is the only signal.
    - Fix: SEAL-C0 adds an upload-kind field to the version schema. A web slice in C0 or C1 gets the mark and the
      disabled start on the existing version screens, with its census and journey entries (R2-03).

16. **R2-16 · MAJOR · CMP-STAGE-REVIEW-01 «Excel through `src/auditmanager/exports/` public API», G-26** — The
    cited public API does not exist.
    - Evidence: there is no `exports/public.py`. `exports/__init__.py` exports `export_run_csv` / `export_run_xlsx`
      only, and the XLSX writer is «for the W57b review layout», with closed finding enums
      (`exports/xlsx/writer.py:1-10`, labels `CATEGORY_LABELS`, `SEVERITY_LABELS`, `VERDICT_LABELS`).
    - Fix: grant CMP-STAGE-REVIEW-01 `src/auditmanager/exports/**` for a generic sheet writer exported from
      `exports/__init__.py` (S1 has merged, so the path is free), or let the lane write its workbook with the same
      stored-ZIP technique inside `comparison/stage_review/**`.

17. **R2-17 · MAJOR · §8 «Disk/memory», A-5, CMP-ENGINE-01** — Memory is the binding resource on this host and on
    a single worker, and only the profile is measured.
    - Evidence: `free -g` → 11 GiB total, 3 GiB available, 10 GiB swap in use; `nproc` 8; `df -h /` → 5.4 GiB free.
      An A1 page at 200 dpi is 6622 × 4677 ≈ 31 Mpx: about 93 MB RGB per raster, and a float64/complex FFT plane of
      that size is about 250–500 MB. Phase correlation, masks and A/B planes multiply that per sheet pair. The
      worker container runs `AUDITMANAGER_WORKER_SLOTS` jobs beside run analysis (`compose.server.yml:301,349`).
    - Fix: CMP-ENGINE-01 also measures peak RSS per A1 pair at the chosen registration scale and fixes a
      downsample-for-registration rule plus a per-job memory budget. The test fixtures stay A4 at low dpi. A
      stop/size rule goes into §8 (e.g. refuse > N Mpx per page with a typed state).

18. **R2-18 · MAJOR · §7 estimate** — 9–11 working days is the optimistic edge, and the method leaves the real
    driver out.
    - Measured lane spans (first lane commit → merge into integration):

      | Slice | Size | Span | Files / lines |
      | --- | --- | --- | --- |
      | AR-V3-DECISIONS-01 (L, migration) | L | base 14:12 → merge 16:11, 2.0 h | 53 / 3 696 |
      | COMPARE-PERSISTED-SUMMARY-01 (L, contract + migration) | L | 03:35 → 06:37, 3.0 h | 85 / 11 790 |
      | W59-VERSION-COMPARE-01 | — | 1.8 h | 63 / 6 879 |
      | EXEC-PULL-01 | — | 1.6 h | 71 / 7 337 |
      | EXEC-PAR-QUEUE-01 | — | 0.7 h | 16 / 1 321 |
      | EXEC-PAR-START-01 (contract bump) | — | 0.5 h | 114 / 2 250 |

    - Lane execution is not the bottleneck. The integration branch merged about 30 lanes on 2026-10-26/27. The
      bottleneck is the serial chain.
    - Method: critical-path steps per wave from §4's order lines plus judge and FIX:
      - C0: ADR → SEAL → {4 ∥} → INGEST-02 → judge → FIX, 6 steps;
      - C1: 7 steps, with ENGINE XL on the path;
      - C2: 7 steps;
      - C3: 5 steps, partly overlapping C2, so +3;
      - C4: 7 steps.
      That is about 30 steps at a measured 2–3 h per lane plus about 1 h of merge and light acceptance: 90–120 h of
      orchestration. Add ENGINE XL (+6 h) and the STOP/regrant cycles that the grants missing in this review would
      cause (about 8 × 1.5 h ≈ +12 h) if revision 2 does not fix them.
    - Range: about 100–140 h, which is **11–15 working days of ≈ 10 h** (P50 ≈ 13), not 9–11. From a C0 start on
      2026-10-29: code-complete P50 ≈ 2026-11-16 and P80 ≈ 2026-11-20 (working days). The full gate before beta
      (≤ 1 day) is on top.
    - The entry itself waits on SX and PR (R2-05). Re-state §7 with this method and the measured spans.

19. **R2-19 · MAJOR · CMP-INGEST-01/02 (identity and staging), AGENTS §4** — Resume and grouping identities,
    and the chunk staging, are not fixed.
    - Evidence: the batch upload groups by «designation or name base», «(N)» order hints and «Общая папка».
      `contracts/domain/v1/identifiers.json` rules: «A filesystem path, directory name, uploaded file name … must
      not be identity». A resumable transfer needs a durable owner for every partial upload. The repository
      pattern is to persist the `BlobDeclaration` before staging (`storage/models.py:120-128`) plus the
      temporaries sweep (`jobs/temporaries.py`, `workers/service.py:391-404`).
    - Fix: in ADR-0025, the resume key is an opaque `cbt_`/item id plus the declared sha256 and size, never a
      path. File names and folders only feed the proposal the user confirms. A chunk has a DB owner before its
      bytes are staged, an abandoned batch is swept by the existing sweep, and the 10 000-file limit is a typed
      refusal.

20. **R2-20 · MINOR · §2 G-06, G-19, G-22; §3 A-6; CMP-PROFILE-01; CMP-STAGE-REVIEW-01** — Citations that do not
    say what the plan says:
    - (a) `jobs/repository.py:211` and `:266-343` are the effect-journal insert (stage hard-coded `'text_analysis'`)
      and the completed-call/window selects plus `_INSERT_MODEL_CALL`, **not cost queries**. The cost queries are
      `runs/repository.py` `_COST_SUMMARY` (≈ `:180-187`) and `dashboard/repository.py` `_SPEND` (≈ `:105-112`); the
      meter is `analysis/text/cost.py`.
    - (b) G-19 omits `ck_model_call_stage_id`, `ck_provider_effect_stage_id CHECK (stage_id = 'text_analysis')` and
      `uq_job_run_id`.
    - (c) G-06: proposals are in `comparison/sheet_match_suggestions.py`; `comparison/pairing.py` approves and
      withdraws.
    - (d) G-22: the line diff is `comparison/raw_text.py` (`diff_approved_pairs`); `raw_evidence_seal.py` seals it.
    - (e) A-6 omits the DB constraint `ck_executor_route_work_kind CHECK (work_kind IN ('text_analysis'))`
      (`0030_executor_connections.py:360`), which SEAL-C2's migration must widen.
    - (f) «`analysis/public.py` (one-line export)»: no full-page renderer is exported. `analysis/geometry/render.py`
      is a clip renderer under ingest's `PDFIUM_LOCK`.
    - (g) «exports public API»: see R2-16.

    The citations that hold: `bundle_archive.py:200`, `repository.py:28`, `image_input.py:34-53`,
    `pull.py:193-196`, `model.py:68-70`, `0002:820-823`, `runs/commands.py` (`:385-395`), `screen-registry.ts:161`,
    `optimisation/specification.py:3`, `pyproject.toml:30-32/46/48` and `tools/fixtures/ar_corpus/pdfwrite.py`.

21. **R2-21 · MINOR · A-2 identities** — «Content-keyed» `cpr_`/`csp_` contradicts the identifier format.
    - Evidence: `identifiers.json` `"format": "<prefix>_<ULID>"`, «never parsed to recover business meaning».
      The proposed prefixes are free: none of the 18 collides with the 48 existing ones.
    - Fix: each such row gets a ULID id plus a unique content-key digest column.

22. **R2-22 · MINOR · §6, §0 base** — Stale facts.
    - Evidence: D-245 was «Fixed 2026-10-27 by `FIX-P02-GUARDS-01` (merge `ae869a2c`)» on the integration tip, so
      «two halves under one hour each (`D-245`)» is no longer the rule.
    - Fix: re-read the base facts from the tip at revision 2.

23. **R2-23 · MINOR · §4 own paths** — Several own paths are not machine-checkable, and no enumerators are named.
    - Evidence: paths such as «`runs/commands.py` (refusal only)», «one entry in `screen-registry.ts`»,
      «`comparison/engine/tiles*`» and `comparison/matrix/**` (no `src/auditmanager/` prefix) do not pass
      `scripts/task_handoff.py`, which «refuses an ambiguous allowlist» (`TASK_TEMPLATE.md` «Allowed paths»).
      No slice names its enumerators: `screen-registry.ts`, `routes.ts`, `manifest.json`, `screens.ts`,
      `identifiers.json` + `shared/identity/ids.py`, the recovery lists, `catalog-message.ts`.
    - Fix: rewrite every own path as an exact path or `dir/**` and add the «Enumerator ownership» block per seal
      and UI slice.

24. **R2-24 · MINOR · §5** — Some shared single files are unassigned.
    - Evidence: `src/auditmanager/comparison/public.py` is the only cross-context entry ALR-05 allows
      (`tests/contract/architecture/test_alr05_boundaries.py:120-140`, `parts[2] == "public"`), and every comparison
      lane appends to it. `comparison/README.md`. The web API hooks live in `web/src/entities/**`
      (`entities/version-comparison/api/use-sheet-pairing.ts`), which no slice owns.
    - Fix: assign `public.py` appends per lane, serialised. Grant `web/src/entities/<new>/**` to the UI slices.

25. **R2-25 · MINOR · O-2, §6 fixtures** — The fixture PDF writer has gaps.
    - Evidence: `tools/fixtures/ar_corpus/pdfwrite.py:1-8` supports a page tree, uncompressed content, one
      CIDFontType2 font, image XObjects and RC4. It has no `/Annots`, which the plan's `annotations` channel needs.
      Its font `tools/fixtures/assets/ARCorpusSans.ttf` is a 32 KB subset. «Promoting» it to a product PDF writer
      means moving about 900 lines (`pdfwrite.py` + `ttfsubset.py`) and a full Cyrillic font into `src/`. `tools/`
      is not in the API image (`Dockerfile.api` copies `pyproject.toml uv.lock` + `src`).
    - Fix: price annotation support in the corpus slice, and in O-2 state the font and licence the product writer
      ships with.

26. **R2-26 · MINOR · §5 «C3 may run beside C2»; C4** — Once SEAL-C3 holds the head, no slot is left for later
    fixes.
    - Evidence: with SEAL-C3 holding the migration head and contract, a C2 FIX lane after the C2 judge cannot add
      a migration or contract fix. C4 has no seal for its fixes either (R2-01).
    - Fix: run SEAL-C3 only after the C2 judge's FIX has merged, or reserve a C2-FIX seal slot.

27. **R2-27 · MINOR · A-5 dependency lock** — The lock change has more pins than `pyproject.toml` and `uv.lock`.
    - Evidence: `tests/contract/test_w55b_direct_pins.py:22-54` holds `pyproject.toml`, `uv.lock` and
      `docs/program/P02_LOCK.json` equal for direct pins. `numpy` is not in `uv.lock` today
      (`grep -n numpy uv.lock` → nothing). `uv lock` needs network access.
    - Fix: grant `docs/program/P02_LOCK.json` and that test's `DIRECT` tuple to SEAL-C0 and SEAL-C2.

28. **R2-28 · MINOR · A-3 effective matrix; §1.2 tab 2 masks (AGENTS §4 «LLM output as canonical»)** — The
    plan does not say what downstream outputs show when AI decisions shaped them.
    - Evidence: an accepted AI link («ИИ») changes which pairs the deterministic series compares and what the
      verdict and MD summary say. An AI SAME/MOVED adds the grey masks that hide a raw difference from the cards.
      Neither is an expert act.
    - Fix: the series verdict, the MD summary and the report mark transitions whose pairs depend on an AI link.
      Masked differences stay listed in «Показать исходные текстовые различия» with their AI class. The mutation
      proofs include «an AI SAME never removes a raw difference row».

ROUND 2 VERDICT: 4 BLOCKER, 15 MAJOR, 9 MINOR
