# W53C-WEB-OPS-01 — hand-back report

Lane: `agent/w53c-web-ops`, base `04de50c` (`integration/w53-close`). Task file:
`docs/program/tasks/W53C-WEB-OPS-01.md`. Findings C-26…C-30 of
`docs/program/dispatch/W53-CLOSE-PLAN.md` §2.

## Findings: re-verification and outcome

| Finding | Reproduced at base | Change |
|---|---|---|
| C-26 | Yes. `use-execution.ts` set only `refetchOnWindowFocus: 'always'`; the default `staleTime: 30_000` (`_app/query-client.ts:35`) applied. `useStartRun` invalidated only `dashboard.summary()`. | Both execution query options set `staleTime: 0`; `useStartRun` also invalidates `queryKeys.execution.all()`. |
| C-27 | Yes. `queue-page.tsx` rendered the rows only when `account.data !== undefined`. | Rows render whenever the queue read succeeded. Roles default to `[]` until `getMe` answers, so the widget draws no command; on a `getMe` failure the page adds «Очередь показана без команд: права не прочитаны.» (`data-execution-controls-withheld`) above the existing retryable error. |
| C-28 | Yes. The menu offered «История версий» to every session; `listReleases`/`getProductVersion` are `_ANY_COMPLETE_ACCOUNT` in `src/auditmanager/api/security.py:322-323` (read only). | `AccountMenuSession` now carries `isDefaultCredential` and `profileComplete` (the frame already passed the whole `AppFrameSession`); `canReadReleaseHistory(session)` = complete profile and changed credential gates the item and the panel. |
| C-29 | Yes; cited line numbers differ: `getWebBuildId` is at `shared/config/env.ts:65-74`, the throw on an unknown kind at `entities/release/model/presentation.ts:17-22`, and `assertReleaseKinds` in `useReleases`' `queryFn` failed the whole list. | `ReleaseNotices`: one `visibilitychange` listener (`listenForTabReturn`), no `focus` listener; the mount reads only the version (the query already fetches the list), a later route change re-reads both (`readOnRoute`, keeping `W52-PLAN.md` §3.5's route trigger); the sign-in redirect on `authentication_required` now watches `releases.error`. A missing build id is read as `null` (`bundleBuildId`, catching only `MissingConfigurationError`): the banner and `/bff/version` check are disabled and one `console.error` names the variable. Unknown kind: `releaseKindLabel` returns «Другое изменение» (`OTHER_RELEASE_KIND_LABEL`), `UnknownReleaseKindError`/`assertReleaseKinds` removed, the history no longer echoes the raw kind into a class name. `env.ts`, `version-check.ts` unchanged. |
| C-30 | Partly. The count was assigned only after `navigateWithTransientRetry` returned. In `write.mjs` each step uses a fresh `withColdBrowser` page, so a rejection recorded `null` (not literally the previous route's count); a stale count needs a page reused for two navigations. Either way the attempts made were lost. | New exported `navigateCountingAttempts(send, url, record, options)` in `cdp.mjs`: records `null` before the first command, then the number of `Page.navigate` commands sent on success **and** on rejection, and rethrows. `Page.goto` counts through it. `write.mjs` unchanged. |

## 1. Changed files (`git diff --name-only 04de50c..HEAD`)

```
docs/program/W53C-WEB-OPS-01.md
tests/e2e/pc01/journey/cdp.mjs
web/src/_app/account-menu.tsx
web/src/_app/release-notices.tsx
web/src/_pages/queue/ui/queue-page.tsx
web/src/entities/execution/api/use-execution.ts
web/src/entities/release/api/use-releases.ts
web/src/entities/release/index.ts
web/src/entities/release/model/presentation.ts
web/src/features/start-run/model/use-start-run.ts
web/src/widgets/version-history/ui/version-history.tsx
web/tests/guards/rendered-language.guard.test.ts
web/tests/unit/execution/execution-commands.test.ts
web/tests/unit/execution/execution-screens.test.ts
web/tests/unit/journey/cdp-navigation-attempts.test.ts   (new)
web/tests/unit/release/history.test.ts
web/tests/unit/release/notices.test.ts                    (new)
web/tests/unit/shell/frame.test.ts
```

Guard touched: `web/tests/guards/rendered-language.guard.test.ts` — one added matrix state,
`release-history-failed`. Required by C-29: the history's error title used to be a ternary
over `UnknownReleaseKindError`; as a plain literal («История версий недоступна») the guard's
branch census now sees it and demanded a state that renders it. No pinned text was changed.

## 2. Checks (run in the worktree on the final tree)

| Command | Result |
|---|---|
| `git diff --check 04de50c..HEAD` | exit 0 |
| `npm --prefix web run lint` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `cd web && npx vitest run tests/guards tests/unit/execution tests/unit/journey tests/unit/release tests/unit/shell tests/unit/qa_w50/r66-navigation.test.ts tests/unit/ui/menu.test.ts tests/unit/styles tests/unit/screens tests/unit/api/authorization-state.test.ts tests/unit/run tests/unit/projects tests/unit/lib/intent-key.test.ts tests/unit/icon-convention.test.ts tests/contract/csv-columns.contract.test.ts` (touched tests, all guards, and every test file importing a changed module) | 72 files, 1001 passed |
| `node --check tests/e2e/pc01/journey/cdp.mjs` and `… write.mjs` | exit 0 |
| `node --test tests/e2e/pc01/journey/navigation-retry.test.mjs` | 4 passed |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/e2e/test_pc01_journey_conformance.py` | 82 passed |

No Next server, browser, docker or database was started.

### How each new test fails without the fix

- Base production files restored with `git checkout 04de50c -- <the 10 production paths>`,
  tests kept, then `npx vitest run` of the new/changed tests (restored with
  `git checkout HEAD -- …` afterwards):
  - C-26: `execution-commands … C-26: an accepted start …` (invalidation set lacks
    `execution.all()`) and `execution-screens … never stale (C-26)` (`staleTime` undefined) failed.
  - C-27: `execution-screens … renders the rows without any command when getMe fails` failed.
  - C-28: `frame … C-28: offers «История версий» only where …` failed.
  - C-29: `history … C-29: labels an unknown note kind generically …` failed; all six
    `notices.test.ts` cases failed.
  - C-30: all four `cdp-navigation-attempts.test.ts` cases failed.
- Targeted mutations on the fixed tree (each reverted):
  - `const buildId = getWebBuildId();` in `ReleaseNotices` → «disables the banner instead of
    throwing during render» fails with `MissingConfigurationError` thrown during render.
  - an added `window.addEventListener('focus', …)` effect → «is wired with no focus listener…»
    fails.
  - `record(sent)` commented out in `navigateCountingAttempts`' `catch` → the two rejection
    cases fail.

## 3. Contracts

None new or changed. `contracts/**`, the OpenAPI document and the migration head are untouched.
New in-module exports only: `canReadReleaseHistory` (`_app/account-menu`); `bundleBuildId`,
`readOnRoute`, `listenForTabReturn`, `ReleaseNotices`, types `NoticeReads`, `TabDocument`
(`_app/release-notices`); `OTHER_RELEASE_KIND_LABEL`, `isKnownReleaseKind` (`entities/release`,
which no longer exports `UnknownReleaseKindError`); `navigateCountingAttempts` (`cdp.mjs`).

## 4. Risks and known limitations

- C-29 departs from `W52-PLAN.md` §3.5 «an unknown `kind` is a typed fault», as the W53 task
  directs: an unknown kind is now a generic label with no colour.
- The trigger wiring inside `ReleaseNotices` (effects) is verified through the two pure
  functions it calls and a source assertion; no browser test of a real tab return was run.
- Under React StrictMode (development only) the mount effect runs twice, so development reads
  the version twice on mount; production reads it once.
- With a missing build id the `/bff/version` check is skipped entirely (nothing to compare);
  the BFF route itself (`app/bff/version/route.ts`, EDGE lane) still uses the strict reader.
- `web/tests/unit/journey/cdp-navigation-attempts.test.ts` imports `tests/e2e/pc01/journey/cdp.mjs`
  by URL at run time; it is the first web unit test to reach a repository-root module.
- The queue page's own `focus` listener (age refresh) is unrelated to C-29 and unchanged.

## 5. Integrator instructions

Merge `agent/w53c-web-ops` as is. It touches no path of the other W53C lanes (§4 of the plan):
no `web/src/app/bff/**`, identity screens, registry, routes, home, `_app/query-client.ts`,
`globals.css`, `shared/config/index.ts`, lock files, contracts or Python. Possible textual
overlap only if another lane edits `rendered-language.guard.test.ts` near the
`release-history-*` states. After merging all lanes, the planned web lint + typecheck + full
Vitest covers this lane.

## 6. Containment

`git diff --name-only 04de50c..HEAD` is the list in §1: every path is inside the task's
`allowed_paths` (`web/tests/guards/rendered-language.guard.test.ts` per the dispatch rule for
guards that pin a changed file's structure). `git status --porcelain -uall` is empty after the
report commit. No container, volume, port, published ref, tag, worktree or other checkout was
touched; no process was killed.
