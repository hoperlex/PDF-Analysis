# Task W52-INT-B2C-01 — accept the release seal and grant Stage C

task_id: W52-INT-B2C-01

## Outcome

The exact SEAL candidate is accepted on the development line, read back from
`origin/dev`, and the first Stage-C lane has a current-tree implementation grant.

## Depends on

- `W52-SEAL-01`, complete on clean `agent/w52-seal-01` at
  `0dd3f7b20623e51d7927dd0fc14a1fb12292b062`.

## Frozen inputs

- Development base `fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022`;
  accepted SEAL SHA `0dd3f7b20623e51d7927dd0fc14a1fb12292b062`.
- W52 contract: domain revision 9 / 29 identities; API 30 paths / 37 operations /
  83 schemas; 23 error codes; head `0016_release_notes`;
  `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` §§3.1–3.5, Stage C and §5; R-70–R-74.
  D-137–D-140 retain independent QA, live checks and complete gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: no contract or migration change in this integration slot

## Captured premise evidence

- premise: the local integration line has the exact SEAL commit and the
  development remote still names the preceding Stage-B grant.

### P-01 — SEAL tip and development remote

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  0dd3f7b20623e51d7927dd0fc14a1fb12292b062
  fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022 refs/heads/dev
  1e9bb1308b7b97cd75eef28e206b23c569871b68 refs/heads/main
  ```
- interpretation: the development push must prove a fast-forward from
  `fd78ad8`; `origin/main` is outside this task.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-B2C-01.md`
- `docs/program/tasks/W52-RELEASES-API.md`
- `docs/program/W52-INT-B2C-01.md`
- `docs/program/CURRENT_STATE.md` — opening W52 status only
- `docs/program/dispatch/W52-PLAN.md` — status and integration-order sentences only
- `docs/program/dispatch/PORT_REGISTRY.md` — exact W52 Stage-B/C rows only
- clean `integration/w51` ref, `origin/dev` fast-forward and Stage-C local branch/worktree

## Forbidden hotspots

Every other tracked path, especially contracts, migrations, product code,
generated client, dependency and lock files, composition roots, global styles,
`origin/main`, tags and the deployed stand.

## Non-goals

No Stage-C implementation, release loader, UI, complete gate, QA, release verdict,
tag or deployment.

## Deliverables

- Reviewed SEAL diff and grant proof; focused contract/client/role/migration
  evidence on the exact code candidate.
- A current-tree `W52-RELEASES-API` task with isolated port reservation.
- Clean docs-only integration commit on `origin/dev` with remote readback.

## Required checks

- `python3 tools/plan/pin_sweep.py reseal-surface migration table --check docs/program/tasks/W52-SEAL-01.md`
- `.venv/bin/python -m pytest tests/contract/api_v1 tests/contract/domain_p02 -q`
- `npm --prefix web run api:verify`, lint and typecheck; focused new
  real-service API and migration checks using `gate-w52s` evidence.
- Focused governance/prose checks for the docs grant, `git diff --check`,
  changed-path and clean-tree proof.
- Full `make gate` is D-140 under the owner's code-first exception; no
  `GATE OK` claim in this task.

## Integration contract

Accept SEAL first. Re-sweep the merged tree before granting Stage C. Re-check
`origin/dev` immediately before publication; push only a proven fast-forward
of the exact checked SHA and read it back. Stage C starts from that grant SHA.
No operation on `origin/main`.

## Failure / rollback

A missing grant, changed remote ref, or unreviewed SEAL path stops publication.
Revert the docs-only grant commit if its boundary is wrong; a populated 0016
database requires restore rather than migration downgrade. No feature flag.

## Handoff

List changed files, checks, contracts, limits, integrator steps and
forbidden-hotspot proof. No checkpoint or tag.
