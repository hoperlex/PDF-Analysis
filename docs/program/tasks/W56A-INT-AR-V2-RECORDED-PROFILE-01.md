# Task W56A-INT-AR-V2-RECORDED-PROFILE-01 — pin recorded AR v2 descriptor

task_id: W56A-INT-AR-V2-RECORDED-PROFILE-01

## Outcome

An exact `ap_`/`pb_` pair resolves to an immutable AR v2 descriptor only
while six reviewed resources, response schema and deterministic prompt
material match their pinned digests. Focused tests reject altered identity or
content. The descriptor is recorded-only and is not a runtime profile switch.

## Depends on

- `W56A-INT-PROFILE-CONTENT-01` — completed reviewed six-source content;
- `W56A-INT-RESPONSE-SCHEMA-PREP-01` — completed pure seven-category schema;
- `W56A-INT-PROMPT-MATERIAL-PREP-01` — completed deterministic material;
- `CFB-INT-PIPELINES-AND-PREFLIGHT-05` — completed recorded executor preflight.

## Frozen inputs

- base commit: `697279facee30216871389cc783e68b3bc58243b`
- W56 plan SHA-256: `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`
- code-first order SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`
- stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`
- provider lock SHA-256: `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`
- migration head: `0022_findings_v2`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: AR v2 material and schema exist, but its recorded profile registration is absent on the exact base.

### P-01 — unregistered AR v2 descriptor

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/registered.py`
- captured_output:
  ```text
  697279facee30216871389cc783e68b3bc58243b
  ```
- interpretation: the path is absent at the base; this task may add it without modifying a shared runtime registry.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/registered.py`
- `tests/integration/analysis/test_ar_v2_registered_profile.py`
- `docs/program/tasks/W56A-INT-AR-V2-RECORDED-PROFILE-01.md`
- `docs/program/W56A-INT-AR-V2-RECORDED-PROFILE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing analysis/runtime modules,
composition root, root dependencies/locks, global styles, recordings,
`CURRENT_STATE.md`, Git refs and tags.

## Non-goals

No verified live model identity or price, generation settings, provider request,
run creation, stage execution, active registry selection, recording, baseline,
full gate, release or beta claim. The stored stage tuple is an inert descriptor;
the run repository and executor do not consume it in this task.

## Deliverables

One immutable descriptor module, content/identity refusal tests and result report.
`2.0.0-recorded` is an internal descriptor version, not a contract or release version.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_registered_profile.py`
- Python compilation, direct task governance, `git diff --check` and exact changed-path proof.
- Full `make gate` and service-backed acceptance deferred under R-135.

## Integration contract

`resolve_recorded_profile(profile_id, bundle_id)` returns a frozen descriptor
only for the two pinned identities and matching reviewed-source, response-schema,
prompt-material and profile-content digests. Future runtime code must resolve it
independently of a run row and separately check recorded provider mode and the
request checksum. This task does not authorize live calls or an active stage plan.

## Failure/idempotency/security cases

Unknown identities and changed digest inputs fail closed; the six-source loader
also refuses missing/tampered bytes. Repeated resolution returns equal values.
No fallback, DB write, provider side effect or expert decision occurs.

## Rollback / feature flag

Remove the additive descriptor before runtime wiring. No flag or data rollback
is needed because the descriptor has no consumer on this base.

## Handoff

- changed files/checks/limits: task report;
- contracts: none changed;
- next: integrator verifies paths and focused tests, then grants a separate
  recorded request/artifact/stage wiring task when prerequisites permit.
