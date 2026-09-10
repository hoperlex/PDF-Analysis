# Task P1-NAV-01 — build the decision-to-code navigation layer

> **Status: specified; not dispatchable.** It becomes dispatchable when `P1-INT-00` is
> accepted and the owner has accepted ADR-0019 with this plan. It then runs in parallel
> with the P01 provider lanes and gates nothing in P01. It is a required predecessor of
> P02 fan-out.

## Outcome

A rebuildable, machine-validated navigation layer in which an agent resolves a decision to
its implementation seam, contracts and proving tests without repository-wide search, and in
which a planned path can never be presented as implemented.

## Depends on

- none complete at plan time

Planned predecessors and dispatch conditions — this task is not dispatchable until all of
these hold:

  - `P1-INT-00` accepted and integrated. Its `make bootstrap` is what creates the two
    ignored environments, including `.venv/bootstrap`; before it exists this task has no
    interpreter to run its own gates with, so it cannot be dispatched earlier.
  - owner decision `OD-15`: the owner has accepted ADR-0019 together with this plan and
    records the status transition. This task never accepts it and may not edit the ADR.

This task does not wait for `P1-INF-01`, `P1-DB-01` or `P1-STO-01`, and does not block
them. Foundation seams are authored here as `planned` and are flipped to `implemented` by
`P1-NAV-02` after `PF-01`.

## Frozen inputs

- ADR-0019 and Architecture Bible P-23 as committed at the `P0-PLN-01` base commit
  `1cb86cd2708f11712a0cd2f481862652fac2e377`; their acceptance is an owner decision
  recorded with this plan
- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md` at `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`
  — the source of the frozen command surface and the four reserved provider paths
- domain/analysis/event contracts at `1.0.0-draft.1`: read only
- migration head: `none`; this task creates no schema
- base commit: the accepted `P1-INT-00` integration commit, pinned by the integrator at
  dispatch

## Allowed paths

- `docs/navigation/navigation-entry.schema.json`
- `docs/navigation/incident.schema.json`
- `docs/navigation/incidents/README.md` — the directory contract; each later task writes
  its own `docs/navigation/incidents/<task-id>.jsonl`, so the appenders stay disjoint and
  there is no shared append target
- `docs/navigation/entries/**` — creation only, one fragment per owner scope. A fragment a
  later task owns belongs to that task, and no entry is flipped to `implemented` here
- `docs/navigation/INDEX.md` — first generation only; every later regeneration belongs to
  the integration owner of the active batch, per ADR-0019 item 5
- `docs/navigation/README.md`
- `tools/navigation/**`
- `docs/program/tasks/P1-NAV-01.md` status/handoff

## Forbidden hotspots

- `Makefile` and the frozen nine-target command surface: this task adds no target and no
  private alias; its commands are invoked directly
- `scripts/**`, `contracts/**`, `fixtures/**`, `tests/**`
- root dependency/lock files, `db/migrations/**`, `infra/local/**`,
  `src/auditmanager/**`, `web/**`
- `docs/architecture/**` including ADR-0019 itself, CP-00 evidence and Git tags

## Non-goals

- No new architectural authority: entries point at decisions and never override them.
- No embeddings, vector index, external service or semantic search.
- No line-number identity and no per-file architecture comments.
- No runtime, product or infrastructure code.
- No commit SHA that would have to identify the commit containing it.
- No flip of any entry to `implemented`; that is `P1-NAV-02`'s sole job.

## Deliverables

- one versioned JSON Schema for a navigation entry requiring at least: stable `entry_id`,
  `lifecycle` of `planned`, `implemented` or `superseded`, bounded scope, owning task and
  context, decision references, contract references, implementation paths with public
  symbol names, runtime entrypoints, test and evidence references, supersession links and
  known gaps
- independently owned entry fragments covering the accepted FF-01 decisions, ADR-0019
  itself, the CP-00 contract families the prototype consumes, and the four FF-01-reserved
  provider seams — the last authored as `planned`, with the exact `entry_id` list handed to
  `P1-NAV-02`
- a deterministic generator producing `docs/navigation/INDEX.md` in both directions:
  decision to implementation, and implementation path or context to decisions, contracts
  and tests
- a validator enforcing unique ids, schema conformance, referenced-path and
  referenced-document existence, lifecycle and supersession consistency, one owner per
  fragment, and byte-identical regeneration
- an agent search and rework **incident log**: `incident.schema.json` plus a
  `docs/navigation/incidents/` directory in which **each task writes its own
  `<lowercase-task-id>.jsonl`**, never a shared file, so no two lanes ever append to one
  path. The rule, recorded in the directory README and in every later task's handoff, has
  three parts: a task creates its file **only when it actually records an incident** — it
  searched outside the index, or reworked because the index was wrong or missing; each of
  the **28 P02–P05 tasks** reports a handoff status of `recorded`, `none_observed` or
  `practice_not_exercised`; and an absent file is therefore ambiguous on its own and is
  disambiguated only by that status. The two `P1-NAV` tasks build this contract and are not
  subject to it: they own no incident file and report no status, so they are never counted
  as non-reporting. Aggregation is status-aware and scoped, identically for every
  aggregator: within its own scope, **zero is a legitimate result** when every in-scope
  task returned `recorded` or `none_observed`, because a complete set of statuses over an
  empty directory is a real measurement; a single `practice_not_exercised`, or a missing
  status, makes the metric `absent` and the non-reporting tasks are named. Each aggregator
  is the last task in the wave it reports — `P2-INT-02` covers P02, `P4-OPS-01` the P02/P03
  tasks already complete when it runs, `P4-INT-01` covers P04, `P5-INT-01` covers P05 — so
  none reports on an unfinished wave. The P02 set is deliberately read twice, and where the
  readings differ `P4-OPS-01`'s later one governs the PC-02 metric
- `docs/navigation/README.md`: the agent onboarding order — `CURRENT_STATE.md`, then the
  index, then the entries relevant to the task, then the task and its frozen contracts
- negative-control fixtures proving the validator fails on a duplicate `entry_id`, a
  dangling reference, a `planned` path claimed as `implemented`, and a stale generated index

## Required tests

- Command: `make bootstrap`
  Expected: exit `0`; this is the first command of the task and it is what provides the
  interpreter the remaining gates use.
- Command: `.venv/bootstrap/bin/python tools/navigation/validate_navigation.py`
  Expected: exit `0`; prints the count of validated entries and rules.
- Command: `.venv/bootstrap/bin/python tools/navigation/generate_index.py --check`
  Expected: exit `0`; the committed `docs/navigation/INDEX.md` is byte-identical to a fresh
  generation.
- Command: `.venv/bootstrap/bin/python tools/navigation/validate_navigation.py --self-test`
  Expected: exit `0`; every negative-control case is reported as a failure by the rule that
  owns it, proving each guard can go red.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Every P02+ implementation task owns exactly one navigation fragment for the code it adds or
materially changes, or records a reviewed `navigation_not_applicable` reason, and appends
an incident record when the index failed it. The generated aggregate index has one writer
at a time — the integration owner of the active batch. Consumers may rely on the schema and
on the two-direction index; they may not treat an entry as authority over the decision,
contract or test it points at.

## Failure/idempotency/security cases

- Regeneration is deterministic: identical fragments produce byte-identical output.
- A dangling decision, contract, path or test reference fails validation.
- A `planned` entry naming an implemented symbol, or an `implemented` entry whose path does
  not exist, fails validation.
- The layer holds no credential, customer payload or internal object key.
- A superseded entry keeps its id and points forward; history is never deleted.

## Rollback / feature flag

Documentation and tooling only. Revert the integration commit; no runtime, schema or
foundation behavior changes. The layer is additive and blocking only from P02 fan-out.

## Estimate

Effort P50 1.0 person-day, P80 2.0 person-days. Runs in parallel with the P01 provider
lanes and is not on the `PF-01` critical path.

## Handoff

- changed files and the validator and generator transcripts
- the entry inventory with lifecycle counts, and the exact `entry_id` list of `planned`
  foundation seams handed to `P1-NAV-02`
- known gaps recorded as entries rather than omitted
- integration notes: accept before P02 fan-out
