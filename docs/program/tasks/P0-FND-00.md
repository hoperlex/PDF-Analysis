# Task P0-FND-00 — approve the early PostgreSQL/S3 Foundation Freeze

> **Status: accepted by the repository owner on 2026-09-09 (`FF-01 ACCEPTED`).** This
> completes the Foundation Freeze only and does not approve the P02–P05 roadmap.

## Outcome

An independently approvable PostgreSQL/S3 skeleton plan with fixed boundaries,
ownership, gates and rollback rules. Its acceptance allows P01 implementation to start
while `P0-PLN-01` completes the detailed P02–P05 roadmap in parallel.

## Depends on

- `W0-BHV-02` — accepted golden journeys and edge-case matrix
- `W0-ARC-01` — accepted architecture candidate and owner decisions
- `W0-DOM-01` — accepted domain-contract candidate
- `W0-ANA-01` — accepted analysis-contract candidate

## Frozen inputs

- domain contract: `contracts/domain/v1/**` at `1.0.0-draft.1`, candidate revision 5
- analysis/event contracts: `contracts/analysis/v1/**` and `contracts/events/v1/**`
  at `1.0.0-draft.1`
- architecture source: `docs/architecture/**` at base commit
- migration head: `none`
- base commit: `1220523af9091acf40b36ef2a18424e205e30bb4`
- repository-owner direction dated 2026-09-09: optimize for the fastest working
  prototype; start with PostgreSQL and private S3-compatible storage; do not port
  non-working or obsolete legacy runtime; analyze and revise deeper architecture after
  the working prototype is exercised

## Allowed paths

- `docs/program/tasks/P0-FND-00.md`
- `docs/program/tasks/P0-PLN-01.md` — specification only, not execution status
- `docs/program/tasks/P1-INT-00.md`
- `docs/program/tasks/P1-INF-01.md`
- `docs/program/tasks/P1-DB-01.md`
- `docs/program/tasks/P1-STO-01.md`
- `docs/program/tasks/P1-QA-00.md`
- `docs/program/tasks/P1-INT-01.md`
- `docs/program/PROTOTYPE_PROFILE.md`
- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md`
- `docs/program/ROADMAP.md`
- `docs/program/EXECUTION_PLAN.md` — authority/status banner at the top only
- `docs/program/CURRENT_STATE.md` — prototype banner and obsolete CP-01 code-hold
  sentence only
- `docs/program/CHECKPOINT_REGISTRY.md` — prototype checkpoint table only
- `docs/program/tasks/W1-GOV-00.md` — superseded/non-dispatchable status banner only
- `README.md` — bootstrap/foundation code-authority paragraph only
- `docs/INDEX.md`

## Forbidden hotspots

- `contracts/**`, `fixtures/**`, `scripts/**`, `tests/**`
- `artifacts/checkpoints/**`, `docs/architecture/**`, `docs/stages/**`
- root dependency/lock files, migration head, application composition root and global
  styles
- every Git tag and the history of `main`

## Non-goals

- No runtime, infrastructure, migration, API or UI implementation.
- No approval of P02–P05 details or their implementation tasks.
- No selection of cloud vendor, production credentials, retention, legal hold, HA or DR.
- No rewriting or deletion of CP-00 history.
- No claim of production readiness or complete CP-00 contract implementation.

## Deliverables

1. `PROTOTYPE_FOUNDATION_FREEZE.md`: exact approved/deferred surface, task graph,
   ownership, acceptance commands and estimates for the PostgreSQL/S3 skeleton.
2. `PROTOTYPE_PROFILE.md`: reusable principles, runtime inclusion policy and gate
   classification.
3. `ROADMAP.md`: the two-approval model, complete P00/P01 definition and an explicitly
   non-dispatchable outline of P02–P05.
4. `P0-PLN-01.md`: the separate task that completes P02–P05 in parallel with P01.
5. Six concise, dispatch-ready P01 task specifications.
6. Narrow authority/code-hold corrections and index entries.
7. Prototype `FF-01`/`PF-01` rows in the checkpoint registry.

## Required tests

- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.
- Command: compare the changed path set with `Allowed paths`.
  Expected: every changed path is allowed; every forbidden hotspot is absent.
- Manual check: root locks, environment contract, migration head, local infrastructure,
  storage adapter and integration tests each have exactly one writer in P01.
  Expected: no concurrent hotspot ownership.
- Manual check: P01 provider paths are explicitly authorized after `FF-01 ACCEPTED`,
  while domain product code remains locked.
  Expected: README and current-state authority statements agree with the freeze.

The historical CP-00 contract/checkpoint suite is not run from the shared checkout:
its sandbox can mutate Git state during a failed reset. It remains historical evidence
and may run only in a disposable clone until made hermetic by a later task.

## Integration contract

After owner acceptance, `P1-INT-00` may start immediately. Once its exact toolchain,
environment names, command surface and path pins are independently accepted,
`P1-INF-01`, `P1-DB-01` and `P1-STO-01` may execute in parallel. They do not wait for
`P0-PLN-01`; P02 implementation does.

Parallel provider execution also requires distinct service state as defined in FF-01:
unique instance name, ports, database and bucket per authoring lane. Final acceptance is
serial on the integration instance.

Later planning may add consumers, but it cannot replace PostgreSQL or S3, expose object
keys as identity, bypass the storage port or give migration/root/composition hotspots a
second writer without an explicit Foundation Freeze break.

## Failure/idempotency/security cases

- Planning approval creates no resource and uses no credential.
- Reapplying the document change is idempotent.
- A historical/advisory failure cannot silently become P01-blocking.
- A later task cannot import excluded legacy runtime because it is locally available.
- Foundation replacement or boundary weakening is explicit and independently reviewed.

## Rollback / feature flag

Before P01 starts, rollback is a revert of the planning integration commit. After P01
starts, a Foundation Freeze break requires a named replacement decision and a migration
or disposal plan for any created local data. No automatic fallback is allowed.

## Handoff

- changed files: exact allowed-path list above
- commands/results: every required check and its exit code
- known limits: P02–P05 remain outline-only and non-dispatchable
- integration notes: `FF-01 ACCEPTED` is recorded in the Foundation Freeze; dispatch
  `P1-INT-00` and `P0-PLN-01` from the acceptance commit, with its literal SHA
