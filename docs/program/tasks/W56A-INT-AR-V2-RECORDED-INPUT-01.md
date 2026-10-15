# Task W56A-INT-AR-V2-RECORDED-INPUT-01 — bind recorded AR v2 source artifacts

task_id: W56A-INT-AR-V2-RECORDED-INPUT-01

## Outcome

A pure input binder checks the run version against exact text-layer and
recognised-artifact identities, verifies both read digests against independently
supplied artifact references, selects only stored textless-page OCR, then builds
one deterministic recorded AR v2 request and a separate source-binding SHA-256.
Changed source metadata changes that binding even when the rendered request is equal.

## Depends on

- `W56A-INT-RECOGNISED-CONTEXT-PREP-01` — completed OCR selector;
- `W56A-INT-AR-V2-RECORDED-REQUEST-01` — completed request builder;
- `CFB-INT-RECORDED-REQUEST-07` — completed recorded replay integration.

## Frozen inputs

- base commit: `62a9e23dd44cdd7d9373e69413ce6ad27e508d3d`
- source branch: `integration/code-first-entry`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; `P02_SEAMS.md` §§4.3, 4.8 and R-134.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the OCR selector and recorded request builder exist, but no component
  checks a version's artifact references and read digests before joining them.

### P-01 — exact new paths absent on the frozen base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/recorded_input.py tests/integration/analysis/test_ar_v2_recorded_input.py docs/program/tasks/W56A-INT-AR-V2-RECORDED-INPUT-01.md docs/program/W56A-INT-AR-V2-RECORDED-INPUT-01.md`
- captured_output:
  ```text
  62a9e23dd44cdd7d9373e69413ce6ad27e508d3d
  ```
- interpretation: only these four additive paths are granted; this does not
  prove a run has independently supplied the correct references.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recorded_input.py`
- `tests/integration/analysis/test_ar_v2_recorded_input.py`
- `docs/program/tasks/W56A-INT-AR-V2-RECORDED-INPUT-01.md`
- `docs/program/W56A-INT-AR-V2-RECORDED-INPUT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing selector/request/adapter,
run executor and repository, findings publisher, recordings, corpus, root
dependency/lock files, composition roots, global styles, `CURRENT_STATE.md`,
`VERSION`, refs, tags and deployment state.

## Non-goals

No DB/Blob read, provider call, active stage or run switch, OCR generation,
model/price pin, artifact publication, finding write, full gate or beta verdict.
The caller still sources trusted references and read digests from a durable run
stage and verifies the underlying Blob reads.

## Deliverables

Additive pure binder, focused identity/checksum/OCR tests and this task report.

## Required tests

- focused pytest for `tests/integration/analysis/test_ar_v2_recorded_input.py`
  when CPU/RAM allow; Python compilation, direct task governance, frozen-hash
  checks, `git diff --check` and exact changed-path proof;
- no Docker, database, network or complete `make gate` under R-135.

## Integration contract

The later recorded executor supplies the version UID and `textless_pages` from
the persisted version, plus `ArtifactRef` values from the persisted stage and
actual SHA-256 values returned by `read_artifact`. This helper refuses a role,
version, read digest, declared digest or size mismatch before making a request.
It returns selected non-citable OCR, the request key and a distinct digest of
the version, artifact references, page selection and request key for later
durable provenance. It does not authenticate a caller-created reference.

## Failure/idempotency/security cases

Wrong version, missing required recognition, out-of-range stored page, altered
artifact document, digest/size/role mismatch and invalid profile/model inputs
fail closed. Equal inputs give equal request and source-binding checksums;
changed rendered PDF/OCR changes the request key, and changed source metadata
changes the source binding. Multiple OCR TEXT blocks on one page remain an explicit request-builder
refusal until a separately reviewed representation is specified. No fallback
to unmarked text or live provider exists.

## Rollback / feature flag

Remove the new module before runtime wiring. No behavior or data migration is
active, so no feature flag is needed.

## Handoff

- changed files/checks/limits: accompanying report;
- contracts: none;
- next: an owned executor task must persist both request and source-binding
  digests, artifact and stage results, and enforce run-level idempotency before
  activation.
