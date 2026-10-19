# W59-SECTION-SEAL-01 — version stage, confirmed section and section-routed run start

**Base:** `a1a25ebc` (night round 1 on `origin/dev` `9cf21cc0`), branch
`agent/w59-section-seal-01`, isolated worktree `w59-section-seal`, lane PostgreSQL 57480 /
MinIO 61080. **Status:** development candidate under `R-135`; no full gate, no live journey,
no paid provider call, no push, merge into another branch or tag.

Commits on the branch: `a23433ed` (contract seal; the UI lane branched from it), `0468c0fc`
(merge of `integration/night-1020`, bringing the 13 `W59-SECTION-PROFILES-01` packages so the
registry is tested against them), `bd08e03c` (backend and tests), and the closing commit that
regenerates the web mirror and adds this report (its SHA is in the hand-back message).

## Result

An expert classifies one document version — project stage `P`/`R` plus one of the fifteen
sections — through `classifyDocumentVersion`. The classification is stored once, outside the
immutable `document_version` row, in `document_version_classification` (migration
`0024_version_classification`), and every read that returns `DocumentVersion` projects it
(`listDocuments`, `listVersions`, `getDocumentVersion`; `uploadDocument` answers a new version,
which is unclassified). `startRun` and `reauditRun` read the persisted classification in the
run-creating transaction and resolve the profile through a section-keyed text-profile
registry; an unclassified version, an unknown code or a section without a registered profile
is refused before the idempotency key is claimed. There is no AR fallback. The executor runs
every v1-style text run with the profile and prompt bundle the run pinned.

### Surface

| | before | after |
|---|---|---|
| paths / operations / schemas | 48 / 55 / 131 | 50 / 57 / 137 |
| API error codes / stored vocabulary | 25 / 23 | 25 / 23 |
| migration head | `0023_norm_citations` | `0024_version_classification` |

New operations (tag `documents`), each addressing a version **through its document and
project** so a foreign version is refused:

- `classifyDocumentVersion` — `PUT /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification`,
  body `ClassifyDocumentVersionRequest {project_stage, section_code}`, `200 VersionClassification`.
  `expert` only (`admin` alone is `403 permission_denied`, `required_capability: role:expert`);
  the command re-reads the actor's role set in its own transaction. No `Idempotency-Key`: an
  exact repeat answers the stored row with its first confirmer; a different stage or section
  is `409 conflict` (`conflict_reason: version_already_classified`) and writes nothing.
- `getVersionSectionReview` — `GET .../section-review`, any one role, `200 SectionReview`:
  all fifteen `SectionReviewOption`s (code, Russian name from the reviewed suggestion
  catalogue, `executable` from the registry, `suggestion` evidence or `null`), the
  classification or `null`, and `recognised_text_consulted`. Evidence is the stored upload
  name plus the bundle's recognised-text markdown (read from the store, held to its SHA-256);
  nothing is pre-selected.

New schemas: `ProjectStage`, `ClassifyDocumentVersionRequest`, `VersionClassification`,
`SectionSuggestion`, `SectionReviewOption`, `SectionReview`. `ProjectSection` gains `PS`
(after legacy's fourteen, which keep their order); `DocumentVersion` gains the optional
`classification` (omitted while unclassified, never `null`).

### Error-code decision

No code was added (the brief's preference). Registered in `error-codes.json` notes:

- `conflict` / `conflict_reason: version_already_classified` — a different stage or section
  for an already-classified version.
- `required_norm_unavailable` / `reference_kind: version_classification` — run start or
  re-audit of a version with no persisted classification; `reference_kind: analysis_profile` —
  the confirmed section has no registered text profile (or the executor meets a pinned pair
  the registry does not hold). The integrator accepted this as a semantic overload of the
  norms code and registers it as debt.

### Migration `0024_version_classification`

`document_version_classification (version_uid PK → document_version RESTRICT, project_stage
CHECK P/R, section_code CHECK over the fifteen, confirmed_by_user_uid → app_user RESTRICT,
confirmed_at default now())` with `trg_document_version_classification_immutable`
(`am_immutable_row`, `AM003` on UPDATE/DELETE). The confirmer's foreign key is registered in
`access.references` (integrator grant), so purging a confirmer is `account_referenced`.
`ck_document_section` is replaced by the fifteen-code CHECK; `0011` stays the historical
fourteen. No backfill. The downgrade drops the table and restores the fourteen-code CHECK
(`NOT VALID` while a `PS` document exists, so no document row is deleted or rewritten).
Schema inventory resealed: columns +5 → 465, relations +1 → 53, constraints +7 → 499 (plus
the redefined `ck_document_section`), indexes +1 → 126, triggers +1 → 54; the other six
families unchanged.

### Text-profile registry

`analysis/text/profile_registry.py`: AR from the v1 constants (no `profiles/ar/` package; one
is refused as a duplicate) plus every `profiles/<code_lower>/{profile.json,
system_prompt.md}` in `text-profile/1`. Exactly the eight keys; `section_code` in the fifteen
and equal to the directory name; `ap_`/`pb_` identities unique across entries; `status`
`draft`/`reviewed` (both executable); `source.files` with SHA-256s; exactly one trailing
`"\n"` of the prompt file is stripped. Any defect refuses the whole load, and the composition
root turns it into a start-up `ConfigurationError` for the API and the worker. Against the
merged tree it registers **14** sections: AR (builtin) and AI, EOM, GP, ITP, KJ, KM, OV, POS,
PS, PT, SS, TX, VK (all `draft`). **PB has no profile** and is refused at run start.

### Run start and execution

- `start_audit_run` / `reaudit_run` take `section_profiles` (the registry's table) **or** an
  explicit profile pair (in-process callers and suites); both or neither is a `ValueError`.
  The served application always passes the table and never a pair
  (`test_the_served_application_routes_by_section.py`).
- A key the ledger already knows replays its run using that run's pinned profile for the
  fingerprint — an existing run keeps its profile; re-audit routes from the version's
  classification now, never from the source run.
- `execute_run(..., text_profiles=registry.resolve)` resolves the run's pinned pair before any
  state change or effect; `None` (in-process harness only) keeps the pre-seal AR behaviour.
  The API carrier and the worker runtime always pass the resolver.

## Refusals proven

| case | evidence |
|---|---|
| admin-only classify → 403 `role:expert`; command's own check with `{}`/`{admin}` | HTTP + command tests |
| exact repeat keeps first confirmer; different stage/section → 409, nothing written | HTTP tests |
| concurrent first confirmations: loser waits, then same row or 409 | command test (two sessions, thread) |
| foreign version / document / unknown project → 404 on both operations | HTTP tests |
| unknown stage/section → 422 | HTTP test |
| unclassified version (legacy `document.section = AR`) → 422 `version_classification`, no run, no command record | HTTP test |
| PB-classified → 422 `analysis_profile`, no AR substitute | HTTP test |
| KJ/TX/AR routed to their own pairs; replay answers the run; re-audit re-routes, source pin unchanged | HTTP tests |
| newer version unclassified, older keeps classification and run pin | command + projection tests |
| executor: AR-routed run reproduces the recorded corpus run; KJ run sends the KJ prompt; unregistered pin refused before any stage | routed-execution tests |
| populated 0023 → 0024: no fabricated row, version/run/document unchanged; AM003, CHECK, PK, FK; downgrade | migration test |

## Checks run (lane-local, `R-135` bounded)

All Python with the lane `.venv` (reference packages of `w55b-main-candidate`), `-c
pyproject.toml --rootdir=.`; DB/S3 tests on the lane's own containers.

- New tests: `tests/integration/db/test_version_classification_migration.py` 4 passed;
  `tests/integration/runs/test_w59_section_routing_over_http.py` 12 passed;
  `test_w59_classification_command.py` 8 passed; `test_w59_routed_execution.py` 3 passed;
  `test_w59_classification_projection_over_http.py` 2 passed;
  `tests/integration/composition/test_the_served_application_routes_by_section.py` 5 passed;
  `tests/unit/analysis` 30 passed (registry tests plus the profiles lane's package tests).
- Mutation probes (each reverted from git): composition without the table → 2 failed; AR
  fallback in `start_audit_run` → 2 failed; executor always AR → 2 failed; conflict answered
  as a repeat → 2 failed; duplicate section accepted by the loader → 1 failed. Ignoring the
  stored row in `classify_document_version` survives by design: the `ON CONFLICT` re-read is a
  second layer that still refuses.
- `tests/integration/api tests/integration/runs tests/integration/sections tests/unit`:
  1055 passed, 23 failed; 18 were this seal's pins (fixed and re-run green), 5 are
  pre-existing and fail identically on the base tree (`test_v2_recorded_merge_stage.py` ×3,
  `test_query_surface.py` FindingCategory ×2).
- Head-pinned DB suites: 136 passed; 12 downgrade-chain cases fail identically on the base
  tree (`0022` downgrade: "cannot drop columns from view").
- `tests/contract`: API/domain/architecture/program guards green except the out-of-scope
  prose claims below and pre-existing base failures (`test_cp00_candidate.py` git sandbox,
  `test_error_kernel` twenty-four, `fixtures_seeded` categories).
- Web: `api:generate` / `api:verify` OK (contract and mirror SHA-256
  `3e1f070a6db0dab87bd358112a3e66ebe6cc2bd44656c3af5152ff1e46a172ac`), `typecheck` exit 0,
  touched vitest files green except `rendered-language.guard` FindingCategory seeding, which
  fails identically on the base tree.

The final command list with exit statuses is in the hand-back message.

## Deferred, outside this lane

- Complete `make gate`, whole frontend suite, live journey `e2e:pc01`, paid provider (R-135).
- Suites outside the allowed paths that must classify before a served run or move a head pin:
  `tests/characterization/w13_baseline/**` (startRun records now need a classify step),
  `tests/integration/qa_w55b/**`, `tests/integration/jobs/test_recorded_v2_publication_gate.py:176`
  and `tests/integration/norms/references/test_catalogue_input_db_s3_accept.py:170` (head
  literal `0023`). Not run here.
- Prose claims outside the allowed paths: `web/src/app/bff/v1/[...path]/route.ts` and
  `web/src/shared/api/authorization.ts` (UI lane), `docs/program/CURRENT_STATE.md` (integrator).

## Risks and limits

- **Every pre-seal version is unrunnable until an expert classifies it**, by design (no
  backfill). The stand's PC-01 journey and the UI must classify before run start.
- In `recorded` mode only AR has recordings; a run routed to a package profile fails at
  `text_analysis` for want of a recording. Package prompts are `draft` until an expert review.
- The dashboard's `section_breakdown` still groups by the legacy `document.section`, not by
  the confirmed classification of the current version (recorded limitation; changing it
  changes `SectionDocumentCount`'s documented meaning and its suites).
- `required_norm_unavailable` now also carries the classification/profile refusals (accepted
  overload, debt to register).
- Corrections of a classification are refused; the append-only correction workflow is a later
  task.

## Integrator instructions

1. Merge this branch after the profiles lane; run `tests/unit/analysis` and
   `tests/integration/runs/test_w59_routed_execution.py` on the merged tree.
2. `CURRENT_STATE.md`: surface **50 paths / 57 operations / 137 schemas**, migration head
   **`0024_version_classification`**, error catalogue unchanged at 25.
3. The UI lane fixes the two web prose counts and owns the classify step of the browser
   journey; take this branch's `web/openapi/**`, `generated/**` and `FRONTEND_LOCK.json`.
4. Schedule the out-of-scope suite updates listed above before the final gate.

## Hotspot proof

Changed paths are inside the task's allowed paths plus `src/auditmanager/access/references.py`
(integrator grant by message, recorded in the task file). Not touched: `pyproject.toml`,
`uv.lock`, `web/package*.json`, `web/src/_app/providers.tsx`, global styles,
`CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*`, other sections' profile packages,
any ref or tag. Web edits are limited to `web/openapi/**`, `web/src/shared/api/generated/**`,
`web/FRONTEND_LOCK.json`, `web/src/entities/project/model/section.ts` and two web unit tests,
all in the contract commit before the UI lane took ownership of `web/src/**`.
