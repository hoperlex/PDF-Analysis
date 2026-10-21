# Task W59-VERSION-UPLOAD-01 — upload a further version into an existing document set

task_id: W59-VERSION-UPLOAD-01

## Outcome

On a document screen a user uploads the next version of that document set (the same
portal bundle envelope `uploadDocument` accepts); the new immutable version gets the
next ordinal, becomes the document's current version, starts unclassified (no stage
or section inherited) and immediately appears in the version list, in the project
structure and as a comparison candidate. Older versions, their classifications,
runs, findings and decisions are untouched.

## Depends on

- `W59-SECTION-SEAL-01`, `W59-SECTION-UI-01`, `W59-VERSION-COMPARE-01` — completed, merged.

## Frozen inputs

- base commit: `1af17a4869546119b371bfba68e1f2148340a6af` (`origin/dev`);
- API at base: 51 paths / 58 operations / 147 schemas; head `0024_version_classification`;
- ingest: `src/auditmanager/ingest/service.py` `upload_bundle`, `documents/repository.py`
  `publish_version`; W55b envelope rules (portal bundle only, ≤ 500 pages / 250 MiB);
- design: `W59-SECTION-IDENTITY-DECISION-01.md` (a new version inherits nothing; the
  current-head pointer never rewrites older facts); rulings `R-135`, `R-139`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W59-VERSION-UPLOAD-01 (phase B only, after the integrator hands over the contract slot)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['surface'])"`

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

- `src/auditmanager/ingest/**`
- `src/auditmanager/documents/**`
- `tests/integration/ingest/**`
- `tests/integration/documents/**`
- `tests/unit/ingest/**`
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
- `web/src/_pages/document-detail/**`
- `web/src/app/projects/**`
- `web/src/app/bff/**`
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
- `docs/program/W59-VERSION-UPLOAD-01.md`
- `docs/program/tasks/W59-VERSION-UPLOAD-01.md`

**Phasing (binding):** phase A may touch only the first five paths and the two docs
files. Every other path opens only after the integrator's message that hands over
the contract slot, from the commit it names.

## Lane resources

- foundation_instance: `auditmanager-w59-version-upload`
- postgres_port: `57550`
- s3_api_port: `61150`
- s3_console_port: `61151`
- postgres_db: `auditmanager_w59_version_upload`
- s3_bucket: `auditmanager-w59-version-upload`

## Forbidden hotspots

Migrations (none expected; if the schema cannot express the next version, stop and
report), dependency files, `web/src/_app/providers.tsx`, global styles,
`CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No change of the envelope rules, no bare-PDF upload, no automatic classification
inheritance, no version deletion, no full gate.

## Deliverables

Phase A: an ingest/documents service that admits a bundle as the next version of an
existing document with the existing custody/outbox discipline, and its tests. Phase B:
`uploadDocumentVersion` (multipart like `uploadDocument`) with the reseal, the BFF
upload forwarding for the new path with the same memory bounds, and «Загрузить новую
версию» on the document screen. Report `docs/program/W59-VERSION-UPLOAD-01.md`.

## Required tests

Phase A: focused integration tests on the lane's own containers (next ordinal,
current pointer moves, older version facts unchanged, foreign document refused,
idempotent retry). Phase B: `tests/contract`, `api:verify`, lint, typecheck, changed
vitest files, rendered-language guard, journey static conformance. No full gate.

## Integration contract

Phases A and B merge as one slice.

## Failure/idempotency/security cases

Foreign/missing document or project refused; an exact retry with the same idempotency
key returns the same version; a concurrent second upload gets the following ordinal,
never a duplicate; envelope refusals as `uploadDocument`.

## Rollback / feature flag

Revert the merge; versions already uploaded stay valid immutable versions.
