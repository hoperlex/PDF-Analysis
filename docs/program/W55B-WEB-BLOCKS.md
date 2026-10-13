# W55B-WEB-BLOCKS — report (the «Блоки» screen shows a portal bundle; the budget refusal shows its figures)

> **Living report.** Written while the lane runs, updated with every commit, so a restarted session resumes from
> `git log` and this file. Final form: the six items of `AGENTS.md` §5 (a later commit rewrites this file into them).

## 0. Status

- Lane: `W55B-WEB-BLOCKS` (plan `docs/program/dispatch/W55-PLAN.md` §B3.9, grant §B4 item 5). Branch `agent/w55b`, base
  `f94283d2` (the GEOMETRY report). Writer: one session; the wave executor verifies afterwards.
- Done (`77d8a4a6`, `4c5c7284`): `entities/block` (paged query, crop address, vocabulary, page sections, bundle check);
  `widgets/portal-blocks`; the two tabs on `/blocks`; `queryKeys.versions.portalBlocks`; the input-budget figure sentence
  read by the start-run and re-audit classifiers; unit tests under `web/tests/unit/blocks/**` and
  `web/tests/unit/run/input-budget.test.ts`; the language-guard registration and shapes; the census screens; the query-key
  guard entries; `PC01_UI_SEAM.md` §6; the `/blocks` manifest entry.
- Next: full light acceptance (lint, typecheck, Vitest in two parts, `tests/contract`, `tests/e2e` conformance), the
  mutation proofs, the live journey and the screenshots, then the final form of this report.

## 1. Decisions (each names the alternative rejected; each open to the integrator's veto)

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
   the four calls a choice makes (`listDocuments`, `listVersionPortalBlocks`, `streamVersionPortalBlockCrop`,
   `getVersionBlocks`) as `optional_api` with the choice that makes each — which also puts each through the contract
   check — and the sentence in `$comment`, saying in so many words that nothing in the file checks it and which tests
   pin it. Rejected: an `expects_rendered` key on the route (read by nothing: a claim no checker can fail) and a new
   route-level checker in `test_pc01_journey_conformance.py` (outside the grant, which names only one control there).
   `test_control_a_reworded_panel_is_detected` therefore needed no change.
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
   (its separator is the ICU build's choice, U+00A0 today) and printing a single valid figure.
5. **The crop is an `<img>` with an address, not a blob.** Every other binary here (a version's PDF, a norm document) is
   read by script into a `Blob` and an object URL. A crop is fetched by the browser: `loading="lazy"` loads only what is
   scrolled to, the HTTP cache keeps it, and the same-origin request carries the session cookie the BFF turns into the
   API credential. The address is built in ONE place, `entities/block/api/crop-url.ts`, from the generated operation
   table's path template (`OPERATIONS.streamVersionPortalBlockCrop.path`) and `getApiBaseUrl()` (which refuses an
   unconfigured build), each identifier encoded as the transport encodes it. This is a reading of the seam's "a slice
   never constructs a URL": the template is the contract's, not typed out. Rejected: blob + object URL (eager, in memory,
   47 crops / 25 MB on the owner's export), and a URL helper in `shared/api` (outside the grant). The integrator may move
   the function into `shared/api` unchanged.
6. **Paging: an explicit «Показать ещё», 100 blocks a request.** One infinite query per version (key
   `['versions','portal-blocks',uid,{limit}]`); the first page loads with the tab, each next page only on a press, with
   the last page's cursor; no automatic continuation, so requests = presses. The version's `block_count` is printed
   beside the count loaded, and while more remain the screen says the last page shown may continue. The client
   concatenates pages in load order and **repairs nothing** (no sort, no de-duplication): a server that broke its order
   or repeated a block is shown, not hidden; React keys carry the position so a repeat cannot collide. Rejected: infinite
   scroll (needs an `IntersectionObserver` this suite cannot test, and loads without an act of the reader), a loop to the
   end (thousands of blocks for a 500-page bundle), and the maximum page size 200 (more recognised text per response).
7. **Two `not_produced` sentences.** «Блоки портала появятся после первого запуска анализа этой версии.» for a version
   whose manifest has the block list (`source.structured_companion`); «У этой версии нет комплекта портала.» for a version
   published as a bare PDF before W55b, which stays `not_produced` after its runs (`W55B-GEOMETRY-01` §5 item 4). Both
   `NotApplicableState`; produced-but-empty is `EmptyState` «В комплекте портала нет ни одного блока.». The screen reads
   `status`, never the length of `items`. Rejected: one sentence for both (it would promise blocks that never come).
8. **Tabs: local to the page, WAI-ARIA with automatic activation.** No tabs primitive exists in `shared/ui` and this is
   the only screen with tabs. Arrows (wrapping), Home and End move selection and focus; only the open tab is in the tab
   order; both panels exist, the closed one `hidden` and empty (its content is mounted only while open, so the text-line
   index is read only when asked for). The keyboard contract is a pure function (`tabAfterKey`) because this suite has no
   DOM to fire a key in. The tab and the version choice are page state and do not survive a reload. Rejected: a
   `shared/ui` primitive (one consumer), panels kept mounted (both reads on every choice).
9. **What a block shows.** Type label (Текст / Изображение / Штамп), the portal's status in Russian (`recognized` →
   «распознан порталом», `failed` → «сбой распознавания портала», anything else → «состояние у портала неизвестно этому
   экрану», raw token only in `data-portal-status`), «порядок на странице: N» when there is an ordinal, «вершин в контуре:
   N» when there is a polygon (a count of the list the response holds; nothing drawn), and on a mismatch page the
   sentence «страница не совпала с PDF — фрагмент не вырезан» (own wrapping style, not a nowrap badge). Recognised text in
   a `<pre>` (pre-wrap, React-escaped) under «распознано»; each flag a Russian chip and a plain sentence; an unknown flag
   «другой признак качества» with no token. A TEXT block without text: «Текст не распознан.». Description under
   «описание портала — в анализе не используется». The crop `<img>` with `width`/`height` from the response, `loading=lazy`,
   a Russian `alt`, `max-width:100%`, `height:auto`, `max-height:32rem` with `object-fit:contain` (a tall drawing does not
   take several screens, and the box is reserved before the bytes arrive), a link to open it whole, and on `error` the
   sentence «Изображение не удалось загрузить.» instead of a broken icon.
10. **The text-line tab's leftover English, found by the guard.** Rendering «Строки текста» over a loaded index for the
    first time (no instrument had reached it since `W45-BLOCKS`) showed `x0 … y0 … x1 … y1 … pt · начало координат
    top_left` and the block id `b_000001` as visible text. The coordinates are now «левый край / верхний край / правый
    край / нижний край, в пунктах от левого верхнего угла страницы» (values unchanged, the machine words in `data-bbox-unit`
    and `data-bbox-origin`, the two single-member vocabularies as `Record`s), and the language guard gains one machine
    shape, the contract's own pattern for that id (`openapi.json` pins `BlockGeometry.block_id` to `^b_[0-9]{6}$`), with a
    control that a wrong shape still reddens. Otherwise the tab's content is unchanged. Rejected: leaving the loaded
    text-line state unseeded (the guard would stay blind to R-18 words a reader sees).
11. **The guard registration and the `text_analysis` expectation.** `PortalBlockType` and `PortalGeometryState` are in
    `TRANSLATED_SCHEMAS` with markers `data-portal-block-type` / `data-portal-geometry`; every member of both is on a
    rendered screen. The expectation `unexplainedLatin('text_analysis')` is **restored** to `['text', 'analysis']` (SEAL had
    narrowed it to `['analysis']`), and `text`, `image`, `stamp`, `ok`, `geometry_mismatch` are asserted to be offences as
    bare words. The chosen version's tabs are exported (`VersionBlockViews`, `PortalBlockListView`, `CropFigureView`) so
    the instruments render the markup the page renders; four `BlockMarkup` entries left `UNREACHABLE_IN_ONE_PASS` because
    the ratchet said a state now renders them. `prepared-sections.guard.test.ts` needed no entry (`blocks` graduated from
    it in `W45-BLOCKS`).
