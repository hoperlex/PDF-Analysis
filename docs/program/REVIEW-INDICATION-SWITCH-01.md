# REVIEW-INDICATION-SWITCH-01 — one switch for the two «no human reviewed this» indications of the beta

Lane S1c of wave PW5 (part (c) of `SMALL-HARDENING-02`, `docs/program/dispatch/PRODUCTION-WAVE-PW5.md` section 4). Base `05f4584d` (`integration/ar-close-1026`), branch `agent/review-indication-switch-01`. Task file: [`tasks/REVIEW-INDICATION-SWITCH-01.md`](tasks/REVIEW-INDICATION-SWITCH-01.md) (premises P-01 to P-11). Rulings: `R-146ba` (the owner's poll of 2026-10-27), accepted risks `A-10` and `A-11` (`PRODUCTION-READINESS-PLAN-01.md`).

## Result

* **One switch.** `web/src/shared/config/review-indication.ts` exports `SHOW_REVIEW_INDICATION`, default `false` (the beta), re-exported by `web/src/shared/config/index.ts`. It is read, at the moment a string is built, by five presentation owners (list below). To restore the wording: set it to `true` and change the first case of `web/tests/unit/review-indication/review-indication-default.test.ts` in the same commit (that test names the beta default and goes red on purpose). Nothing else changes: with `true` the markup of every affected screen is byte-identical to the base (measured, see «Byte identity»).
* **OFF (the beta).** The profile status `reviewed` shows the contract word «проверен» (no claim about who). The AR v3 result views drop the wording that a citation is provisional and waits for the expert.
* **Stale sentence fixed.** `run-progress.tsx` said «Канонические находки здесь не публикуются.» for every published AR v3 Run. For a Run whose reading reports at least one published finding it now says «Находки с [предварительными ]нормативными ссылками опубликованы; решение по каждой записывает эксперт. Числовой или правовой вывод не утверждён.» (the wording `AR-V3-DECISIONS-01` proposed, bracketed words behind the switch); a Run that published none, or whose count the server did not report, keeps the old sentence.
* **Release note.** `release-notes/0.9.0.json` is revision 2 and no longer says that a screen shows the profile label (details below).

## The gated strings

Lines are those of the final tree. `ON` is what the base printed (and what a `true` switch still prints); `OFF` is the beta.

| Where | ON | OFF |
| --- | --- | --- |
| `entities/analysis-profile/model/presentation.ts:23-25` (`reviewed`) | рабочая версия, проверка человеком не проводилась | проверен |
| `widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:41` | Предварительный разбор доступен | Разбор доступен |
| `…/ar-v3-beta-review.tsx:47` | Предварительная ссылка | Ссылка на норму |
| `…/ar-v3-beta-review.tsx:67-71` | **Только предварительные ссылки.** Каждая тема и цитата требует проверки эксперта. Числовой или правовой вывод здесь не утверждён. | Числовой или правовой вывод здесь не утверждён. |
| `…/ar-v3-beta-review.tsx:76` | `<тема> — <режим>; требует проверки эксперта.` | `<тема> — <режим>.` |
| `…/ar-v3-beta-review.tsx:82` | Предварительные цитаты | Цитаты |
| `…/ar-v3-beta-review.tsx:83` | Предварительных цитат нет. | Цитат нет. |
| `…/ar-v3-beta-review.tsx:87` | Предложение N; требуется проверка эксперта. | Предложение N. |
| `…/ar-v3-beta-review.tsx:125-129` | …шесть прогонов и только предварительные нормативные ссылки. | …шесть прогонов и нормативные ссылки. |
| `widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx:36-42` | Предварительная ссылка — требуется проверка эксперта / Только контекст — требуется проверка эксперта | Ссылка на норму / Только контекст |
| `…/ar-v3-beta-status.tsx:49` | АР v3: предварительная карта норм | АР v3: карта норм |
| `…/ar-v3-beta-status.tsx:56-60` | Тем: 22; предварительные ссылки: 14; только контекст: 8. Все пункты требуют проверки эксперта. | Тем: 22; ссылки на нормы: 14; только контекст: 8. |
| `features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx:65` | …результат — предварительные цитаты для проверки экспертом, без числовых выводов. | …результат — нормативные цитаты, без числовых выводов. |
| `widgets/run-progress/ui/run-progress.tsx:158` | Прогон завершён. Предварительный нормативный разбор АР v3 сохранён. | Прогон завершён. Нормативный разбор АР v3 сохранён. |
| `…/run-progress.tsx:135-139` (count 0 or not reported) | Канонические находки здесь не публикуются. Каждая тема и цитата требует проверки эксперта; числовой или правовой вывод не утверждён. | Канонические находки здесь не публикуются. Числовой или правовой вывод не утверждён. |
| `…/run-progress.tsx:128-133` (count above 0; new) | Находки с предварительными нормативными ссылками опубликованы; решение по каждой записывает эксперт. Числовой или правовой вывод не утверждён. | Находки с нормативными ссылками опубликованы; решение по каждой записывает эксперт. Числовой или правовой вывод не утверждён. |
| `…/run-progress.tsx:177` (partial) | Предварительный нормативный разбор АР v3 завершился частично. Полный проверенный результат не подтверждён. | Нормативный разбор АР v3 завершился частично. Полный проверенный результат не подтверждён. |
| `…/run-progress.tsx:178` (partial) | Канонические находки не публикуются; требуется проверка эксперта. | Канонические находки не публикуются. |
| `…/run-progress.tsx:435` (box title) | Предварительный разбор АР v3 | Разбор АР v3 |

## What the switch does not govern, and why

| String | Why it stays |
| --- | --- |
| «Сводка подготовлена моделью, проверка человеком не проводилась» (server data above the comparison summary) and «…проверка человеком не проводится.» (`entities/version-comparison/ui/comparison-summary.tsx:101`) | The integrator's rule: it separates model text from document facts (`AGENTS.md` section 4). Forbidden path. |
| `ATTESTATION_SENTENCE` (`widgets/ar-v3-beta-pack/model/pack-presentation.ts`) | The attestation record of the sealed pack: who prepared it and that the system does not check it. Integrator's rule. |
| «Формулировка модели, не решение эксперта.», «Решение записывает эксперт.», «Находки и решения эксперта», «Важность, решённая экспертом», «Предложение модели о важности», «…решение по каждой записывает эксперт» | Statements that a verdict is the expert's own decision, or whose text it is. |
| «черновик, требует экспертной проверки» (`presentation.ts:16`) | The owner removed the label of a reviewed profile, not the label of a draft. |
| «Числовой или правовой вывод … не утверждён», «Проверка сохранённого разбора отказала», «Полный проверенный результат не подтверждён», «Ссылки появятся только после проверенного сохранения результата» | They state the numeric limit or the system's own integrity check and completeness, not that a person did not review. |

Found and **not** changed (outside the allowed paths or outside the owner decision; see «Integration notes»): `shared/ui/stage-label.ts:66` «Предварительная проверка нормативных ссылок АР v3» (the name of a stage), «проверенный экспертом набор» in `AR_START_NOTE` and in `features/classify-version/ui/classify-version-form.tsx:211`, and the live journey manifest.

## Release note: items as they now read

`release-notes/0.9.0.json`: `revision` 1 → 2, date (2026-10-28) and title unchanged; every item stays under 400 characters (largest 398, the item that this lane did not touch).

* **Item 3** (`/analysis-settings`, 386 characters). Before: «…версия 1.1.0 или 1.2.0 и пометка «рабочая версия, проверка человеком не проводилась» вместо черновика. …Ни человек, ни реальные документы эти инструкции для модели не проверяли.» After: «У профилей анализа 14 разделов, кроме АР, версия 1.1.0 или 1.2.0 и состояние «проверен» вместо «черновик, требует экспертной проверки». Для 12 разделов добавлены сверки внутри документа, например итога таблицы с суммой строк: о расхождении модель просят сообщить в категории «Внутреннее противоречие» с цитатами. Ни человек, ни реальные документы эти инструкции для модели не проверяли.» The last sentence is kept, as the brief allows: it is a statement about the instructions, not about a label on a screen. **A risk to confirm:** the release note is itself a screen, and `A-10` says no screen says that a profile was not reviewed by a human; the owner or the integrator may want that sentence out too.
* **Item 6** (`/projects/[project_uid]/versions/[version_uid]`, 315 characters). It contains no profile label. It did claim «кнопка есть, если установлен проверенный экспертом набор», which `A-11` makes unsafe (the pack is attested as prepared by the AI integrator, no subject-matter expert took part), and what the code tests is only that a pack is installed. Now: «…Анализ АР идёт только шестью проверками АР v3: кнопка есть, если на сервере установлен пакет норм АР v3, иначе экран объясняет, почему запуска нет. …» The screens' own sentence («проверенный экспертом набор») is not touched (outside the paths); the note simply does not repeat it.
* Item 2 (the summary) is unchanged and still quotes «Сводка подготовлена моделью, проверка человеком не проводилась»: that label is not behind the switch.
* Pins moved: `tests/contract/release_notes/test_release_notes_form.py` (revision map `"0.9.0": 2` and its comment), `docs/program/RELEASES.md`, `docs/program/RELEASE-0-9-0-DEV-01.md` (result paragraph, claim rows 3 and 6, disposition row 1, line numbers of the cited tests). `tests/integration/releases/test_release_loader.py` pins only the set of versions, not the revision of `0.9.0`, so it needed no edit; it was run (59 passed). New: `tests/contract/release_notes/test_note_follows_review_switch.py` reads the web constant and the current note together and fails if the note quotes the switched wording while the constant is `false`.

## Byte identity with the switch on

A scratch test (not committed) rendered 12 states with the switch on — a reviewed and a draft profile row, the beta source preview, the group review for an expert and for an administrator, the group lookup, the idle start control, a published AR v3 Run with count 0 and with no count, a partial, a queued and a failed AR v3 Run, and an ordinary published Run — once on the base (with `presentation.ts` temporarily restored to the base) and once on this tree with the constant mocked `true`: **12 of 12 markups are byte-identical.** The one deliberate difference is the published AR v3 Run with a count above 0, which the base printed with the stale sentence.

## Files

* **New (6):** `web/src/shared/config/review-indication.ts`; `web/tests/unit/review-indication/{surfaces.ts,review-indication-states.test.ts,review-indication-default.test.ts}`; `web/tests/guards/review-indication.guard.test.ts`; `tests/contract/release_notes/test_note_follows_review_switch.py` (the two docs of the lane are listed under «Release and docs»).
* **Web source (7):** `web/src/shared/config/index.ts`, `entities/analysis-profile/model/presentation.ts`, `widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx`, `widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx`, `widgets/run-progress/ui/run-progress.tsx`, `features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx`, `widgets/ar-v3-beta-pack/model/pack-presentation.ts` (a comment only: this sentence is not behind the switch).
* **Tests modified (4):** `web/tests/unit/analysis-settings/analysis-settings.test.ts`, `…/ar-v3-group-start-failure.test.ts`, `web/tests/unit/screens/run-progress.test.ts`, `tests/contract/release_notes/test_release_notes_form.py`.
* **Release and docs (4):** `release-notes/0.9.0.json`, `docs/program/RELEASES.md`, `docs/program/RELEASE-0-9-0-DEV-01.md`, `docs/program/tasks/REVIEW-INDICATION-SWITCH-01.md`.

## Tests

* `review-indication-states.test.ts` (54): for each of the 21 gated strings one case with the switch ON (the base's words) and one with it OFF (the neutral wording, and none of the old); three cases on the label functions (`analysisProfileStatusLabel`, `ANALYSIS_PROFILE_STATUS_LABELS`); and, in both states, the comparison-summary label and its confirmation sentence, the pack attestation, the expert statements and the integrity wording. The constant is replaced there by a getter the file sets, so the cases do not depend on the beta default.
* `review-indication-default.test.ts` (19): the real constant is `false` (the one test that names the default); the shipped profile label; eleven shipped screens carry none of the removed wording; what stays; the new findings sentence.
* `review-indication.guard.test.ts` (19): parses every file of the six owned trees with the TypeScript compiler; every string literal, template part, JSX text and JSX attribute that reads as «предварительн…», «проверк… эксперт/человек…» or «экспертн… проверк…» must be inside the branch an `?:`, `if` or `&&` on exactly `SHOW_REVIEW_INDICATION` (or its negation) selects, or be in a two-entry allow-list with reasons (the draft label, the pack attestation). Also: no file of the never-gated list names the switch; the switch is declared once, named only by its seven owners, not read from the environment or a second flag. Nine self-tests show it fails on a bare string, bare JSX, an attribute, a template, a wrong condition, the wrong branch, a local copy and a missing import.
* `test_note_follows_review_switch.py` (3).

### Before / after of modified tests

No assertion was removed or loosened. The three web files assert the screens as they read with the switch ON (the only state in which their text exists), so each pins the switch ON by a `vi.mock('@/shared/config/review-indication', () => ({ SHOW_REVIEW_INDICATION: true }))` after the vitest import and a comment, and every assertion stays as it was. The beta default (OFF) of the same strings is asserted by the new files.

| Test | Before | After |
| --- | --- | --- |
| `analysis-settings.test.ts` (all 23 cases) | rendered with the base tree's only wording; `labels a reviewed profile and shows its own version` asserted `проверка человеком не проводилась`; the beta source preview asserted `предварительные ссылки: 14; только контекст: 8` and `Только контекст — требуется проверка эксперта` | the same assertions, with the switch pinned ON; without the pin three of them (the reviewed label and the two preview cases) are red under the OFF default |
| `ar-v3-group-start-failure.test.ts` (26) | the idle control asserts `…результат — предварительные цитаты для проверки экспертом, без числовых выводов.` | the same, switch pinned ON (one case red under OFF) |
| `run-progress.test.ts` (84) | `keeps a published v3 preliminary review separate from canonical findings` asserts `Каждая тема и цитата требует проверки эксперта` | the same, switch pinned ON (one case red under OFF) |
| `test_release_notes_form.py` | revision map `"0.9.0": 1` | `"0.9.0": 2`, comment extended |

## Mutations

Method: `/tmp/…/scratchpad/mutate.py` applies one text edit, runs the six web files (the two new unit files, the guard and the three pinned files, 225 tests) and restores the file with `git checkout`; `git status --short` was empty after each. «red» is the number of failing tests.

| id | mutation | red |
| --- | --- | ---: |
| M1 | the default flipped to `true` | 14 |
| M2 (×5, per file) | the constant read nowhere in `presentation.ts` / the review widget / the status widget / `run-progress.tsx` / the start control (replaced by `false`) | 6 / 11 / 9 / 11 / 5 |
| M2:all | the same in all five files | 30 |
| M3 (×5, per file) | the constant ignored, always `true`, in the same five files | 6 / 14 / 8 / 17 / 5 |
| M3:all | the same in all five files | 38 |
| M4 | one string ungated (the heading «Цитаты» replaced by the ON text) | 4 |
| M5 | a new bare «Требуется проверка эксперта.» added to the status widget | 2 |
| M6 | the comparison-summary label put behind the switch | 4 |
| M7 | the pack attestation put behind the switch | 5 |
| M8 | «Формулировка модели, не решение эксперта.» put behind the switch | 4 |
| M9 | the draft label put behind the switch | 2 |
| M10 | the findings sentence never chosen | 6 |
| M11 | a count of zero chooses the findings sentence | 4 |
| M12 | an unreported count chooses the findings sentence | 2 |
| M13 | the neutral word becomes «проверен экспертом» | 3 |
| M14 | a second source of the switch (`process.env.REVIEW_INDICATION`) | 1 |
| M15 | a local copy of the constant instead of the import | 5 |
| M16 | the index no longer re-exports it | 31 |
| M17 | the stale sentence back for a Run that published findings | 4 |
| N1 | note item 3 quotes the profile label again | 1 (`test_the_current_note_quotes_nothing_the_switch_hides_while_it_is_off`) |
| N2 | note revision 2 → 1 | 1 (`test_authored_shape_and_form`) |
| N3 | revision pin 2 → 1 | 1 (the same) |
| N4 | an item above 400 characters | 1 (the same) |
| N5 | the declaration of the constant in another form | 2 |
| N6 | note item 3 says «требует проверки эксперта» | 2 |

Per string: under M2:all the ON case of every one of the 21 gated strings is red, and under M3:all the OFF case of every one is red (checked against the failing test names in the JSON reports; the 22nd entry of the table is the fixture topic C05, not a string).

## Commands and counts

All from `.local/worktrees/review-indication-switch-01`; `web/node_modules` is a symlink to `gate-night`'s; `.env` is a copy of `ar-close-1026/.env` (untracked, ignored); no docker, no network, no push, no tag.

| Command | Result |
| --- | --- |
| `npx vitest run` in `web/` (whole suite, once, committed tree `2527e9c1`) | **206 files, 3,187 passed** (base: 203 files, 3,095), 201 s |
| `npx vitest run tests/unit/review-indication tests/guards/review-indication.guard.test.ts` | 3 files, 92 passed |
| `npx tsc --noEmit`; `npx eslint --quiet .` in `web/` | exit 0; exit 0 |
| `pytest tests/contract/release_notes` | 26 passed (23 before + 3 new) |
| `pytest tests/integration/releases` (DATABASE_URL from the copied `.env`; the suite makes and drops its own clone of a template; the three `a1_tpl_*` template databases on the stand belong to other runs and were left alone) | 59 passed |
| `pytest tests/e2e/test_pc01_journey_conformance.py` (static) | 135 passed — **green although the live journey will fail, see the first integration note** |
| `web` `tests/unit/release-notes tests/unit/release` | 5 files, 18 passed |
| `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py`, `test_surface_counts_in_prose.py`, `git diff --check`, the governance one-liner | see the hand-back (run on the final commit) |

## Integration notes

1. **The live journey breaks; only the gate sees it.** `tests/e2e/pc01/journey/manifest.json` lines 2184 and 2188 expect `рабочая версия, проверка человеком не проводилась` on `/analysis-settings` (the rows `tr[data-section="PB"][data-profile="reviewed"]` and `tr[data-profile="reviewed"]`). With the switch off the rows say «проверен». `tests/e2e/**` is outside this lane's paths, so the two `text_contains` values must become `проверен` under the integrator (the static conformance test above is green either way, because the old sentence still exists in the source as the ON branch).
2. **A string outside the lane's paths:** `web/src/shared/ui/stage-label.ts:66` names the stage «Предварительная проверка нормативных ссылок АР v3» (shown in the stage table of an AR v3 Run). It is a stage name, not a statement about review, and the file is outside the allowed paths; not changed. Decide whether the owner's «предварительная цитата» covers it.
3. **A claim in the other direction (`A-11`).** `AR_START_NOTE` (`entities/analysis-profile/model/presentation.ts`) and `classify-version-form.tsx:211` say the six checks start «когда на сервере установлен проверенный экспертом набор», while the attestation of the pack will say that no subject-matter expert took part. That is not an indication that no one reviewed, so it is not behind the switch and was not changed here; the note no longer repeats it (item 6).
4. **The release note is a screen.** Item 3 still says «Ни человек, ни реальные документы эти инструкции для модели не проверяли» (kept on the brief's instruction). See the risk under item 3 above.
5. **`data-review-only="ar-v3-beta"`** stays on the outcome block of a published AR v3 Run, also when it published findings. It is an attribute no one reads but the existing test; the name is now slightly off.
6. **The box «Разбор»** on the run screen still says «Здесь нет канонических находок для разбора или принятия решения» next to a link to the group review. For a Run that published findings the decisions are taken in the group review, so the sentence is about this screen and was left as it was; the title of the box is behind the switch.
7. **The pins of the switch:** `web/tests/unit/review-indication/review-indication-default.test.ts` (first case), `tests/contract/release_notes/test_note_follows_review_switch.py` (reads the declaration `export const SHOW_REVIEW_INDICATION = false as boolean;` by regular expression: keep that form), the guard (`MAY_NAME_THE_SWITCH`, `ALLOWED_UNGATED`, `NEVER_GATED`). A new string of this kind goes behind the constant; the guard fails otherwise.
8. **Restoring the wording** is one value (`true`), one test (the default pin), and the manifest lines of note 1 back. The release note then may quote the label again (the contract test lets it).

## Limits

* The guard reads wording, not meaning: a sentence that says the same in other words passes it. The word pattern is written out in the test.
* The static markup of the 12 states was compared; no browser, no live journey, no stand.
* The scan of strings was by wording over the six trees named in the brief plus a repository-wide search of `web/src`; a differently worded indication elsewhere would not have been found (note 2 and 3 are the two found).
* The whole web suite was run once, on the committed tree, before this document was written; the document adds no web file.

## Forbidden paths are untouched

`git diff --name-only 05f4584d..HEAD` lists only the files above. None is under `contracts/`, `src/`, `db/migrations/`, `infra/`, `tests/e2e/`, `web/src/entities/version-comparison/`, `web/src/shared/ui/`, a root dependency or lock file, a composition root or global styles. The commands that prove it (all print nothing):

```
git diff --name-only 05f4584d..HEAD | grep -E '^(contracts/|src/|db/migrations/|infra/|tests/e2e/|web/src/entities/version-comparison/|web/src/shared/ui/|web/package|web/FRONTEND_LOCK|uv\.lock|pyproject\.toml|Makefile)'
git diff --name-only 05f4584d..HEAD | grep '^web/src/' | grep -v -E '^web/src/(shared/config|entities/analysis-profile|widgets/(ar-v3-beta-review|ar-v3-beta-pack|ar-v3-beta-status|run-progress)|features/start-ar-v3-group)/'
```
