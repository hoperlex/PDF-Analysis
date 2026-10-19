# Task W59-SECTION-SEAL-01 — version stage, confirmed section and section-routed run start

task_id: W59-SECTION-SEAL-01

## Outcome

An expert classifies one document version (project stage `P`/`R` plus one of the
15 section codes) through the API; the classification is persisted outside the
immutable `document_version` row and projected on version reads; run start and
re-audit read the persisted classification and resolve the profile through a
section-keyed registry. A version with no classification, an unknown code or a
section without an executable profile is refused; there is no AR fallback.

## Depends on

- `W59-SECTION-IDENTITY-DECISION-01` — completed design input.
- `W59-INT-SECTION-SUGGESTION-PREP-01`, `W59-INT-CONFIRMATION-PREP-01`,
  `W59-INT-SECTION-ROUTE-PREP-01`, `W59-INT-STAGED-ROUTE-PREP-01` — completed pure modules.

## Frozen inputs

- base commit: the `integration/night-1020` commit that adds this file (descendant of `origin/dev` `9cf21cc0`);
- API contract: `contracts/api/v1/openapi.json` 48 paths / 55 operations / 131 schemas;
- error catalogue: 25 API codes, 23 stored;
- migration head: `0023_norm_citations`; this task alone takes `0024`;
- rulings: `R-135` (bounded checks), `R-139` (seal before W56b/W58-code close).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W59-SECTION-SEAL-01
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['path_count'],len(d['operations']),len(d['schema_names']),d['migration_head'])"`

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

- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `db/migrations/versions/**`
- `src/auditmanager/sections/**`
- `src/auditmanager/documents/**`
- `src/auditmanager/runs/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/**`
- `src/auditmanager/dashboard/**`
- `src/auditmanager/analysis/text/profile.py`
- `src/auditmanager/analysis/text/profile_registry.py`
- `src/auditmanager/analysis/text/profiles/ar/**`
- `src/auditmanager/shared/**`
- `tests/support/**`
- `tests/contract/**`
- `tests/integration/sections/**`
- `tests/integration/runs/**`
- `tests/integration/api/**`
- `tests/integration/db/**`
- `tests/integration/composition/**`
- `tests/unit/**`
- `tests/e2e/pc01/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/generated/**`
- `web/src/entities/project/model/section.ts`
- `web/tests/**`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/manual-tests/**`
- `infra/deploy/README.md`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/serve.py`
- `docs/program/W59-SECTION-SEAL-01.md`
- `docs/program/tasks/W59-SECTION-SEAL-01.md`

## Lane resources

- foundation_instance: `auditmanager-w59-section-seal`
- postgres_port: `57480`
- s3_api_port: `61080`
- s3_console_port: `61081`
- postgres_db: `auditmanager_w59_section_seal`
- s3_bucket: `auditmanager-w59-section-seal`

## Forbidden hotspots

Root dependency/lock files (`pyproject.toml`, `uv.lock`, `web/package*.json`),
`web/src/_app/providers.tsx`, global styles, `docs/program/CURRENT_STATE.md`,
`DEBT_REGISTER.md`, `OWNER_RULINGS_*`, `src/auditmanager/analysis/text/profiles/<other codes>/**`
(owned by `W59-SECTION-PROFILES-01`), refs, tags, the stand.

## Non-goals

No web screen (the classification UI is the next slice), no comparison API, no
classification correction workflow (a conflicting choice is refused), no
backfill from `document.section`, filename or current head, no live provider call,
no full gate.

## Deliverables

Migration `0024_version_classification`; 15-code `ProjectSection` (adds `PS`,
keeps `PB`; migration 0011's fourteen stay as the historical record); classify
and read operations; run-start/re-audit routing with explicit refusals; a
section-keyed text-profile registry that loads data packages
`src/auditmanager/analysis/text/profiles/<code>/profile.json` + `system_prompt.md`
(format `text-profile/1`, see integration contract) and registers AR from the
existing v1 constants; reseal of all synchronized artifacts; report
`docs/program/W59-SECTION-SEAL-01.md`.

## Required tests

Bounded under `R-135`: contract guards touched by the reseal
(`tests/contract/api_v1`, `tests/contract/domain_p02`, `tests/contract/program`),
`npm --prefix web run api:verify`, typecheck and the web guard/contract tests
the reseal touches; migration upgrade 0023→0024 on the lane's own PostgreSQL
with existing rows; new focused integration tests for classify/refusals/routing
written and run on the lane's own containers. No full gate, no whole frontend
suite, no live journey.

## Integration contract

Text-profile package format `text-profile/1`: `profile.json` keys `format`,
`section_code`, `analysis_profile_id` (`ap_` ULID), `prompt_bundle_id` (`pb_`
ULID), `profile_version`, `status` (`draft`|`reviewed`), `title_ru`, `source`
(`repository`, `commit`, `files[{path, sha256}]`); `system_prompt.md` replaces
v1's `SYSTEM_PROMPT`; categories, response schema, user preamble, page banner and
token limits stay v1's. A package whose `section_code` duplicates another or is
outside the 15 refuses at load. Report the new surface counts, error-code
decisions, migration name and any profile packages the registry found.

## Failure/idempotency/security cases

Expert-only write (admin alone refused); exact repeat keeps the first confirmer;
conflicting stage/section refused; foreign project/document/version refused;
unclassified, unknown or profile-less section refused at run start and re-audit;
an existing run keeps its pinned profile.

## Rollback / feature flag

Revert the merge; migration 0024 has a downgrade that drops only its new table.
