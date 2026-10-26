# WEB-SECTION-COPY-01 — the dashboard sections panel and the section catalogue say what is true after W59 and PROD-11

Task: [`tasks/WEB-SECTION-COPY-01.md`](tasks/WEB-SECTION-COPY-01.md) (premise P-01 to P-12 captured before the first edit). Wave `PW4`, lane `WC`, branch `agent/web-section-copy-01`, base `6075df889beef40084d337f03d2a072349fc9620` (tip of `integration/ar-close-1026`). Source of the finding: `ROADMAP-GAP-2026-10-27.md`, workflow step 16. Nothing was pushed, merged or tagged. The live journey and the full gate are not part of this lane (`R-135`).

## What a user sees now

| Screen | Before | Now |
|---|---|---|
| Dashboard, panel «Разбивка по разделам» | A sentence that blamed the upload form for the row «Без раздела» (the form «offers no section», so a document sent through it «stays without one»). | A sentence that says what the server counts: a document stands in the section an expert confirmed for its current version; until then it stands in «Без раздела»; the expert confirms on the version screen. The rows and their numbers are unchanged. |

The server counts by the expert-confirmed classification of the current version and never reads the legacy document label (P-04). The old sentence was therefore wrong twice: the upload form is not the cause, and a section is not «named at upload». Since `W59-SECTION-UI-01` a document sent through the form leaves «Без раздела» as soon as an expert confirms its section.

## The exact old and new strings

### 1. The panel sentence (`web/src/widgets/dashboard/ui/sections-panel.tsx`)

Old (the paragraph, as it was in the source, `am-state__correlation` class unchanged):

```text
Раздел документа сохраняется и проверяется на сервере, когда его называют при
загрузке. Форма загрузки в этом продукте раздел не предлагает, поэтому документ,
отправленный через неё, остаётся без раздела — вот откуда строка «Без раздела» ниже,
а не из пропуска в подсчёте.
```

New:

```text
Документ учитывается в том разделе, который эксперт подтвердил для его текущей версии.
Пока раздел не подтверждён, документ попадает в строку «Без раздела». Раздел
подтверждает эксперт на экране версии.
```

The new sentence is Russian, plain, names no operation, field or identifier, and has no digit (the dashboard's «no invented number» render test would fail on one; P-09). The wording follows the project structure's own sentence (`widgets/project-sections`): «Документ стоит в разделе, который эксперт подтвердил для его текущей версии на экране версии».

### 2. The registry field (`web/src/entities/project/model/section.ts`)

| | Old | New |
|---|---|---|
| Field | `readonly analysed: boolean;` («the section the analysis is built for»: `true` for АР, `false` for the other fourteen) | `readonly analysedBy: SectionAnalysis;` with `export type SectionAnalysis = 'text_profile' \| 'six_run_group';` |
| АР | `analysed: true` | `analysedBy: 'six_run_group'` (analysed by the group of six AR v3 checks; no text profile) |
| the other fourteen (АИ, КМ, КЖ, ОВ, ЭОМ, ВК, ПТ, ПБ, СС, ИТП, ГП, ТХ, ПОС, ПЗ) | `analysed: false` | `analysedBy: 'text_profile'` |
| Attribute on each panel row | `data-analysed={section.analysed}` | `data-analysed-by={section.analysedBy}` |
| Comment of `ANALYSED_SECTION_CODE` | «The section the analysis is written for, and the one the upload rule names.» | «The section a section picker starts on: the first of the catalogue, АР. It is a default choice and not a statement that only this section is analysed (every section is, see `ProjectSection.analysedBy`). The name is kept because `widgets/section-specification` imports it.» The export and its value `'AR'` are unchanged. |

`SectionAnalysis` is also exported from `@/entities/project`. Nothing renders `analysedBy` as text; the product already says «группой из шести проверок АР v3» where it matters (`entities/analysis-profile`, the version classification panel), and «рабочая версия, проверка человеком не проводилась» stays as `presentation.ts` has it.

### 3. Comments that described the removed behaviour

- `section.ts` header: the paragraph «What is still true, and is the reason a section still reads as navigation here» (every document the product accepts is unclassified; the restriction to АР lives in the analysis prompt) and the paragraph that left the section picker «out of scope (`D-107`)» are replaced by «What a section is here now» (an expert confirms it on the version screen) and «How a section is analysed» (two routes). The `W46-WIRE` paragraph is kept as history.
- `sections-panel.tsx` header: the paragraph «What is true instead» (the form offers a file and a title and nothing else) is replaced by the account of what the numbers are; «fourteen» became «fifteen» where the header meant the sections.
- `section-breakdown.ts` comments: «fourteen frozen codes» and the quotation of the generated type are brought to the fifteen the contract type states («Every one of the fifteen current codes is present even at `document_count: 0`»). The surface-count prose guard reads a number followed directly by the word for a code as the error-catalogue size, so the comment says «each of the fifteen sections» (this guard went red once on the first wording and was fixed in the next commit).

## Files

Changed:

- `web/src/widgets/dashboard/ui/sections-panel.tsx` — the sentence, `data-analysed-by`, header comment
- `web/src/widgets/dashboard/model/section-breakdown.ts` — comments only
- `web/src/entities/project/model/section.ts` — `SectionAnalysis`, `analysedBy`, the comment of `ANALYSED_SECTION_CODE`, header comment
- `web/src/entities/project/index.ts` — exports the `SectionAnalysis` type
- `web/tests/unit/projects/project-sections.test.ts` — the last `describe` rewritten (below)
- `web/tests/unit/widgets/dashboard.test.ts` — four cases added (below)

Added: `docs/program/tasks/WEB-SECTION-COPY-01.md`, this report.

Not edited, read and run: `web/tests/guards/rendered-language.guard.test.ts`, `web/tests/unit/projects/section-catalogue.test.ts`, the section picker (`widgets/section-specification`; it carries no copy about «analysed»).

## Tests: before and after, per test

No assertion of an existing test was removed or loosened. The one test file whose assertions changed is `project-sections.test.ts`, because the field it pinned is gone.

### `web/tests/unit/projects/project-sections.test.ts` (8 tests before, 9 after)

Six tests are untouched: the three of `the section set is legacy's fourteen plus PS` and the three of `nothing a reviewer reads is Latin` (the file's header and the first two `describe` blocks are byte-identical). Two tests are replaced by three. Imports gained `readdirSync`, `join`, and `REPO_ROOT`, `readJson` from `../../guards/lib/repo` (the same helpers `section-catalogue.test.ts` uses to read a backend file).

| Before (`describe('exactly one section is the one the analysis is built for')`) | After (`describe('every section is analysed by one of two routes, and the registry says which')`) |
|---|---|
| `marks AR and nothing else`: `PROJECT_SECTIONS.filter(s => s.analysed)` equals `[ANALYSED_SECTION_CODE]`; `ANALYSED_SECTION_CODE` is `'AR'`. | `sends АР to the group of six checks and the fourteen others to their text profile`: the `six_run_group` codes equal `['AR']`; the `text_profile` codes number fourteen and do not contain `'AR'`; the two groups together are all `PROJECT_SECTIONS`. The old fact (АР is the only section on its own route) is kept; the fourteen are now asserted too. |
| (none) | `holds the text-profile sections to the packages the server loads, in both directions` (new): the sorted `text_profile` codes equal the sorted `section_code` of every `src/auditmanager/analysis/text/profiles/*/profile.json`, and the packages do not contain `'AR'` (the server refuses such a package). |
| `keeps the analysed code in the registry, so the screen's default is a real section`: `findProjectSection(ANALYSED_SECTION_CODE)?.analysed` is `true`. | `keeps the section pickers' default a real section`: `ANALYSED_SECTION_CODE` is `'AR'` (moved here from the first old test) and `findProjectSection(ANALYSED_SECTION_CODE)` matches `{ code: 'AR', analysedBy: 'six_run_group' }` (fails if the code is not in the registry). |

### `web/tests/unit/widgets/dashboard.test.ts` (19 tests before, 23 after)

The 19 existing cases are untouched, including `always shows the unclassified section row` (`Без раздела: 16`) and `every section row carries its own section's count`. Four cases are added in `describe('the sections panel says what the count is, not where the unclassified row comes from')`; nothing pinned the old sentence, so none of them could have failed before the repair, and each fails against it (M1):

1. `says a document stands in the section an expert confirmed for its current version`: the panel's visible text contains the three sentences of the new copy.
2. `does not blame the upload form for the unclassified row`: the panel text matches none of `загрузк`, `загруж`, `отправленн`, `Форма`, `при загрузке`.
3. `writes no digit in its sentence, so every number on the panel is a count of the server`: the `<p>` exists and its visible text has no digit. The global «renders exactly the fixture's numbers» test is blind to a figure that happens to be a fixture count (with «15» in the sentence it stays green, because the fixture counts run 1 to 15); this case is not.
4. `marks each row with the route that analyses its section`: the АР row carries `data-analysed-by="six_run_group"`, each of the other fourteen `text_profile` (literals, not read from the registry), the unclassified row carries none, and the removed `data-analysed=` is absent.

## Mutation table

Each mutation was applied to the committed tree, `npx vitest run tests/unit/widgets/dashboard.test.ts tests/unit/projects/project-sections.test.ts` run (32 tests when green), and the tree restored with `git checkout` (`git status --short` empty after each).

| # | Mutation | Red (file :: case) |
|---|---|---|
| M1 | the old paragraph restored in `sections-panel.tsx` | `dashboard` :: `says a document stands …`; `does not blame the upload form …` (2 red) |
| M2 | `Всего разделов: 99.` appended to the new paragraph | `dashboard` :: `renders exactly the fixture's numbers, nothing invented`; `never renders absent spend as 0 labelled measured`; `writes no digit in its sentence …` (3 red) |
| M3 | `data-analysed-by={…}` renamed back to `data-analysed={…}` | `dashboard` :: `marks each row with the route …` (1 red) |
| M4 | the `<p>` deleted | `dashboard` :: `says a document stands …`; `writes no digit … ` (the paragraph is missing) (2 red) |
| M5 | КЖ marked `six_run_group` in the registry | `project-sections` :: `sends АР … and the fourteen others …`; `holds the text-profile sections to the packages …`; `dashboard` :: `marks each row …` (3 red) |
| M6 | АР marked `text_profile` in the registry | `project-sections` :: all three cases of the new `describe`; `dashboard` :: `marks each row …` (4 red) |
| M7 | `profiles/pb/profile.json`: `"section_code": "PB"` changed to `"ZZ"` | `project-sections` :: `holds the text-profile sections to the packages …` (1 red) |
| M8 | a new package `profiles/zz/profile.json` (`section_code` `ZZ`) added, catalogue unchanged | the same case (1 red) |
| M9 | the package `profiles/pb/` moved away, catalogue unchanged | the same case (1 red) |
| M10 | `ANALYSED_SECTION_CODE` changed to `'KJ'` | `project-sections` :: `keeps the section pickers' default a real section` (1 red) |

The M2 row records a correction made while running the table: the first mutation used the figure 15, which is a count in the dashboard fixture, so the global digit test stayed green and only the new local case caught it. The mutation was repeated with a figure the fixture does not contain (99), and the test file's note says so.

## Commands and counts (tip of the lane; `web/node_modules` is a symlink to the gate-night worktree's, no `npm ci`)

| Command | Result |
|---|---|
| baseline, before any edit: `cd web && npx vitest run tests/unit/widgets/dashboard.test.ts tests/unit/projects/project-sections.test.ts tests/unit/projects/section-catalogue.test.ts tests/guards/rendered-language.guard.test.ts` | 4 files, 61 passed (guard 26, dashboard 19, project-sections 8, section-catalogue 8) |
| same four files after | 4 files, 66 passed (26, 23, 9, 8) |
| `npx vitest run tests/unit/widgets/dashboard.test.ts tests/unit/projects tests/guards/rendered-language.guard.test.ts` | 10 files, 173 passed |
| `npx vitest run tests/unit/widgets tests/unit/projects tests/guards` | 33 files, 465 passed |
| `npx vitest run tests/unit/styles tests/unit/screens tests/unit/sections` (the suites that render the dashboard in the contrast census and the screen matrix) | 28 files, 507 passed |
| `npx tsc --noEmit` | exit 0, no output |
| `npx eslint src/widgets/dashboard src/entities/project tests/unit/widgets/dashboard.test.ts tests/unit/projects/project-sections.test.ts` | exit 0, no output |
| `pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/e2e/test_pc01_journey_conformance.py` (committed tree, no stack) | 240 passed. A first run had 1 failed (`test_the_api_prose_states_the_surface_this_document_declares`: a comment in `section-breakdown.ts` put a number directly before the word for a code and was read as the error-catalogue size); fixed, rerun green |
| the governance one-liner for `docs/program/tasks/WEB-SECTION-COPY-01.md` | `[]` |
| `scripts/task_handoff.py` `read_task` on the task file | parses: one base commit, six allowed paths |
| `git diff --check` | exit 0 |

Deferred under `R-135` and the lane rules: the full frontend suite, `npm --prefix web run e2e:pc01`, the browser look at the dashboard, `make gate`. The journey step `dashboard-sections-panel` reads `[data-panel="per-section-breakdown"] li[data-section="PB"] strong`; those handles are unchanged and `test_pc01_journey_conformance.py` is green, but the step has not been run in a browser.

## Other stale places found (listed, not edited: not this lane's paths)

1. **`uploadDocument` operation text — the contract owner's.** `contracts/api/v1/openapi.json:334`, mirrored in `web/openapi/openapi.json:334` and the generated client: «The analysis is built for AR (architectural solutions) text and is applied to any uploaded document; a stated `section` is stored and counted but neither selects nor refuses the analysis (`D-110`).» After `W59` the confirmed section selects the profile and `PROD-11` removed the АР text path. `OPT-PROJECT-ALL-SECTIONS-01` reseals the contract in this wave and the brief gives it this repair.
2. **`getDashboardSummary` operation text — the contract owner's.** The same file says «every one of the fourteen frozen sections is present even with no documents»; the type's own text and the server say fifteen. Same reseal.
3. **Optimisation screens and entity, АР-only copy — `OPT-PROJECT-ALL-SECTIONS-01`.** `web/src/widgets/specification-prices/ui/specification-prices-section.tsx:56` and `web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx:78` («В проекте нет комплектов раздела АР»), `optimisation-proposals.tsx:254` («… из вендор-листа раздела АР …»), `web/src/entities/optimisation-proposal/model/failure.ts:21` («… предложения строятся только для АР.»). They stay true until that lane removes the guard.
4. **Refusal sentence that promises a profile for АР — `entities/audit-run` and `shared/api`.** `web/src/entities/audit-run/model/routing-refusal.ts:38-45` and `web/src/shared/api/catalog-message.ts:133-136`: «… прогон станет возможен, когда профиль раздела появится.» True for a section whose profile is missing; false for АР, which never gets a text profile (`profile_registry.py`). `run-list.tsx` draws the six-check control instead for an АР version whose section is known, so the sentence can reach a user only through a press made before the version is read. A candidate for a small copy lane.
5. **Documents that mention the removed field, not edited.** `docs/program/tasks/BETA-PB-PROFILE-TRUTH-01.md:82` («No change to `ProjectSection.analysed`: it is a legacy AR-only marker»; a historical record, correct for its time); `tests/e2e/pc01/journey/manifest.json:677` («the analysed section (АР)», about the section picker's default, which is still АР).
6. **Cosmetic, left:** test titles in `dashboard.test.ts` (`renders every one of the fourteen frozen sections`, `never folded into the fourteen`) and the comments of `widgets/project-sections` and `_pages/project-detail` still say «fourteen» for the set that is now fifteen. No user sees them and renaming a test title is churn outside the brief.

## Integration notes

- **Compatibility.** `PROJECT_SECTIONS[i].analysed` no longer exists. P-02 shows no reader outside the registry, the panel and the one test, so nothing else changes. A lane merged later that adds a reader of `.analysed` fails `tsc` at the merge and should use `analysedBy`. `ANALYSED_SECTION_CODE` and its value `'AR'` stay, because `widgets/section-specification` imports it as its picker's initial choice.
- **Overlap with the other lanes of `PW4`.** None of this lane's files is in the hotspot of `CH`, `OP`, `G1` to `G3` or `SG`. The registry test reads `section_code` of `src/auditmanager/analysis/text/profiles/*/profile.json`; the section lanes edit the version and the status of those files, not the code, so they do not break it. A lane that adds a fifteenth package would have to give АР a text profile, which the server refuses; the test then fails on purpose.
- **No contract, route, error code, migration or screen was added**, so no set is enumerated anew (`enumerated_set_changed: no`), the surface counts and the frozen lock are unchanged, and `FRONTEND_LOCK.json` is untouched.
- **Rollback.** Revert the lane's commits; there is no flag and no data.
- **For the integrator's registers (not edited here).** Items 1 to 4 above name their owners; items 1 and 2 belong to the reseal of `OPT-PROJECT-ALL-SECTIONS-01`, item 4 has no owner yet.

## Limits

- Not seen in a browser; the panel was rendered through the unit harness (`renderWith`) and the contrast and language census only. The journey was checked statically.
- `analysedBy` records which route analyses a section, not whether a given version can run now. That is the API's answer (`SectionReviewOption.executable`; for АР the checked pack), and no screen is made to claim otherwise.
- The sentence says the expert confirms the section «на экране версии» without naming the panel («Стадия и раздел»), so a rename of that panel does not make it false; the cost is that it does not link to it.
- The registry test reads another tree's files (`src/auditmanager/analysis/text/profiles`), as `section-catalogue.test.ts` already does with `suggestion_patterns.json`. A web checkout without `src/` would fail it, as it already fails that test.

## Forbidden hotspots

`git diff --name-only 6075df88..HEAD` (run on the lane's last commit):

```text
docs/program/WEB-SECTION-COPY-01.md
docs/program/tasks/WEB-SECTION-COPY-01.md
web/src/entities/project/index.ts
web/src/entities/project/model/section.ts
web/src/widgets/dashboard/model/section-breakdown.ts
web/src/widgets/dashboard/ui/sections-panel.tsx
web/tests/unit/projects/project-sections.test.ts
web/tests/unit/widgets/dashboard.test.ts
```

It contains none of `contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `src/**`, `db/**`, `infra/**`, `fixtures/**`, `web/package*.json`, a global style, a composition root, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the rulings or the ADRs. Every path is inside the task's allowed paths.
