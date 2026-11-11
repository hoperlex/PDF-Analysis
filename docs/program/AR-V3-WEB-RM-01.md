# AR-V3-WEB-RM-01 — AR v3 removed from the web

Wave `AR-V3-REMOVE + V3-OPTIN`, lane 1 of 4 (web). Owner ruling `R-154a` (2026-11-10): the six-scope АР
beta group, called AR v3 here, is removed everywhere, so that nothing in the tree can be confused with
extended-review v3. Branch `agent/ar-v3-web-rm-01`, base `826470582` (VERSION 0.23.1, contract 1.49.0).
Web only: no contract, migration, dependency, composition root or global style changed, and nothing
under `web/src/shared/api/generated/**` was touched.

## What changed

- **Slices deleted:** `features/start-ar-v3-group`, `widgets/ar-v3-beta-pack`, `widgets/ar-v3-beta-review`,
  `widgets/ar-v3-beta-status` (with its two JSON mirrors of the beta source policy),
  `features/start-run/ui/analysis-choice.*` (the «Анализ» radio), `widgets/run-list/ui/analysis-start.tsx`.
- **«Запуск» of an АР version** is now the start form every section has. `run-list.tsx` mounts
  `StartRunWithReadiness` always; the heading «Запустить анализ АР» stays.
- **`entities/audit-run`:** deleted the pack-status read (`use-ar-v3-pack-status`, `ar-v3-pack-status`), the group
  id helpers and `run-analysis` (kind, label, «Стандартный»). Removed from the rest of the entity: the AR v3 profile
  id, the `ar_v3_citation_review` stage row, its chip and label, `runHasPublishedResult`'s profile argument, and
  the `analysis_profile_id` pick of `stageRows` and `runChips`.
- **Run page and run table:** no «Анализ» line, no `data-run-analysis`, no v3 outcome texts, no v3 findings tile, no
  «Шесть проверок» link.
- **`entities/execution`:** the two v3 conflict sentences are gone. **`shared/api/query-keys.ts`:** the two v3 keys.
- **«Настройки анализа»** keeps the profile table and loses the three AR v3 panels and the `group_id` address
  (the route no longer answers 404 for a malformed one; it ignores the parameter). The page, its route and its
  menu entry stay.
- **Cost-estimate scope guards.** The four checks `estimate.scope === 'run'` (`one-click-start.ts`, `batch-start.ts`,
  `use-reaudit-cost-approval.ts`, `use-start-from-stage-cost-approval.ts`) only told a run estimate from a group one.
  They are removed, so the code compiles whether the regenerated contract keeps `scope` or drops it.
- **Comments and one text:** the comparison refusal for another analysis no longer says «(АР v3)».

## Tests

Deleted (AR v3 only): ten files of `tests/unit/analysis-settings`, four of `tests/unit/screens`,
`tests/unit/execution/ar-v3-refusals`, `tests/unit/cost-approval/start-cost-flow`.
Edited: the shared tests lose their v3 cases. Kept and adapted:

- `screens/run-list-ar-start` now also pins that an АР version has no radio, no wrapper of one and no analysis line.
- `run/stage-rows` gained two neutral cases that the deleted v3 tests used to give: an unknown stage id is
  refused by `hasKnownRunVocabulary`, and `StageTable` with no rows says nothing reported yet.
- The review-indication switch tests keep the profile label and the comparison-summary label; the guard
  `review-indication.guard` now owns `run-progress` and `entities/analysis-profile`.
- `qa_w50/r66-navigation`: `/analysis-settings` reads the profile registry alone.
- `guards/rendered-language`: the AR v3 screens, the beta policy vocabulary and the stale allowlist entry
  «Решение не записано» are gone.

## Checks (tree `70fc075ab` content)

- `npx tsc --noEmit -p .`: exit 0.
- `npx eslint` on the 61 touched `.ts`/`.tsx` files: exit 0; re-run on `run-presentation.ts` after its last edit
  (see the commit that adds this record).
- `npx vitest run --maxWorkers=1` on 110 files (the touched tests, their neighbours, the route registry and menu
  tests, the CSS census, all guards and all contract tests): 2181 passed, 1 failed. The one red is
  `tests/contract/seam-operations.contract.test.ts` «requires an idempotency key on exactly the keyed writes»:
  the generated client still carries `startArV3BetaGroup`. It turns green when the backend lane regenerates the client.
- `grep -rniE "ar[_-]?v3|ArV3|АР v3|AR v3" web/src web/tests --exclude-dir=generated`: 0 lines.
- Post-regeneration typecheck, simulated: a scratch copy with the generated `RunStatus` and `RunCostEstimate`
  shapes patched as the contract change will make them (no `analysis_kind`, `ar_v3_*`, `scope`; stage ids
  without the v3 member) typechecks, apart from one line named below.

Logs: `.local/evidence/lane-AR-V3-WEB-RM-01/`. Preview: `.local/reports/ar-v3-remove-2026-11-10/web-preview/`
(`preview.png`, `before/`, `after/`, `facts.json`, `tools/`).

## Instruction to the integrator

- Merge this lane last, after the backend lane's regenerated client. After the merge run `tsc` and
  `tests/contract/seam-operations.contract.test.ts`.
- If the regenerated `RunCostEstimate` has no `scope`, delete `scope: 'run'` in
  `web/tests/unit/analysis-settings/cost-estimate-fixtures.ts` (the only line that fails).
- If the regenerated `ComparisonRefusal.reason` drops `analysis_not_comparable`, delete its entry in
  `web/src/entities/document-version/model/comparison.ts` (`REFUSAL_TEXT`).
- `web/openapi/openapi.json` is the snapshot `api:generate` writes; it still lists the AR v3 operations until then.

## Risks and limits

- `stageRows` and `runOutcome` read the stage ids of a reading as the closed `StageId` set with `as StageId`: until
  the client is regenerated the generated union is wider. A value outside the set is refused upstream by
  `hasKnownRunVocabulary`, as before. The casts are harmless afterwards and can stay.
- Old links `/analysis-settings?group_id=…` open the page without the group; nothing in the product emits them now.
- `.panel:focus-visible` and `.flush` in `analysis-settings-page.module.css` are now only a frame of the profile
  table. They were left as they were to keep the styling census unchanged.
