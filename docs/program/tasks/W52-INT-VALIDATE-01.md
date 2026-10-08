# Task W52-INT-VALIDATE-01 — measure the deferred validation baseline

task_id: W52-INT-VALIDATE-01

## Outcome

The integrator records the full gate attempt and the frontend diagnostics for one exact
published `origin/dev` candidate, and leaves D-137–D-140 open wherever the required
evidence is absent or red.

## Depends on

- `W52-INT-129R2-01` — completed at `e2cfea92e0ba8b7481156ee8eceeefee582ee562`.

## Frozen inputs

- Base and measured candidate: `e2cfea92e0ba8b7481156ee8eceeefee582ee562`.
- Domain candidate revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `docs/program/dispatch/W51-PLAN.md` §4–§5 and D-137–D-140 in the debt register.
- Owner's 2026-10-08 request for a full run relevant to closing accumulated debts.
  This baseline does not use a temporary product stand; `make gate` itself requires
  isolated local PostgreSQL/S3 foundation services.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the exact development candidate is clean and D-137–D-140 are open.

### P-01 — candidate and deferred checks

- captured_at: 2026-10-08
- command: `git status --short && git rev-parse HEAD && git ls-remote origin refs/heads/dev`
- captured_output:
  ```text
  e2cfea92e0ba8b7481156ee8eceeefee582ee562
  e2cfea92e0ba8b7481156ee8eceeefee582ee562 refs/heads/dev
  ```
- interpretation: no status line preceded the local SHA; local HEAD equalled `origin/dev`
  before measurement. No claim about `origin/main` or a deployed tree follows.

## Historical evidence

- correction_mode: addendum
- source_record: W51 lane reports and the D-137–D-140 opening entries
- addendum_path: `docs/program/W52-INT-VALIDATE-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-VALIDATE-01.md`
- `docs/program/W52-INT-VALIDATE-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`
- ignored local `.env`, `.local/norms/corpus` link and `.local/validation/w52-int-validate-01/**`
  for the measurement only

## Forbidden hotspots

Every other tracked path, especially contracts, migrations, dependency and lock files,
composition root, global styles, runtime code, tests, deployment refs and tags.

## Non-goals

No source correction, temporary product stand, browser identity journey, human A13–A20
attestation, independent judge claim, release, tag or `origin/main` publication.

## Deliverables

- Full `make gate` attempts with exact result and local raw logs.
- Separate frontend Vitest diagnostic after the gate's fail-fast typecheck.
- A debt matrix that names the evidence still needed for D-137–D-140.
- Cleanup of the isolated foundation containers and volumes.

## Required tests

- `make gate` with unique local foundation credentials, ports and real corpus:
  record the literal final status, never infer `GATE OK` from partial passes.
- `npm --prefix web test -- --run` with child-process execution permitted;
  `git diff --check`; clean tracked status.
- Docs governance/prose tests for the report and register update.

## Integration contract

The measured subject remains `e2cfea92e0ba8b7481156ee8eceeefee582ee562`. A later
docs-only report commit is not itself a gated release candidate. Publish only to
`origin/dev` after reviewing the allowed-path diff and a fast-forward remote-ref check.
D-137–D-140 remain open until the separate validation/correction stages satisfy their
individual checks on a new exact candidate.

## Failure/idempotency/security cases

- Local `.env` uses disposable example credentials and an instance name unique to this
  measurement. Do not print passwords or browser credentials in evidence.
- The first gate run lacking the real corpus is a failed environment preparation, not a
  code pass. The second run's green Python battery is still not a green gate.
- If Vitest cannot spawn nested tools under the sandbox, repeat with permission and
  classify only the second run's real failures.

## Rollback / feature flag

Revert the docs-only commit to remove this evidence summary. No feature flag applies.
The raw logs are ignored local artifacts, not release metadata.

## Handoff

- changed files, commands/results, contracts, risks, integration notes and forbidden-hotspot
  proof are in `docs/program/W52-INT-VALIDATE-01.md`.
