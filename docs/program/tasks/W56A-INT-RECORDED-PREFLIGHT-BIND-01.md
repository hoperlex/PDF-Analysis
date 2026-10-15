# Task W56A-INT-RECORDED-PREFLIGHT-BIND-01 — bind v2 preflight to registration

task_id: W56A-INT-RECORDED-PREFLIGHT-BIND-01

## Outcome

The recorded AR v2 executor preflight resolves the exact immutable profile
and prompt bundle through the analysis public seam, refusing a guessed or
content-drifted registration before any effect.

## Depends on

- `W56A-INT-RECORDED-EXECUTOR-01` — completed preflight at `697279fa`;
- `W56A-INT-AR-V2-RECORDED-PROFILE-01` — completed immutable descriptor.

## Frozen inputs

- base commit and `origin/dev`: `697279facee30216871389cc783e68b3bc58243b`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/public.py`
- enumerator_owner: `W56A-INT-RECORDED-PREFLIGHT-BIND-01`
- totality_query: `sed -n '85,170p' src/auditmanager/analysis/public.py`

## Captured premise evidence

- premise: a frozen profile descriptor is now available but the executor
  preflight still accepts unverified registered IDs from its caller.

### P-01 — exact base and independent functions

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && rg -n 'def resolve_recorded_profile|def plan_recorded_v2_execution' src/auditmanager`
- captured_output:
  ```text
  697279facee30216871389cc783e68b3bc58243b
  697279facee30216871389cc783e68b3bc58243b
  src/auditmanager/runs/executor.py:222:def plan_recorded_v2_execution(
  src/auditmanager/analysis/profiles/ar_v2/registered.py:92:def resolve_recorded_profile(
  ```
- interpretation: the public seam can bind a checked descriptor into the
  existing preflight without activating the v1 executor path.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/executor.py`
- `tests/integration/runs/test_v2_recorded_executor.py`
- `docs/program/tasks/W56A-INT-RECORDED-PREFLIGHT-BIND-01.md`
- `docs/program/W56A-INT-RECORDED-PREFLIGHT-BIND-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, root dependency/lock files,
composition root, global styles, v1 publication, provider adapter,
historical recordings, corpus, `CURRENT_STATE.md`, refs and tags.

## Non-goals

No model request, registered runtime stage, executor switch, live mode,
provider call, DB acceptance, full gate or beta claim.

## Deliverables

Public profile-resolution seam, bound fail-closed preflight, focused tests,
task and result report.

## Required tests

- focused profile/preflight tests including content tamper refusal;
- Python compilation, direct governance, frozen hashes, whitespace and exact
  owned-path proof;
- full `make gate` deferred under R-135.

## Integration contract

The preflight obtains independently registered IDs by calling
`resolve_recorded_profile` rather than trusting matching caller values.
It continues to compare the persisted run and recorded adapter/config, with
no invocation from `execute_run`. A later owned task must build the recorded
request/artifact/stage and connect it to the run transaction.

## Failure/idempotency/security cases

Wrong profile, wrong bundle or modified reviewed bytes are refused before any
effect. Repeated preflight is read-only and deterministic. v1 path remains
unchanged.

## Rollback / feature flag

Revert the preflight binding and public exports before runtime activation.
No flag, migration or data rollback is needed.
