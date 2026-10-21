# Task W57A-SEAL-01B — API and stage contract reseal

task_id: W57A-SEAL-01B

## Outcome

The published API describes the 0023 citation vocabulary and certified v3 observations, the served API exposes a role-guarded `getRunNormVerification` endpoint that returns a typed refusal until a verified reader exists, and the stage registry reserves v3's optional pinned norms input. Legacy v1/v2 finding JSON omits the new properties.

## Depends on

- `CFB-INT-DEV-PUBLISH-18` — complete at `c157ee0d4601f2bf81c68708ebf556b95b87acd5`.
- `W57A-INT-RULE-FREEZE-01` — complete at `33a4d45647adea7e4f94f2fa0b94f75737eb89b5`.
- `W57A-SEAL-01A` — complete at `c71048f788e5d0bee39a312217dfd4c0912e5bc1`.

## Frozen inputs

- base commit: `c71048f788e5d0bee39a312217dfd4c0912e5bc1`;
- migration head: `0023_norm_citations`;
- domain identifier and error catalogues: the committed 01A versions; no new error code;
- API OpenAPI SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, 47 paths / 54 operations / 124 schemas;
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- W57 plan §A3.5–A3.6 and `W57A-INT-RULE-FREEZE-01`, including the certified zero partition.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: `W57A-SEAL-01B`
- totality_query: `python3 tools/plan/pin_sweep.py reseal-surface migration table error-code route`

This serial owner alone writes the API operation, schema, role, category/reason and stage enumerators. 01A is committed; no parallel writer of these paths is permitted.

## Captured premise evidence

- premise: c710 exact base, 0023 vocabulary, direct prose pins and 48/55/131 served surface measured before changes.

### P-01 — exact base and frozen contract bytes
- captured_at: 2026-10-16
- command: `git rev-parse HEAD; sha256sum contracts/api/v1/openapi.json contracts/analysis/v1/stage-registry.json`
- captured_output:
  ```text
  c71048f788e5d0bee39a312217dfd4c0912e5bc1
  fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227  contracts/api/v1/openapi.json
  bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a  contracts/analysis/v1/stage-registry.json
  ```
- interpretation: the serial base is exact and the API/stage contracts remain the pre-01B bytes.

### P-02 — migration vocabulary and existing route
- captured_at: 2026-10-16
- command: `sed -n '40,57p' db/migrations/versions/20261016_0023_norm_citations.py; rg -n 'getRunNormVerification|norm-verification' src/auditmanager/api contracts/api/v1/openapi.json`
- captured_output:
  ```text
  NORM_CATEGORIES = (
      "evacuation", "fire_safety", "accessibility", "insulation", "sound",
  )
  NEW_REASONS = (
      *OLD_REASONS, "norm_label_unknown", "norm_quote_too_short",
      "norm_quote_ambiguous", "norm_quote_absent", "norm_value_not_in_quote",
      "stated_value_not_in_evidence",
  )
  [no route or schema match]
  ```
- interpretation: 01B must mirror the DB's exact new literals; it must not claim a working citation reader.

### P-03 — direct live prose pin inventory
- captured_at: 2026-10-16
- command: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/contract/api_v1`
- captured_output:
  ```text
  4 failed, 290 passed: CURRENT_STATE.md and PC-01_prototype.md name 0022; CURRENT_STATE.md and ALPHA_ROADMAP.md name 47/54/124; P02_SEAMS.md, infra/deploy/{README.md,proxy/nginx.conf,serve.py}, src/auditmanager/api/{README.md,app.py,health.py,routers/__init__.py,routers/declarations.py,routers/errors.py}, web/src/app/bff/v1/[...path]/route.ts and web/src/shared/api/authorization.ts name the old 47/54/124 counts.
  ```
- interpretation: the exact files below contain live claims that must be resealed to the measured 0023 and 48/55/131 surface. `CURRENT_STATE.md` remains excluded because the integrator owns it. Historical counts inside prose remain historical.

### P-04 — measured operation breakdown
- captured_at: 2026-10-16
- command: `python3 -c "import json; p=json.load(open('contracts/api/v1/openapi.json')); ops=[o for x in p['paths'].values() for k,o in x.items() if k in ('get','post','put','patch','delete')]; print(len(p['paths']),len(ops),len(p['components']['schemas']),sum('422' in o['responses'] for o in ops),sum('422' not in o['responses'] for o in ops))"`
- captured_output:
  ```text
  48 55 131 39 16
  ```
- interpretation: the 422 numerator remains 39, the no-422 count becomes 16, and the only new operation is the refusing report read.

### P-05 — prose mutation anchors after exact consumer reseal
- captured_at: 2026-10-16
- command: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- captured_output:
  ```text
  4 failed, 73 passed: two CURRENT_STATE.md failures reserved for the integrator, and two mutation tests still target the pre-01B literal phrases in nginx.conf and P02_SEAMS.md.
  ```
- interpretation: update only the mutation-test anchors to the newly measured literal text, preserving the proof that a stale claim is detected.

### P-06 — v1/v2 stage version coupling
- captured_at: 2026-10-16
- command: `rg -n 'STAGE_VERSION =|stage_version=TEXT_STAGE_VERSION|stage_version=stage.stage_version' src/auditmanager/analysis/text/stage.py src/auditmanager/runs/executor.py src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/stage.py:67:STAGE_VERSION = "1.0.0"
  src/auditmanager/runs/executor.py:498:        stage_version=TEXT_STAGE_VERSION,
  src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py:171:        stage_version=stage.stage_version,
  ```
- interpretation: registry 1.1.0 would stamp recorded v2 results as 1.1.0 while active v1 executor still stamped 1.0.0. Align only the v1 stage identity constant and prove both producers agree with the registry; artifact_version remains its separate 1.0.0 contract. No W56 executor change is granted.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57A-SEAL-01B.md`
- `docs/program/W57A-SEAL-01B.md`
- `contracts/api/v1/openapi.json`
- `contracts/analysis/v1/stage-registry.json`
- `web/openapi/openapi.json`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/generated/client.gen.ts`
- `web/src/shared/api/generated/index.ts`
- `web/src/shared/api/generated/operations.gen.ts`
- `web/src/shared/api/generated/types.gen.ts`
- `web/src/entities/expert-decision/model/category-labels.ts`
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/schemas/findings.py`
- `src/auditmanager/api/schemas/runs.py`
- `src/auditmanager/api/routers/runs.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/handlers.py`
- `src/auditmanager/api/security.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/findings/grounding.py`
- `src/auditmanager/analysis/text/stage.py`
- `tests/support/expected_facts.json`
- `tests/integration/api/test_operation_surface.py`
- `tests/integration/api/conftest.py`
- `tests/integration/api/test_role_register.py`
- `tests/integration/api/test_served_document_and_health_plane.py`
- `tests/integration/composition/test_every_port_implementation_is_whole.py`
- `tests/integration/analysis/test_ar_v2_recorded_artifact.py`
- `tests/integration/analysis/test_ar_v2_recorded_stage_result.py`
- `tests/integration/analysis/test_w57a_stage_version_compat.py`
- `tests/integration/api/test_w57a_seal_surface.py`
- `tests/contract/api_v1/test_w57a_citation_contract.py`
- `tests/contract/api_v1/test_openapi_conformance.py`
- `tests/contract/api_v1/test_finding_detail_composition.py`
- `tests/contract/api_v1/test_w55b_portal_bundle_seal.py`
- `tests/contract/api_v1/test_surface_counts_in_prose.py`
- `docs/program/P02_SEAMS.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/manual-tests/PC-01_prototype.md`
- `infra/deploy/README.md`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/serve.py`
- `src/auditmanager/api/README.md`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/health.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/routers/declarations.py`
- `src/auditmanager/api/routers/errors.py`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/src/shared/api/authorization.ts`
- `tests/integration/findings/test_grounding_gate.py`
- `tests/integration/findings/test_ungrounded_vocabulary_is_enforced.py`
- `tests/integration/analysis/test_ungrounded_reason_vocabulary.py`
- `tests/integration/p02_journey/test_ungrounded_diagnostic_path.py`

## Forbidden hotspots

- old migrations and the 0023 head, all 01A-owned domain/custody files;
- W56 executor, run command, profile and worker composition paths; exception: the v1 text-stage identity constant in `analysis/text/stage.py` only, necessary to match the 1.1.0 registry, with no artifact version change;
- root dependency/lock files, API composition wiring, deployment behavior/config directives, global styles, `P02_LOCK.json`;
- exception: exact `infra/deploy/{proxy/nginx.conf,serve.py}`, `src/auditmanager/api/app.py`, and `web/src/app/bff/v1/[...path]/route.ts` grants are prose/count comments only, apart from `app.py`'s OpenAPI description text. No executable route, host, proxy, BFF, security, or service configuration changes are permitted.
- `CURRENT_STATE.md`, remote refs, tags and live stand.

## Non-goals

No qualified retrieval set, v3 runtime activation, corpus publication, working report reader, verified citation publisher, W57b export or beta gate. No PostgreSQL/S3 lane until integrator release.

## Deliverables

Atomic OpenAPI mirror, generated client and frontend lock; served typed refusal and role register; stage registry pin; legacy omission and vocabulary tests; focused report.

## Required tests

- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/contract/api_v1 tests/integration/api/test_w57a_seal_surface.py tests/integration/api/test_operation_surface.py tests/integration/api/test_role_register.py`;
- `npm --prefix web run api:verify`; `npm --prefix web run typecheck`;
- focused stage/grounding tests, `git diff --check`, and `git diff -- infra/deploy/proxy/nginx.conf infra/deploy/serve.py src/auditmanager/api/app.py 'web/src/app/bff/v1/[...path]/route.ts'` showing prose/metadata-only lines;
- no DB/S3 test or full release gate in this serial slice.

## Integration contract

The operation is present and `_ANY_ROLE`-guarded, but returns `503 dependency_unavailable` from the adapter until CITE supplies a reader that verifies the stored count, stage, snapshot and set. An empty SQL result is never interpreted as a certified zero. All new v3 observation properties are omitted on legacy v1/v2 JSON rather than emitted as null. The report schema permits only closed withheld reasons and verified/rebound citations.

## Failure/idempotency/security cases

Unauthenticated/incomplete/no-role calls follow existing role registers. A permitted caller receives a typed 503 and no unverified data. Neither the refusing read nor schema generation writes state; no fallback to caller-supplied citations.

## Rollback / feature flag

The new route is inert until its verified reader is supplied. A rollback removes this contract/route together; 01A's additive 0023 storage remains intact.

## Handoff

- changed files: exact allowlisted diff in report;
- commands/results: report;
- known limits: report;
- integration notes: cherry-pick only after 01A and never activate CITE from this seal alone.
