# Current state

**Updated 2026-11-05 by `UI-PARITY-INT-1105c` (unverified development candidate, third publication).** The administrator forms offer «Наблюдатель» (`VIEWER_ROLE_OFFERED` on). Both the user form and the registration approval refuse it beside another role before sending (`R-150e`); turning the switch off is the rollback.

Stand rerun on `b9a725c5`: 108 passed. It covers the dashboard census, the inventory at `0050`, the `0015` vocabulary and the optimisation viewer capability tests, the three reds of the earlier combined check, now green.

`test_project_match` `unit_mismatch` stays red and is unrelated to this work (`D-315`). Web checks for the form change: `tsc`, eslint and focused vitest, green.

**Updated 2026-11-05 by `UI-PARITY-INT-1105b` (unverified development candidate, second publication).** New on top of `UI-PARITY-INT-1105`:
- the dashboard's section rows carry the original's five numbers (`UI-A-35`);
- the findings table in «Разбор», with the first `shared/ui` `Table` (`UI-A-68`, `R-150f`);
- the decision gate moved from `DecisionPanel` to the review page, and the review writes `?finding=`/`?verdict=` through `window.history`;
- fixes from the combined check: the cancel failure sentence, the census renders with a query client, the guards and role tests know the operator screens (`R-150w`), the viewer's refusal capability in the optimisation tests, the `0050` vocabulary and the inventory reseal (constraints digest at `0050`), and the dashboard census seeds a second project.

Checks on this tree's web part:
- `tsc` and eslint (whole `web/`) are green;
- the whole web vitest: 5047 / 5051 on `d8e36ee4`, then the four remaining files green on `9d017a8a`.

Backend checks, measured earlier on `bef54479`:
- the combined check gave contract 543, unit 81, and stand integration green for access (309), dashboard (22), execution (18) and characterization (75);
- its two DB reds and the dashboard census red are fixed by test changes here, and were **not re-run on a stand**.

Still owed (`D-314`): those three tests on a stand, the `test_project_match` `unit_mismatch` comparison at the base, the browser journey and `next build`. No full gate without the owner's order.

**Updated 2026-11-05 by `UI-PARITY-INT-1105` (unverified development candidate, published ahead of its checks by the owner's order).** UI-parity waves 0–3 code on one tree (`docs/program/UI-PARITY-01.md`, `R-150a`…`R-150z`). It holds:
- the readable queue (contract 1.18.0: work names, start, end, error, state and period filters);
- document audit-state counters (1.19.0, `UI-PARITY-METRICS.md`);
- the viewer role «Наблюдатель» (`Role` gains `viewer`; 112 reads open to it; the queue, journal, executors and assignments closed to it; never combined with another role; migration `0050_viewer_role`; the admin forms do not offer it yet, `VIEWER_ROLE_OFFERED = false`), and screens that stop offering expert actions to it;
- the «Проекты ▾» selector in the top strip with «не запускались» / «нет решений эксперта»; `/projects` leaves the sidebar;
- the project carried in the address on the comparison screens; the project tab, the chosen finding and the verdict filter in the address;
- the review's verdict tally and filter;
- the context strip «Проекты › Проект › Документ › Версия › Прогон › Разбор» with a version choice;
- «Отменить прогон» and «События прогона» on the run page;
- a job state badge in the queue; «Обновить» on a project's sections;
- one source for poll intervals, with the workers list auto-refreshing.

Checks run per branch before the merge:
- readable queue: contract 559, web 1007 + 327, stand integration 18 + 60 + 37;
- polling: web 677;
- counters: contract 706, unit 94, `tsc`, eslint, stand integration (dashboard 184, API 101, composition, characterization 75); its full web battery was voided by host memory;
- viewer role: contract 543, `tsc`, stand access 309.

**Not run on the merged tree:** the combined check `.local/evidence/ui-parity-int-logs/` was queued at publication; the web branches merged after their own checks were dequeued. No browser journey, no `next build`, no full gate (owner: only on his order). Debt `D-314`. `agent/ui-parity-doc-state-p0d` is postponed (`R-150z`) and not on this tree.

**Updated 2026-11-05 by `UI-PARITY-P0B` (unverified development candidate).** Contract **1.19.0** gives a document an audit state and its counters (`R-150n`…`R-150u`, `docs/program/UI-PARITY-METRICS.md`); the counts are 250 paths / 277 operations / 675 schemas (one new schema, `DocumentAuditCounts`), with no migration and no new error code. A document counts by its current version only; its result run is the latest `published` or `partial` run, and it is `not_run`, `clean`, `awaiting_decision` or `checked`, with a `partial` flag. `listProjects` items carry `audit_counts`, `SectionDocumentCount` carries `audit_counts` and `finding_count`, and `DashboardSummary` carries `awaiting_decision_findings`; all three are tallies of one read model (`dashboard/audit_state.py`). `VerdictCount` is described as every finding of every run, «за всё время». The home tile «Находки, ожидающие решения» reads the new figure and the verdict panel is labelled. The header selector and the new columns are waves 1 and 2. Checks: see the lane's record; the DB-backed tests ran on the lane's own stand.

**Updated 2026-11-04 by `UI-PARITY-P0A` (unverified development candidate).** Contract **1.17.0** is an additive read slice; the counts stay 250 paths / 277 operations / 674 schemas, with no migration and no new error code. `getDashboardSummary` takes an optional `project_uid`: every panel keeps its definition, restricted to that project, and an unknown project is the existing not-found. `listDecisions` takes an optional `project_uid`, a filter where an unknown project gives an empty page. `DecisionRecord` gains `document_uid`, `version_uid`, `project_name` and `document_name`, joined at read time, plus an optional `section` from the current classification. `DecisionRecordPage` gains `total`. Pins, the generated client and `FRONTEND_LOCK.json` are resealed. Checks: contract and unit-api pytest (580 passed on the merged tree); `api:verify`, `tsc` and web contract tests; integration tests on the lane's own stand (the new dashboard, decision and spend tests pass; the reds are the stage-operation ones already red at the base). Pending until the EXEC-2 register repair lands: the 1.17.0 query census in `tests/integration/api/test_query_surface.py` and `getDashboardSummary` in the declared-422 set. No screen consumes the new parameters yet.

**Updated 2026-11-04 by `UI-PARITY-NIGHT-1` (unverified development candidate).** UI/UX parity with the original application starts (`R-150a`…`R-150m`, `docs/program/UI-PARITY-01.md`). «Разбор находок» now reads every finding of a run: `limit` 200, `next_cursor` followed to the end, and no partial list on a failed page. Before this it showed the first 50 silently. The knowledge base pages with «Назад/Далее». «Очередь» and «Журнал выполнения» refresh every 10 s while visible; they back off to 60 s on errors, show «Обновлено ЧЧ:ММ:СС» and mark old data as possibly stale. The screen registry classes every address as `required`/`optional`/`global` for the project context, and pure address helpers implement the path-wins and dependent-reset rules; no screen uses them yet. Owner questions go to debt `D-300`…`D-310`. Checks: focused vitest (97 files / 1589 tests), `tsc`, `eslint` on the touched packages. **No live browser journey and no backend or contract runs** for this web batch.

**Updated 2026-11-03 by `EXEC2-FIX-CONTRACT` (unverified development candidate).** The container-free contract suite is made to describe the tree it runs on: 26 reds in 12 files, from EXEC-2 and from earlier waves on `origin/dev` (the comparison stage, the 2026-10-30 hotfixes, W55b). Stale pins and prose were re-measured and not loosened: the required-operation, keyed-write and input-less sets; the P02 seam register (every operation of contract 1.16.0 in its table, the keyed-write rule and the unkeyed writes); the run-start, preset, identity and conformance counts; the PDF ceilings that `SECTION-STATS-UNCAPPED-1030` lifted; the fifteenth (draft АР) profile in the release-note checks; the unauthenticated `downloadAgentPackage`, whose path is keyed by version (`ADR-0026` decision 6) and is registered as an exception by path. A response spelled out in full counts as the shared `401`/`403` only when it equals the component. One code defect (ALR-05): `comparison/stage*` imported `ingest` internals and now goes through `auditmanager.ingest.public`. The live part of this file is cut to its newest entries; the full state at `EXEC2-INT-3` is archived verbatim. The `info.description` sentence of the contract that states the `1.14.0` triple is registered as history, not edited. No contract, migration, generated client, web or release-note file changed. Measured once under the host lock on the uncommitted tree: `tests/contract` without the three bootstrap files, 1361 passed and 1 failed — `test_alpha_acceptance_command`, which refuses a checkout with uncommitted changes and passed on the clean tree before this change. dev only.

**Updated 2026-11-03 by `EXEC2-INT-3` (unverified development candidate).** EXEC-2 stage 3 completes the wave (`ADR-0026`, `R-149a`…`R-149i`): Runs and the five comparison kinds are admitted by executor group or by per-work-kind rule and bound to one member at dispatch (least-loaded, write-once, consent and USD ceilings re-checked against the member, model I/O after commit); durable wait reasons, `no_executor_online` after the offline wait; the «Группы»/«Правила» screens, the three-way start selector and planned-versus-actual model; the Primary/Standby → rules cut-over with preview, confirmation and rollback (`docs/manual-tests/EXEC2-CUTOVER.md`). All 277 operations of contract 1.16.0 are served; migration head `0048_dispatch_time_binding`. **No tests/build/typecheck/lint/DB/browser/model checks were run (`R-149d`)**; static parse, generator check and a read-only review (1 HIGH queue stall and 1 MEDIUM fixed). The host run slot belongs to the EXEC-2 integrator (`R-149i`); `D-292` waits for it. dev only. See `EXEC2-INT-3.md`.

**Updated 2026-11-03 by `EXEC2-INT-2` (unverified development candidate).** EXEC-2 stage 2 (`ADR-0026`, `R-149a`…`R-149g`): path A agent install over SSH run by the worker (destination policy, pinned host key, secret on stdin only; private ranges only with `AUDITMANAGER_AGENT_INSTALL_ALLOW_PRIVATE=1`); the «Добавить подключение» wizard for paths A and B, one agent lifecycle, OpenRouter preset, moving an agent; executor groups and per-work-kind rules stored and validated (homogeneous, closed membership), least-loaded selection ready for stage 3; `executor_group_id` on a run start is refused until stage 3. Contract 1.16.0 (250 paths / 277 operations / 674 schemas), migrations `0047_executor_groups_rules` and `0048_dispatch_time_binding`. **No tests/build/typecheck/lint/DB/browser/model checks were run (`R-149d`)**; static parse, generator check and one read-only review (fixes merged). Routing preview and mode are declared and not served until `EXEC2-CUTOVER-01`. dev only. See `EXEC2-INT-2.md`.

**Updated 2026-11-02 by `EXEC2-INT-1` (unverified development candidate).** EXEC-2 stage 1 (`ADR-0026`, rulings `R-149a`…`R-149f`): per-connection capacity units (`max_active_runs`, default 1 = the old exclusivity) in the Run claim, the dispatcher hint and the comparison call; pull claims serialised per runner token with `runner_instance_id`; agent enrollment (single-use grant → runner token), health, package download, agent-install API side and the integration mark; one `install.sh` for SSH and copied-command paths with the model taken only from the connection; capacity and waiting reasons in the web. Contract 1.15.0 (241 paths / 267 operations / 644 schemas), migration `0046_executor_capacity_enroll`. **No tests/build/typecheck/lint/DB/browser/model checks were run (`R-149d`)**; static parse, generator check and one read-only review (fixes merged). Client documents unenforced (`D-291`), acceptance tests unrun (`D-292`). dev only. See `EXEC2-INT-1.md`.

**Updated 2026-10-30 by `BLOCK16-INT-1030` (unverified development candidate).** Saved preliminary correspondence now includes actual text field/ranges, recognised-entry identity, page-text/artifact/role and exact observation/primary quotes. Same wording at different locations on one page stays separate; malformed or conflicting evidence cannot justify exact pairing. Quote ranges use Unicode code points and must fit known source bounds; full supplied piece text is checked when available. Raw records/multiplicity and reader/export limits remain, no source/expert/model mutation. **No tests/build/compile/import/lint/typecheck/browser/DB/model checks were run.** API1.14.0/migration0044/backend/paid authority unchanged, synthetic inputs untouched, dev only/owner deploys. See `BLOCK16-INT-1030.md`; D-290 remains open.

## Facts of this tree

Each is re-measured by `tests/contract/api_v1/test_doc_prose_facts.py` against the tree, so a stale one is a red test and not a habit.

- Product `VERSION` is `0.9.0`; this file describes development, not a release.
- The development API contract is `1.19.0`: **250 paths / 277 operations / 675 schemas** (`contracts/api/v1/openapi.json`); the error catalogue has **27** codes; the migration head is **`0050_viewer_role`** (`db/migrations/versions/`).
- The surface of each earlier seal, and the head it left, are stated in the entries above (the stage-1 entry names the `1.15.0` triple) and in [the 2026-11-03 state archive](history/CURRENT_STATE_2026-11-03_51183a75.md); they are records of their day and not claims about this tree.

Run `infra/deploy/verify-deployed.sh` for the current deployment; this document is no substitute for that probe.

## Pointers and history

Read the assigned task, completed `depends_on`, frozen contracts and allowed
paths before editing. `docs/program/DEBT_REGISTER.md` tracks open work.

This file keeps the newest entries only (`tests/contract/program/test_process_acceleration.py` holds it to 120 lines).
The complete state at `EXEC2-INT-3`, every dated entry and the sections «Normative corpus (W54)» and
«Code-first series (R-135)», is preserved verbatim in
[the 2026-11-03 state archive](history/CURRENT_STATE_2026-11-03_51183a75.md);
the complete state at candidate 66 in
[the 2026-10-19 state archive](history/CURRENT_STATE_2026-10-19_ec41bb58.md),
and the 320-line state before candidate 17 in
[the 2026-10-16 state archive](history/CURRENT_STATE_2026-10-16_71373417.md).

## Previous release state — wave 48 (historical record)

The full previous release state, including the older CP-00 history, is stored
verbatim in [the dated archive](history/CURRENT_STATE_2026-10-15_ccfb9735.md).
That archive is a point-in-time record of the base tree, not live status.
