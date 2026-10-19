# W59-SECTION-UI-01 — section and stage classification screens

Task: [`tasks/W59-SECTION-UI-01.md`](tasks/W59-SECTION-UI-01.md). Branch
`agent/w59-section-ui-01`, base `6231c0e6`: the contract commit `a23433ed`, plus
`integration/night-1020` `2b93655d`, plus the frozen task file. Nothing was pushed, merged or
tagged. The live journey and the full gate are deferred (`R-135`).

## What a user sees now

| Screen | Before | Now |
|---|---|---|
| Version (`/projects/{p}/versions/{v}`) | manifest and runs | a «Стадия и раздел» panel (`id="version-classification"`) under the manifest. **Confirmed:** badges «Стадия: П/Р» and the section («Архитектурные решения (АР)»), who confirmed it and when, plus «профиль анализа недоступен» when the review's option for that section has `executable: false`. **Unconfirmed, expert:** the form described below. **Unconfirmed, not an expert** (an `admin` alone included, as the API refuses it): «Раздел ещё не подтверждён экспертом.» |
| Form (expert) | — | Stage radios «П — проектная» / «Р — рабочая». All fifteen sections: suggested ones first, by score, each with its evidence (file-name patterns, text keywords, name found in text); then the rest in `S-5` order. A section without a profile is marked and stays choosable. Nothing is pre-selected. «Подтвердить раздел» is disabled until both choices are made and while the request is in flight; a synchronous single-flight gate makes a double click send one `PUT`. **409 `version_already_classified`:** the review and the version are re-read, the panel switches to the stored classification, and it notes that this came from another decision. **403:** a role sentence. No override is offered. |
| Document (`/documents/{d}`) and every version list | rows without a section | every `VersionRow` carries the stage/section badges, or «Раздел не подтверждён» |
| Project (`/projects/{p}`) | static 14-tab stub (`R-18`) | the project's storage structure: the 15 sections in `S-5` order (АР, АИ, ПЗ, ПОС, ТХ, КЖ, КМ, ОВ, ВК, ПТ, ЭОМ, СС, ИТП, ГП, ПБ). Each lists the documents whose **current** version is confirmed for it, with a count and a stage badge on every row. Then «Не классифицировано», whose rows open the version at its classification panel. The upload panel sits below. When the server has more than one page, the screen says the grouping covers this page. |
| Run control (`features/start-run`) | `422 required_norm_unavailable` fell through to «Запрос завершился ошибкой на сервере» | `reference_kind: version_classification` → «У версии не подтверждены стадия и раздел.» plus a «Подтвердить стадию и раздел» link to `#version-classification`. `analysis_profile` → «Для подтверждённого раздела нет профиля анализа.» plus a link to the panel. Neither is retryable, and neither offers АР or any other profile. Any other `reference_kind` gets the catalog sentence. The queue's re-audit (`entities/execution`) uses the same sentences. |

Section names now follow `S-3`: АИ «Архитектурные решения (интерьер)», ОВ «Отопление,
вентиляция и кондиционирование», ЭОМ «Электроснабжение и электрооборудование», ПТ
«Противопожарный водопровод», ПОС «Проект организации строительства». PS is ПЗ «Пояснительная
записка». A unit test holds all fifteen names to
`src/auditmanager/sections/suggestion_patterns.json`.

## Data flow

- **Version screen.** `getDocumentVersion` runs first. Then `getVersionSectionReview` runs at
  the version body's own `project_uid` / `document_uid` / `version_uid` (never the address bar),
  under the new key `queryKeys.versions.sectionReview(uid)`. The route passes the session's
  `roles` from `requireScreen` to the page, as `/norms` does; they only choose which control to
  draw.
- **`classifyDocumentVersion`** (`features/classify-version/model/use-classify-version.ts`,
  `retry: false`). On success it writes the answer into `versions.sectionReview(uid)` and
  `versions.detail(uid)`, then invalidates the review, the document's first `versions.list`
  page, `projects.all()` (the project structure) and `dashboard.summary()`. On `409
  version_already_classified` it invalidates the review and the version.
- **Dashboard invalidation.** It is defensive. The seal branch's
  `dashboard/repository.py` still groups the breakdown by the document's legacy `section`,
  which a classification does not write. The backend is unwritten, so the integrator's rule
  "if unsure, invalidate" applies. The guard map entry is `true`.
- **Project structure.** It uses only `listDocuments`, which the screen already made. Each
  item is the document's current `DocumentVersion`, and the contract gives that schema the
  optional `classification`, so the grouping needs **no request per document**. This
  depends on the backend filling `classification` in list items as the schema says (see
  Risks).
- **Run refusals** are worded once in `entities/audit-run/model/routing-refusal.ts`. Both
  `classifyRunFailure` and `executionFailure` use that module.

## Files

New:

- `web/src/entities/document-version/{model/classification.ts, api/use-section-review.ts, ui/classification-badges.tsx, ui/classification-badges.module.css}`
- `web/src/entities/audit-run/model/routing-refusal.ts`
- `web/src/features/classify-version/**` (mutation hook, single-flight gate, form view and form, layout module)
- `web/src/widgets/version-classification/**` (the panel)
- `web/src/widgets/project-sections/model/structure.ts` (the grouping)
- tests: `web/tests/unit/sections/{fixtures.ts, classification-panel.test.ts, classify-command.test.ts, project-structure.test.ts, run-refusal.test.ts}` and `web/tests/unit/projects/section-catalogue.test.ts`

Changed:

- web/src: `entities/project/{model/section.ts, index.ts}`, `entities/document-version/{index.ts, ui/version-row.tsx, api/use-document-version.ts}`, `entities/audit-run/{index.ts, model/run-failure.ts}`, `entities/execution/model/failure.ts`, `features/start-run/ui/start-run-control.tsx`, `widgets/project-sections/**` (rewritten), `widgets/run-list/ui/run-list.tsx`, `_pages/version-detail`, `_pages/project-detail`, `app/projects/[project_uid]/versions/[version_uid]/page.tsx`, `app/bff/v1/[...path]/route.ts` and `shared/api/authorization.ts` (prose now «fifty-seven operations across fifty paths»), `shared/lib/{routes.ts, index.ts}` (`routes.versionClassification`, `VERSION_CLASSIFICATION_ANCHOR`)
- web/tests: `guards/rendered-language.guard.test.ts`, `unit/screens/{routes.test.ts, cold-load.test.ts, forms-and-pages.test.ts, route-screens.ts}`, `unit/run/input-budget.test.ts`, `unit/styles/{screens.ts, contrast.test.ts}`
- Deleted: `web/tests/unit/screens/project-sections.test.ts`. It pinned the stub's sentences, which the screen no longer has; `unit/sections/project-structure.test.ts` replaces it.
- Journey: `tests/e2e/pc01/journey/{manifest.json, README.md, verify-acceptance.mjs}`
- Granted by the integrator (2026-10-20):
  - `web/src/shared/api/query-keys.ts`: `versions.sectionReview`
  - `web/docs/PC01_UI_SEAM.md`: §6 row and a note
  - `web/tests/guards/dashboard-invalidation.guard.test.ts`: the map line, `true`
  - `tests/contract/test_alpha_acceptance_command.py`: `WRITE_STEPS` from the manifest

  The grants are recorded in the task file's allowed paths.

`authorization.ts` maps no operation to a role; it holds only the two refusal sentences. So
the only edit there was the prose count. The backend role table already has
`classifyDocumentVersion: expert` and `getVersionSectionReview: any role`, and the
panel follows it.

### Guard and instrument changes

- **Rendered-language guard.** It seeds the section review (unconfirmed) in the loaded client.
  It renders these extra shapes: the confirmed panel (profile-less section, after a 409), the
  form pending, the form after 409, the form after 403, a failed review read, and the project
  structure with both stages. `ProjectStage` and `ProjectSection` joined `TRANSLATED_SCHEMAS`.
  A Latin code on screen is now an offence, and every member must reach a
  `data-project-stage` / `data-section-group` attribute.
- **Rendered-language guard, base repair.** At the lane's base, the case "renders every member
  of every translated schema" was **red**: the five `FindingCategory` members `W57A-SEAL-01B`
  added (`fire_safety`, `evacuation`, `accessibility`, `insulation`, `sound`) were unseeded. A
  probe worktree at `6231c0e6` reproduced it. Five findings now seed them.
- **Route seeds.** `route-screens.ts` has a second seed for the version address,
  `version-detail-reader`, with `roles: ['admin']`, so the instruments read the read-only
  branch.
- **Contrast census.** It renders the loaded panel, the structure, the confirmed panel and the
  refused form. `.am-form__problem` became reachable, so its `UNREACHED_BY_ANY_SCREEN` entry was
  deleted, as the ratchet demands.
- **Journey.** It has a new write step, `classify-version`, between `upload-document` and
  `start-run`:
  - it clicks `input[data-stage-choice="P"]`, then `input[data-section-choice="AR"]`, then
    «Подтвердить раздел»;
  - it expects `PUT …/classification` → `200` echoing `version_uid`, `project_stage: "P"` and
    `section_code: "AR"`;
  - it captures `document_uid` from `[data-classified-document]`;
  - it forbids `[data-classification-failure]` and `[data-classification-conflict]`.

  The read walk's `version` route declares `getVersionSectionReview`.
  `verify-acceptance.mjs` and the acceptance contract test now read the write-step count
  from the manifest, as they already read the route count.

## Checks (bounded, R-135)

All checks ran on the committed tree of this lane unless stated otherwise.

| Command | Result |
|---|---|
| `npm --prefix web ci` | ok (184 packages) |
| `npm --prefix web run lint -- --quiet` | clean |
| `npm --prefix web run typecheck` | clean |
| `npx vitest run tests/unit/sections tests/unit/projects/section-catalogue.test.ts` (from `web/`) | 5 files, all pass |
| `npx vitest run tests/guards/rendered-language.guard.test.ts` | 26/26 |
| `npx vitest run tests/guards tests/contract tests/unit/{screens,run,execution,projects,widgets,sections,styles,api,shell}` | 85 files, 1302 passed, **7 failed**. All 7 are pre-existing and outside this lane (below). |
| `$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/e2e/test_pc01_journey_conformance.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/program tests/contract/test_alpha_acceptance_command.py` (`PY` = w55b-main-candidate venv) | **181 passed**. The surface-prose test is fully green. It was briefly red over a comment of mine ("three path identities"), now reworded. `CURRENT_STATE.md` is not flagged. |

**The 7 vitest failures predate this lane.** They are 5 cases in
`tests/contract/openapi-drift.contract.test.ts` and 2 in
`tests/guards/frontend-lock.guard.test.ts`. At `6231c0e6`:
- `web/openapi/openapi.json` hashes to `a79d07c9…`;
- `contracts/api/v1/openapi.json` hashes to `3e1f070a…`;
- the committed generated client therefore differs from what the contract generates.

This lane did not change any of those files (`git diff 6231c0e6..HEAD` on `contracts/`,
`web/openapi/`, `web/src/shared/api/generated/` and `web/FRONTEND_LOCK.json` is empty), and all
of them are forbidden hotspots. Regenerating them belongs to `W59-SECTION-SEAL-01` or the
integrator.

## Deferred

- The live PC-01 journey (`R-135`). The new step is checked statically only: handles exist in
  `web/src`, the operation, method and path are in the contract, `200` is published, and the
  capture is bounded.
- The full frontend suite and `make gate`.
- A browser look at the new screens.

## Risks and known limitations

1. **List items must carry `classification`.** The project structure and the list badges read
   `DocumentVersion.classification` from `listDocuments` / `listVersions`. The contract
   implies it, since the items are `DocumentVersion` and that schema carries the field. The
   seal branch has no implementation committed yet. If the backend omits the field in list
   answers, every document shows as «Не классифицировано»: visible, but wrong.
   **Integrator:** check the SEAL implementation fills it in list serialisation, or add a
   contract test.
2. **The project structure groups one page** of `listDocuments` (50 documents). Larger projects
   page through it, and the screen says so.
3. **Run rows carry no section.** `RunStatus` has no classification. The version's badge
   stands above its run list on the version screen. A run pins its profile at start, so the
   version's badge is not drawn per run.
4. **The journey assumes a fresh, unclassified upload and an expert session.** Both hold for
   every write run, since each run uploads a new document. On a stand without an AR text
   profile the `start-run` step would now get the routing refusal instead of a run. That is
   the intended behaviour, but it makes the journey red until the profile exists.
5. **The dashboard invalidation on classify is defensive** (see Data flow) and can become
   `false` once the seal's dashboard read is final.
6. **The read-only panel uses the route's session roles.** A role change mid-session shows up
   on the next navigation, as on `/norms`. The API decides the write either way.

## Integrator instructions

1. Merge `W59-SECTION-SEAL-01` first, then this branch. Conflicts are possible only in
   `web/docs/PC01_UI_SEAM.md`, `query-keys.ts` and the guard files if the seal lane also
   touched them; it was not expected to.
2. Regenerate `web/openapi/openapi.json`, the generated client and `FRONTEND_LOCK.json` from
   the final contract. That is the seal lane's job, and it clears the 7 pre-existing reds.
3. Confirm risk 1 against the seal implementation.
4. The live journey, with the new `classify-version` step, belongs to the deferred complete
   gate.

## Forbidden hotspots

`git diff --name-only 6231c0e6..HEAD` contains none of:

- `contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`
- `web/src/_app/providers.tsx`, `web/src/app/globals.css`
- `web/package*.json`
- `src/**`, `db/**`
- `docs/program/CURRENT_STATE.md`

The four paths outside the frozen allowed set were each granted by the integrator (listed
above). No refs, tags or stand were touched.
