# CMP-VERSION-MARK-01 — the «загружено без пакета портала» mark and the disabled run start

Written 2026-10-28 by the Sonnet lane `CMP-VERSION-MARK-01` (branch `agent/cmp-version-mark-01`, base `cc3dd36b` on `integration/compare-modules`; nothing pushed, merged or tagged). Task file: `docs/program/tasks/CMP-VERSION-MARK-01.md`.

A web-only change. A document version whose `upload_kind` is `comparison_pdf` carries the mark «Загружено без пакета портала — только для сравнения» wherever the version screens draw it, and its run list draws the start disabled with the reason. A version with `portal_bundle`, with no field, or with a value this client does not know, is drawn byte for byte as before (compared by tests).

## 1. Base facts, printed before any edit

Contract `1.9.0`, 115 paths / 130 operations / 351 schemas; head `0038_comparison_foundation`; base `cc3dd36b`. They equal the brief, so the lane went on. The generated client already types `DocumentVersion.upload_kind?: VersionUploadKind` (`portal_bundle` | `comparison_pdf`); no screen read it (task file P-01, P-02).

## 2. What the screens do now

| Screen | Where | What changed |
| --- | --- | --- |
| Version screen | `_pages/version-detail` → `VersionPanel` | the mark and a sentence («Это обычный PDF-файл, принятый только для сравнения…») above the identity fields; the run list is told the kind |
| Version list of a document | `widgets/version-list` → `VersionRow` | the mark under the classification badges |
| Document list of a project | `widgets/document-list` → `VersionRow` | the same row, the same mark |
| Project structure (not on the brief's list, same row component) | `widgets/project-sections` → `VersionRow` | the same mark, in a section group and in «Не классифицировано» |
| Run list and start control | `widgets/run-list` | for `comparison_pdf`: the label «Запустить прогон» drawn `disabled`, `aria-describedby` pointing at the sentence «Запуск прогона недоступен: версия загружена без пакета портала и только для сравнения…», in place of the ordinary start AND of the six-check start AND of the АР sentence; the heading over a non-empty list reads «Запуск прогона»; listed runs stay listed |
| Version history | `widgets/version-history` | **nothing**: it is the release-notes drawer of the PRODUCT («История версий», `getReleases`), not a history of document versions. It draws no `DocumentVersion` and has no field to read. Its folder is in the lane's paths by the brief; no file in it was touched |

The mark is one `.am-badge.am-badge--degraded` (the existing amber tone of «профиль анализа недоступен»: a version that cannot be analysed) plus a layout-only module class (`comparison-only-mark.module.css`: `white-space: normal`, `overflow-wrap: anywhere`, `max-width: 100%`, so the sentence wraps instead of widening a phone screen). No colour is declared in the module, so no colour-bearing rule is new; the contrast census measures the badge through the global rule.

Where the code lives: `entities/document-version/model/upload-kind.ts` (the predicate `isComparisonOnly` — only `upload_kind === 'comparison_pdf'` counts — and the three sentences), `ui/comparison-only-mark.tsx` (`ComparisonOnlyMark`, `ComparisonOnlyStart`), exported from the entity's public API. `RunList` takes one optional prop `uploadKind`; `VersionDetailPage` passes `version.data?.upload_kind`. Every other caller of `RunList` passes nothing and gets the ordinary list.

## 3. Tests

| Check | Result |
| --- | --- |
| `web/tests/unit/version-mark/comparison-only-version.test.ts` (new) | 31 passed |
| `npm --prefix web run test -- --run` (the whole web suite, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, measured on the committed code, 229 s) | **208 files, 3278 tests passed** (the 31 new ones included) |
| the instruments the brief names (`tests/unit/styles` — contrast census with `screens.ts` — and `tests/guards` — rendered-language, gender-agreement, presentation-language, screen-set, screen-registry, lazy-boundary), run alone before the suite | 28 files, 384 tests passed |
| `npm --prefix web run lint -- --quiet` | clean |
| `npm --prefix web run typecheck` | clean |
| `git diff --check` | clean |
| `pytest -q tests/contract` minus the three `D-220` files (`test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py`), seal venv, `PYTHONPATH=$PWD/src`, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, on the committed tree that already held this report (the section below was the only text added afterwards) | **1307 passed**, 19283 subtests passed, 159 s |

The new file renders, through the harness (`renderScreen`/`renderWith`, one server pass, as `D-53` asks), every state the brief names:

* mark shown / not shown: the panel for `comparison_pdf`, `portal_bundle`, no field and an unknown future value; the version list, the document list and the project structure over a mixed page (exactly the `comparison_pdf` row is marked, found by `data-version-uid`); the version screen;
* start disabled / enabled: the run list over an empty list and a list with runs, for `comparison_pdf` (with the six-check pack installed, and with the section АР), `portal_bundle`, no field and an unknown value; loading and failed lists draw no start; the version screen for all three kinds;
* byte-for-byte equality of the markup of a `portal_bundle` and an absent field in the panel, a list, the run list and the whole screen;
* the contract's value set is pinned (`VERSION_UPLOAD_KIND_VALUES` is exactly the two values), so a third value must be looked at, not defaulted;
* the Russian text has no Latin letter in the mark.

`web/tests/unit/styles/screens.ts` (the one existing test file touched, by the lane instruction) gained one block after `VersionDetailPage loaded` with five screens — `DocumentList`, `VersionList`, `RunList` (with a run and empty) and `VersionDetailPage`, all over a `comparison_pdf` version. A throwaway probe (deleted) rendered the census and found all five reached, three carrying `data-comparison-only-mark` and three `data-start-run-disabled`, so the contrast, rendered-language and gender-agreement guards judge the mark and the note where they are drawn.

### Mutation proofs (the guard shown red, restored, green)

Each mutation was applied to the committed file, the new test file run, and the file restored with `git checkout`.

| Mutation | Result |
| --- | --- |
| `isComparisonOnly` always `false` | 7 red |
| `isComparisonOnly` = «any value but `portal_bundle`» (an unknown value becomes comparison-only) | 4 red |
| `ComparisonOnlyStart` button without `disabled` | 5 red |
| `VersionRow` draws no mark | 3 red |
| `VersionPanel` draws no mark | 3 red |
| `VersionDetailPage` does not pass `uploadKind` | 2 red |
| the АР sentence wins over the comparison reason | 3 red |
| the six-check start drawn beside the disabled start | 6 red |

A ninth mutation survived and was acted on: a guard `!comparisonOnly &&` I had added to the `sixChecks` expression changed nothing a test could see (the comparison start never reads `sixChecks`, and the only other reader is the in-flight branch of the loading and error states, which a static render cannot reach and which a comparison version cannot have). The guard was removed rather than left as dead code; the property it was meant to hold («the six checks are not reachable») is held by the eighth row above.

## 4. Contracts

None new or changed. The lane reads `DocumentVersion.upload_kind` from the generated client and nothing else (`contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `FRONTEND_LOCK.json` untouched).

## 5. Forbidden hotspots

`git diff --name-only cc3dd36b..HEAD` lists only: the task file and this report; `web/src/_pages/version-detail/ui/version-detail-page.tsx`; `web/src/widgets/run-list/ui/run-list.tsx`; `web/src/entities/document-version/{index.ts, model/upload-kind.ts, ui/comparison-only-mark.tsx, ui/comparison-only-mark.module.css, ui/version-panel.tsx, ui/version-row.tsx}`; `web/tests/unit/version-mark/comparison-only-version.test.ts` (new) and `web/tests/unit/styles/screens.ts` (appended block). All inside the brief's allowed paths; no `contracts/**`, `db/migrations/**`, `src/**`, lock file, composition root, `globals.css`, `features/start-run/**` or `features/start-ar-v3-group/**`. The `node_modules` symlink is git-ignored.

## 6. Risks and known limitations

1. **Nothing shows in a running stand yet.** The repository read of `document_version.upload_kind` is `CMP-INGEST-01`'s (`CMP-SEAL-C0`, last section): until it lands the API says `portal_bundle` for every version, so no mark is drawn. The screens are proved by seeded data and by the contract type, not by a served `comparison_pdf`.
2. **Screens outside the lane's paths that draw a version without the mark.** Not changed (non-goal, other owners): the version picker of `widgets/version-comparison`, `_pages/stage-comparison`, the set choosers of `widgets/specification-prices` and `widgets/optimisation-proposals` (an `<option>` per classified set; `setLabel` carries no kind), and the document picker of `_pages/blocks` (a comparison PDF has no portal blocks). The integrator may want a follow-up that marks or filters them; the entity now exports `ComparisonOnlyMark`, `isComparisonOnly` and the sentences for that. The specification-prices and optimisation choosers matter most: they start work over a chosen set, and whether the server refuses a comparison-only set there is not in this lane's reading.
3. **The disabled button has the same label as the enabled one**, by choice (the reader sees the same control, greyed, with the reason beside it). A test that looks for `>Запустить прогон</button>` to prove the ordinary start is drawn would also match the disabled one; the new tests use the enabled markup (`<button type="button" class="am-button">`). The existing `run-list-ar-start.test.ts` and `run-list-ar-v3-start.test.ts` pass no kind and are unaffected (the whole suite is green).
4. **The kind arrives with the version.** The run list receives `uploadKind` from the version screen's own read; while it is loading the list is the ordinary one, and a press in that interval is refused by the server with the catalogued sentence of `comparison_only_version` (`catalog-message.ts`). The interval is short and is the same one `sectionCode` has had since `PROD-11`; the refusal is the server's, as it was before this lane.
5. **Tone.** `am-badge--degraded` (amber) was chosen over `pending`/`inert` so that the mark reads as a limit and not as a state of confirmation. A different tone is a one-word change in `comparison-only-mark.tsx`; the census measures whichever is used.
6. A `comparison_pdf` version that has a classification (the stamp proposals of `CMP-INGEST-01` may produce one) still shows its stage and section badges beside the mark; this lane does not decide whether such a version may be classified.

## 7. Instructions for the integrator

* Merge order: last (`VERSION-MARK`), per the wave brief §3. No wiring file is touched, so there is nothing to resolve against the other lanes except, possibly, `web/tests/unit/styles/screens.ts` (one block appended after the `VersionDetailPage loaded` line) and the `1.9.0` literals the other lanes' web tests carry.
* After `CMP-INGEST-01` lands (it serves `upload_kind`), a stand check is worth one look: upload a plain PDF for comparison and open the version, the document list and the run list.
* The census floors in `tests/unit/styles/contrast.test.ts` (`rendered.length >= 45`, pairs `>= 140`) are floors, not exact counts; five screens were added and no floor moved.

### `tests/contract`

1307 passed and 19283 subtests passed in 159 s (command in section 3). The lane changed no Python, no contract and no migration, so the figure is the integration branch's own at `cc3dd36b` plus the two documents; it includes `tests/contract/program` (the wave-governance check that reads this lane's task file: command, date and output of the premise block are present) and the prose-fact tests. The three `D-220` files were not run (they open `.git` as a directory and cannot pass in a worktree; `CMP-SEAL-C0` measured them identical on the base).
