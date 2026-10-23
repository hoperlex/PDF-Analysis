# Task AR-V3-BETA-REQUEST-DELIVERY-01 — bind sealed v3 material to the transport request

task_id: AR-V3-BETA-REQUEST-DELIVERY-01
status: implementation in progress

## Outcome

A sealed, scoped AR v3 beta request becomes one deterministic `ModelRequest` body and SHA-256 for every existing model transport. The request contains only the sealed system/user prompts, JSON schema and explicit generation settings; it does not load unselected norm paragraphs or call a provider.

## Depends on

- `AR-V3-BETA-PROMPT-SEAL-01` — completed immutable v3 profile and six request materials.
- `AR-V3-BETA-EXECUTE-GUARD-01` — completed pre-effect refusal until the full executor is installed.

## Frozen inputs

- Base published `origin/dev` commit: `15f3e0f371b6146a8f529892270a0910792a0aaa`.
- Contract family/API `1.2.0`, migration head `0032_ar_v3_run_group`, product `VERSION=0.8.0`.
- Sealed AR v3 profile/bundle `ap_01M5M28ZCDD8VPSP1BTAEW92YE` / `pb_01M5M28ZCDVCR37BX1884JGSPM`; no change to their bytes or golden scoped candidates.
- Existing `ModelRequest` and adapters are the only provider-facing transport seam.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the sealed v3 material and transport `ModelRequest` are separate types with no conversion owner.
- captured_at: 2026-10-23
- command: `rg -n -F -e 'class SealedV3Request' -e 'def prepare_beta_v3_request' src/auditmanager/analysis/profiles/ar_v3/v3_profile.py; rg -n -F -e 'class ModelRequest' -e 'def complete(self, request: ModelRequest)' src/auditmanager/analysis/text/adapter.py`
- captured_output:
  ```text
  140:class SealedV3Request:
  196:def prepare_beta_v3_request(
  32:class ModelRequest:
  112:    def complete(self, request: ModelRequest) -> ModelResponse: ...
  ```
- interpretation: provider adapters share a request type, while the frozen v3 request currently stops at a local material envelope. This task owns only the pure conversion, not dispatch authority.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/request_delivery.py`
- `src/auditmanager/analysis/public.py`
- `tests/integration/analysis/test_ar_v3_request_delivery.py`
- `docs/program/tasks/AR-V3-BETA-REQUEST-DELIVERY-01.md`
- `docs/program/AR-V3-BETA-REQUEST-DELIVERY-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots

Contracts, migration head, composition root, root dependency/lock files, global styles, original topics/norm maps/sets, provider adapters, Run executor, CITE stage, `origin/main`, tags and deployment host.

## Non-goals

No Job, Attempt, provider call, cost journal, StageResult, CITE artifact, finding, approved norm, numeric verdict or pack activation. The later executor must prove Run/Attempt/set custody before invoking this pure conversion and recheck authority after response.

## Deliverables

- Public v3 request builder taking a sealed v3 envelope, explicit pinned model identity and strict generation settings; deterministic `ModelRequest` body and request SHA.
- Validation of the sealed profile/material envelope and selected scope so malformed or cross-profile material cannot be dispatched.
- Six-scope positive and mutation tests for prompt/schema/body fidelity, exact digest, unknown model/settings and absence of unselected rebinding text.
- Report and queue note preserving the open full-executor boundary.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_request_delivery.py tests/integration/analysis/test_ar_v3_profile_seal.py -x --tb=short`.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/runs/test_v3_execution_guard.py -x --tb=short`.
- `git diff --check` and exact allowed-path inventory. Full `make gate` is deferred to the final beta candidate under `R-135`.

## Integration contract

The returned `ModelRequest.body` is constructed once from the sealed candidate and generation pins. Existing HTTP, pull and SSH adapters receive this same object; they may serialize it for their protocol but cannot recalculate a different v3 prompt. The local candidate SHA and provider-body SHA are distinct and both must be recorded by the future executor. An idempotency scope is transport metadata and does not alter the body SHA.

## Failure/idempotency/security cases

Wrong profile/bundle, mutated seal/material, empty or placeholder model identity, invalid output cap/effort/thinking, missing scope and malformed schema refuse before a request is returned. Repeated identical inputs return equal bytes and digest. No idempotency key is claimed here.

## Rollback / feature flag

This pure builder is unserved. Revert its code and tests before full executor integration, or leave it unused; the existing v3 execution guard remains active.

## Handoff

- changed files: report
- commands/results: report
- known limits: no provider dispatch or saved response
- integration notes: future executor supplies trusted sealed material and provider pins
