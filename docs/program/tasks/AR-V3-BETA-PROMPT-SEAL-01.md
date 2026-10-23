# Task AR-V3-BETA-PROMPT-SEAL-01 — seal the AR v3 scoped prompt bundle

task_id: AR-V3-BETA-PROMPT-SEAL-01
status: ready for an isolated analysis-profile code lane; code not started

## Outcome

A recorded test can construct a byte-stable AR v3 beta request for each F1/F2/A1/A2/S1/S2 scope from a supplied, custody-checked set, and can read a distinct immutable v3 profile/bundle identity and content digest. The bundle is ready for the later executor integration; this task does not make a Run or provider call.

## Depends on

- `AR-CORPUS-CITATION-BRIDGE-01` — completed Attempt/set request seam.
- `AR-SIX-RUN-SCOPE-BRIDGE-01` — completed six-scope membership and digest rules.
- `AR-BETA-CITATION-REVIEW-GATE-01` — completed review-only output policy.
- `AR-V3-BETA-STATUS-VERSION-01` — completed development preview and code queue.

## Frozen inputs

- base commit: `5286248d68ea72740aec2130a98913333b69a9ea`
- API/domain contract `1.1.0`, migration head `0031_executor_pull_channel`, product `VERSION=0.8.0`.
- Frozen original topic file `src/auditmanager/analysis/profiles/ar_v3/original_topics.md` is verified by its existing SHA-256 `df2ee31f57d52a3c597cc8b56713da1a4f6af08c3bf420cf6e3129a8b678a477`; six-scope composition SHA-256 `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`.
- F1.3 beta policy digest `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`; only exact reviewed/custody-checked set bytes may later be passed to this pure renderer. No map or set is approved by this task.
- Existing draft request formats `ar-v3-request-prep-v1` and `ar-v3-scoped-request-prep-v1`; historical AR v1 and recorded-only v2 profile identities remain pinned.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the scoped v3 prompt and request builders exist, but explicitly state that they are unserved draft material without a registered immutable bundle.
- captured_at: 2026-10-23
- command: `rg -n -F -e 'Draft, unserved AR v3 prompt material' -e 'Pure, unserved AR v3 request candidate' -e 'Two sources, and only two:' src/auditmanager/analysis/profiles/ar_v3/prompt_material.py src/auditmanager/analysis/profiles/ar_v3/request_candidate.py src/auditmanager/analysis/text/profile_registry.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profile_registry.py:8:Two sources, and only two:
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py:1:"""Pure, unserved AR v3 request candidate from pinned input identities.
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py:1:"""Draft, unserved AR v3 prompt material from supplied verified-set input.
  ```
- interpretation: the later executor needs its own v3 bundle identity and checked bytes; the v1 section registry must not be silently changed to point AR at a draft.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/v3_profile.py`
- `src/auditmanager/analysis/profiles/ar_v3/prompt_material.py`
- `src/auditmanager/analysis/profiles/ar_v3/request_candidate.py`
- `src/auditmanager/analysis/profiles/ar_v3/response_schema.py`
- `tests/integration/analysis/test_ar_v3_profile_seal.py`
- `tests/integration/analysis/test_ar_v3_request_candidate.py`
- `tests/integration/analysis/test_ar_v3_scope_request.py`
- `tests/integration/analysis/test_ar_v3_prompt_material.py`
- `docs/program/tasks/AR-V3-BETA-PROMPT-SEAL-01.md`
- `docs/program/AR-V3-BETA-PROMPT-SEAL-01.md`

## Forbidden hotspots

`contracts/**`, migrations, composition root, text-profile registry, existing v1/v2 profile bytes, `original_topics.md`, `norm_map/**` and the `AR-NORM-MAP-01` owner slot, provider transports, Run writer/executor, root dependency/lock files, global styles, `origin/main`, tags and deployment host.

## Non-goals

No normative source or edition approval, map/set promotion, provider/model choice, API or UI activation, Run dispatch, CITE result, accepted finding or numerical conclusion. No synthetic set is promoted; synthetic fixtures are only for tests.

## Deliverables

- An explicit immutable v3 profile/bundle manifest with new stable identity pair, version, source digests, prompt/schema digest and six-scope policy. Reject collisions with historical AR v1 and recorded v2 identities.
- A single scoped request builder that seals the exact system prompt, selected canonical norm paragraph labels, project text, response schema and identity/digest fields. It rejects absent scope, changed composition, wrong set item order, over-budget prompt part and changed original topic bytes; it never falls back to unscoped or v1 material.
- Golden byte/digest tests for all six scopes, negative mutations, and proof that unselected rebinding paragraphs do not enter the provider request. Existing historical AR profile-resolution tests stay green.

## Checks

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_profile_seal.py tests/integration/analysis/test_ar_v3_request_candidate.py tests/integration/analysis/test_ar_v3_scope_request.py tests/integration/analysis/test_ar_v3_prompt_material.py tests/unit/analysis/test_text_profile_registry.py`.
- `git diff --check`, exact allowed-path audit and change inventory; complete `make gate` is deferred to the final code candidate under R-135.

## Integration contract

The executor may later consume the bundle only after proving the Run's v3 identity, scope, snapshot, map, set digest and current Attempt/custody authority. This pure module never grants legal authority to a cited paragraph or expert authority to model output. The served AR v1 route continues to resolve its historical profile and prompt bundle. The v3 executor task owns any registration/route switch and must require an exact, reviewed six-set pack before dispatch.

## Rollback / feature flag

The sealed bundle is unserved, so reverting this task before runtime integration has no data effect. After any Run uses its identity, retain the immutable bundle bytes for replay; disable new v3 starts at the later trusted-pack switch instead of changing the old identity.
