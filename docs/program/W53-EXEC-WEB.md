# W53-EXEC-WEB handback — execution journal and queue

Branch: `agent/w53-exec-web`. Exact dispatch base: `a72b7e9e588e4c19bf156f1090402a3af889173e`. The task-file's stale `e210c67` base line was corrected by the integrator on its branch; this lane remained at the assigned base. Narrow repair grant: `8282d9fde9b7b3ea090f398cfdfaeba35e445bd7`, allowing only the now obsolete `/queue` placeholder assertions in `web/tests/unit/qa_w50/r66-navigation.test.ts` to be updated. HEAD is the handback commit containing this report; the integrator reads it back after commit.

## 1. Changed files

The exact base-to-HEAD path list is below. `/logs` now reads the bounded server journal with a run filter and cursor pages. `/queue` reads durable Jobs, shows priority and age, and offers role-aware cancel, re-audit, priority and pause controls. A command is confirmed with the target Run named, mints one key per intent and retains that key for an explicit repeat after an unknown outcome. On success the affected execution, run and dashboard cache prefixes are invalidated. Reads refresh on focus and by «Обновить», without a timer. The run page links to its journal. Workers copy now acknowledges Jobs and Attempts while keeping the distributed-worker placeholder.

## 2. Checks and results

- Frozen contract hashes: OpenAPI `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; domain state machines `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`. Surface remains 36 paths / 43 operations / 91 schemas, domain revision 9 / 29 identities, 23 error codes, migration head `0017_execution_queue`, version `1.0.0-draft.1`.
- `npm --prefix web run lint` — pass; `npm --prefix web run typecheck` — pass; `npm --prefix web run api:verify` — pass, 43 operations and exact OpenAPI digest.
- `npm --prefix web test -- --maxWorkers=1` — **116 files, 1,750 tests passed** after the exact W50 repair and CSS token correction. Complete log `/tmp/w53-exec-web-npm-test-repeat.log`, SHA-256 `ab916bcbf4ba5906b9fd375ef57be761c817636d7fb9f63174be9c9b2cb46865`.
- The first full run had 1,750 passed and 3 failed: two W50 tests still asserted that `/queue` was a no-API placeholder, and the style guard found a literal colour in a new CSS module. Both causes were corrected and their narrow tests passed before the one full repeat. First log `/tmp/w53-exec-web-npm-test.log`, SHA-256 `f3b7bda32eac90d845e74435c7e3061e71e3dd088ea4f21524c1d8ff013fe1d8`.
- Focused execution tests: 13 passed, covering all four role combinations, typed 403/409/503/transport states, known plus arbitrary legacy journal events, safe field rendering, identical key reuse on explicit command repeat, cache invalidation, cursor separation, focus refresh and long opaque identities with the 780 px overflow policy. `rendered-language.guard.test.ts` 24 passed; W50 R-66 plus style 35 passed.
- `/root/projects/PDF-Analysis/.venv/bin/pytest -q tests/e2e/test_pc01_journey_conformance.py` — 82 passed; `git diff --check` — pass.
- Disk preflight before the full repeat, 2026-10-09 13:08:30 UTC: worktree and Docker data root on the same filesystem, 12,297,789,440 bytes available; memory 5,971,267,584 bytes available; the two current `vmstat` samples had zero swap-out. Record `/tmp/w53-exec-web-preflight-2.log`, SHA-256 `d56bab838b62170da6dbc5614f1d24e9346482eec072a0ceb26a080f49f1f271`. The ~12.3 GB margin covered this bounded one-worker frontend battery; no image build or full gate was launched.

## 3. Contracts

No API, domain, generated client, error catalog or migration contract changed. The web query-key seam adds only the `execution` namespace for queue and journal pages; `web/docs/PC01_UI_SEAM.md` §6 and its guards agree. The `/logs` and `/queue` screen registry entries already had the required session access and labels, so they were reviewed without a redundant edit. The prepared-section and journey enumerators now declare the two real reads. Unknown legacy `event_type` is shown as «Другое событие выполнения» without displaying raw event type or payload. Only safe, closed state and error-code values may be rendered from payload.

## 4. Risks and known limitations

- STOP-01 remains: any HTTP 503 has an unknown command outcome from this client's perspective; this UI never promises automatic own-proxy retry. A user may explicitly repeat the same intent with the same key after checking state.
- STOP-02 remains: `validating` cancellation may return `state_transition_not_allowed`; the UI shows a typed refusal and does not change the displayed state optimistically.
- The 780 px assertion is a static CSS/markup check of wrapping and max width over long opaque IDs. No browser viewport or live stand was driven by this lane. The sealed queue DTO has no Run display-name field, so the screen displays the opaque Run ID without inventing a label.
- The journal deliberately omits raw payload fields, provider text, paths, keys and secrets. An arbitrary older event receives a generic safe label.
- Full `make gate`, independent QA and release checks belong to the integrator on the final clean SHA. No lane services or reserved ports were used, and the working stand was not touched.

## 5. Instructions for the integrator

Integrate this commit after EXEC on the exact W53 line, carrying the already committed narrow W50 repair grant. Read back the changed-path list against base `a72b7e9e588e4c19bf156f1090402a3af889173e`; then independently review role refusals, action confirmation, cursor behavior and the journal allowlist. Keep 503 and `validating` cancellation stop records open. Do not treat the frontend battery as a full gate or release verdict. The temporary local `web/node_modules` symlink used for tests was removed before commit.

## 6. Allowed-path and forbidden-hotspot proof

The staged audit before the report showed 38 paths, all within W53-EXEC-WEB allowed paths except the one historical W50 test explicitly added by repair grant `8282d9f`. The final base-to-HEAD audit adds this report as path 39. No `contracts/**`, migration, generated client, root or web dependency/lock file, composition root, global style, MinIO, backup, `VERSION`, release note, ref, tag or working-stand path was changed. The changed W50 test only removes `/queue` from the old stub set; its menu, registry, session, guest and three other stub checks remain.

### Exact changed paths

- `docs/program/W53-EXEC-WEB.md`
- `tests/e2e/pc01/journey/manifest.json`
- `web/docs/PC01_UI_SEAM.md`
- `web/src/_pages/logs/ui/logs-page.tsx`
- `web/src/_pages/queue/ui/queue-page.tsx`
- `web/src/_pages/run/ui/run-page.tsx`
- `web/src/_pages/workers/ui/workers-page.tsx`
- `web/src/app/logs/page.tsx`
- `web/src/app/queue/page.tsx`
- `web/src/entities/execution/api/use-execution.ts`
- `web/src/entities/execution/index.ts`
- `web/src/entities/execution/model/failure.ts`
- `web/src/entities/execution/model/presentation.ts`
- `web/src/features/cancel-run/index.ts`
- `web/src/features/cancel-run/model/use-cancel-run.ts`
- `web/src/features/pause-execution/index.ts`
- `web/src/features/pause-execution/model/use-pause-execution.ts`
- `web/src/features/reaudit-run/index.ts`
- `web/src/features/reaudit-run/model/use-reaudit-run.ts`
- `web/src/features/set-job-priority/index.ts`
- `web/src/features/set-job-priority/model/use-set-job-priority.ts`
- `web/src/shared/api/query-keys.ts`
- `web/src/shared/lib/routes.ts`
- `web/src/widgets/execution-journal/index.ts`
- `web/src/widgets/execution-journal/ui/execution-journal.module.css`
- `web/src/widgets/execution-journal/ui/execution-journal.tsx`
- `web/src/widgets/execution-queue/index.ts`
- `web/src/widgets/execution-queue/ui/execution-queue.module.css`
- `web/src/widgets/execution-queue/ui/execution-queue.tsx`
- `web/tests/guards/dashboard-invalidation.guard.test.ts`
- `web/tests/guards/prepared-sections.guard.test.ts`
- `web/tests/guards/query-key-shape.guard.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/api/configuration-and-cache-keys.test.ts`
- `web/tests/unit/execution/execution-commands.test.ts`
- `web/tests/unit/execution/execution-screens.test.ts`
- `web/tests/unit/qa_w50/r66-navigation.test.ts`
- `web/tests/unit/screens/routes.test.ts`
- `web/tests/unit/styles/screens.ts`
