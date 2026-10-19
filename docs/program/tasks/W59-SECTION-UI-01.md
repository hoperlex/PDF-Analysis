# Task W59-SECTION-UI-01 — section and stage classification screens, project structure by sections

task_id: W59-SECTION-UI-01

## Outcome

An expert opens a document version, sees the 15 sections with the suggested ones
first, picks the project stage (П/Р) and the section and confirms; the version,
document and project screens then show the confirmed stage and section, the project
page groups its documents by confirmed section (the storage structure of a project:
section → document set → versions with stage), and the run control explains a
refusal for an unclassified version or a section without a profile instead of
failing silently. Non-experts see the classification read-only.

## Depends on

- `W59-SECTION-SEAL-01` contract commit `a23433ed` (operations
  `classifyDocumentVersion`, `getVersionSectionReview`, `DocumentVersion.classification`).
- `W59-SECTION-PROFILES-01` — completed, merged.

## Frozen inputs

- base commit: `a23433ed16897f8ccf9586aa4fab33242d530552` merged with `integration/night-1020` `2b93655d4452d0f60aaf549653692d97bc294f07`;
- API contract: 50 paths / 57 operations / 137 schemas, client already generated in `web/src/shared/api/generated/**`;
- refusals: `startRun`/`reauditRun` answer 422 `required_norm_unavailable` with
  `details.reference_kind` `version_classification` (no stage/section) or
  `analysis_profile` (no profile for the confirmed section);
- rulings: `R-135`, `R-139`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/entities/**`
- `web/src/features/**`
- `web/src/widgets/**`
- `web/src/_pages/**`
- `web/src/app/projects/**`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/src/shared/api/authorization.ts`
- `web/src/shared/lib/**`
- `web/src/shared/ui/**`
- `web/tests/unit/**`
- `web/tests/guards/rendered-language.guard.test.ts`
- `tests/e2e/pc01/journey/**`
- `docs/program/W59-SECTION-UI-01.md`
- `docs/program/tasks/W59-SECTION-UI-01.md`

## Forbidden hotspots

`contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`,
`web/FRONTEND_LOCK.json`, `web/src/_app/providers.tsx`, `web/src/app/globals.css`,
dependency files, every backend path (owned by `W59-SECTION-SEAL-01`),
`CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No contract change, no correction workflow for a conflicting classification (409
is shown as "уже подтверждено другим решением"), no comparison screen, no live
journey run (static conformance only under `R-135`), no full frontend suite.

## Deliverables

Classification panel on the version screen; stage/section badges on version,
document and run lists; project page section structure replacing the static
14-section stub; run-control refusal messages; the two surface-prose lines fixed
(fifty-seven operations across fifty paths); PC-01 journey classifies a version
before it starts a run; report `docs/program/W59-SECTION-UI-01.md`.

## Required tests

`npm --prefix web run lint -- --quiet`, `npm --prefix web run typecheck`, the vitest
files of every changed widget/feature/page plus the rendered-language guard;
`pytest tests/e2e/test_pc01_journey_conformance.py
tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/program`. No
full gate, no live journey.

## Integration contract

The integrator merges `W59-SECTION-SEAL-01` first, then this lane; at the window's
end the live journey belongs to the deferred complete gate.

## Failure/idempotency/security cases

403 for a non-expert write is rendered as a role message; a double click sends one
request; 409 shows the stored classification; the run refusal never offers AR as a
fallback.

## Rollback / feature flag

Revert the merge; the API keeps refusing unclassified runs, so the rollback
returns to "classification by API only".
