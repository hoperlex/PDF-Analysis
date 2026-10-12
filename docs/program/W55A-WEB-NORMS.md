# W55A-WEB-NORMS — hand-back report

- Task: `docs/program/tasks/W55A-WEB-NORMS.md`. Grant: `dispatch/W55-PLAN.md` §A4 Stage B
  item 4, plus this file. Behaviour follows §A3.6 and §A3.7, and rulings R-80, R-112 and R-113.
  Checks follow `R-102`/`R-111` (light and container-free).
- Branch `agent/w55a-web-norms`, worktree `.local/worktrees/w55a-web-norms`. Base `959eb86`,
  which holds the W55a seal merge. The generated client has the seven norms operations as
  `503` stubs.
- Implementation commit `9b6169d`. This report is the next commit.

## 0. What was built

| Plan item (§A3.7) | Where |
|---|---|
| The `R-66` stub graduates. `/norms` reads `listNormSnapshots` and says which snapshot search uses. | `_pages/norms/ui/norms-page.tsx`, `entities/norms/**` |
| Before any snapshot is current, the screen shows the refusal «Текущий снимок норм не назначен» and never an empty list. This happens in two cases. (1) The whole list was read and no snapshot is current: the form is disabled and no search is sent. (2) A search was refused with `required_norm_unavailable` / `reference_kind: norms_snapshot`. | `widgets/norm-search` (`NoCurrentSnapshot`), `entities/norms/model/{presentation,failure}.ts` |
| Search over the current snapshot: a plain `GET` form to `/norms?q=…`, so a search is an address. Each result shows the designation, title, clause (`п. 5.1`), `стр. N` and the fragment. Matched spans are marked with `<mark>`, using code-point offsets. Each result carries its attribution (NORM-Q04). «Открыть» goes to `routes.normDocument(id, page_label)`. A cancelled search says «Запрос слишком широкий»; a refused request says «Запрос не принят». Results page with «В начало»/«Дальше». | `widgets/norm-search/**`, `entities/norms/model/presentation.ts` (`fragmentParts`) |
| Document view: a second registry row `/norms/document`, `session`/`any-role`, not in the menu, group «Знания». It shows the document facts, then the canonical paragraphs in order. Unreliable paragraphs are marked (F-4) with a sentence, a class and `data-norm-reliability`. Each paragraph links its own PDF page. The PDF is read only when a page is asked for, a confirmed binding serves it and the page exists (`wantsNormPdf`). It opens in `<object>` at `#page=N`, the evidence viewer's approach. With no `id`, the view says «Документ не выбран». | `app/norms/document/page.tsx`, `_pages/norms/ui/norm-document-page.tsx`, `widgets/norm-document/**` |
| Administrators get three things. (1) The snapshot list, with counts, index state, `qualified` and the missing qualification half named. (2) «Сделать текущим» on a qualifying, non-current snapshot. It opens a confirmation that names the target and the snapshot it replaces. «Подтвердить» sends one `setCurrentNormSnapshot {norms_snapshot_id, expected_current}` with no idempotency key; «Отмена» sends nothing. A refusal, including `stale_current_snapshot`, closes the intent. Any other failure keeps it, so «Повторить» sends the same compare-and-set. (3) The designation history. | `widgets/norm-snapshots/**`, `features/set-current-snapshot/**` (`retry: false`, invalidates `queryKeys.norms.all()` on settle) |
| Admin controls are hidden from experts. The route passes the session's roles, as the home page does. An expert's page draws no list, control or history, and never builds the history query. | `app/norms/page.tsx`, `norms-page.tsx` |
| Role-less sessions are kept out. Both rows are `any-role` (R-80): `requireScreen` sends a role-less session to `/403` from both addresses before any read. | `shared/config/screen-registry.ts` |
| New query-key root `norms` (`all`, `snapshots`, `events`, `search`, `document`, `paragraphs`, `content`). New route builders `routes.norms()` and `routes.normDocument(id, page?)`. | `shared/api/query-keys.ts`, `shared/lib/routes.ts` |

**Design choice to review: the document view's address.** The identity is a query parameter:
`/norms/document?id=ndoc_…&page=N`, not `/norms/[norm_document_id]`. Only a search hands out
a norm document, and the live journey's cold walk never searches. A dynamic route would need
a captured `norm_document_id`. `journey.mjs` throws on an uncaptured segment.
`tests/e2e/test_pc01_journey_conformance.py` (`placeholder_sample_findings`) allows a
placeholder sample only for `/admin/users/{user_uid}`. Both files are outside this grant. With
a dynamic route, the live journey (`make alpha-acceptance`) could not complete. With the
static address, the journey walks `/norms/document` with no `id`: the screen says no document
was chosen and calls nothing. The manifest declares this. If the integrator prefers a path
segment, the journey needs a search step or a sample allowance first.

## 1. Changed files (`git diff --name-only 959eb86..HEAD`, 41 paths + this report)

```
tests/e2e/pc01/journey/manifest.json
web/docs/PC01_UI_SEAM.md
web/src/_pages/norms/index.ts
web/src/_pages/norms/ui/norm-document-page.tsx          (new)
web/src/_pages/norms/ui/norms-page.tsx
web/src/app/norms/document/page.tsx                     (new)
web/src/app/norms/page.tsx
web/src/entities/norms/api/use-norms.ts                 (new)
web/src/entities/norms/index.ts                         (new)
web/src/entities/norms/model/failure.ts                 (new)
web/src/entities/norms/model/presentation.ts            (new)
web/src/features/set-current-snapshot/index.ts          (new)
web/src/features/set-current-snapshot/model/use-set-current-snapshot.ts (new)
web/src/shared/api/query-keys.ts
web/src/shared/config/screen-registry.ts
web/src/shared/lib/routes.ts
web/src/widgets/norm-document/{index.ts,ui/norm-document.tsx,ui/norm-document.module.css} (new)
web/src/widgets/norm-search/{index.ts,ui/norm-search.tsx,ui/norm-search.module.css}       (new)
web/src/widgets/norm-snapshots/{index.ts,ui/norm-snapshots.tsx,ui/norm-snapshots.module.css} (new)
web/tests/guards/dashboard-invalidation.guard.test.ts
web/tests/guards/prepared-sections.guard.test.ts
web/tests/guards/query-key-shape.guard.test.ts
web/tests/guards/rendered-language.guard.test.ts
web/tests/guards/screen-registry.guard.test.ts
web/tests/unit/api/configuration-and-cache-keys.test.ts
web/tests/unit/norms/{fixtures.ts,presentation.test.ts,norms-screen.test.ts,designation.test.ts,designation-command.test.ts,document-view.test.ts} (new)
web/tests/unit/qa_w50/r66-navigation.test.ts
web/tests/unit/screens/route-screens.ts
web/tests/unit/screens/routes.test.ts
web/tests/unit/styles/screens.ts
```

### Guards and shared tests changed, each because this change required it

- `screen-registry.guard.test.ts`
  - The tree and registry size moves from 27 to 28.
  - New case: `/norms/document` is `knowledge`/`session`/`any-role`/not in the menu, and the
    «Знания» menu is unchanged.
- `prepared-sections.guard.test.ts`: `/norms` graduates out of `SECTIONS`, as `/workers` did.
  The header records it.
- `r66-navigation.test.ts`
  - `/norms` leaves `STUBS`, which now holds two stubs.
  - New case: `/norms` keeps its ruled row and menu place, renders no `RoutePlaceholder`, and
    on a cold route builds only the `snapshots` query.
- `rendered-language.guard.test.ts`
  - Five norms keys are seeded in the loaded and empty clients, and failed via `failedClient`.
  - Eleven new `EXTRA_SHAPES`: three server refusals of a search, the empty first and later
    pages, the PDF panel's four shapes, and the "current beyond the page" list.
  - Two `UNREACHABLE_IN_ONE_PASS` entries: «Снимок не назначен» and «Назначение не выполнено».
    Both appear only after a settled mutation, as with the workers lane.
  - **One entry removed: «В начало».** The norms lists take `onFirst` as a prop, so a static
    pass now renders it, and the ratchet required the deletion.
- `query-key-shape.guard.test.ts`: new block holding every norms key under `['norms']` and
  keeping searches, cursors, documents, paragraphs and bytes apart.
- `configuration-and-cache-keys.test.ts`: the ten roots become eleven with `norms`, plus the
  per-builder roots and distinctness entries.
- `dashboard-invalidation.guard.test.ts`: the new hook is mapped `false`.
- `routes.test.ts` gains three cases and two builder-map entries:
  - `/norms` passes the roles and the trimmed `q`.
  - `/norms/document` passes the `id` and `page`.
  - A malformed `id` or `page` gives a 404 after the guard; role-less sessions are redirected.
  - D-94 builder map: `norms`, `normDocument`.
- `route-screens.ts`
  - Four seeds: an administrator's landing, an expert's search, the document at a page, and no
    document.
  - Shared constants: `NORM_QUERY`, `NORM_DOCUMENT_ID`, `NORM_PAGE`.
- `styles/screens.ts`: four census entries reach the three new modules' colour rules (match
  highlight, unreliable marker, row borders). Contrast passes in both palettes.
- `web/docs/PC01_UI_SEAM.md` §6 gains:
  - the `norms` rows and root;
  - the missing `execution.workers` row, which W54 omitted;
  - the invalidation rule.
- `tests/e2e/pc01/journey/manifest.json`
  - `/norms` expects `listNormSnapshots` and `listNormSnapshotEvents`. The journey signs in as
    an administrator, as `admin-users` already assumes.
  - New row `norm-document` for `/norms/document`, with `expects_api: []` and a reason.
- `web/tests/contract/narrow-sets.contract.test.ts` was not changed. It reads §6 and passes.

## 2. Checks (in the worktree, container-free; no Next server, browser or docker)

| Command | Result |
|---|---|
| `git diff --check` | clean |
| `npm --prefix web run lint` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `cd web && npx vitest run tests/guards tests/unit/screens tests/unit/qa_w50 tests/unit/styles tests/unit/api tests/contract tests/unit/shell` | 60 files, 1028 passed |
| `cd web && npx vitest run tests/unit/norms` | 5 files, 44 passed |
| `cd web && npx vitest run` (whole suite, on committed `9b6169d`) | **131 files, 1938 passed** (base `959eb86`: 126 / 1889) |
| `.venv/bin/python -m pytest -q tests/e2e/test_pc01_journey_conformance.py tests/contract/api_v1/test_surface_counts_in_prose.py` | 115 passed |
| `.venv/bin/python -m pytest -q tests/contract --ignore=…cp00_candidate --ignore=…cp00_final_state --ignore=…validate_bootstrap` (SEAL's container-free set) | 620 passed, 50 subtests |

**Shown able to fail.** Method: apply each mutation to the source, run the named tests, then
restore the file from a scratch copy. `git status` was clean of mutations afterwards.

| Mutation | Red |
|---|---|
| `currentSnapshotOf` never answers `none` | 4 (refusal ×2, a press with none current, the reading) |
| Administrator = any role | 5 (expert sees controls, events query built, …) |
| Hook invalidates `onSuccess` instead of `onSettled` | 1 |
| `wantsNormPdf` ignores binding and page count | 3 |
| `isUnreliable` → `false` | 1 (F-4 marking) |
| `/norms/document` row `any` instead of `any-role` | 2 (role-less `/403`, registry case) |
| English title on «Ничего не найдено» | 3 (language guard) |
| English unreliable marker | 2 (language guard) |
| Search sent when no snapshot is current | 1 |
| `expected_current` always `null` | 1 |
| Highlights not marked | 1 |
| Malformed `id` no longer a 404 | 1 |
| «Открыть» without the page | 1 |
| Registry address renamed | 2 |

## 3. Contracts

No API, domain, event, error-catalog or migration contract changed, and the generated client
was not touched. The web-internal surface:

- `QUERY_NAMESPACES` gains `norms`, together with `queryKeys.norms.*`.
- `routes.norms()` and `routes.normDocument(id, page?)`.
- One registry row, `/norms/document` («Нормативный документ»).
- `@/entities/norms`:
  - the hooks and query options for the six reads;
  - `normFailure`, `NO_CURRENT_SNAPSHOT_DETAIL`;
  - `currentSnapshotOf`, `fragmentParts`, `wantsNormPdf`, `looksLikeNormDocumentId`,
    `pageFromAddress`;
  - labels: `attributionLabel`, `buildStateLabel`, `clauseLabel`, `isUnreliable`;
  - limits: snapshots 200 (the contract maximum), events 50, search 20, paragraphs 200.
- `@/features/set-current-snapshot`: `useSetCurrentSnapshot`.
- Widgets: `NoCurrentSnapshot`, `NormSearchForm`, `NormSearchResults`, `NormDocumentFacts`,
  `NormParagraphList`, `NormPdf`, `NormSnapshotList`, `NormSnapshotHistory`.
- `@/_pages/norms`:
  - `NormsPage {roles, query?}` and `NormDocumentPage {normDocumentId, page}`;
  - module exports `noDesignationIntent` and `designationIntentLabel`, for tests.

## 4. Risks and known limitations

1. **Until `W55A-SEARCH-01` merges, every norms operation answers the sealed `503`.**
   - `/norms` shows «Снимки норм не прочитаны» with the correlation id.
   - The live journey's `/norms` route is red, because a `503` is ≥ 400.
   - After SEARCH, with no designation, both reads answer `200 []`. The refusal renders and
     the route is green.
2. **The journey account must hold `admin`** for `listNormSnapshotEvents` to be called. If the
   window's journey account is an expert, move that operation to `optional_api`.
3. **The document view's address is a query parameter** (§0). The journey covers the address
   and its no-document state, not the document reads. Those reads are held by
   `web/tests/unit/norms` and the window's manual check.
4. **The designation confirmation says new runs and re-audits record the snapshot.** That is
   true once `W55A-PIN-01` merges. Before PIN, runs still pin `NULL`.
5. **The snapshot list is one page of 200.**
   - If the current snapshot is not on it and more pages exist, the screen says so.
   - In that case it offers no «Сделать текущим», because it cannot state `expected_current`.
6. **The PDF is fetched whole into an object URL**, as the evidence viewer does (§A3.5: "the
   viewer keeps `<object>#page=N`"). CONTENT's ranged BFF path is not used by this viewer.
7. **Search paging is first page and next page only**, as on the other lists.
   - The cursor is bound to the query and the snapshot.
   - If a designation lands between pages, the cursor is refused and the screen shows
     «Запрос не принят».
8. **Invalid highlight spans are left unmarked.** A span out of range, empty or overlapping
   loses its emphasis, never its text.
9. **Mutation outcomes are verified without a browser.** Pressing, confirming and
   cancelling were checked through the element tree and a recording `fetch`. The settled
   refusal and failure panels can only be reached by a browser (`UNREACHABLE_IN_ONE_PASS`).

## 5. Integrator instructions

1. Merge `agent/w55a-web-norms` after reading the diff and this report.
   - No path overlaps CONTENT, SEARCH or PIN.
   - Likely textual neighbours only in `rendered-language.guard.test.ts` and
     `tests/unit/styles/screens.ts`, if another web lane seeds there.
2. Post-merge light acceptance:
   - `npm --prefix web run lint`
   - `npm --prefix web run typecheck`
   - `cd web && npx vitest run`
   - `.venv/bin/python -m pytest -q tests/e2e/test_pc01_journey_conformance.py`
3. **Window step** (after SEARCH is merged, on a lane stack):
   - Run `npm --prefix web run e2e:pc01 -- --phase all`.
   - Expect `/norms` cold to call exactly `listNormSnapshots` and `listNormSnapshotEvents`,
     plus the optional `listReleases`.
   - Expect `/norms/document` to call nothing.
4. **By hand, in the window**, once a qualifying snapshot exists:
   - an administrator's «Сделать текущим» → «Подтвердить» flips «Текущий снимок» and adds a
     history row;
   - a second, stale confirmation shows «Снимок не назначен» with the stale sentence;
   - `/norms?q=СП 54` lists results, and «Открыть» shows the PDF at the result's page;
   - unreliable paragraphs are marked;
   - an expert sees no list or control;
   - a role-less account gets `/403`.

## 6. Containment

- `git diff --name-only 959eb86..HEAD` is the list in §1. Every path is inside §A4 Stage B
  item 4:
  - `app/norms/**`, `_pages/norms/**`;
  - the three widgets, the feature and the entity;
  - `screen-registry.ts` with its guard;
  - `routes.ts` with `routes.test.ts` and `route-screens.ts`;
  - the R-66 test;
  - `query-keys.ts` with the key-shape guard and `configuration-and-cache-keys.test.ts`;
  - seam §6;
  - the three guards named in the grant, `styles/screens.ts`, the journey manifest
    (entries), and `web/tests/unit/norms/**`;
  - this report.
- Not touched:
  - backend, BFF (`web/src/app/bff/**`), `credentialed-forward.ts`, and any other
    `web/tests/unit/api/**` file;
  - `contracts/**`, migrations, the generated client, lock files, `globals.css`;
  - `shared/{api,config,lib,ui}/index.ts`;
  - `features/open-evidence` (imported, unchanged);
  - `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`;
  - other worktrees, refs, tags, the stand.
- No container, server or browser was started. No push, merge, tag or stash. No process was
  killed. `git status --porcelain -uall` is empty after this commit.
