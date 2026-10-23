# Task AR-V3-BETA-SIX-RUN-02 — seal and persist the six-Run AR beta group

task_id: AR-V3-BETA-SIX-RUN-02
status: replacement integration task ready; code not started

## Outcome

An authenticated expert can start one Ф1.3 AR v3 beta group for a confirmed AR Version and read six durable Run IDs and statuses in F1/F2/A1/A2/S1/S2 order. The group has its own opaque identity, one exact verified set per Run and an atomic replay key. Without a trusted reviewed pack, the start refuses before writing or dispatching. Historical AR v1 Runs still resolve their original profile.

## Depends on

- `AR-SET-PROMOTION-01` — completed verified-set custody and Run pin.
- `AR-SIX-RUN-SCOPE-BRIDGE-01` — completed six-scope request membership.
- `AR-BETA-CITATION-REVIEW-GATE-01` — completed review-only normative disposition.
- `AR-V3-BETA-PROMPT-SEAL-01` — completed immutable v3 bundle and six golden request digests.
- `AR-V3-BETA-STATUS-VERSION-01` — completed visible 0.8.0 development preview.

## Frozen inputs

- base commit: `6e9f887e8d7de268ab327390e73a658c1123f9aa`
- API/domain/analysis/events contract `1.1.0`, migration head `0031_executor_pull_channel`, product `VERSION=0.8.0`.
- Six-scope composition SHA-256 `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`, Ф1.3 beta policy SHA-256 `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`, and v3 prompt profile/bundle identities `ap_01M5M28ZCDD8VPSP1BTAEW92YE` / `pb_01M5M28ZCDVCR37BX1884JGSPM`.
- Proposed additive family/API contract version `1.2.0`; all family version pins, examples, served constants and generated client must reseal together. Local repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` is a beta pack requirement, never a default in general Run creation.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/domain/v1/identifiers.json`
- enumerator_owner: `AR-V3-BETA-SIX-RUN-02`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/domain_p02/test_identifier_catalog.py tests/contract/api_v1/test_openapi_conformance.py`

## Captured premise evidence

- premise: the frozen six-Run task allowed API changes but omitted the domain identifier catalog and shared identity type needed for a distinct group entity; existing `run_id` names an `AuditRun`.
- captured_at: 2026-10-23
- command: `rg -n -F -e '"run_id": "run"' -e 'class RunId(' contracts/domain/v1/identifiers.json src/auditmanager/shared/identity/ids.py`
- captured_output:
  ```text
  src/auditmanager/shared/identity/ids.py:192:class RunId(OpaqueId, prefix="run", entity="AuditRun"):
  contracts/domain/v1/identifiers.json:39:    "run_id": "run",
  ```
- interpretation: reusing `run_id` for an independent group would change an existing identity's meaning. A distinct group ID needs a catalog entry and matching type; `AR-V3-BETA-SIX-RUN-01` does not own those paths. No group implementation started under that task.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/AR-V3-BETA-SIX-RUN-01.md
- addendum_path: docs/program/AR-V3-BETA-SIX-RUN-01-ADDENDUM.md

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `contracts/**`
- `db/migrations/versions/20261023_0032_ar_v3_run_group.py`
- `src/auditmanager/shared/identity/**`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/analysis/text/stage.py`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/runs/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/**`
- `web/openapi/openapi.json`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/credentialed-forward.ts`
- `web/src/shared/api/authorization.ts`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/src/shared/api/generated/**`
- `web/tests/**`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/README.md`
- `infra/deploy/serve.py`
- `tests/contract/**`
- `tests/integration/runs/**`
- `tests/integration/api/**`
- `tests/integration/db/**`
- `tests/integration/composition/**`
- `tests/support/expected_facts.json`
- `docs/program/CURRENT_STATE.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/tasks/AR-V3-BETA-SIX-RUN-02.md`
- `docs/program/AR-V3-BETA-SIX-RUN-01-ADDENDUM.md`
- `docs/program/AR-V3-BETA-SIX-RUN-02.md`

## Forbidden hotspots

Root dependency/lock files, global styles, original topic and normative map/source bytes, the `AR-NORM-MAP-01` data slot, provider transports, CITE publication, unrelated context internals, `origin/main`, tags and deployment host. This task alone owns the domain/API/analysis/events family reseal, migration head and composition root while active; no concurrent integration task may edit those hotspots.

## Non-goals

No legal-edition or map approval, set promotion, model dispatch, CITE StageResult, finding, numerical conclusion, stand import or beta acceptance. Synthetic packs exercise code only; production refuses until the exact approved six-set pack exists.

## Deliverables

- New opaque `ArV3RunGroup` identity and type with a distinct catalog prefix, plus a consistent `1.2.0` family/API reseal and generated client. Existing `AuditRun` identity and wire shape remain backward compatible.
- One migration after 0031 with a durable group row, exact six child memberships and immutable group/scope/map/set pins; preserve historic Run rows and migration upgrade path.
- New explicit group-start/read API and server adapter. The command checks confirmed AR classification, project/version ownership, qualified current snapshot, trusted pack digest and six distinct verified sets with custody and ≤22,000-character prompt parts before claiming or writing. It inserts the group and six Runs in one transaction before any Job/provider effect.
- Same idempotency key plus same payload returns the original six IDs; changed payload refuses. A group read reports each child ID, scope and current status even after partial execution failure.
- Real PostgreSQL rollback/replay/foreign-set/stale-snapshot/duplicate-membership tests, contract totality, generated-client seal and historical v1 profile-resolution tests.

## Checks

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/domain_p02 tests/contract/api_v1 tests/contract/analysis_v1 tests/contract/events_v1 tests/integration/runs tests/integration/api tests/integration/db tests/integration/composition` with focused new cases; isolated migration upgrade from 0031.
- Generated web client/typecheck and contract version-totality validation; `git diff --check` and exact allowed-path inventory. The final beta candidate owns the complete `make gate` under R-135.

## Integration contract

The trusted pack is selected from a versioned server registry, not from arbitrary request SHA values. The group start freezes the existing v3 profile/bundle identity, six scope/map/set triples, one current snapshot, one shared project/version and per-Run input digests. A preflight or SQL failure leaves no command, group, Run or provider effect. Child Runs stay addressable by their normal Run IDs; group readback is an additional projection. The later executor rechecks Attempt/set authority and refuses missing pack or mismatched historic pins with no v1 fallback.

## Rollback / feature flag

Without an installed trusted pack, group-start stays disabled and the served v1 route remains the default. Before any group exists, revert the additive code/migration candidate. Once a group exists, retain its immutable identity and child pins for replay; turn off new starts through the trusted-pack switch, never rewrite old Runs.
