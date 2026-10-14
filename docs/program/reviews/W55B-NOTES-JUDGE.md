# W55B-NOTES-JUDGE — independent judgment of the 0.6.0 release notes

**Subject:** candidate `03042093` (W55b, W55B-FIX and GATE-PKG-01 merged), `release-notes/0.6.0.json` revision 1,
judged against `git diff 9da3ea06 03042093` and the tree. The judge is a fresh-context reader. It did not write the
notes or the code, and it changed no file except this one.

**Verdict: ACCEPT-WITH-EDITS.** Items 1 and 3 are true as written. Items 2, 4, 5 and 6 each need a precise edit.
Item 5 also has to absorb two user-visible changes the notes miss. The edited entry becomes **revision 2**:
`RELEASE_PROCESS.md:15` requires a new revision for every content correction. This also means changing the pin
`"0.6.0": 1` → `2` in `tests/contract/release_notes/test_release_notes_form.py:147` and its comment.

## Items

| Item | Verdict | Evidence (file:line) | Edit, if any |
|---|---|---|---|
| 1 bundle upload, 500 pages / 250 MiB, previously 30 / 25 MiB, bare document refused | true | `src/auditmanager/ingest/envelope.py:136,139`; `ingest/service.py:404-413` (not a ZIP → `portal_bundle_required`; archive > 250 MiB refused); `web/src/entities/document-version/model/upload-envelope.ts:35,41,51,100` (pre-check sentence says what to upload); old limits `9da3ea06:…/upload-envelope.ts:26-28`; the screen is `screen-registry.ts:120-122` with `project-detail-page.tsx:64` (the only `UploadPanel`) | none |
| 2 «Блоки» tabs, crops, when blocks appear | edit | Tabs and names: `web/src/_pages/blocks/model/tabs.ts:18,20-23`. The tabs exist only after a version is chosen: `blocks-page.tsx:73-110`. Crops are cut by the product, for IMAGE blocks only: `analysis/geometry/portal.py:260-268`, `portal-block-card.tsx:84`. W55B-FIX rewrote the empty state to «…после первого запуска анализа этой версии, который дойдёт до разметки страниц»: `widgets/portal-blocks/ui/portal-blocks.tsx:168-169`. A bare-PDF version has no blocks: `:172-174`. Navigation path: `screen-registry.ts:176`, `_app/navigation.ts:25` | E2 |
| 3 «распознано», flags, description marker, analysis reads embedded text only | true | `web/src/entities/block/model/vocabulary.ts:81-82,114-115,130,133`; `portal-block-card.tsx:105,127`; `src/auditmanager/analysis/README.md:134-136,166`. No stage consumes crops: `analysis/stages/` has no `block_analysis` | none |
| 4 input budget refusal with both figures | edit | `src/auditmanager/runs/commands.py:315-331,404,587`. The figures are `entities/audit-run/model/input-budget.ts:54-60`, `run-failure.ts` (start) and `entities/execution/model/failure.ts` (queue «Повторный аудит», `execution-queue.tsx:58`). Not universal: `commands.py:324` admits a version with no recorded count, and migration `0021` records no count for older versions. At the default ceiling the budget is 152 361 characters, while a 500-page text bundle has 1 786 430: `W55B-REHEARSAL-01.md:12,112`; the guaranteed floor is 93 690 (`analysis/text/budget.py:97`) | E4 |
| 5 the form names the broken rule; the same rules are listed before a file is chosen | edit | W55B-FIX adds refusals the form now names with numbers: `upload-failure.ts:42-53` (`blocks_count` 100/3000/1000, `bundle_envelope.py:88-96,282-289`; `pdf_page_content`, `pdf_document_content`, `pdf_reader_limits`). These are absent from the list shown before a file is chosen (`upload-envelope.ts:50-57`), so «те же правила перечислены…» no longer holds. The new upload gate is missing entirely: 2 slots and a retry after 5 s (`api/routers/multipart.py:76,85`, absent at `9da3ea06`), with the busy message at `upload-failure.ts:159-174` | E5 |
| 6 a text-less page is admitted by a portal block | edit | A block of **any** type admits the page: `ingest/bundle_envelope.py:17-18,403-409`. Recognised text exists only for TEXT blocks (`portal-block-card.tsx:166-174`), and it is never passed to analysis (`analysis/README.md:134-136`). The sentence «её распознанный текст виден» presumes text that an image- or stamp-only page lacks. It also leaves unsaid that analysis does not read this text | E6 |

## Missing changes

- **Added to E5:** the concurrent-upload gate and its «повторите через N с» refusal (O-1). Also the block ceilings and
  the PDF content/reader limits (X-4, X-1), which a user's bundle can break and which the form states.
- **Corrected by E2 and E4:** FIX addendum 2. The «Блоки» empty state for an over-budget version is consistent with
  item 4, but item 2's «после первого прогона» repeats the promise FIX removed from the screen.
- **Considered and not needed:**
  - crop caching (`Cache-Control`, X-4): speed only;
  - the 401 before the body is read (X-3): same refusal, earlier;
  - control characters in titles replaced (X-10);
  - paging by 100 and the page-box mismatch sentence;
  - archive-hygiene rules (ratio, symlinks, 300 MiB unpacked), which «например» covers.

## Proposed replacement texts (Russian, exact)

(The outer «» delimit each text and are not part of it. Inner «» are the notes' own quotes.)

**E2 (item 2):** «После выбора версии «Блоки» открываются на вкладке «Блоки портала»: блоки версии по страницам — текст, изображения и штампы. Для изображения показан фрагмент страницы, который система вырезала из документа сама. Блоки появляются, когда прогон анализа версии доходит до разметки страниц; у версий, загруженных раньше без комплекта, их нет. Прежний список строк остался на вкладке «Строки текста».»

**E4 (item 4):** «Прогон анализа принимает текст не больше установленного объёма, и документ в сотни страниц может в него не уложиться. Если текст версии, загруженной комплектом, больше, запуск прогона и «Повторный аудит» в очереди отклоняются сразу, без нового прогона; сообщение называет оба числа: сколько символов в тексте и сколько допустимо. Блоки портала строит прогон, поэтому у такой версии их не будет.»

**E5 (item 5):** «Комплект проверяется при загрузке целиком. При отказе форма теперь называет нарушенное правило, например о составе архива, размере, числе страниц, тексте на страницах, числе блоков (до 100 на странице, 3000 в комплекте, 1000 изображений) или объёме графики и текста. Основные правила перечислены в форме до выбора файла. Пока идут две загрузки, третью форма просит повторить через несколько секунд.»

**E6 (item 6):** «Страница без встроенного текста, например отсканированная, принимается, если на ней есть хотя бы один блок портала; её блоки видны в «Блоках», но её распознанный текст в анализ не передаётся. Страница без встроенного текста и без блока портала по-прежнему отклоняется.»

## Form, audience and checks

- The texts are Russian, with no Latin script or code tokens. Dictionary words appear only inside «». The units are
  «МиБ». The title has 7 words. The kinds are ordered new ×4, then improved ×2.
- `screen`/`where` match the registry for all six items. The date `2026-10-15` is strictly after 0.5.1's
  `2026-10-14`. Re-dating at publication is also a revision.
- **On revision 1:** `free -m` showed 4 478 MiB available. Then
  `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/release_notes` → **23 passed**, rc 0.
- **On the edits:** each was run in memory through the test's own `form_failures` (scratch script, tree untouched),
  which returned `set()`. Lengths 366/395/375/394/398/268, each under 400. The vitest registry check was not run
  (2.2 GiB available); the paths were checked by reading the registry.
- **Containment:** read-only apart from this file. No git write, Docker, network or `.local/portal-exports/`, and no
  process was killed.
