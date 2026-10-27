# Task CMP-VERSION-MARK-01 — the «загружено без пакета портала» mark and the disabled run start on the version screens

task_id: CMP-VERSION-MARK-01
status: in progress (lane `agent/cmp-version-mark-01`, wave C0; nothing pushed, merged or tagged)

## Outcome

A document version whose `upload_kind` is `comparison_pdf` (a plain PDF admitted for comparison only, `Q-CMP-5`) is marked «Загружено без пакета портала — только для сравнения» on every existing screen that lists or opens a document version: the version screen, a document's version list, the project's document list and the project structure (the three of them draw the same version row). On the version screen its run list offers no working start: the control is drawn disabled with a sentence that says why («Версия загружена только для сравнения: анализ по разделам для неё не запускается»), and neither the ordinary start nor the six-check start is reachable. The server refuses the same start (`analysis_input_invalid`, reason `comparison_only_version`); the screen does not wait for that refusal. A version with `upload_kind` `portal_bundle`, or without the field, renders exactly as before.

## Depends on

- `CMP-SEAL-C0` — completed (merged `0990de4b` on `integration/compare-modules`); it added `DocumentVersion.upload_kind` (`portal_bundle` | `comparison_pdf`, optional, always sent) and the catalogue sentence of `comparison_only_version`.
- `CMP-ADR-01` — completed; ADR-0025 decisions 11 and 25 (a comparison PDF never becomes the portal version of a document; no section analysis starts on it).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.9.0`, unchanged (`contracts/**`, `web/openapi/**`, the generated client and `web/FRONTEND_LOCK.json` are not touched); the field is read from the generated type `DocumentVersion.upload_kind` (`VersionUploadKind`)
- analysis/comparison/event contract: not_applicable
- migration head: `0038_comparison_foundation`, unchanged
- base commit: `cc3dd36b5b05b28ed0232107c8d0a437e304f07b`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: contract `1.9.0`, 115 paths / 130 operations / 351 schemas, head `0038_comparison_foundation`; the generated client already types `DocumentVersion.upload_kind`; no screen reads it yet

### P-01 — the wave's base facts

- captured_at: 2026-10-28
- command: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); print(d['info']['version'], len(d['paths']), sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')), len(d['components']['schemas']))"; grep -n 'revision: str = ' db/migrations/versions/20261028_0038_comparison_foundation.py; git rev-parse HEAD`
- captured_output:
  ```text
  1.9.0 115 130 351
  81:revision: str = "0038_comparison_foundation"
  cc3dd36b5b05b28ed0232107c8d0a437e304f07b
  ```
- interpretation: the premise of the brief (`docs/program/dispatch/CMP-WAVE-C0.md` §1 rule 1) holds, so the lane went on. It does not prove that the server serves `comparison_pdf` yet: the repository read of the column is `CMP-INGEST-01`'s (`CMP-SEAL-C0` last section), so until it lands every served version says `portal_bundle` and this lane's screens show no mark in a running stand.

### P-02 — the generated type and the absence of any reader

- captured_at: 2026-10-28
- command: `grep -n "upload_kind" web/src/shared/api/generated/types.gen.ts; grep -rnE "upload_kind|comparison_pdf|comparison_only" web/src --include=*.ts --include=*.tsx | grep -v generated/`
- captured_output:
  ```text
  1354:  upload_kind?: VersionUploadKind;
  web/src/shared/api/catalog-message.ts:137:  // `CMP-SEAL-C0` (ADR-0025 decision 25): the reason `comparison_only_version` rides this code —
  web/src/shared/api/catalog-message.ts:143:    '(причина comparison_only_version), не анализируется по разделам.',
  ```
- interpretation: the field is optional in the type and is read nowhere on a screen. «Absent» must therefore render as `portal_bundle`.

### P-03 — where a version is drawn and where a run is started

- captured_at: 2026-10-28
- command: `grep -rlE "VersionRow|VersionPanel|<StartRunControl|<StartArV3GroupControl" web/src`
- captured_output:
  ```text
  web/src/entities/document-version/index.ts
  web/src/entities/document-version/ui/version-panel.tsx
  web/src/entities/document-version/ui/version-row.tsx
  web/src/features/start-ar-v3-group/index.ts
  web/src/features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx
  web/src/features/start-run/index.ts
  web/src/features/start-run/ui/start-run-control.tsx
  web/src/_pages/version-detail/ui/version-detail-page.tsx
  web/src/widgets/document-list/ui/document-list.tsx
  web/src/widgets/project-sections/ui/project-sections.tsx
  web/src/widgets/run-list/ui/run-list.tsx
  web/src/widgets/version-list/ui/version-list.tsx
  ```
- interpretation: one row component (`VersionRow`, entity `document-version`) serves the document list, the version list and the project structure; one panel (`VersionPanel`) serves the version screen; the two start controls are drawn by `run-list.tsx` only. So the mark goes into the row and the panel, and the start is decided in `RunList`, which already decides between the ordinary start and the АР sentence. `widgets/version-history` is the release-notes drawer of the PRODUCT («История версий»), not a document version history: it shows no `DocumentVersion` and has no field to read (see the report).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/_pages/version-detail/**`
- `web/src/widgets/version-list/**`
- `web/src/widgets/version-history/**`
- `web/src/widgets/document-list/**`
- `web/src/widgets/run-list/**`
- `web/src/entities/document-version/**`
- `web/tests/unit/**`
- `docs/program/tasks/CMP-VERSION-MARK-01.md`
- `docs/program/CMP-VERSION-MARK-01.md`

## Forbidden hotspots

- `contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `db/migrations/**`
- root dependency/lock files (`web/package.json`, `web/package-lock.json`)
- `web/src/app/globals.css` and every global style; the composition root
- `web/src/features/start-run/**` and `web/src/features/start-ar-v3-group/**` (not owned by this lane: the run list decides whether to draw them)
- `src/**` (the server: the refusal and the repository read are `CMP-INGEST-01`'s)

## Non-goals

- no change of the server, the contract or the generated client; no new operation or error code
- no marking of a screen outside the paths above that draws a version some other way (the stage comparison and version comparison pickers, the block and optimisation screens); the report lists them for the integrator
- no filtering of comparison-only versions out of any list: they stay listed and addressable
- no upload form for comparison PDFs (`CMP-INGEST-01` and the comparison screens of later waves)
- no new colour: the mark takes an existing `.am-badge--*` tone

## Deliverables

- `entities/document-version/model/upload-kind.ts` (the predicate and the two Russian sentences), `ui/comparison-only-mark.tsx` (+ a layout-only module, no colour), the mark in `VersionRow` and `VersionPanel`
- `widgets/run-list`: the disabled start and its explanation for a comparison-only version, fed by the version screen
- `web/tests/unit/screens/comparison-only-version.test.ts` (each screen state: mark shown / not shown, start disabled / enabled), census entries appended to `web/tests/unit/styles/screens.ts` (the one existing file touched, by the lane's instruction: the new states must be reached by the contrast and rendered-language census)
- the report `docs/program/CMP-VERSION-MARK-01.md`

## Required tests

- command: `cd web && AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent npx vitest run tests/unit/screens/comparison-only-version.test.ts tests/unit/styles tests/guards`
- expected: green, with the new file's cases listed in the report
- command: `npm --prefix web run lint -- --quiet`, `npm --prefix web run typecheck`, `npm --prefix web run test -- --run`
- expected: green
- command: mutation proofs (the guard shown red, restored, green) for: the predicate reading `upload_kind`, the disabled state, the six-check start staying unreachable
- expected: each test fails under its mutation

## Integration contract

- the screens read `DocumentVersion.upload_kind` from the generated client and nothing else; `comparison_pdf` is the only value that changes any rendering
- `RunList` gains one optional prop `uploadKind`; the version screen passes `version.data?.upload_kind`. An absent prop (every other caller) is the ordinary list
- the sentences live in `entities/document-version` and are exported from its public API for the later comparison screens

## Failure/idempotency/security cases

- field absent, `portal_bundle`, or a value this client does not know: the ordinary rendering (only `comparison_pdf` is treated as comparison-only; an unknown future value is never read as a refusal, but the server still refuses what it refuses)
- the version has not arrived yet (`uploadKind` `undefined`): the list is what it always was; a press in that interval is refused by the server in the catalogued words
- a comparison-only version with runs in its list (cannot exist by the refusal, may exist by an old row): the runs stay listed, the start stays disabled

## Rollback / feature flag

Not applicable: a presentation change over an optional field that is `portal_bundle` for every row that can exist until `CMP-INGEST-01` lands. Reverting the lane's commits restores the previous screens.

## Handoff

- changed files: (filled in the last commit)
- commands/results: (filled in the last commit)
- known limits: (filled in the last commit)
- integration notes: (filled in the last commit)
