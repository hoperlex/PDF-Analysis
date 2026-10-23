# Task AR-V3-BETA-SIX-RUN-01 — atomically create six scoped AR beta Runs

task_id: AR-V3-BETA-SIX-RUN-01
status: ready for an exclusive contract/migration/composition slot; code not started

## Outcome

An authenticated expert can request one Ф1.3 AR v3 beta group for a confirmed AR Version and receive six durable Run IDs in F1/F2/A1/A2/S1/S2 order. Each Run freezes the same qualified snapshot and exactly one verified scoped set. The group can be read later with all six IDs and statuses; an absent approved pack refuses before any Run or provider effect. Existing AR v1 runs remain executable by their historical profile.

## Depends on

- `AR-SET-PROMOTION-01` — completed verified-set selection and Run pin seam.
- `AR-SIX-RUN-SCOPE-BRIDGE-01` — completed six-scope and request identity check.
- `AR-BETA-CITATION-REVIEW-GATE-01` — completed review-only disposition boundary.
- `AR-V3-BETA-STATUS-VERSION-01` — completed visible 0.8.0 development status and code queue.

## Frozen inputs

- base commit: `5286248d68ea72740aec2130a98913333b69a9ea`
- API/domain contract `1.1.0`, migration head `0031_executor_pull_channel`, product `VERSION=0.8.0`.
- Six-scope composition SHA-256 `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`; F1.3 beta policy digest `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`.
- The qualified local snapshot is `ns_01M59N8QNBVN91ACA2HCE6VE74`, but this task must not bake that identity into general Run creation or presume the stand has imported it.
- The proposed additive API contract version is `1.2.0`; the implementer must reseal all required contract/generated-client artifacts together or refuse the slice.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: `AR-V3-BETA-SIX-RUN-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/api_v1/test_openapi_conformance.py`

## Captured premise evidence

- premise: one Run can pin one verified set, while served start still creates only one section-routed Run and the v3 beta plan is unserved.
- captured_at: 2026-10-23
- command: `git rev-parse HEAD; rg -n -F -e 'norm_retrieval_set_id: str | None = None' -e 'def start_audit_run(' -e 'def plan_v3_beta_citation_review' src/auditmanager/runs/repository.py src/auditmanager/runs/commands.py src/auditmanager/runs/v3_citations.py`
- captured_output:
  ```text
  5286248d68ea72740aec2130a98913333b69a9ea
  src/auditmanager/runs/v3_citations.py:193:def plan_v3_beta_citation_review(
  src/auditmanager/runs/commands.py:407:def start_audit_run(
  src/auditmanager/runs/repository.py:264:    norm_retrieval_set_id: str | None = None
  src/auditmanager/runs/repository.py:381:        norm_retrieval_set_id: str | None = None,
  ```
- interpretation: immutable set pinning exists, but group identity, atomic six-Run creation and served selection are absent; no existing route is silently repurposed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `contracts/api/v1/**`
- `db/migrations/versions/20261023_0032_ar_v3_run_group.py`
- `src/auditmanager/runs/**`
- `src/auditmanager/api/routers/runs.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `web/src/shared/api/generated/**`
- `tests/contract/api_v1/**`
- `tests/integration/runs/**`
- `tests/integration/api/**`
- `tests/integration/db/**`
- `tests/integration/composition/**`
- `docs/program/tasks/AR-V3-BETA-SIX-RUN-01.md`
- `docs/program/AR-V3-BETA-SIX-RUN-01.md`

## Forbidden hotspots

Root dependency/lock files, global styles, normative source bytes and the existing `AR-NORM-MAP-01` data slot, provider transports, CITE publication, unrelated context internals, other lanes' data, `origin/main`, tags and deployment host. This task is the sole owner of its API contract, migration head and composition-root changes while active; start no overlapping integration task in those hotspots.

## Non-goals

No approval of legal editions or map bytes, no map or set promotion, no model dispatch, no CITE StageResult, finding or numerical conclusion, no stand import or beta acceptance. The trusted pack reader may be injected with synthetic verified sets for tests; production must refuse if no exact approved pack is installed.

## Deliverables

- New explicit `startArV3Beta`/group-read contract and server adapter, with a dedicated group identity and six Run/set/scope records rather than overloading re-audit fields.
- One atomic idempotency command: same key and same payload returns the same six IDs; changed payload refuses. It checks confirmed AR classification, project/version ownership, snapshot qualification, exact pack membership/digest, verified set custody and 22,000-character per-scope cap before claiming/writing.
- New migration after 0031 and generated client reseal; Run frozen-input digests include exact group, scope, map and set authority without changing historical v1 bytes.
- Focused real PostgreSQL tests for rollback, replay, wrong scope, missing/foreign set, stale snapshot, duplicate membership and old v1 Run compatibility.

## Checks

- Contract totality/seal checks for API `1.2.0` and generated web client; migration upgrade on an isolated DB from head 0031.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/runs tests/integration/api tests/integration/db tests/contract/api_v1` with the task's bounded cases and recorded provider (no paid call).
- `git diff --check`, exact allowed-path audit and change inventory; full `make gate` remains deferred to the final code candidate under R-135.

## Integration contract

The selected pack is read from a trusted, versioned server registry, never from an arbitrary request SHA. A group starts only after all six verified sets match one snapshot, content key, composition and scenario. The group and six child Runs commit together before any Job/provider dispatch; a failed preflight leaves no command or Run. Run rows retain individual IDs, profile/bundle identities, scope and set, while group readback reports every child status including partial/failure. A future executor task consumes those pins and rechecks Attempt/set authority after a model effect. No v1 fallback for a selected v3 group.

## Rollback / feature flag

The API operation remains unavailable when no trusted pack is configured; v1 routing stays the default. Before activation, revert the additive code and migration candidate. After any group exists, retain its immutable rows and disable new starts through the trusted-pack switch, never rewrite historical Run pins.
