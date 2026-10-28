# CMP-DEBT-261 — the comparison-only mark on the five screens that pick a version or a set

Written 2026-10-29 by the Sonnet lane `CMP-DEBT-261` (branch `agent/cmp-debt-261`, base `6db7db23` on `integration/compare-modules`; nothing pushed, merged or tagged). Task file: `docs/program/tasks/CMP-DEBT-261.md`.

A web-only change that closes the check of `D-261`. A document version whose `upload_kind` is `comparison_pdf` (a plain PDF admitted for comparison only, `Q-CMP-5`; it can never start a run) carries the mark of `CMP-VERSION-MARK-01` («Загружено без пакета портала — только для сравнения») on the five screens that pick a version or a set and did not mark it. Where the screen starts work over the chosen set or version the comparison-only one is listed, marked and offered disabled with the reason sentence of the refused start. A version with `portal_bundle`, with no field, or with a value this client does not know is drawn byte for byte as before (compared by tests). The lane reuses `isComparisonOnly`, `ComparisonOnlyMark`, `COMPARISON_ONLY_MARK`, `COMPARISON_ONLY_DETAIL` and `COMPARISON_ONLY_START_NOTE` from `@/entities/document-version` as they are: no new mark, no new colour, no module rule, no new export of the entity.

## 1. Base facts, printed before any edit

Contract `1.10.0`, 131 paths / 148 operations / 432 schemas; head `0039_comparison_core`; base `6db7db23a6d16d36d9763cc3377cd3d6bd425869`. They equal the brief, so the lane went on (task file P-01). The check of the row before the change listed only the entity `document-version` (P-02).

## 2. What each of the five places shows now

| Place | Kind of screen | A comparison-only version |
| --- | --- | --- |
| `widgets/version-comparison` (the «Сравнить с версией» picker and the compared pair) | compares | **Stays chosen and comparable** (comparing is what it is for; no option is disabled). Its `<option>` says «Версия 2 (Загружено без пакета портала — только для сравнения)»; the pair line draws the shared mark badge after the name and classification of each compared version that is comparison-only. |
| `_pages/stage-comparison` (new `ComparisonOnlyNote`) | compares | When the version of the address is comparison-only: the shared mark and `COMPARISON_ONLY_DETAIL` («Это обычный PDF-файл, принятый только для сравнения…») above the comparison, which also says why «Сравнение прогонов» below has nothing to compare. Reads the version through the query the widget under it already makes (one request). Nothing is drawn for any other version or while the version is unread (the widget says loading or why it failed). |
| `widgets/specification-prices` (the «Комплект» chooser) | reads a set | **Listed, marked, disabled.** The `<option>` is `disabled` and says the mark in words; under the select a list names each comparison-only set with the shared badge, then `COMPARISON_ONLY_START_NOTE` once (`aria-describedby` on the select points at it). The default set is the first set that is not comparison-only; nothing is asked of the server for a comparison-only set; with only such sets nothing is selected and no read is made. |
| `widgets/optimisation-proposals` (the «Комплект» chooser and «Запустить проход») | starts a pass | The same chooser. «Запустить проход» is therefore never offered for a comparison-only set (the feature receives only a startable set, and `null` when there is none, which draws its existing disabled button); passes are not read for it. A reader who may not start sees the same read-only sentence as before. |
| `_pages/blocks` (`DocumentChooser`, the document picker) | starts a block read | The row draws the shared badge in its detail block; «Показать блоки» is drawn `disabled` with `aria-describedby` pointing at the one `COMPARISON_ONLY_START_NOTE` paragraph above the list (said once however many rows are comparison-only). The row stays listed. |

`DocumentChooser` was a private function of `blocks-page.tsx`, reachable only by clicking a project row; it is now exported (and re-exported by the slice's `index.ts`) so one static pass can render it, as `VersionBlockViews` was for the tabs. Its three unreachable-state entries in the language guard are unchanged (the lane renders only the loaded list).

How the start-control rule maps: `CMP-VERSION-MARK-01` draws a start disabled with the reason beside it and keeps the version listed and addressable. A `<select>` has no button, so the equivalent is a disabled option (cannot be chosen, so nothing starts, structurally) with the reason beside the select; the blocks picker has real buttons and uses the same disabled-button-with-reason as `ComparisonOnlyStart`.

## 3. Tests

| Check | Result |
| --- | --- |
| `web/tests/unit/comparison-only-pickers/comparison-only-pickers.test.ts` (new) | 48 passed |
| `tests/unit/styles` (the contrast census with `screens.ts`) + the new file, run alone | 7 files, 119 tests passed (165 s) |
| `tests/guards` (rendered-language, gender-agreement, presentation-language, screen-set, screen-registry, lazy-boundary and the rest), run alone | 22 files, 313 tests passed (257 s) |
| `cd web && AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent npx vitest run --maxWorkers=4` (the whole web suite, committed code, run once) | **218 files, 3560 tests passed**, 411 s |
| `npm --prefix web run lint -- --quiet` | clean |
| `npm --prefix web run typecheck` | clean |
| `git diff --check` | clean |

A first run of the three instruments together (`vitest run tests/unit/comparison-only-pickers tests/guards tests/unit/styles`, 02:37) was voided by host load (load average 6.9 on 8 cores): a worker RPC timeout (`Timeout calling "onTaskUpdate"`), 3 of 29 files completed, no test red. It is not counted; the same files were rerun in the two runs of the table and are green.

The new file renders, through the harness (`renderScreen`/`renderWith`/`renderToStaticMarkup`, one server pass, as `D-53` asks), every state the brief names, with the field seeded as `comparison_pdf`, `portal_bundle`, absent and an unknown future value:

* the version picker: the option text and the pair badge for the target, for the version of the address, no option disabled, the comparison-only version chosen by default when it is the nearest; a set without one is free of the mark; the three not-comparison-only kinds draw byte for byte alike;
* the stage page: the note for a comparison-only version, ahead of «Сравнение прогонов»; none for the other kinds; byte-for-byte equality with an absent field; nothing while the version is unread;
* the two set choosers (the same cases in a loop): the disabled option and its mark text, the badge list and the single reason sentence, the select pointing at the reason, two comparison-only sets counted, a chooser with every set comparison-only (no `selected`), the unchanged markup for ordinary sets (no `disabled`, no `aria-describedby`, no note);
* the sections over a seeded cache: the default is the next set when a comparison-only one is listed first; the cache holds a query for the readable set and none naming the comparison-only one; with only comparison-only sets no specification or pass is asked for, «Обновить» is disabled, and «Запустить проход» is drawn disabled (the ordinary one is the enabled button); the read-only role still gets its sentence;
* the blocks picker: mark and disabled button on the comparison-only row, the portal row exactly as before (`<button type="button" class="am-button">Показать блоки</button>`), the reason once with every disabled button pointing at it, the row still listed, byte-for-byte equality of the three kinds.

`web/tests/unit/styles/screens.ts` gained one block after the `CMP-VERSION-MARK-01` block with five census screens (the version comparison over a comparison-only version, `SpecificationPricesChooser`, `ProposalSetChooser`, `DocumentChooser` and `StageComparisonPage`, each with a comparison-only version), so the contrast census and the language guards judge the badge, the note and the disabled controls where these screens draw them. The lane declares no module rule, so no colour-bearing rule is new.

### The check of D-261 after the change

`grep -rln "isComparisonOnly" web/src`:

```text
web/src/widgets/version-comparison/ui/version-comparison.tsx
web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx
web/src/entities/document-version/ui/version-row.tsx
web/src/entities/document-version/model/upload-kind.ts
web/src/entities/document-version/ui/version-panel.tsx
web/src/entities/document-version/index.ts
web/src/entities/document-version/ui/comparison-only-mark.tsx
web/src/_pages/blocks/ui/blocks-page.tsx
web/src/widgets/specification-prices/ui/specification-prices-section.tsx
web/src/_pages/stage-comparison/ui/comparison-only-note.tsx
```

Each of the five paths now appears once (version-comparison, stage-comparison, specification-prices, optimisation-proposals, blocks); before the lane none did.

### Mutation proofs (the guard shown red, restored, green)

Each mutation was applied to the committed file, the new test file run, and the file restored with `git checkout`; the file then ran 48 / 48 again.

| Mutation | Result |
| --- | --- |
| `version-comparison`: the pair mark draws nothing | 2 red |
| `blocks`: the row draws no mark | 2 red |
| `blocks` (start control): «Показать блоки» not `disabled` | 1 red |
| `optimisation-proposals` (start control): `startable = sets` (a comparison-only set may be the default, so «Запустить проход» could be offered for it) | 2 red |
| `specification-prices`: `readable = sets` (the default may be a comparison-only set, so it is asked for) | 3 red |
| `specification-prices` chooser: the option is not `disabled` | 2 red |
| `stage-comparison`: the note is never drawn | 1 red |

## 4. Contracts

None new or changed. The lane reads `DocumentVersion.upload_kind` from the generated client through the entity's helper and nothing else (`contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `FRONTEND_LOCK.json` untouched).

## 5. Forbidden hotspots

`git diff --name-only 6db7db23..HEAD` lists only: the task file and this report; `web/src/widgets/version-comparison/ui/version-comparison.tsx`; `web/src/_pages/stage-comparison/ui/{comparison-only-note.tsx (new), stage-comparison-page.tsx}`; `web/src/widgets/specification-prices/ui/specification-prices-section.tsx`; `web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx`; `web/src/_pages/blocks/{index.ts, ui/blocks-page.tsx}`; `web/tests/unit/comparison-only-pickers/comparison-only-pickers.test.ts` (new) and `web/tests/unit/styles/screens.ts` (imports and one block). All inside the task's allowed paths; no `contracts/**`, `db/migrations/**`, `src/**`, lock file, composition root, `globals.css`, `entities/document-version/**`, `features/**`, no module CSS file, and `DEBT_REGISTER.md` is untouched. `web/tests/guards/rendered-language.guard.test.ts` needed no edit. The `node_modules` symlink is git-ignored and was removed before the last commit.

## 6. Risks and known limitations

1. **The server refuses a comparison-only version by kind on the run starts only.** `refuse_comparison_only_version` (`analysis_input_invalid`, reason `comparison_only_version`) is called by `start_audit_run`, `reaudit_run` and `start_ar_v3_group` (task file P-03). The three screens that start work over a set answer something else: the pass start (`startOptimisationPass`) is refused with `conflict` whose reason is the state of the specification read (`analysis_missing`, no published run); the specification read answers the state `analysis_missing`; the block read answers `not_produced`. The lane disables the choice on those screens with `COMPARISON_ONLY_START_NOTE` verbatim, as briefed, but that sentence speaks of «Запуск прогона» and says «Сервер отклонил бы такой запуск», which is exact for a run and only approximately true for a pass or a read (they are refused or answered empty for the same cause: no portal bundle, so no run). The integrator may want either a sentence per screen (the entity is not in this lane's paths) or a refusal by kind on the pass start.
2. **The `<option>` text repeats the mark in words** because an option holds text only; the badge itself is drawn in the list under the select. The same three-line `optionLabel` stands in `version-comparison`, `specification-prices` and `optimisation-proposals`, and the same list in the two choosers: the entity that owns the mark is outside this lane's paths and widget-to-widget imports are not allowed, so they are not hoisted. One entity helper (`optionLabel` and the chooser list) would remove the repetition.
3. **`specification-prices` is read-only** (it starts no run); it is treated, as the brief and the row say, as a chooser that starts work over a set (it reads a specification). A comparison-only set has no published run, so its read could only answer `analysis_missing`.
4. **Nothing shows in a running stand until a comparison PDF is confirmed into a set.** The set choosers offer only sets whose current version is classified, and the blocks picker lists the project's documents; a comparison-only version appears there once `CMP-INGEST-01`'s set confirmation has written one. The screens are proved by seeded data and by the contract type.
5. **The version of the stage page is marked twice when the comparison is drawn** (the note above, and the pair line of the widget below): the note stays when the widget shows loading, a failure or «В комплекте пока одна версия», which the pair line does not.
6. **A stale choice is not guarded.** The section keeps `chosen ?? first readable`; a comparison-only set cannot be chosen through the interface (its option is disabled) and `upload_kind` does not change for a version, so no state is added for an input that cannot occur. A programmatic `onSelect` with such an identity would still be asked for; the tests pin the default and the disabled option, not that call.
7. The `ul` of the two choosers and the `<p>` of the stage note use the global element rules; no layout was added.

## 7. Instructions for the integrator

* The row `D-261` can close on `grep -rln "isComparisonOnly" web/src` listing a file under each of the five paths (section 3) and on the tests of section 3; the lane does not edit `DEBT_REGISTER.md`.
* No wiring file is touched, so there is nothing to resolve against another lane except, possibly, `web/tests/unit/styles/screens.ts` (three imports and one block after the `VersionDetailPage comparison-only` entry) and the `1.10.0` literals other lanes' web tests carry.
* Decide item 1 of section 6 (a sentence per screen or a refusal by kind on the pass start) and item 2 (hoisting) before the next wave touches these screens; both are one-slice changes.
