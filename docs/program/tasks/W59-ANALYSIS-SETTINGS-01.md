# Task W59-ANALYSIS-SETTINGS-01 — section profiles proven by recorded runs and listed in «Настройки анализа»

task_id: W59-ANALYSIS-SETTINGS-01

## Outcome

1. A confirmed version of АИ, ПЗ, ПОС or ТХ runs end to end in recorded mode with
   its own section profile: the run pins that profile's identity and prompt-bundle
   hash, the recorded response is parsed by the v1 stage and findings are
   published; ПБ and an unclassified version are refused; another section's
   recording never satisfies the call.
2. «Настройки анализа» (today an honest stub) lists the 15 sections with their
   analysis profile: identity, version, status (`draft`/`reviewed`), prompt-bundle
   hash and legacy source, and «профиль не создан» for ПБ — read-only for admin and
   expert.

## Depends on

- `W59-SECTION-SEAL-01`, `W59-SECTION-PROFILES-01`, `W59-SECTION-UI-01` — completed, merged.

## Frozen inputs

- base commit: `c4cbc026ce4bd1d61f8c06c4ecb4a1c76a65b8d6` (`origin/dev`);
- API contract at base: 50 paths / 57 operations / 137 schemas, head
  `0024_version_classification`; phase B starts from the commit the integrator names;
- rulings: `R-135`, `R-139`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W59-ANALYSIS-SETTINGS-01 (phase B only, after the integrator hands over the contract slot)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['path_count'],len(d['operations']),len(d['schema_names']))"`

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

- `tests/integration/runs/test_w59_section_profile_recorded.py`
- `tests/integration/sections/**`
- `fixtures/recorded/sections/**`
- `src/auditmanager/analysis/text/recorded.py`
- `src/auditmanager/analysis/text/profile_registry.py`
- `contracts/api/v1/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/**`
- `tests/support/**`
- `tests/contract/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/**`
- `web/src/entities/**`
- `web/src/features/**`
- `web/src/widgets/**`
- `web/src/_pages/analysis-settings/**`
- `web/src/app/analysis-settings/**`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/tests/**`
- `web/docs/**`
- `tests/e2e/pc01/**`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/manual-tests/**`
- `infra/deploy/README.md`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/serve.py`
- `docs/program/W59-ANALYSIS-SETTINGS-01.md`
- `docs/program/tasks/W59-ANALYSIS-SETTINGS-01.md`

**Phasing (binding):** phase A may touch only the first five paths and the two docs
files. Every other path opens only after the integrator's message that hands over
the contract slot, from the commit it names.

## Lane resources

- foundation_instance: `auditmanager-w59-analysis-settings`
- postgres_port: `57520`
- s3_api_port: `61120`
- s3_console_port: `61121`
- postgres_db: `auditmanager_w59_analysis_settings`
- s3_bucket: `auditmanager-w59-analysis-settings`

## Forbidden hotspots

Migrations, dependency files, `web/src/_app/providers.tsx`, global styles, the
profile packages' content (`src/auditmanager/analysis/text/profiles/**` — read only),
`CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No profile editing or upload, no change of a profile's `status`, no live provider
call (recordings are synthetic and labelled so), no full gate.

## Deliverables

Phase A: synthetic recorded responses for АИ, ПЗ, ПОС, ТХ keyed exactly as the
recorded adapter keys requests, and the routed end-to-end tests. Phase B: one read
operation listing the registry with the reseal, and the «Настройки анализа» page.
Report `docs/program/W59-ANALYSIS-SETTINGS-01.md`.

## Required tests

Phase A: the new integration tests on the lane's own containers. Phase B:
`tests/contract`, `api:verify`, lint, typecheck, changed vitest files and the
rendered-language guard, journey static conformance. No full gate, no live journey.

## Integration contract

Phases A and B merge as one slice. Synthetic recordings never count as field
evidence for the profiles' review.

## Failure/idempotency/security cases

A recording made for one profile's prompt bundle must not answer another's; a
missing recording fails the run explicitly; the settings page is read-only.

## Rollback / feature flag

Revert the merge; no data migration.
