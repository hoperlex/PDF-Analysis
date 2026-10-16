# Task W55B-INT-MAIN-VERIFY-ADDENDUM-01 — record manual same-tree verification

task_id: W55B-INT-MAIN-VERIFY-ADDENDUM-01

## Outcome

Record the owner's direct deployment-host `verify-deployed.sh` output for
the already published W55b `origin/main=37393a97`, resolving the exact-tree
proof missing from workflow run `38897018419`. Preserve the earlier report
as the historical account of what the automated job actually proved.

## Depends on

- `W55B-INT-MAIN-PREP-03`, completed on the exact gate-checked candidate.
- `CFB-INT-DEV-PUBLISH-40`, published as `9f0f536c4d9e2c86960ff11fb1ced451dae8cd62`.

## Frozen inputs

- base commit: `9f0f536c4d9e2c86960ff11fb1ced451dae8cd62`
- remote main: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- workflow run `38897018419`, head SHA same, job `success` but no actual `verify-deployed.sh` output;
- owner-provided 2026-10-16 host command: `cd /srv/auditmanager && infra/deploy/verify-deployed.sh`;
- public origin preflight from the exact candidate: `PREFLIGHT OK`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the owner supplied successful exact-tree host output after the earlier integration report recorded an incomplete automated verification.

### P-01 — script success branch at the published candidate

- captured_at: 2026-10-16
- command: `tail -n 1 infra/deploy/verify-deployed.sh`
- captured_output:
  ```text
  echo "verify-deployed.sh: the deployed stack IS this tree ($HEAD_SHA$DIRTY)."
  ```
- interpretation: the owner's final output is emitted only after the proxy/image comparison passes; the final echo returns status zero under `set -euo pipefail`.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/W55B-INT-MAIN-01.md
- addendum_path: docs/program/W55B-INT-MAIN-VERIFY-ADDENDUM-01.md

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W55B-INT-MAIN-VERIFY-ADDENDUM-01.md`
- `docs/program/W55B-INT-MAIN-VERIFY-ADDENDUM-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/test source, deployment workflow, old task/report,
`CURRENT_STATE.md`, production DB/S3, `origin/main` and tags.

## Non-goals

No new deployment, credentialed product acceptance, workflow repair push,
corpus import, release tag or beta claim.

## Deliverables

This task and an addendum naming the exact host output, script success
semantics, workflow gap and remaining acceptance limits; dev-only readback.

## Required tests

- `tests/contract/program/test_wave_governance.py`, exact allowed-path
  handoff, whitespace and clean tree;
- read `origin/main` and `origin/dev` immediately before the dev-only push,
  prove fast-forward, push exact SHA and read back;
- no full gate under R-135: this is documentation of a completed read-only host check.

## Integration contract

The addendum is the authoritative later outcome for `W55B-INT-MAIN-01`.
The successful host script final line proves the deployed API, web, worker
and proxy match its checkout at `37393a97`; GitHub's full head SHA and direct
main readback bind that short form to the published candidate. The green
workflow's missing verification remains a separate defect; its repair
candidate may not be pushed to main without a new exact-SHA instruction and
gate. No user-facing beta claim follows from this host check alone.

## Failure/idempotency/security cases

If remote dev moves, stop. The host output contains no credentials; do not
copy env files, workflow credentials or complete logs into Git. A repeat of
this exact dev publication is a no-op.

## Rollback / feature flag

Documentation only; correct with a later evidence addendum. No runtime flag
or data rollback applies.

## Handoff

- changed files: this task and its addendum only;
- checks/limits: governance, handoff, no credentialed W55b product journey;
- contracts: none;
- forbidden hotspots remain untouched.
