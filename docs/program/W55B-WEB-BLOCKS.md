# W55B-WEB-BLOCKS — report (the «Блоки» screen shows a portal bundle; the budget refusal shows its figures)

Lane `W55B-WEB-BLOCKS` (plan `docs/program/dispatch/W55-PLAN.md` §B3.9, grant §B4 item 5), branch `agent/w55b`, base `f94283d2`
(the GEOMETRY report). Light acceptance and the live journey (`R-102`); no full gate. The design decisions, each with the
alternative it rejected, are in the appendix.

**What a reader now sees.** On «Блоки», once a version is chosen, two tabs: «Блоки портала» (new, the one the screen opens on)
and «Строки текста» (the text-line index the screen showed before). The portal tab groups the version's portal blocks under
«Страница N» in the API's order; each block shows its type (Текст / Изображение / Штамп), the portal's status in Russian, the
portal's ordinal, the number of polygon vertices when there is a polygon, and on a page whose box disagreed with the PDF the
sentence «страница не совпала с PDF — фрагмент не вырезан». A TEXT block shows the portal's recognised text as plain
preformatted text under «распознано», with each quality flag as a Russian chip and a plain sentence; an IMAGE block shows the
crop this product cut (`<img>`, lazy, sized by the response) and the portal's description under «описание портала — в анализе
не используется». Before a bundle's first run the tab says «Блоки портала появятся после первого запуска анализа этой
версии.»; a version published as a bare PDF says «У этой версии нет комплекта портала.»; a produced empty list says «В комплекте
портала нет ни одного блока.». Blocks load 100 at a time, the next page on «Показать ещё». Starting a run, or re-auditing one,
for a version over the analysis input budget now prints the refusal's two figures, e.g. «Символов в тексте версии: 175 671;
допустимо не более: 152 361.», with no retry.

## 1. Changed files

`git diff --name-only f94283d2..HEAD`, 34 paths (2 783 insertions, 128 deletions):

- **The screen:** `web/src/_pages/blocks/index.ts`, `model/tabs.ts` (new), `ui/blocks-page.tsx`, `ui/blocks-tabs.tsx` (new),
  `ui/blocks-page.module.css` (new), `ui/text-lines.tsx` (new: the text-line view moved out of `blocks-page.tsx`).
- **The entity** `web/src/entities/block/` (new): `index.ts`, `api/use-portal-blocks.ts`, `api/crop-url.ts`, `model/vocabulary.ts`,
  `model/pages.ts`, `model/bundle.ts`.
- **The widget** `web/src/widgets/portal-blocks/` (new): `index.ts`, `ui/portal-blocks.tsx`, `ui/portal-block-card.tsx`,
  `ui/portal-blocks.module.css`.
- **The budget refusal:** `web/src/entities/audit-run/index.ts`, `model/input-budget.ts` (new), `model/run-failure.ts`;
  `web/src/entities/execution/model/failure.ts`. (`web/src/features/start-run/**` needed no edit: appendix, decision 3.)
- **The key and its seam:** `web/src/shared/api/query-keys.ts`, `web/docs/PC01_UI_SEAM.md` (§6 only).
- **Guards and instruments:** `web/tests/guards/rendered-language.guard.test.ts`, `web/tests/guards/query-key-shape.guard.test.ts`,
  `web/tests/unit/api/configuration-and-cache-keys.test.ts`, `web/tests/unit/styles/screens.ts`.
- **Tests (new):** `web/tests/unit/blocks/{fixtures.ts,portal-blocks.test.ts,portal-states.test.ts,portal-paging.test.ts,blocks-tabs.test.ts}`,
  `web/tests/unit/run/input-budget.test.ts`.
- **The journey:** `tests/e2e/pc01/journey/manifest.json` (the `/blocks` entry only).
- **This report:** `docs/program/W55B-WEB-BLOCKS.md`.

## 2. Checks, with exact commands and results

On the code tree of `5968ca85` (the commits after it change this file only), the tree clean when each ran, one invocation at a
time, exit codes read directly (`cmd > log 2>&1; rc=$?`). Host: 8 to 9 GiB available, 17 GiB disk free, load under 1.

| Command | Exit | Result |
| --- | --- | --- |
| `git diff --check f94283d2..HEAD` | 0 | clean |
| `npm --prefix web run lint` | 0 | |
| `npm --prefix web run typecheck` | 0 | |
| `cd web && npx vitest run --exclude tests/guards/query-key-shape.guard.test.ts` | 0 | 135 files, 2 013 tests passed |
| `cd web && npx vitest run tests/guards/query-key-shape.guard.test.ts` | 0 | 16 passed |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | 0 | 752 passed, 18 927 subtests |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/e2e/test_pc01_journey_conformance.py` | 0 | 87 passed |
| `set -a; . ./.env; set +a; .venv/bin/python -m pytest -q -p no:cacheprovider tests/e2e` (lane stack up) | 0 | 163 passed, 5 skipped (the opt-in live-model tests) |
| `.venv/bin/python tests/e2e/pc01/journey/prove_the_guard_can_fail.py` | 0 | 39 mutations of the real `manifest.json`, 39 reds; the manifest restored, 87 passed |
| the mutation proofs (2.1) | — | 33 mutations, 33 red, 33 restored byte for byte |
| the live journey and the refusals (2.2) | 0, 0 | `write steps checked: 3/3`, `routes checked: 28/28`, `e2e:pc01 OK`; `6 fixture(s) driven, 0 finding(s)` |
| the browser drive of «Блоки» and both refusals (2.3) | 0, 0, 0 | 0 findings in each phase |

Before this lane Vitest counted 130 files / 1 963 tests and the key guard 14 (`W55B-INGEST-01` §2.6); the 50 + 2 new tests are
this lane's. The first full Vitest run went red once, in `presentation-language.guard.test.ts`: the crop builder's refusal was an
English sentence; it is Russian now (`9d70ddf4`).

### 2.1 Mutation proofs

Method: a scratch driver (session scratchpad, not committed) applied one textual replacement to the committed file (asserting
the old text occurs exactly once), ran the named test files with `npx vitest run --bail=1`, restored the original bytes and
compared SHA-256 before and after: **restored in every row**. Run on the final code tree `5968ca85` (and once before, on
`290da698`, with the same 33 reds).

| Mutation (file) | First failing test (`web/tests/…`) |
| --- | --- |
| «распознано» marker removed (`portal-block-card.tsx`) | `unit/blocks/portal-blocks` > marks the text «распознано» and keeps the machine value in data-quote-source |
| recognised text through `dangerouslySetInnerHTML` | > renders a recognised text carrying markup as literal characters |
| description through `dangerouslySetInnerHTML` | > renders a portal description carrying markup as literal characters |
| the `homoglyph` entry missing from the flag map (`vocabulary.ts`) | > shows each flag the backend emits as a Russian chip with a sentence, never the token |
| an unknown flag printed as its token | > names a flag it does not know neutrally and does not print the token |
| an unknown portal status printed as its token | > names the two statuses the portal sends, and an unknown one neutrally |
| description marker removed | > marks the portal description with the words the plan fixes |
| mismatch sentence removed (`geometryLabel` bypassed) | > says the crop is not cut on a mismatch page, visibly, and asks for no image |
| `loading="lazy"` removed | > points an <img> at the crop address with its own size, lazily, with a Russian alt |
| `width`/`height` removed | (same test) |
| the failed-crop fallback never chosen | > stands a sentence in for an image that failed to load, never a broken icon |
| paging keeps only the last page (`pages.ts`) | `unit/blocks/portal-paging` > loads every block exactly once, in order, across three pages |
| paging ignores the cursor (repeats page one) (`use-portal-blocks.ts`) | (same test) |
| paging never continues (`nextPortalCursor` → `undefined`) | (same test) |
| «Показать ещё» shown without a next page (`portal-blocks.tsx`) | `unit/blocks/portal-blocks` > offers no «Показать ещё» once the API reports no next page |
| loaded count printed instead of the version's `block_count` | > prints the version block count the API reports beside the count loaded |
| a bare-PDF version promised blocks after a run | `unit/blocks/portal-states` > says a version without a bundle has none, rather than promising them after a run |
| `items.length` read instead of `status` | > says a produced block list is empty, in different words from both absences |
| `aria-selected` inverted (`blocks-tabs.tsx`) | `unit/blocks/blocks-tabs` > marks «Блоки портала» as the open tab, and only it |
| ArrowRight does not wrap (`tabs.ts`) | > wraps on the arrows, jumps on Home and End, and ignores every other key |
| the closed panel's content mounted | > mounts only the open tab's content |
| the figures not rendered on start (`run-failure.ts`) | `unit/run/input-budget` > names the refusal and prints both figures after the catalog sentence |
| a retry shown on the budget refusal (`error` + `retryable: true`) | (same test) |
| re-audit not covered (`entities/execution/model/failure.ts`) | > is a refusal, not an unknown outcome: the queue offers no repeat for it |
| a non-integer figure accepted (`input-budget.ts`) | > invents nothing when a figure is missing, not an integer, negative or not a number |
| digits grouped with a plain space | > groups every three digits from the right and leaves short numbers alone |
| key segment `portal-blocks` → `blocks` (`query-keys.ts`) | `guards/query-key-shape` > files the portal blocks under the root a version invalidation reaches |
| key root `versions` → `blocks` | `unit/api/configuration-and-cache-keys` > puts each builder under the root it belongs to |
| crop address not encoded (`crop-url.ts`) | `unit/blocks/portal-paging` > is the contract path under the configured base, each identifier encoded |
| text-line unit back to `pt` (`text-lines.tsx`) | `guards/rendered-language` > finds no English on a rendered screen that D-53 has not already recorded |
| `PortalBlockType` dropped from `TRANSLATED_SCHEMAS` | > now reddens the contract words the owner ruled translated |
| «Штамп» → `Stamp` | > finds no English on a rendered screen that D-53 has not already recorded |
| `data-portal-geometry` renamed | > renders every attribute it claims to read, so a renamed one is red and not merely empty |

The census (`unit/styles/contrast.test.ts`) and the language guard's branch coverage were also seen red on the real tree before
their entries existed: 17 module rules «reached by no screen» and 6 widget branches «rendered by no state», then, once the
loaded text-line index was rendered, two English offences on it (decision 10).

### 2.2 The live journey

Lane stack `auditmanager-w55b-webblocks` (PostgreSQL 57470, S3 61070/61071, `make up`, `make migrate` to `0021_portal_bundles`,
`make check-db` OK). API `PYTHONPATH=src .venv/bin/python infra/deploy/serve.py` with the lane's `.env`,
`AUDITMANAGER_API_PORT=57570`, `AUDITMANAGER_HEALTH_PORT=57571`, `AUDITMANAGER_BIND_HOST=127.0.0.1`,
`AUDITMANAGER_PROVIDER_MODE=recorded` and a generated `AUDITMANAGER_API_TOKEN` (scratchpad only); startup line `provider_mode=recorded,
operations=54`. Web `NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=w55b-webblocks npm --prefix web run build`, then
`npx next start -p 31670 -H 127.0.0.1` with `AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:57570` and the same token. The account was
provisioned through the API (`POST /auth/token` as the seeded `admin`, `POST /auth/password`, `PATCH /me` with names and an
e-mail that became the login); `E2E_PC01_LOGIN`, `E2E_PC01_PASSWORD`, `E2E_PC01_CHROME` (Chrome for Testing 154) at run time.
Every process was ours by PID (its `/proc/<pid>/cwd` read before each stop).

| Run | Command | Exit | Result |
| --- | --- | --- | --- |
| on the build of `290da698` | `npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31670 --phase all --out <scratch>/journey-out` | 0 | 3/3 write steps (the run `published` in 1 507 ms), 28/28 routes, `e2e:pc01 OK` |
| same | `node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31670 --out <scratch>/refusals-out` | 0 | `6 fixture(s) driven, 0 finding(s)` |
| on the build of `5968ca85` (final) | the same two commands into `journey-out2`, `refusals-out2` | 0, 0 | 3/3, 28/28, `e2e:pc01 OK`; 6 fixtures, 0 findings |

`blocks` walked `200 api=2 auth=0 w=780/780` (the cold load still makes `listProjects`, plus the optional `listReleases`). Every
route logs one console line, `NEXT_PUBLIC_WEB_BUILD_ID is missing from this build`, as in `W55B-INGEST-01` §2.7: the lane's build
does not set it.

### 2.3 The browser drive of «Блоки» and of both refusals (synthetic data only)

A scratch script (`blocks-drive.mjs`, session scratchpad, not committed) reusing `tests/e2e/pc01/journey/{cdp,session}.mjs`. Seed
through the API: one project; five uploads — `fixtures/synthetic/ar/bundles/ar_baseline.zip` (8 TEXT, 2 IMAGE of which one with a
polygon, 2 STAMP), `ar_baseline_ocr_defects.zip`, `ar_baseline_minimal.zip`, and two text-rich bundles built in the scratchpad by
the repository's own writers (`tools/fixtures/portal_bundle`: `simple_text_pdf`, `make_files`, `build_bundle`; 50 and 72 pages of a
synthetic sentence); runs of the first two (`published`) and of the 50-page one (`failed` in recorded mode — a run exists, which
is what the re-audit needs). Then in cold browsers, at 1280 × 900 and at 390 × 844:

- `/blocks` → the project → `ar_baseline.pdf`: the tabs open on «Блоки портала» (`aria-selected` true/false); 12 blocks under 8
  page sections; «распознано» on every recognised text (8/8); the description marker's exact wording; `block_count` 12 shown as
  reported; **both IMAGE `<img>` `complete` with `naturalWidth` 1886** (after scrolling each into view, they are lazy), `loading=lazy`,
  `width`/`height` from the response, shown at 1100 px on the desktop and scaled down on the phone; no horizontal page scroll at
  either width; «Строки текста» by click shows the text-line index (now with Russian coordinates) and unmounts the portal panel;
  ArrowLeft on the focused tab selects and focuses «Блоки портала».
- `ar_baseline_ocr_defects.pdf`: 5 flag chips (`mixed_script`, `homoglyph`, `cjk`, `doubled_list_marker`), each Russian, none
  printing its token; at the phone width the chips wrap and the two tabs share one row.
- `ar_baseline_minimal.pdf` (no run): «Блоки портала появятся после первого запуска анализа этой версии.»
- **Start refusal:** the 72-page version's own screen, «Запустить прогон» → the warning state with «Символов в тексте версии:
  175 671; допустимо не более: 152 361.» (the API's `details`: `character_count` 175671, `budget_characters` 152361), the
  correlation id, «Прогон не запущен.», and no button in the state.
- **Re-audit refusal:** the API restarted with `AUDITMANAGER_RUN_COST_CEILING_USD=0.80` (budget 96 361; 0.79 is refused at start-up,
  its budget 93 561 is under the AR set's 93 690 characters), then `/queue` → «Повторный аудит» on the 50-page run → «Подтвердить»
  → «Команда не выполнена» with «Символов в тексте версии: 121 991; допустимо не более: 96 361.», and the confirm button disabled
  (no repeat offered).

Screenshots (scratchpad only, never committed): the portal tab full page at both widths in the light and the dark palette, the
text-line tab, the flags at both widths, the not-produced state, both refusals. **Looked at, and fixed what they showed**
(`5968ca85`): on the phone the two tabs wrapped one under the other (now they share the row below 520 px); a long flag name in the
global badge could not wrap (now its own wrapping chip); the description marker became a lozenge when it wrapped (now a small
radius); the synthetic bundle numbers ordinals across the whole document, so «порядок на странице» was untrue for it (now
«порядок у портала»). The drive was rerun on the rebuilt web: 0 findings.

## 3. Contracts

- **Unchanged:** `contracts/**`, the OpenAPI document and the generated client (`web/src/shared/api/generated/**`, `web/openapi/**`;
  47 paths / 54 operations / 123 schemas), the error catalog (24 codes), the migration head `0021_portal_bundles`,
  `web/package.json`, `web/package-lock.json`, `web/FRONTEND_LOCK.json`, `globals.css` and its tokens.
- **Operations read:** `listVersionPortalBlocks` (generated client; `limit` 100, `cursor` from the last page) and
  `streamVersionPortalBlockCrop` (an `<img>` address built from the generated operation table's path template and the configured
  base, decision 5); `getVersionBlocks`, `listProjects`, `listDocuments` as before; `startRun`, `reauditRun` unchanged.
- **New query key:** `queryKeys.versions.portalBlocks(versionUid, limit)` → `['versions', 'portal-blocks', uid, { limit }]`, one
  infinite query; no new root namespace (still eleven). `PC01_UI_SEAM.md` §6 gains its row and the missing `versions.blocks` row.
- **New public API:** `@/entities/block` (`usePortalBlocks`, `portalBlocksQueryOptions`, `PORTAL_BLOCK_PAGE_LIMIT`,
  `portalBlockCropUrl`, `loadedPortalBlocks`, `sectionsByPage`, `nextPortalCursor`, `versionHasPortalBundle`, the vocabulary);
  `@/widgets/portal-blocks` (`PortalBlocks`, `PortalBlockListView`, `PortalBlockCard`, `CropFigureView`); `@/_pages/blocks` adds
  `VersionBlockViews`, `BLOCK_TABS`, `BLOCK_TAB_LABELS`, `DEFAULT_BLOCK_TAB`, `tabAfterKey`; `@/entities/audit-run` adds
  `inputBudgetFigures`, `inputBudgetSentence`, `groupDigits`, `DIGIT_GROUP_SEPARATOR`; `RunFailureKind` gains `input_budget_exceeded`.
- **Machine values on the screen live in `data-` attributes:** `data-portal-block-type`, `data-portal-geometry`,
  `data-portal-status`, `data-quote-source`, `data-recognised-flag`, `data-portal-crop`, `data-portal-page`,
  `data-portal-blocks-loaded`, `data-portal-block-count`, `data-block-tab`, `data-block-panel`, `data-bbox-unit`, `data-bbox-origin`;
  the start refusal keeps `data-run-failure="input_budget_exceeded"`.
- **Guard entries** (`rendered-language.guard.test.ts`): `PortalBlockType` and `PortalGeometryState` in `TRANSLATED_SCHEMAS` with
  markers `data-portal-block-type` / `data-portal-geometry` (every member of both on a rendered screen); the `text_analysis`
  expectation **restored** to `['text', 'analysis']`, plus `text`, `image`, `stamp`, `ok` and `geometry_mismatch` asserted as
  offences; one machine shape, the contract's `BlockGeometry.block_id` pattern `^b_[0-9]{6}$`, with a control; `BLOCKS_SHAPES`
  (both tabs over every answer, the loaded portal list, the failed crop); four `BlockMarkup` entries removed from
  `UNREACHABLE_IN_ONE_PASS` because the ratchet said a state now renders them. `prepared-sections.guard.test.ts`: no entry
  (`blocks` graduated from it in `W45-BLOCKS`). Query-key guard: one `describe` for the new key. Census: the tabs and every kind
  of portal block in both palettes, and the failed crop.
- **The journey manifest's `/blocks` entry:** `expects_api` unchanged (`listProjects`); `optional_api` gains `listDocuments`,
  `listVersionPortalBlocks`, `streamVersionPortalBlockCrop`, `getVersionBlocks`, each with the choice that makes it, so the
  contract check now covers them; the not-produced sentence is in the entry's `$comment`, which says plainly that nothing in the
  file checks it (decision 2). `test_control_a_reworded_panel_is_detected` needed no change.

## 4. Risks and limitations

1. **What the browser check does not cover.** The synthetic bundle's IMAGE blocks sit over blank areas of the synthetic PDF
   (measured: no ink inside either block's box on pages 3 and 5), so both crops are white rectangles — the drive proves the crops
   load, have their size and scale, not that they depict anything. A real drawing is `W55B-REHEARSAL-01`'s to see with the owner's
   export (129 blocks, 47 crops), which this lane did not open (F-7). The keyboard check in the browser dispatched a synthetic
   `keydown` on the focused tab rather than a CDP key press. No mismatch page and no unknown flag exist in the synthetic bundles, so
   those were seen in unit tests and the instruments only. A version published as a bare PDF can no longer be uploaded, so the
   «нет комплекта портала» state was not seen live.
2. **A 500-page version.** 100 blocks per press: a 2 000-block version is 20 presses, and every loaded block stays in the DOM (no
   virtualisation) with its whole recognised text. Crops load only as scrolled to. Nothing loads without a press. Measuring the
   screen on such a version is REHEARSAL's.
3. **Open vocabularies.** The flag map names the nine flags `analysis/recognised/flags.py` emits today; a flag the backend adds
   later shows «другой признак качества» until worded here (the token stays in `data-recognised-flag`). The portal status names
   `recognized` and `failed`; any other token shows «состояние у портала неизвестно этому экрану».
4. **Portal content is shown as it is.** Recognised text and descriptions are the portal model's output and may carry English and
   markdown (`**Summary:**` in the synthetic descriptions); the screen shows them as text, marked, and translates nothing in them.
   The language guard judges this application's words, with fixtures that hold Russian portal text.
5. **«Блоки портала появятся после первого запуска»** is also what a bundle whose runs all failed before the geometry stage shows;
   its detail says no run has reached the page markup yet, which stays true.
6. **The re-audit refusal's tone.** The queue renders a refusal as `ErrorState` («Команда не выполнена», red) rather than the
   warning tone the start control uses; `_pages/queue` is outside the grant and was left. It offers no repeat (its confirm button
   is disabled for a `refusal`).
7. **The crop address is built in `entities/block`**, not in `shared/api`, which the seam reserves for URL building; it reads the
   generated path template and the configured base and encodes as the transport does (decision 5).
8. **Nothing I could not fix on screen.** The white synthetic crops are glaring in the dark palette; that is the image (paper),
   not a style.

## 5. Integrator instructions

1. Merge `agent/w55b` through this report's commit. No contract, migration, lock file, dependency or fixture is touched.
2. **Heavy steps owed by this lane: none.** Light acceptance only (`R-102`); the full gate runs once on the final W55b candidate.
3. **Outside the grant, each needed and minimal:** `web/src/entities/audit-run/{index.ts,model/input-budget.ts,model/run-failure.ts}`
   (pre-authorised by the brief: one classification of the figures, and the `input_budget_exceeded` case in `classifyRunFailure`);
   `web/src/entities/execution/model/failure.ts` (**not anticipated by the brief**: the re-audit control classifies with
   `executionFailure`, not `classifyRunFailure`; the edit appends the same figure sentence for this one code, importing it through
   `@/entities/audit-run`'s public API). Veto either and re-audit or start loses its figures.
4. **Two contradictions met:** the manifest has no route-level sentence a checker reads (decision 2); the re-audit control's
   classifier is in `entities/execution` (decision 1).
5. **For REHEARSAL:** open «Блоки» on the owner's export and look at the 47 crops; press «Показать ещё» on the 500-page bundle.
   **For FIXTURES (a later wave):** the synthetic IMAGE blocks could be placed over the drawing the synthetic PDF carries, so a
   browser check could see a crop's content.
6. **Optional:** `portalBlockCropUrl` can move unchanged into `shared/api` if the seam owner prefers it there.
7. The lane stack is down: API and Next stopped by their own PIDs, `make down`,
   `docker volume rm auditmanager-w55b-webblocks-postgres-data auditmanager-w55b-webblocks-s3-data`, `.env` removed, `web/.next`
   removed.

## 6. Containment

`git diff --name-only f94283d2..HEAD` is the list of section 1 (34 paths). Against the grant:

- **inside:** `web/src/_pages/blocks/**` (6); `web/src/widgets/portal-blocks/**` (4, new); `web/src/entities/block/**` (6, new);
  `web/src/shared/api/query-keys.ts` (the key beside `versions.blocks`) with `web/tests/guards/query-key-shape.guard.test.ts` and
  `web/tests/unit/api/configuration-and-cache-keys.test.ts`; `web/docs/PC01_UI_SEAM.md` (two hunks, both in §6);
  `web/tests/guards/rendered-language.guard.test.ts` (entries, shapes, one machine shape with its control);
  `web/tests/unit/styles/screens.ts`; `web/tests/unit/run/input-budget.test.ts`; `web/tests/unit/blocks/**` (5, new);
  `tests/e2e/pc01/journey/manifest.json` (two hunks, both inside the `/blocks` entry); `docs/program/W55B-WEB-BLOCKS.md`;
- **outside, each with its reason:** `web/src/entities/audit-run/index.ts`, `model/input-budget.ts`, `model/run-failure.ts` (the
  family the brief pre-authorised), `web/src/entities/execution/model/failure.ts` (section 5 item 3);
- **in the grant and not touched:** `web/src/features/start-run/**`, `web/tests/guards/prepared-sections.guard.test.ts`,
  `tests/e2e/test_pc01_journey_conformance.py`;
- **forbidden hotspots untouched:** `contracts/**`, `db/migrations/**`, `web/src/shared/api/generated/**`, `web/openapi/**`,
  `web/package.json`, `web/package-lock.json`, `web/FRONTEND_LOCK.json`, `web/src/app/**` (including `globals.css`),
  `web/src/_app/**`, `web/src/shared/ui/**`, `src/**`, `tools/**`, `fixtures/**`, any `conftest.py`, `tests/support/**`.
- `git status --porcelain -uall` is empty at the tip.

## Appendix: design decisions (made while writing; each is open to the integrator's veto)

1. **The re-audit control does not go through `classifyRunFailure`.** The brief expected it to; the tree says otherwise:
   `QueuePage` (`web/src/_pages/queue`) classifies a re-audit failure with `executionFailure` from
   `web/src/entities/execution/model/failure.ts`. One sentence for the figures lives in `entities/audit-run`
   (`model/input-budget.ts`, beside `classifyRunFailure`, which start-run uses), and `entities/execution` imports it through
   `@/entities/audit-run`'s public API (an entity reading another entity's public API has a precedent: `entities/user`
   imports `@/entities/account`). Rejected: two copies of the sentence (one per classifier), and a helper in `shared/api`
   (a frozen seam file outside the grant, for a sentence only two run classifiers print).
2. **The journey manifest has no route-level sentence.** The grant asks for the `not_produced` sentence in the `/blocks`
   entry of `tests/e2e/pc01/journey/manifest.json`. Measured: a route entry carries `name`, `path`, `page_module`,
   `expects_api`, `optional_api`, `follow`, `redirects_to` and `$comment`; `expects_rendered` exists only on write steps
   and refusal cases, which `test_pc01_journey_conformance.py` and the language guard read; nothing reads a sentence on a
   route, and a cold load of `/blocks` chooses no version, so the sentence cannot be on that screen. What the entry got:
   the four calls a choice makes as `optional_api` with the choice that makes each — which also puts each through the contract
   check — and the sentence in `$comment`, saying in so many words that nothing in the file checks it and which tests pin it.
   Rejected: an `expects_rendered` key on the route (read by nothing: a claim no checker can fail) and a new route-level checker
   in `test_pc01_journey_conformance.py` (outside the grant, which names only one control there).
3. **Budget refusal on start: `unsupported`, its own kind.** `analysis_input_budget_exceeded` fell to the classifier's
   `default` arm, titled «Запрос завершился ошибкой на сервере.» — wrong for a refusal of the input. It is now kind
   `input_budget_exceeded`, presentation `unsupported` (the tone that says no retry will help; `UnsupportedState` has no
   action), title «Текст версии больше бюджета входа анализа.», detail = the catalog sentence, the figures, «Повтор с тем
   же текстом получит тот же отказ.». `features/start-run` needed **no edit**: `StartRunControl` already renders an
   `unsupported` failure without a button. On re-audit the kind stays `refusal` (the queue re-enables its confirm button
   only for `unknown_outcome`) and the detail gains the figures. Rejected: `error` presentation (red, with the retry slot).
4. **Figures exactly as returned, or none.** Both `details.character_count` and `details.budget_characters` must be
   non-negative safe integers, else the figure sentence is absent and the catalog sentence stands alone (no `NaN`, no
   rounding, no lone figure). Digits grouped by threes with U+202F; labels before numbers («Символов в тексте версии: N;
   допустимо не более: M.») so no Russian plural agrees with a server number. Rejected: `Intl.NumberFormat('ru-RU')`
   (its separator is the ICU build's choice) and printing a single valid figure.
5. **The crop is an `<img>` with an address, not a blob.** Every other binary here (a version's PDF, a norm document) is
   read by script into a `Blob` and an object URL. A crop is fetched by the browser: `loading="lazy"` loads only what is
   scrolled to, the HTTP cache keeps it, and the same-origin request carries the session cookie the BFF turns into the
   API credential. The address is built in ONE place, `entities/block/api/crop-url.ts`, from the generated operation
   table's path template (`OPERATIONS.streamVersionPortalBlockCrop.path`) and `getApiBaseUrl()` (which refuses an
   unconfigured build), each identifier encoded as the transport encodes it, and an empty one refused. Rejected: blob +
   object URL (eager, in memory, 47 crops / 25 MB on the owner's export), and a URL helper in `shared/api` (outside the grant).
6. **Paging: an explicit «Показать ещё», 100 blocks a request.** One infinite query per version; the first page loads with the
   tab, each next page only on a press, with the last page's cursor; no automatic continuation, so requests = presses. The
   version's `block_count` is printed beside the count loaded, and while more remain the screen says the last page shown may
   continue. The client concatenates pages in load order and **repairs nothing** (no sort, no de-duplication): a server that
   broke its order or repeated a block is shown, not hidden; React keys carry the position so a repeat cannot collide.
   Rejected: infinite scroll (needs an `IntersectionObserver` this suite cannot test, and loads without an act of the reader),
   a loop to the end (thousands of blocks for a 500-page bundle), and the maximum page size 200 (more text per response).
7. **Two `not_produced` sentences.** «Блоки портала появятся после первого запуска анализа этой версии.» for a version whose
   manifest has the block list (`source.structured_companion`); «У этой версии нет комплекта портала.» for a version published
   as a bare PDF before W55b, which stays `not_produced` after its runs (`W55B-GEOMETRY-01` §5 item 4). Both
   `NotApplicableState`; produced-but-empty is `EmptyState` «В комплекте портала нет ни одного блока.». The screen reads
   `status`, never the length of `items`. Rejected: one sentence for both (it would promise blocks that never come).
8. **Tabs: local to the page, WAI-ARIA with automatic activation.** No tabs primitive exists in `shared/ui` and this is the only
   screen with tabs. Arrows (wrapping), Home and End move selection and focus; only the open tab is in the tab order; both panels
   exist, the closed one `hidden` and empty (its content is mounted only while open, so the text-line index is read only when
   asked for). The keyboard contract is a pure function (`tabAfterKey`) because this suite has no DOM to fire a key in. The tab
   and the version choice are page state and do not survive a reload. Below 520 px the two tabs share the row. Rejected: a
   `shared/ui` primitive (one consumer), panels kept mounted (both reads on every choice).
9. **What a block shows.** Type label (Текст / Изображение / Штамп), the portal's status in Russian (`recognized` → «распознан
   порталом», `failed` → «сбой распознавания портала», anything else → «состояние у портала неизвестно этому экрану», the raw
   token only in `data-portal-status`), «порядок у портала: N» when there is an ordinal (the contract calls it the order on the
   page, the synthetic bundle numbers it across the document, so the label claims neither), «вершин в контуре: N» when there is
   a polygon (a count of the list the response holds; nothing drawn), and on a mismatch page the sentence «страница не совпала с
   PDF — фрагмент не вырезан» (a wrapping style, not a nowrap badge). Recognised text in a `<pre>` (pre-wrap, React-escaped) under
   «распознано»; each flag a wrapping chip and a plain sentence; an unknown flag «другой признак качества» with no token. A TEXT
   block without text: «Текст не распознан.». The description under «описание портала — в анализе не используется». The crop
   `<img>` with `width`/`height` from the response, `loading=lazy`, a Russian `alt`, `max-width:100%`, `height:auto`,
   `max-height:32rem` with `object-fit:contain` (the box is reserved before the bytes arrive and a tall drawing does not take
   several screens), a link to open it whole, and on `error` the sentence «Изображение не удалось загрузить.» instead of a
   broken icon.
10. **The text-line tab's leftover English, found by the guard.** Rendering «Строки текста» over a loaded index for the first
    time (no instrument had reached it since `W45-BLOCKS`) showed `x0 … y0 … x1 … y1 … pt · начало координат top_left` and the
    block id `b_000001` as visible text. The coordinates are now «левый край / верхний край / правый край / нижний край, в пунктах
    от левого верхнего угла страницы» (values unchanged, the machine words in `data-bbox-unit` and `data-bbox-origin`, the two
    single-member vocabularies as `Record`s), and the language guard gains one machine shape, the contract's own pattern for that
    id (`openapi.json` pins `BlockGeometry.block_id` to `^b_[0-9]{6}$`), with a control that a wrong shape still reddens.
    Otherwise the tab's content is unchanged. Rejected: leaving the loaded text-line state unseeded (the guard would stay blind
    to R-18 words a reader sees).
11. **The guard registration and the `text_analysis` expectation.** `PortalBlockType` and `PortalGeometryState` are registered
    with markers; the expectation is restored to `['text', 'analysis']`. The chosen version's tabs are exported
    (`VersionBlockViews`, `PortalBlockListView`, `CropFigureView`) so the instruments render the markup the page renders rather
    than a copy; the language guard renders them with a test crop address (`TEST_CROP_SRC`) and the census sets the API base for
    its one render and restores it, the way it already does for the instance label.

## 7. Verification by the wave executor (after the writer's hand-back)

Run by the wave executor on tip `e6cbfed2`, host load under 1, one invocation at a time; exit codes read directly. The live journey was **not** re-driven
by the wave executor (it needs a stack, a build and a browser): its summary in section 2 is the writer's; the wave executor read the writer's
screenshots instead.

| Check | Result |
| --- | --- |
| `git diff --check f94283d2..HEAD`; `git status --porcelain -uall`; stack, volumes, `.env`, the lane's API and Next ports | exit 0; empty; none left |
| `npm run lint`, `npm run typecheck` | exit 0 both |
| Vitest in two parts | 135 files / 2 013 tests, and 16 tests (the writer's counts) |
| `tests/contract` (the three files excluded) | 752 passed, 18 927 subtests |
| `tests/e2e/test_pc01_journey_conformance.py` | 87 passed |
| nine spot mutations (restored byte for byte, SHA-256 compared): recognised text rendered as raw HTML; the «распознано» marker removed; the description marker removed; `loading="lazy"` removed; the mismatch notice removed; an unknown flag printing its raw token; the budget figures losing their digit grouping; a non-integer figure accepted; the re-audit classifier printing no figures | all nine red |
| the writer's screenshots (desktop and phone, light and dark; the flags view, the start refusal, the re-audit refusal), read by the wave executor | the flags with their Russian explanations, no horizontal overflow on a phone, both figures on both refusals and no repeat button |

What the screenshots do not show, and the writer says so (section 4): the synthetic bundles' IMAGE blocks lie over blank regions of their PDFs, so every crop is white;
the browser proves the crops load and are sized, not that they depict what the block marks. The real drawings are REHEARSAL's.

