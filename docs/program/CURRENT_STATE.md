# Current state

**Updated 2026-11-04 by `UI-PARITY-NIGHT-1` (unverified development candidate).** UI/UX parity with the original application starts (`R-150a`…`R-150m`, `docs/program/UI-PARITY-01.md`). «Разбор находок» now reads every finding of a run: `limit` 200, `next_cursor` followed to the end, and no partial list on a failed page. Before this it showed the first 50 silently. The knowledge base pages with «Назад/Далее». «Очередь» and «Журнал выполнения» refresh every 10 s while visible; they back off to 60 s on errors, show «Обновлено ЧЧ:ММ:СС» and mark old data as possibly stale. The screen registry classes every address as `required`/`optional`/`global` for the project context, and pure address helpers implement the path-wins and dependent-reset rules; no screen uses them yet. Owner questions go to debt `D-300`…`D-310`. Checks: focused vitest (97 files / 1589 tests), `tsc`, `eslint` on the touched packages. **No live browser journey and no backend or contract runs** for this web batch.

**Updated 2026-11-03 by `EXEC2-FIX-CONTRACT` (unverified development candidate).** The container-free contract suite is made to describe the tree it runs on: 26 reds in 12 files, from EXEC-2 and from earlier waves on `origin/dev` (the comparison stage, the 2026-10-30 hotfixes, W55b). Stale pins and prose were re-measured and not loosened: the required-operation, keyed-write and input-less sets; the P02 seam register (every operation of contract 1.16.0 in its table, the keyed-write rule and the unkeyed writes); the run-start, preset, identity and conformance counts; the PDF ceilings that `SECTION-STATS-UNCAPPED-1030` lifted; the fifteenth (draft АР) profile in the release-note checks; the unauthenticated `downloadAgentPackage`, whose path is keyed by version (`ADR-0026` decision 6) and is registered as an exception by path. A response spelled out in full counts as the shared `401`/`403` only when it equals the component. One code defect (ALR-05): `comparison/stage*` imported `ingest` internals and now goes through `auditmanager.ingest.public`. The live part of this file is cut to its newest entries; the full state at `EXEC2-INT-3` is archived verbatim. The `info.description` sentence of the contract that states the `1.14.0` triple is registered as history, not edited. No contract, migration, generated client, web or release-note file changed. Measured once under the host lock on the uncommitted tree: `tests/contract` without the three bootstrap files, 1361 passed and 1 failed — `test_alpha_acceptance_command`, which refuses a checkout with uncommitted changes and passed on the clean tree before this change. dev only.

**Updated 2026-11-03 by `EXEC2-INT-3` (unverified development candidate).** EXEC-2 stage 3 completes the wave (`ADR-0026`, `R-149a`…`R-149i`): Runs and the five comparison kinds are admitted by executor group or by per-work-kind rule and bound to one member at dispatch (least-loaded, write-once, consent and USD ceilings re-checked against the member, model I/O after commit); durable wait reasons, `no_executor_online` after the offline wait; the «Группы»/«Правила» screens, the three-way start selector and planned-versus-actual model; the Primary/Standby → rules cut-over with preview, confirmation and rollback (`docs/manual-tests/EXEC2-CUTOVER.md`). All 277 operations of contract 1.16.0 are served; migration head `0048_dispatch_time_binding`. **No tests/build/typecheck/lint/DB/browser/model checks were run (`R-149d`)**; static parse, generator check and a read-only review (1 HIGH queue stall and 1 MEDIUM fixed). The host run slot belongs to the EXEC-2 integrator (`R-149i`); `D-292` waits for it. dev only. See `EXEC2-INT-3.md`.

**Updated 2026-11-03 by `EXEC2-INT-2` (unverified development candidate).** EXEC-2 stage 2 (`ADR-0026`, `R-149a`…`R-149g`): path A agent install over SSH run by the worker (destination policy, pinned host key, secret on stdin only; private ranges only with `AUDITMANAGER_AGENT_INSTALL_ALLOW_PRIVATE=1`); the «Добавить подключение» wizard for paths A and B, one agent lifecycle, OpenRouter preset, moving an agent; executor groups and per-work-kind rules stored and validated (homogeneous, closed membership), least-loaded selection ready for stage 3; `executor_group_id` on a run start is refused until stage 3. Contract 1.16.0 (250 paths / 277 operations / 674 schemas), migrations `0047_executor_groups_rules` and `0048_dispatch_time_binding`. **No tests/build/typecheck/lint/DB/browser/model checks were run (`R-149d`)**; static parse, generator check and one read-only review (fixes merged). Routing preview and mode are declared and not served until `EXEC2-CUTOVER-01`. dev only. See `EXEC2-INT-2.md`.

**Updated 2026-11-02 by `EXEC2-INT-1` (unverified development candidate).** EXEC-2 stage 1 (`ADR-0026`, rulings `R-149a`…`R-149f`): per-connection capacity units (`max_active_runs`, default 1 = the old exclusivity) in the Run claim, the dispatcher hint and the comparison call; pull claims serialised per runner token with `runner_instance_id`; agent enrollment (single-use grant → runner token), health, package download, agent-install API side and the integration mark; one `install.sh` for SSH and copied-command paths with the model taken only from the connection; capacity and waiting reasons in the web. Contract 1.15.0 (241 paths / 267 operations / 644 schemas), migration `0046_executor_capacity_enroll`. **No tests/build/typecheck/lint/DB/browser/model checks were run (`R-149d`)**; static parse, generator check and one read-only review (fixes merged). Client documents unenforced (`D-291`), acceptance tests unrun (`D-292`). dev only. See `EXEC2-INT-1.md`.

**Updated 2026-10-30 by `BLOCK16-INT-1030` (unverified development candidate).** Saved preliminary correspondence now includes actual text field/ranges, recognised-entry identity, page-text/artifact/role and exact observation/primary quotes. Same wording at different locations on one page stays separate; malformed or conflicting evidence cannot justify exact pairing. Quote ranges use Unicode code points and must fit known source bounds; full supplied piece text is checked when available. Raw records/multiplicity and reader/export limits remain, no source/expert/model mutation. **No tests/build/compile/import/lint/typecheck/browser/DB/model checks were run.** API1.14.0/migration0044/backend/paid authority unchanged, synthetic inputs untouched, dev only/owner deploys. See `BLOCK16-INT-1030.md`; D-290 remains open.

## Facts of this tree

Each is re-measured by `tests/contract/api_v1/test_doc_prose_facts.py` against the tree, so a stale one is a red test and not a habit.

- Product `VERSION` is `0.9.0`; this file describes development, not a release.
- The development API contract is `1.16.0`: **250 paths / 277 operations / 674 schemas** (`contracts/api/v1/openapi.json`); the error catalogue has **27** codes; the migration head is **`0048_dispatch_time_binding`** (`db/migrations/versions/`).
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
