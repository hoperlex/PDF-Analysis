# CMP-C1-FIX-B — the web FIX slot of wave C1: the screens aligned with the overview, the viewer in Russian, the markers and the queue mount

Written 2026-10-29 by the Sonnet lane `CMP-C1-FIX-B` (size M, web only, branch `agent/cmp-c1-fix-b`, base `0e867b12` on `integration/compare-modules`; nothing pushed, nothing merged, no tag). Task file: [`tasks/CMP-C1-FIX-B.md`](tasks/CMP-C1-FIX-B.md). The sources are [`CMP-VC-OVERVIEW-01.md`](CMP-VC-OVERVIEW-01.md) (section 6 is binding), [`CMP-VC-UI-01.md`](CMP-VC-UI-01.md) (sections 5, 7, 10), [`CMP-VIEWER-01.md`](CMP-VIEWER-01.md), [`CMP-SERIES-01.md`](CMP-SERIES-01.md) and the series service (`src/auditmanager/comparison/series/service.py`) for the commands it accepts.

## 1. Result

`CMP-VC-UI-01` built the screens before `CMP-VC-OVERVIEW-01` merged and guessed some of its semantics. The lane replaces each guess with the merged rule and closes the web items the C1 reports left. One commit per item, each test shown failing under a quoted mutation.

| # | Item | Commit | Done |
| --- | --- | --- | --- |
| 1 | Row group and counters = the server's rule (OVERVIEW 6.3) | `f46a11e1` | done |
| 2 | Step words, tones, chip sentences, actions = OVERVIEW 6.2 and 6.4 | `9cbb7189` | done |
| 4 | The viewer says its reasons with `pairReasonWords` (the entity's complete table) | `52af0bdd` | done |
| 3 | The viewer's words: «Было»/«Стало», Russian zone and field names; its shapes join the language guard | `aa955e2a` | done |
| 5 | `data-layer`, `data-channel-state`; `ComparisonLayer` and `ComparisonChannelState` in `TRANSLATED_SCHEMAS` | `ebfd28d2` | done |
| 6 | The page of «Очередь» mounts the block «Сравнение»; the slot is gone | `d437d71b` | done |
| — | a type fix of one new test | `5796f752` | |

### 1.1 Item 1 — the group of a row and the counters

`groupOf` (`entities/version-series/model/overview-view.ts`) is the rule of OVERVIEW 6.3: no `next_step` → «Готовы»; the proposed step queued, running or pausing → «Идут»; the proposed step failed and it is the upload, the profile or the matrix → «Ошибки»; anything else → «Ждут действия» (a failed series is waiting). VC-UI-01 had «any step failed > any step running > `next_step` present > ready», which counted a failed series red and a running step the row does not propose as «Идут».

The proof is `tests/unit/version-compare/model.test.ts`, describe «the group of a row and the counters are the server's rule»: every proposed step (7) in every state (13), with the other six steps in three different states (273 sets), against two literal tables written out in the test; the 13 sets that propose nothing; and the counters recomputed over 104 sets (91 + 13), compared with figures written by hand in the test (`all 104, waiting 67, running 21, failed 3, ready 13`). The fixture `overview()` now carries a `next_step` per state and counters that are written out, not computed; `screens.test.ts` shows that a search which lets every row through (the letter «к» is in every code and in the one title) recomputes exactly the five numbers the read carries.

### 1.2 Item 2 — the step cells, the chip, the actions

* **Words and tones (6.2).** Two differences from the guess: a queued series is «в очереди» (VC-UI-01 section 5 item 4 had «идёт», from the SERIES notes; the binding OVERVIEW table says «в очереди» (run)), and a failed series is amber (`warn`), while a failed profile and matrix stay red. Steps 4, 6 and 7 are `not_applicable`: «—», tone `off`. Every other state of the profile, the matrix and the series was already as the table says; the test now writes the table out (24 rows) so it cannot drift.
* **Counts (6.1).** Checked against the table and against `overview/rules.py`: the profile reads `ready`, `total`, `failed` (pages), the matrix `rows`, `unmatched`, `manual_edits`, the series `done`, `total`, `with_changes` (the last only for `done`), the upload `total`. Nothing else is read; tested by the notes of each state.
* **The chip** is the original's sentence (`OV:297-331`, OVERVIEW 6.2) for the step the row names and that step's state: `nextStepSentence`, every sentence of 6.2 a literal in the test, and a sweep over all 7 steps × 13 states proves no Latin letter and no empty sentence. The prefix «Далее:» is gone (the column header says «следующий шаг»). Where 6.2 gives no sentence (a paused profile or matrix, a `pausing` series; the C2 steps, which the server never proposes in C1) the lane's own words are «Разбор версий на паузе», «Сопоставление листов на паузе», «Сравнение соседних: ставится на паузу» and the step's name. No `next_step`: «Одна версия — сравнивать не с чем» when `version_count` < 2, else «Готово».
* **Actions (6.4), checked against the series service.** «Подготовить»/«Повторить» → `prepareComparisonMatrix` («Повторить» for a failed profile or a failed matrix; a profile that is running with a stored failure is a retry in progress and offers nothing — VC-UI-01 offered a second one); «Запустить» → `startComparisonSeries`; «Пауза» → queued or running only (`pause_series` refuses other states); «Продолжить» → `resumeComparisonSeries` for a **paused** series only (`resume_series` refuses everything else; VC-UI-01 also mapped `interrupted` to it); «Досчитать» → `finishComparisonSeries` for a failed or interrupted (cancelled) series **with a transition left** (`done` below `total`; `finish_series` answers `comparison_series_state` with nothing unfinished, so with the figures unknown it is not offered); «Заново» → `startComparisonSeries` with `restart` for a done, stale, failed or interrupted series — and no longer for a paused one, which is live and refused with `comparison_series_active` (`_start`, `live_series`).

### 1.3 Item 4 — the reasons of a pair

`widgets/comparison-viewer/ui/evidence-panels.tsx` had a stopgap table of eight reasons (`REASON_WORDS`) that printed «причина без описания (КОД)» for `SPLIT_SHEET`, `TABLE_GROUP`, `AI_MATCH` and every `UNCHECKED_CHANNEL_<CHANNEL>`. It imports `pairReasonWords` from `entities/version-series` (the one complete table); the stopgap and its export are gone. An unknown code is now «причина не описана» and its code is not printed (a pair's `failure_reason` is said through the same table).

### 1.4 Item 3 — the viewer's words

| Was | Now |
| --- | --- |
| «Лист A: …», «Лист B: …» (header), pane labels «Лист A»/«Лист B» | «Было: л. 5 · …», «Стало: …»; panes «Было»/«Стало» |
| «Шторка: слева лист A, справа наложение», «под ней лист A/B» | «Шторка: слева — было, справа — наложение», «под ней — было/стало» |
| «Графика: добавлено (B)», «удалено (A)» | «… (стало)», «… (было)» |
| «Лист B — часть листа A; … % листа A», «Лист B — весь лист A, составленный из частей» | «Новый лист — часть прежнего листа; … % прежнего листа», «Новый лист — весь прежний лист, составленный из частей» |
| «Совмещение B на A» | «Совмещение нового листа на прежний» |
| «Показать перемещённые блоки листа B …» | «… нового листа …» |
| «зона «stamp»», «поле «revision»» | zone and field in words from tables in `model/labels.ts` (`ZONE_WORDS`, `fieldWords`): «зона «штамп», поле «номер последнего изменения»», «отметка о выпуске», «PDF-пометки», «поля листа»; PDF annotation subtypes («выделение», «заметка», …). A value the table does not know is «другая зона» / «другое поле», never printed |
| «QR-код» (kind of a note) | «Матричный код» (see section 3) |
| «Алгоритм: cmp-engine/1» | «Алгоритм: версия 1»; the raw string is `data-algo-version` |
| «Сравнение листа не удалось: RENDER_FAILED.» | «… лист не удалось отрисовать.» |

«Версия №N» is not shown in the viewer: the viewer knows a sheet's version by its identity only, not its place in the comparison order, and `ComparisonViewer(pair, rasterSize?, navigation?)` keeps its props. The sheets tab, which names the columns «Версия №N», is around it.

The two shapes that mount the viewer (`sheets-tab-with-the-viewer-and-the-order-dialog`, `pair-viewer-opened`) are no longer census-only: the `censusOnly` field of `shapes.ts` and the one-line filter in the language guard are removed, and the guard renders them. It found one more Latin word, in the fixture: «3x2,5» (a Latin x) in a text change; the fixture is Cyrillic like every seed of the guard.

### 1.5 Item 5 — the markers

`data-layer` on the `<label>` of each of the eight layer toggles (the element that wraps the checkbox and the Russian name) and `data-channel-state` (with `data-channel`) on the chip of each channel. The channel strip is now a line of chips per state: «Проверено: …», «Не проверено: …» and, new, «Не применимо: PDF-пометки; позиции СО» — the guard requires every member of `ComparisonChannelState` to be seen on a screen, and `not_applicable` was never drawn. `ComparisonLayer` and `ComparisonChannelState` are in `TRANSLATED_SCHEMAS` with two rows of `SCHEMA_MARKERS`; the guard sees all 8 and all 3 members.

### 1.6 Item 6 — the queue block

`_pages/queue/ui/queue-page.tsx` renders `<ComparisonQueueBlock />` under the list of runs (one line and the import). `ComparisonQueueSlot` is removed from `comparison-queue-block.tsx` and `execution-queue.tsx` is restored to the text it had before the slot (`git show a3015696^`). The block keeps its own query, so it no longer depends on the list's read state (it used to appear only after the list had data). The test that checked the slot is replaced by one that checks the page: the list draws no block, the page does, and the cold page says «Загрузка: сводку сравнения…».

## 2. Base facts, printed before any edit

`contract 1.10.0, 131 paths, 148 operations, 432 schemas`, head `0039_comparison_core`, base `0e867b12cbbfbed1e048e2142748f6286edc6a50` (`P-01` of the task file). They equal the brief's. The lane changed no contract, no migration, no generated client, no dependency, no lock file, no global style, no backend file.

## 3. Decisions the lane took, and what it did not do

1. **A queued series reads «в очереди»**, as OVERVIEW 6.2 says, and not «идёт» as VC-UI-01 (from the SERIES notes). If the integrator prefers the original's single «идёт», it is one entry of `STEP_WORDS.series` and one row of the table test.
2. **The word for a QR code is «матричный код».** `NOT_DERIVABLE` of the language guard stands at its cap of 20 entries (`expect(NOT_DERIVABLE.length).toBeLessThanOrEqual(20)`), so «QR-код» could not be permitted; the guard's own rule is that a Latin word needs a contract to explain it. If the owner wants «QR-код» on screen, an entry with a reason and a raised cap is the change, in the guard.
3. **The version string of the algorithm** (`cmp-engine/1`) is machine text. The reader gets «версия 1»; the string is in `data-algo-version` for whoever quotes it. A value without a trailing number reads «версия не указана».
4. **`channel.reason` is printed as the engine wrote it**: the engine writes Russian sentences there (`engine/child/job.py`). A future English reason would be caught by the guard on a shape that carries it.
5. **A paused profile or matrix, a `pausing` series, the C2 steps as a proposed step** have no sentence in OVERVIEW 6.2; the words are the lane's (section 1.2).
6. **Not done, by the brief:** the menu entry that stays when the module is off (needs `_app/**`), a `group` member or a chip text on the contract (OVERVIEW FIX candidates 2 and 3), steps 4/6/7, a plain sheet view. «Версия №N» in the viewer is not done for the reason in section 1.4.

## 4. Limits and risks

1. **«Пауза» on a series that is queued only because a batch asked for the comparison after the preparation** (`series_after_preparation`, the series row does not exist yet) finds no series: `useSeriesAct` looks for the newest series of the document and does nothing when there is none. The overview cannot tell that case from a queued series that exists. A silent no-op, as before this lane; the way out is an overview member for the series identity (a contract change) or a refusal in words in `useSeriesAct`.
2. **«Досчитать» needs `done` and `total`** of the series step. The server sends both for a failed or cancelled series (`overview/rules.py`); if it ever omitted them the button would not be offered and «Заново» would be.
3. **The guard file is a merge hotspot.** The lane's hunks in `web/tests/guards/rendered-language.guard.test.ts`: the `SCREENS` line (the `censusOnly` filter removed), a comment, two names appended to `TRANSLATED_SCHEMAS`, two rows appended to `SCHEMA_MARKERS`. The C2 seal edits the same arrays; the conflicts are at the ends of the arrays and are append-append.
4. **Not run, by the brief and `R-135`:** `make gate`, the live journey, a browser. The viewer's chips and the new «Не применимо» line were seen as static markup only; the contrast census passes (no stylesheet rule was added).

## 5. Mutation proofs (red, restore, green)

Tool: a script outside the repository applies one quoted replacement to the committed file, runs the named tests, restores the file with `git checkout` and runs them again; the tree was clean after each. `M` = `web/tests/unit/version-compare/{model,screens}.test.ts`; `V` = `web/tests/unit/comparison/viewer/viewer-markup.test.ts`; `G` = `web/tests/guards/rendered-language.guard.test.ts`.

| # | Commitment | Mutation | Red |
| --- | --- | --- | --- |
| M1a | **the group is the server's rule** | the old VC-UI-01 rule: any failed step makes the row red | M: 4 failed |
| M1b | a failed series is waiting | `series` joins the red-when-failed steps | M: 3 failed |
| M1c | `pausing` is running | only `running` and `queued` count | M: 4 failed |
| M1d | nothing proposed is ready | no `next_step` but a running step reads «Идут» | M: 2 failed |
| M2a | a failed series is amber | the tone table alone | M: 2 failed |
| M2b | a queued series is «в очереди» | the guess of VC-UI-01 put back | M: 2 failed |
| M2c | a paused series is only resumed | «Заново» offered too | M: 1 failed |
| M2d | «Досчитать» only with something left | offered always | M: 1 failed |
| M2e | the chip of unmatched sheets | the sentence removed | M: 2 failed |
| M2f | no second «Повторить» during a retry | `counts.failed > 0` offers it | M: 1 failed |
| M4a | **the viewer uses the complete table** | the stopgap table put back | V: 2 failed |
| M4b | the unchecked-channel form is said | it reads «причина не описана» | V + M: 2 failed |
| M5a | `data-layer` is on the toggles | attribute removed | V: 1 failed |
| M5b | `data-channel-state` is on the chips | attribute removed | V: 1 failed |
| M5c | `not_applicable` channels are drawn | the line removed | V: 2 failed |
| G1 | **the viewer is in the language guard** | `SIDE_WORDS` back to «Sheet A» / «Sheet B» | G: 2 failed (`finds none at all`, `finds no English on a render`) |
| G2 | the guard sees every layer | `data-layer` removed | G: 2 failed (`renders every attribute it claims to read`, `renders every member`) |
| G3 | the guard sees every channel state | `data-channel-state` removed | G: 2 failed (the same two) |
| M6 | the page mounts the block | the line removed | `screens.test.ts`: 1 failed |

Every row was green again after the restore.

## 6. Checks

Run on the committed tree (`git status --short` empty) whose code is the commit `5796f752`; the commit after it adds this report and the task file's handoff. `web/node_modules` was the read-only link to `cmp-seal-c0` (git-ignored, removed before the last commit); the host load average was 3 to 6, so the suite ran with `--maxWorkers=4`.

| Command | Result |
| --- | --- |
| `git diff --check 0e867b12..HEAD` | exit 0, prints nothing |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 (one error in a new test found and fixed in `5796f752`) |
| `npm --prefix web run api:verify` | exit 0: `OK - 148 operations, contract sha256 7c4c95a4…98238` |
| `cd web && npx vitest run --maxWorkers=4` (the **whole** suite, once, at the end) | exit 0: **217 files, 3512 tests passed**, 418 s (3495 before this lane) |
| the language guard with the census, `tests/unit/comparison`, `tests/unit/version-compare`, `tests/unit/styles` (after items 3 and 5) | exit 0: 20 files, 366 passed, 360 s |
| `pytest -q tests/contract` without the three `D-220` files, plus `tests/e2e/test_pc01_journey_conformance.py`, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, `--basetemp` under `/tmp` | exit 0: **1445 passed**, 19283 subtests passed, 150 s (1310 in `tests/contract` and 135 in the journey conformance, as at the base of VC-UI-01) |

`--basetemp` must be outside the repository: with `$PWD/.pytest-tmp` 26 tests of `tests/contract/test_alpha_acceptance_command.py` and `fixtures_comparison/test_cmp_fixtures_realistic_a1.py` fail by design, because they refuse an evidence or output directory inside the repository (`--evidence-dir разрешён только внутри .local/manual-alpha или /tmp`, `the sheet is never committed`). That run was repeated with the directory in `/tmp`; it is the second that is quoted.

## 7. Instructions for the integrator

1. **Merge position:** after `CMP-VC-UI-01` (already in the base), beside the C2 seal. The hotspot is the language guard (section 4 item 3); a conflict there is two appended arrays.
2. The wiring files are untouched: no route, registry, manifest, census rule or generated client changed. The journey manifest (`tests/e2e/pc01/journey/manifest.json`, not a path of this lane) does not list `getComparisonQueueSummary` among the calls of the route `queue`; the block already made that call from the same page through the slot (VC-UI-01), the conformance test passes unchanged, and whether the manifest should name the call is the journey owner's to decide.
3. `git diff --name-only 0e867b12..HEAD` lists only the paths of the task file's «Allowed paths» (section 8).
4. No flag, no migration, no dependency. A revert restores the guesses of VC-UI-01.

## 8. Forbidden hotspots

`git diff --name-only 0e867b12..HEAD -- contracts db src pyproject.toml uv.lock docs/program/P02_LOCK.json web/package.json web/package-lock.json web/FRONTEND_LOCK.json web/openapi web/src/shared web/src/app web/src/_app infra Makefile tests docs/program/CURRENT_STATE.md` prints nothing. Every changed file is under `web/src/entities/version-series`, `web/src/widgets/{version-series,comparison-viewer,execution-queue}`, `web/src/_pages/queue`, `web/tests`, or is one of the two documents of the lane.
