# Task CMP-SEAL-C2 — the seal of wave C2: contract 1.11.0, migration 0040, the version-comparison AI, specification, report and queue surface

## Outcome
On `integration/compare-modules` the contract is `1.11.0` with every C2 operation sealed as a stub, migration `0040`
creates the C2 tables and widens `ck_executor_route_work_kind`, the four new executor work kinds exist end to end
(model, contract enum, web vocabulary and route labels), the contract-shaped items left by wave C1 are closed, and every
pin these facts move is updated, so that the C2 lanes (AIPAIR, AISHEET, SPEC, QUEUE, REPORT, VC-UI-02) start on a green
tree.

## Depends on
- wave C1 lanes merged on `integration/compare-modules` (SEAL-C1, ENGINE, MATRIX, VIEWER, SERIES, OVERVIEW, VC-UI-01)

## Frozen inputs
- API contract: `1.10.0`, 131 paths / 148 operations / 432 schemas at the base; domain contract `contracts/domain/v1/**`
- ADR-0025 (decisions 3, 4, 6, 10, 11, 12, 13, 14, 16, 17–23, 25 and both addenda); plan `A-6`, `A-8`, `A-12`, §1.1, §4 C2
- owner answers `Q-CMP-4` (images to models, `A-12`), `Q-CMP-6`, `Q-CMP-7` (USD estimate + consent + ceilings $10 per
  job, $50 per day per installation, a ×1.2 overrun pauses, `not_metered` has no ceiling), `Q-CMP-9` (reportlab)
- migration head: `0039_comparison_core` (this seal takes `0040`, revision id ≤ 32 characters)
- base commit: the integration tip named in the dispatch message

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: CMP-SEAL-C2
- totality_query: the `tools/plan/pin_sweep.py` modes used by CMP-SEAL-C0 and CMP-SEAL-C1 (`docs/program/CMP-SEAL-C1.md` §5)

## Captured premise evidence
- premise: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`, product `0.9.0`
  on the integration tip; the lane prints the same before any edit and STOPs if they differ

### P-01 — base facts of the integration tip before the seal
- captured_at: 2026-10-29
- command: `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(d['info']['version'], len(d['paths']), sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')), len(d['components']['schemas']))"; ls db/migrations/versions/*.py | tail -1; cat VERSION`
- captured_output:
  ```text
1.10.0 131 148 432
db/migrations/versions/20261028_0039_comparison_core.py
0.9.0
  ```
- interpretation: contract `1.10.0` with 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`,
  product `0.9.0`; the lane prints the same before any edit and STOPs if they differ

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- the allowed paths of `docs/program/tasks/CMP-SEAL-C1.md`, plus `src/auditmanager/executors/model.py` (work kinds
  only), `web/src/entities/executor-connection/model/vocabulary.ts`, `web/src/widgets/executor-routes/**` (work-kind
  labels only), the four C1 router files `src/auditmanager/api/routers/comparison_{matrix,series,pair_tiles,overview}.py`
  (docstrings only), and any file the disposable probe proves pins a fact this seal moves (listed with its reason in
  the report)

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c2`
- postgres_port: `57890`
- s3_api_port: `61890`
- s3_console_port: `61891`
- postgres_db: `auditmanager_cmp_seal_c2`
- s3_bucket: `auditmanager-cmp-seal-c2`

## Forbidden hotspots
- as CMP-SEAL-C1; no product logic beyond stubs and the module-flag refusal; `src/auditmanager/jobs/**`,
  `infra/deploy/compose.server.yml`

## Non-goals
- no AI pipeline, prompt, specification extractor, MD or PDF writer, queue runner or screen; the C2 lanes build them

## Deliverables
1. Disposable apply-and-run probe first; its red list is the grant list.
2. Contract `1.11.0` (additive minor), sealed stubs answering `503 dependency_unavailable` with a dependency class name
   per lane, roles per ADR-0025 decision 16 (every command an expert's act; reads any role), keyed writes, for (names
   are proposals; keep the addressing style of C1, no ordinal in a path, identities opaque):
   - **AI check of doubtful pairs** of a document set (CMP-VC-AIPAIR-01): an estimate (questions, pairs, images,
     image bytes, prompt size, routed model, USD estimate), a start that carries the estimate it consents to, a job
     read (state, progress, counts «вопросов · пар · подсказок · против», spend so far), pause / resume / cancel, the
     answers and hints per matrix cell (hint «вероятно стр. N», «ИИ ?»); accepted answers are written as
     `comparison_ai_link` rows by the lane's rule, never by a client call;
   - **AI description of changes** (CMP-VC-AISHEET-01): per series (per transition progress «Листов / Изм. / Вопр. /
     Ошибок / Проверить / Обращ.», tokens, time), estimate, start with consent, pause / resume / cancel / «Досчитать» /
     «Убрать из очереди» / «Повторить листы с ошибкой»; the description of one sheet pair (the eleven state labels of
     the inventory, the changes with object, before/after, place, «Неясно», tiers `text|image|unverified`,
     «Требует уточнения», «Заявлено проектировщиком в разрешении», «Не включено в сводку», diagnostics, history); the
     single-sheet description of an added or removed sheet (estimate → consent → run, cancel); the «Проверить» list;
     the MD of one sheet as a download;
   - **Specifications** (CMP-VC-SPEC-01): part A, the deterministic positions of a specification sheet
     («Спецификация по позициям») per page profile; part B, the AI whole-specification comparison per transition:
     estimate, start with consent, read (method «полное сравнение» / «листовой ИИ», spec sheets A/B, coverage, positions
     «изменено / +добавлено / −удалено / ?неясно», reason), cancel;
   - **Launch queue** (CMP-VC-QUEUE-01): enqueue selected sets × steps (2, 3, 5 and the C2 steps 4, 6, 7, report), the
     queue read («готово N из M · пропущено K · ошибок E»), pause / resume / clear / remove one entry; the
     per-installation AI queue read «Очередь «ИИ-описание изменений»»;
   - **Reports** (CMP-VC-REPORT-01): the deterministic MD summary of a series (download, same bytes for the same data);
     PDF report jobs with source «сводка проекта» or an uploaded MD file, kind `client` (default) or `analytic`,
     estimate / consent / start, per-transition progress, cancel / continue / «Пересобрать PDF» (no model call) /
     delete, «Подготовить отчёт для заказчика» from an analytic report, the report history and downloads (PDF and the
     source MD);
   - **Spend and consent on every AI start**: the USD estimate, the consent line, the ceilings of `Q-CMP-7` as
     refusals with registered reasons, the ×1.2 overrun pause reason, `not_metered` unlimited; every AI command answers
     `dependency_unavailable` naming the module while `ProductVersion.comparison_modules` does not include `versions`
     (`A-12`: drawings reach a model only when the owner has enabled the module).
3. **Executor work kinds (`A-6`)**: `comparison_pair_check`, `comparison_sheet_changes`, `comparison_spec`,
   `comparison_report` in `src/auditmanager/executors/model.py` (`WORK_KINDS` / `SERVES`), the contract enum
   `ExecutorWorkKind`, `web/src/entities/executor-connection/model/vocabulary.ts` and the labels in
   `web/src/widgets/executor-routes/**`; `comparison_stage_review` stays for SEAL-C4.
4. **Migration `0040`**: the tables for the above (AI jobs with their consented estimate and spend link to
   `comparison_model_call`; content-keyed pair-check answers so an answered question is never sent again;
   per-pair-result sheet descriptions keyed by content and prompt version; per-version specification extractions and
   per-transition specification comparisons; reports and their artifacts; launch-queue entries), every table reachable
   from `project` (ADR-0025 decision 5), ULID identities with new prefixes in the identifier catalogue, the widening of
   `ck_executor_route_work_kind`, up/down on an isolated database, the per-table family (`CMP-SEAL-C1` §4 and §5).
5. **Contract items left by wave C1** (reports `CMP-MATRIX-01` §9, `CMP-SERIES-01` §9, `CMP-VIEWER-01`, `CMP-VC-UI-01`):
   `ComparisonMatrixStaleReason` gains `algorithm_changed`; `ComparisonMatrixColumn.label` gets a source (the version's
   label of the upload proposal, or a contract-stated fallback); register `comparison_matrix_stale` on
   `startComparisonSeries` (a matrix that is not ready) and `validation_failed` with constraint
   `comparison_versions_few` (a set of one version); the pair read carries the raster size of page A's pyramid (so the
   viewer need not derive it); remove «sealed as a stub until …» from the C1 routers' docstrings and the OpenAPI
   descriptions of the operations C1 wired.
6. Generated client, `FRONTEND_LOCK.json` reseal, pins (contract version, surface, head, per-table family, identifier
   catalogue, stub enumerators, `P02_TABLES`), the report `docs/program/CMP-SEAL-C2.md` with a per-lane table
   (operations and tables each C2 lane implements).

## Required tests
- as `docs/program/tasks/CMP-SEAL-C1.md` (contract minus D-220, web lint/typecheck/vitest/api:verify, journey
  conformance, the db/recovery/composition/p02_journey/foundation directories on the lane stack, migration round trip)

## Integration contract
Every C2 operation answers `503 dependency_unavailable` until its lane wires it; lanes STOP to the FIX slot for a
missing field.

## Failure/idempotency/security cases
- every AI start carries the estimate it consents to and is refused when the estimate is stale, over a ceiling or the
  module is off; content keys include `project_uid`; an answer once stored is never re-requested

## Rollback / feature flag
`comparison_modules` stays `none` by default; with it off every C2 command refuses before any read or write.

## Handoff
- changed files:
- commands/results:
- known limits:
- integration notes:
