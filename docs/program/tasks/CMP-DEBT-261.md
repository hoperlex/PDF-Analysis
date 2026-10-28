# Task CMP-DEBT-261 — the comparison-only mark on the five screens that pick a version or a set

task_id: CMP-DEBT-261
status: completed in development candidate (lane `agent/cmp-debt-261`, size S, web only; nothing pushed, merged or tagged)

## Outcome

Closes the check of `D-261`. A version admitted for comparison only (`upload_kind` `comparison_pdf`, `Q-CMP-5`; a plain PDF that can never start a run) is marked with the shared mark of `CMP-VERSION-MARK-01` («Загружено без пакета портала — только для сравнения») on the five screens that pick a version or a set and did not mark it: the version picker of `widgets/version-comparison`, `_pages/stage-comparison`, the set choosers of `widgets/specification-prices` and `widgets/optimisation-proposals`, and the document picker of `_pages/blocks`. Where the screen starts work over the chosen set or version (specification-prices, optimisation-proposals, blocks) a comparison-only one is listed, marked and drawn disabled with the reason sentence of the refused start (`COMPARISON_ONLY_START_NOTE`), and nothing is requested for it. Where the screen exists to compare (version-comparison, stage-comparison) the version stays chosen and comparable and carries the mark. A version without the field, with `portal_bundle` or with a value this client does not know is drawn as before.

## Depends on

- `CMP-VERSION-MARK-01` — completed (report `docs/program/CMP-VERSION-MARK-01.md`, §2 and the item «Screens outside the lane's paths that draw a version without the mark» of §6); it exports `isComparisonOnly`, `ComparisonOnlyMark`, `COMPARISON_ONLY_MARK`, `COMPARISON_ONLY_DETAIL` and `COMPARISON_ONLY_START_NOTE` from `@/entities/document-version`.
- `CMP-SEAL-C0`, `CMP-INGEST-01` — completed; `DocumentVersion.upload_kind` and the refusal `analysis_input_invalid` / `comparison_only_version` of the run starts.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.10.0`, unchanged (`contracts/**`, `web/openapi/**`, the generated client and `web/FRONTEND_LOCK.json` are not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0039_comparison_core`, unchanged
- base commit: `6db7db23a6d16d36d9763cc3377cd3d6bd425869` (branch `integration/compare-modules`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`; `grep -rln "isComparisonOnly" web/src` lists only the entity `document-version` (none of the five paths); only the run starts (`start_audit_run`, `reaudit_run`, `start_ar_v3_group`) refuse a comparison-only version by kind

### P-01 — the base facts

- captured_at: 2026-10-29
- command: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); print(d['info']['version'], len(d['paths']), sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')), len(d['components']['schemas']))"; grep -n 'revision: str = ' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  1.10.0 131 148 432
  79:revision: str = "0039_comparison_core"
  6db7db23a6d16d36d9763cc3377cd3d6bd425869
  ```
- interpretation: the brief's base facts hold, so the lane went on.

### P-02 — the check of D-261 before the change

- captured_at: 2026-10-29
- command: `grep -rln "isComparisonOnly" web/src`
- captured_output:
  ```text
  web/src/entities/document-version/index.ts
  web/src/entities/document-version/ui/version-panel.tsx
  web/src/entities/document-version/ui/version-row.tsx
  web/src/entities/document-version/ui/comparison-only-mark.tsx
  web/src/entities/document-version/model/upload-kind.ts
  ```
- interpretation: none of `web/src/widgets/version-comparison`, `web/src/_pages/stage-comparison`, `web/src/widgets/specification-prices`, `web/src/widgets/optimisation-proposals`, `web/src/_pages/blocks` reads the helper. After the lane each of the five paths must appear in this list.

### P-03 — where the server refuses a comparison-only version by kind

- captured_at: 2026-10-29
- command: `grep -rn "refuse_comparison_only_version(" src --include=*.py`
- captured_output:
  ```text
  src/auditmanager/runs/v3_group.py:251:    refuse_comparison_only_version(version)
  src/auditmanager/runs/commands.py:382:def refuse_comparison_only_version(version: Any) -> None:
  src/auditmanager/runs/commands.py:422:    refuse_comparison_only_version(version)
  src/auditmanager/runs/commands.py:622:    refuse_comparison_only_version(version_record)
  src/auditmanager/runs/commands.py:911:    refuse_comparison_only_version(source_version)
  ```
- interpretation: the registered reason is `comparison_only_version` under `analysis_input_invalid` (`COMPARISON_ONLY_VERSION_REASON`, `runs/commands.py:379`), raised by the three run starts only (start, re-audit, the АР v3 group). The optimisation pass start (`optimisation/proposals/commands.py`: `raise _refused(prices.state)`) is refused by the state of the specification read (`analysis_missing`: no published run), and the two reads (specification prices, version blocks) answer a state, not this reason. The Russian sentence of the reason on a screen is `COMPARISON_ONLY_START_NOTE` of the entity (`CMP-VERSION-MARK-01`); the lane uses it verbatim and records in the report that the server's own answer on those three screens is a state of the read, not this reason.

### P-04 — the pickers as they stand

- captured_at: 2026-10-29
- command: `grep -n "<option\|<select" web/src/widgets/version-comparison/ui/version-comparison.tsx web/src/widgets/specification-prices/ui/specification-prices-section.tsx web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx; grep -n "onChooseVersion(doc)\|Показать блоки" web/src/_pages/blocks/ui/blocks-page.tsx`
- captured_output:
  ```text
  web/src/widgets/version-comparison/ui/version-comparison.tsx:203:          <select
  web/src/widgets/version-comparison/ui/version-comparison.tsx:211:              <option key={item.version_uid} value={item.version_uid}>
  web/src/widgets/specification-prices/ui/specification-prices-section.tsx:70:        <select
  web/src/widgets/specification-prices/ui/specification-prices-section.tsx:76:            <option key={version.document_uid} value={version.document_uid}>
  web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx:92:        <select
  web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx:98:            <option key={version.document_uid} value={version.document_uid}>
  195:            <button type="button" className="am-button" onClick={() => onChooseVersion(doc)}>
  196:              Показать блоки
  ```
- interpretation: three `<select>` pickers whose `<option>` holds text only (so the badge component cannot sit inside an option), and one list of buttons. `StageComparisonPage` composes the picker and reads no version itself.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/widgets/version-comparison/**`
- `web/src/_pages/stage-comparison/**`
- `web/src/widgets/specification-prices/**`
- `web/src/widgets/optimisation-proposals/**`
- `web/src/_pages/blocks/**`
- `web/tests/unit/comparison-only-pickers/**`
- `web/tests/unit/comparison/**`
- `web/tests/unit/specification-prices/**`
- `web/tests/unit/optimisation-proposals/**`
- `web/tests/unit/blocks/**`
- `web/tests/unit/screens/stage-comparison.test.ts`
- `web/tests/unit/styles/screens.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `docs/program/tasks/CMP-DEBT-261.md`
- `docs/program/CMP-DEBT-261.md`

## Forbidden hotspots

- `contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `db/migrations/**`
- root dependency/lock files (`web/package.json`, `web/package-lock.json`), the composition root, `web/src/app/globals.css` and every global style
- `web/src/entities/document-version/**` (the mark, the helper and the sentences are reused as they are, not changed), `web/src/features/start-optimisation-pass/**` (the pass start is disabled by not offering the set to it), `web/src/features/start-run/**`, `web/src/features/start-ar-v3-group/**`
- `src/**` (the server)
- `docs/program/DEBT_REGISTER.md` (the integrator closes the row)

## Non-goals

- no new mark, no new colour, no new custom property; the lane reuses `ComparisonOnlyMark` and the helper, and adds no module rule
- no filtering of a comparison-only version out of any list: it stays listed
- no change of the server, the contract or the generated client; no new operation or error code
- no disabling of the two comparison screens: comparing is what a comparison-only version is for
- no change of what a portal version looks like on these screens (compared byte for byte by tests)

## Deliverables

- `widgets/version-comparison`: the mark in the picker's option text and next to each version of the compared pair
- `_pages/stage-comparison`: the mark and the sentence on what the version is, when the version of the address is comparison-only
- `widgets/specification-prices`, `widgets/optimisation-proposals`: the chooser lists a comparison-only set as a disabled option carrying the mark text, the real mark and the reason under the select, never selects one by default and requests nothing for it
- `_pages/blocks`: the document picker draws the mark on a comparison-only document and its «Показать блоки» disabled with the reason
- `web/tests/unit/comparison-only-pickers/comparison-only-pickers.test.ts` (new), census entries in `web/tests/unit/styles/screens.ts`
- the report `docs/program/CMP-DEBT-261.md`

## Required tests

- command: `cd web && AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent npx vitest run tests/unit/comparison-only-pickers tests/guards tests/unit/styles`
- expected: green, with the new file's cases listed in the report
- command: `npm --prefix web run lint -- --quiet`, `npm --prefix web run typecheck`, `cd web && npx vitest run --maxWorkers=4`, `pytest -q tests/contract` minus the three `D-220` files
- expected: green
- command: `grep -rln "isComparisonOnly" web/src`
- expected: lists a file under each of the five paths
- command: mutation proofs (the guard shown red, restored, green) for one picker's mark and one start-control refusal
- expected: each test fails under its mutation

## Integration contract

- the screens read `DocumentVersion.upload_kind` through `isComparisonOnly` and nothing else; `comparison_pdf` is the only value that changes any rendering
- the exports of `@/entities/document-version` are used as they are; no new export is added there
- `DocumentChooser` of `_pages/blocks` becomes an export of the slice (`blocks-page.tsx` and its `index.ts`) for the instruments, as `VersionBlockViews` did

## Failure/idempotency/security cases

- field absent, `portal_bundle`, or an unknown value: the ordinary picker, byte for byte
- every set of a project comparison-only: nothing is selected, nothing is requested, the pass start stays disabled and the reason is on the screen
- a press on a disabled option or button cannot send a request: the option and the button are `disabled`, and the selection never defaults to a comparison-only set

## Rollback / feature flag

Not applicable: a presentation change over an optional field that is `portal_bundle` for every row that can exist until a comparison PDF is confirmed into a set. Reverting the lane's commits restores the previous screens.

## Handoff

- changed files: `web/src/widgets/version-comparison/ui/version-comparison.tsx`, `web/src/_pages/stage-comparison/ui/{comparison-only-note.tsx (new), stage-comparison-page.tsx}`, `web/src/widgets/specification-prices/ui/specification-prices-section.tsx`, `web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx`, `web/src/_pages/blocks/{index.ts, ui/blocks-page.tsx}`, `web/tests/unit/comparison-only-pickers/comparison-only-pickers.test.ts` (new), `web/tests/unit/styles/screens.ts` (imports and one block of five census screens), this task file and the report `docs/program/CMP-DEBT-261.md`
- commands/results: new test file 48 passed; `tests/unit/styles` + new file 7 files / 119 tests passed; `tests/guards` 22 files / 313 tests passed; the whole web suite 218 files / 3560 tests passed (411 s, `--maxWorkers=4`); lint and typecheck clean; `git diff --check` clean; `pytest -q tests/contract` minus the three `D-220` files in the report (section 3, last line); the D-261 check lists a file under each of the five paths; seven mutations shown red and restored (report section 3)
- known limits: the server refuses a comparison-only version by kind on the three run starts only, so the pass start and the two reads on the disabled screens answer other states, and `COMPARISON_ONLY_START_NOTE` is used verbatim on them (report section 6, item 1); the `optionLabel` and the chooser list are repeated in three and two widgets because the entity is outside the lane's paths; nothing shows in a running stand until a comparison PDF is confirmed into a set
- integration notes: merge anywhere after `CMP-VERSION-MARK-01`; no wiring file touched; `screens.ts` has one block after the `VersionDetailPage comparison-only` entry; `DEBT_REGISTER.md` row `D-261` is closed by the integrator
