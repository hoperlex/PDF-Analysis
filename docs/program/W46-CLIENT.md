# W46-CLIENT — session log

`task_id`: `W46-CLIENT` · wave 46, sub-stage C · lane `gate-w46b` · worktree `/root/w46dash` ·
branch `agent/w46-client`, based on `dbba753`.

Opened before the first measurement, per the brief's discipline clause. Committed after each
step; entries are appended, not rewritten, once the step they describe is done.

Read: `docs/program/dispatch/W46-CLIENT.md`, `docs/program/dispatch/W46-STAGE-C.md`,
`docs/program/reviews/W46-JUDGE-X.md` (`git show agent/w46-judge-x:…`, findings X-3, X-6,
X-9, and the cross-examination of Y), `docs/program/reviews/W46-JUDGE-Y.md`
(`git show agent/w46-judge-y:…`, sections 2, 5, 6). `AGENTS.md` read in full.

## Coordinator narrowing, received mid-task

1. C1, the run-state panel: `by_state` carrying only some states (e.g. `published: 2`)
   currently hides the rest rather than showing a fault (`?? 0` feeds a `> 0` filter); the
   panel invents zeros only when the whole array is empty. And unknown members
   (`escalated`, `ZZ`) vanish silently. Both are faults under the same rule: an omitted or
   unknown member is a visible fault, whatever the shape of the omission. The completeness
   check below covers both facets by construction (closed-set membership, not "any row
   present").
2. C4/Y2-a: the contradiction predates wave 46 — one profile, `DISCIPLINE = "AR"`, nothing
   in runs/analysis reads `.section`. The «правило приёма» sentences came in `9bb9385`
   (09-22). Repair is sentences only, matching this brief: the analysis is built for АР
   and applied to any uploaded document; a stated section is stored and counted, but
   neither selects nor refuses the analysis. No behaviour change. `startRun` refusing by
   section is the owner's call (`D-110`).

## Plan

1. **C1** — `section-breakdown.ts`, `verdict-breakdown.ts` and a new
   `run-state-breakdown.ts` stop filling an omitted member with `0` and stop silently
   dropping an unknown one: each returns `{ ok: false }` over a response that does not
   carry exactly its closed vocabulary, once each, no more no less. The three panels
   render the failure shape `dashboard-failure.ts` already has instead of any number when
   that happens. Driven under three mutations (omitted row, unknown row, and X's partial
   `by_state`), shown failing without the fix and passing with it.
2. **C2** — per-row keyed assertions in `dashboard.test.ts`, reading each row by its own
   `data-section`/`data-verdict`/`data-run-state` attribute rather than `toContain`
   anywhere on the page. Y's M5 (neighbour-shifted section counts) and M6
   (accepted/rejected swapped) shown failing under the new assertions, plus one of my own
   (published/failed swapped in the run-state panel), then reverted.
3. **C3** — `use-create-project.ts` invalidates `queryKeys.dashboard.summary()` on success.
   A new guard enumerates every mutation hook under `web/src/features/**` and asserts
   whether it invalidates the dashboard key, failing on a hook the map does not name and
   on a mapped hook whose invalidation cannot be found. Shown failing with
   `create-project`'s new line removed.
4. **C4** — `sections-panel.tsx`, `project-sections.tsx` (Y2-a): the sentences say the
   analysis is built for the text of АР documents and applied to any uploaded document
   regardless of its stored section, never that intake refuses or restricts by section.
   `verdicts-panel.tsx` (Y2-b): the caption's «ожидает решения» becomes «не решено», the
   row's own label. `run-activity-panel.tsx`, `dashboard.test.ts`,
   `rendered-language.guard.test.ts` (X-9): the four comments saying the generated client
   "still types `spend` required today" are corrected — it is optional now.
5. **C5** — drive `npm --prefix web run e2e:pc01` against API `127.0.0.1:56381` and Next
   `127.0.0.1:56383`, quote the summary.
6. Verification: `npm --prefix web test`, `npm --prefix web run typecheck` during
   development; one final `make gate > /root/w46c-gate.log 2>&1`, verdict from `GATE OK`.

## Log

- **C1.** `section-breakdown.ts`, `verdict-breakdown.ts` (rewritten) and
  `run-state-breakdown.ts` (new) each return `{ ok: false }` over a response that does not
  carry exactly its closed vocabulary — one member missing, one repeated, or one the
  vocabulary does not have. `sections-panel.tsx`, `verdicts-panel.tsx` and
  `run-activity-panel.tsx` render `dashboard-failure.ts`'s new `incompleteBreakdownFailure`
  shape (`ErrorState`, `data-panel-fault="incomplete"`) instead of any number when that
  happens; a partial `by_state` (some states present, the rest silently hidden behind
  `?? 0` / `> 0`) is covered by the same check, per the coordinator's narrowing. Six new
  cases in `dashboard.test.ts` drive this over mutated fixtures (a missing row and an
  unrecognised row, for each of the three panels): `npx vitest run
  tests/unit/widgets/dashboard.test.ts` → 16 passed (was 7).
- **C2.** `dashboard.test.ts` gained `rowNumber`/`sectionMarkup` helpers and a new
  `describe('every row is keyed to its own data attribute…')`, asserting each row's value
  by its own `data-section`/`data-verdict`/`data-run-state`, not by `toContain` anywhere on
  the page. Mutations run by hand, confirmed red, then reverted (`git diff` empty after
  each):
  - **Y's M5** (`sections-panel.tsx`, `summary.byCode[PROJECT_SECTIONS[(i + 1) %
    PROJECT_SECTIONS.length]!.code]` in place of `summary.byCode[section.code]`, with the
    `.map` given an index):
    ```
    × every row is keyed to its own data attribute, not to membership on the page > every section row carries its own section's count, never a neighbour's
      AR: expected 0 to be 3
    ```
  - **Y's M6** (`verdicts-panel.tsx`, `accepted`'s `<td>` reads `byVerdict.rejected` and
    back):
    ```
    × every row is keyed to its own data attribute, not to membership on the page > every verdict row carries its own verdict's count, never a swapped one
      accepted: expected 1 to be 2
    ```
  - **Mine** (`run-activity-panel.tsx`, the `<td>` reads `breakdown.byState[state ===
    'published' ? 'failed' : state === 'failed' ? 'published' : state]`):
    ```
    × every row is keyed to its own data attribute, not to membership on the page > every rendered run-state row carries its own state's count, never a swapped one
      published: expected 1 to be 6
    ```
  All three: `npx vitest run tests/unit/widgets/dashboard.test.ts` still reports the whole
  suite `16` collected with exactly the mutated case red, the rest green — the mutation is
  caught by the new per-row assertion and by nothing else. Reverted with the file's
  unmutated content; `git status --porcelain` empty afterward.
- **C4 (partial), Y2-a/Y2-b/X-9.** `sections-panel.tsx` no longer annotates the АР row as
  *"единственный анализируемый раздел"*; `project-sections.tsx`'s header and its two
  inline sentences (the analysed branch, the placeholder promise) say the analysis is
  built for the text of АР documents and is applied to any uploaded document regardless of
  its stored section, never a rule of intake — matching the coordinator's narrowing that
  this predates wave 46 (`9bb9385`) and is sentence-only, no behaviour change.
  `verdicts-panel.tsx`'s caption now says «не решено», the row's own label, in place of
  «ожидает решения». Four comments claiming the generated client "still types `spend`
  required today" (`run-activity-panel.tsx` ×2, `dashboard.test.ts`, `rendered-language.
  guard.test.ts`) are corrected — `types.gen.ts:484` has been `spend?: RunActivitySpend`
  since the reseal. `tests/unit/screens/project-sections.test.ts` and `tests/unit/projects/
  project-sections.test.ts` updated to pin the corrected sentences (both files' own stale
  claims — "checked nowhere in this system", "no section field to count over" — corrected
  too, same falsehood). `npx vitest run tests/unit/screens/project-sections.test.ts
  tests/unit/projects/project-sections.test.ts tests/unit/widgets/dashboard.test.ts` → 40
  passed. `npm run typecheck` clean throughout.
- **C3.** `use-create-project.ts`'s `onSuccess` now also invalidates
  `queryKeys.dashboard.summary()`, alongside `projects.all()`. New guard
  `tests/guards/dashboard-invalidation.guard.test.ts` discovers every
  `features/*/model/use-*.ts` hook calling `useMutation(`, refuses to run unless that set
  equals its own `EXPECTED_INVALIDATION` map exactly (so an unmapped future hook fails
  loudly), and checks each mapped hook by reading whether its source names
  `queryKeys.dashboard.summary()` directly or delegates to an imported `*CacheKeys` helper
  (`decisionCacheKeys`, followed through the `entities/expert-decision` barrel to its
  `model/cache.ts` definition) that itself does. `query-keys.ts:165`'s comment now names
  `createProject` among the four mutations it already listed.
  `npx vitest run tests/guards/dashboard-invalidation.guard.test.ts` → 7 passed.
  Shown failing with the new invalidation line removed from `use-create-project.ts`, then
  restored:
  ```
  × src/features/create-project/model/use-create-project.ts invalidates the dashboard summary
    → …expected invalidatesDashboard() to be true, got false: expected false to be true
  Tests  1 failed | 6 passed (7)
  ```
  `npm run typecheck` clean; `git diff --stat` after restoring shows only the intended
  addition.
- **C5.** Provisioning: `make up`, `make check-services` (all green, bucket
  `audit-w46b`), `make migrate` (head `0011_document_section`). API:
  `PYTHONPATH=src .venv/bin/python infra/deploy/serve.py`,
  `AUDITMANAGER_API_PORT=56381`, `AUDITMANAGER_HEALTH_PORT=56382`,
  `AUDITMANAGER_BIND_HOST=127.0.0.1`, `AUDITMANAGER_PROVIDER_MODE=recorded`, the lane's own
  `DATABASE_URL`/`S3_*` from `.env`, a freshly generated `AUDITMANAGER_API_TOKEN` —
  `operations=20`, PID `1340297`, confirmed this session's own descendant
  (`readlink /proc/1340297/cwd` → `/root/w46dash`). Next: `npm run build`
  (`NEXT_PUBLIC_API_BASE_URL=/bff/v1`) then `next start -p 56383 -H 127.0.0.1`,
  `AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:56381`, the same token — wrapper PID
  `1357956`, listener `next-server` PID `1357990`, both confirmed as this session's
  descendants (`readlink /proc/<pid>/cwd` → `/root/w46dash/web`).

  `E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password npm --prefix web run e2e:pc01 --
  --origin http://127.0.0.1:56383 --phase all --out /root/w46dash-journey-out`, quoted in
  full:
  ```
  sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser

  write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf

  ok  create-project   api=3 {"project_uid":"prj_01M3MZAYD65YPDHAZ3CBVD7688"}
  ok  upload-document  api=4 {"project_uid":"prj_01M3MZAYD65YPDHAZ3CBVD7688","version_uid":"ver_01M3MZC2B97APAYWDDK0P98TGZ"}
  ok  start-run        api=6 {"project_uid":"prj_01M3MZAYD65YPDHAZ3CBVD7688","run_id":"run_01M3MZD2A0T87KMP4S281CZ213"} terminal=published in 4667ms/150000ms

  ok  root           200  api=1 auth=0 console=0 jar=[am_session] w=765/780
  ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"project_uid":"prj_01M3MZAYD65YPDHAZ3CBVD7688"}
  ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"document_uid":"doc_01M3MZC2B16SF4H9CSQBGXC1S6"}
  ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"version_uid":"ver_01M3MZC2B97APAYWDDK0P98TGZ"}
  ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780 {"run_id":"run_01M3MZD2A0T87KMP4S281CZ213"}
  ok  comparison     200  api=1 auth=0 console=0 jar=[am_session] w=780/780
  ok  run            200  api=1 auth=0 console=0 jar=[am_session] w=765/780
  ok  review         200  api=5 auth=0 console=0 jar=[am_session] w=765/780
  ok  sign-in        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
  ok  knowledge-base 200  api=1 auth=0 console=0 jar=[am_session] w=765/780
  ok  change-password 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
  ok  blocks         200  api=1 auth=0 console=0 jar=[am_session] w=765/780
  ok  optimisation   200  api=0 auth=0 console=0 jar=[am_session] w=780/780
  ok  logs           200  api=0 auth=0 console=0 jar=[am_session] w=780/780
  ok  workers        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
  ok  dashboard      200  api=1 auth=0 console=0 jar=[am_session] w=765/780

  envelope: /root/w46dash-journey-out/journey.json
  write steps checked: 3/3
  routes checked: 16/16
  e2e:pc01 OK
  ```

  Read from the raw exchanges in `journey.json`, not only the summary: `dashboard`'s only
  `/bff/*` call is `GET /bff/v1/dashboard`, `blocks`'s only one is
  `GET /bff/v1/projects?limit=50`; both routes' `undeclaredApi` is `[]`, `consoleErrors` and
  `pageErrors` are `[]`, and the envelope's top-level `failures` is `[]`. The dashboard
  route's rendered text over the lane's own accumulated data (109 projects, 223 findings,
  107 runs) carries «не решено» matching the caption (`Y2-b`), no «единственный
  анализируемый раздел» and no «контракт»/«операци» substring; the `project` route's text
  carries the rewritten Y2-a sentence verbatim: *"Анализ построен для текста раздела АР —
  это единственный профиль анализа, который есть у продукта, и он применяется к любому
  загруженному документу вне зависимости от того, под каким разделом сервер его хранит."*

  API and Next stopped by PID afterward (`1340297`, `1357956`, and the orphaned
  `next-server` worker `1357990` the wrapper's exit left behind, each confirmed mine by
  `readlink /proc/<pid>/cwd` before the kill); `ss -ltnp` empty for `56381`–`56383`
  afterward. No process signalled by pattern.

