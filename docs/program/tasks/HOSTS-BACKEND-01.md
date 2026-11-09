# Task HOSTS-BACKEND-01 — hosts, system groups, availability and cell binding at dispatch

## Outcome
A host can be enrolled with one token. The stand then maintains, from the host's reports, its system-managed pull connections and the system groups per (model, access); computes availability from stored facts; honours «Использовать», slots and cooldowns; counts capacity per `capacity_pool` under one advisory lock in the claim, the dispatcher hint, the comparison mirror and the binding; and, for a run with a `stage_plan`, binds every cell in the claim transaction or leaves the run `pending` with the wait reason `model_unavailable`.

## Depends on
- HOSTS-SEAL-1

## Frozen inputs
- domain contract: 1.45.0, owned by `HOSTS-SEAL-1`; frozen here
- API contract: 1.45.0; frozen here
- analysis/comparison/event contract: 1.45.0
- migration head: `0062_hosts_stage_models`; this task adds none
- base commit: `8f76b4ed6daadad95f9c001e2c2c0dca717aad2d`
- the dispatcher replaces the base by the tip carrying `HOSTS-SEAL-1` at dispatch
- architecture: `docs/architecture/adr/ADR-0028-hosts-and-stage-models.md` decisions 1–5, 7, 9, 15, 16, 19; `ADR-0026` decisions 1–3, 10, 12–16 as amended by the table in `ADR-0028`
- the stub modules `bootstrap/hosts_adapter.py` and `bootstrap/hosts_dispatch.py`, the `prepare_provider_call` plumbing for `stage_key`, `host_id` and `access`, and the shape of `audit_run.stage_plan` as the contract declares it, are the seam with `HOSTS-LAYOUT-01`; this task reads only `cells[*]` of the plan (cell key, model, access)

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the three places the capacity decision is taken today

### P-01 — the locks of the claim, the hint and the comparison mirror
- captured_at: 2026-11-09
- command: `git grep -n "^_NEXT_JOB = \|def _hold_connection_limit\|CONNECTION_LOCK_KEY\|_LOCK_CONNECTION" -- src/auditmanager/jobs/repository.py src/auditmanager/comparison/spend/repository.py`
- captured_output:
  ```text
  src/auditmanager/comparison/spend/repository.py:39:__all__ = ["ACTIVE_JOB_STATES", "ComparisonSpendRepository", "CONNECTION_LOCK_KEY", "DAY_LOCK_KEY"]
  src/auditmanager/comparison/spend/repository.py:42:#: takes for a Run's claim (``jobs.repository._LOCK_CONNECTION``). A comparison call takes the same
  src/auditmanager/comparison/spend/repository.py:44:CONNECTION_LOCK_KEY: Final[str] = "auditmanager.executor_connection|"
  src/auditmanager/comparison/spend/repository.py:135:_LOCK_CONNECTION = text(
  src/auditmanager/comparison/spend/repository.py:136:    f"SELECT pg_advisory_xact_lock(hashtextextended('{CONNECTION_LOCK_KEY}' || :connection_id, 0))"
  src/auditmanager/comparison/spend/repository.py:284:        session.execute(_LOCK_CONNECTION, {"connection_id": connection_id})
  src/auditmanager/jobs/repository.py:67:_LOCK_CONNECTION = text(
  src/auditmanager/jobs/repository.py:135:#: (:data:`_LOCK_CONNECTION`) before it prepares a call and asks the mirror of this question, so a Run's claim
  src/auditmanager/jobs/repository.py:193:_NEXT_JOB = text(
  src/auditmanager/jobs/repository.py:1204:    def _hold_connection_limit(session: Session, *, run_id: str) -> None:
  src/auditmanager/jobs/repository.py:1234:        session.execute(_LOCK_CONNECTION, {"connection_id": connection_id})
  src/auditmanager/jobs/repository.py:1302:            session.execute(_LOCK_CONNECTION, {"connection_id": connection_id})
  ```
- interpretation: the lock key is a function of `connection_id` and is mirrored by hand in the comparison package; both move to the `capacity_pool` key together, with one shared constant, and a test proves the two spell the same key.

The integrator re-runs the premise command on the dispatch base and corrects line numbers.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/**`
- `src/auditmanager/jobs/**`
- `src/auditmanager/comparison/spend/repository.py`
- `src/auditmanager/bootstrap/hosts_adapter.py`
- `src/auditmanager/bootstrap/hosts_dispatch.py`
- `tests/unit/executors/**`
- `tests/unit/jobs/**`
- `tests/unit/comparison/spend/**`
- `tests/integration/executors/**`
- `tests/integration/jobs/**`
- `tests/integration/comparison/spend/**`

## Forbidden hotspots
- `src/auditmanager/bootstrap/providers.py`, `composition.py`, `adapters.py` and `src/auditmanager/api/routers/ports.py`: the integrator's; this task fills the stub modules and the public functions of `executors/public.py` and `jobs/public.py` the integrator's wrappers call
- `src/auditmanager/executors/runner.py` line 606, the `task.expected_model` comparison: the integrator swaps it to `accepted_reported` at `HOSTS-INT-1`, using the function `HOSTS-LAYOUT-01` exports from `analysis.public`; this task does not edit that line
- `tests/integration/executors/test_agent_e2e.py`, `test_agent_install.py`, `test_runner_bridge_e2e.py`, `test_runner_client_wire.py`: `HOSTS-AGENT-01`'s
- `tools/executor-runner/**`, `contracts/**`, `db/migrations/**`
- `src/auditmanager/runs/**` and `src/auditmanager/analysis/**`: `HOSTS-LAYOUT-01`'s
- from the merge of `HOSTS-SEAL-1` on, `src/auditmanager/jobs/repository.py` belongs wholly to this task; no other lane edits it

## Non-goals
- no stage layout, no `stage_plan` freezing, no `binding_for(cell)`, no consent
- no routing of the five `comparison_*` kinds through the system groups (`HOSTS-CMP-01`); the comparison mirror changes its lock key and count only
- no change to ADR-0026 decision 16: a member that fails mid-run is handled as for any `bound` run
- no PostgreSQL or S3 started by the lane

## Deliverables
- **Hosts.** Enrollment and install sessions can target a host; a host token claims tasks for any system connection of its host; a token or grant with both or neither of `connection_id` and `host_id` is refused. `reportRunnerHealth` stores the report snapshot only on a change and appends a change event.
- **System objects.** From the quadruple host · provider · access · model: the system-managed pull connection (`not_metered` for a subscription, `metered` for an API key), its revision (changes only with the catalogue), and the system group of the (model, access) pair, revised only when a host is connected or deleted (at most `GROUP_MEMBERS_MAX` hosts). Revising or archiving a system object is refused; lists, the cut-over preview and rule-target pickers filter them out.
- **Availability** computed on read: host enabled, heartbeat at most 120 s old, login present, model verified, pair not in cooldown; each failed condition is a stored reason (`host_disabled`, `model_not_verified`, `model_cooling_down`, `runner_offline`, …). `at_capacity` is «Занято», not unavailability.
- **«Использовать», slots and cooldown.** The use switch is an append-only event with its author; a new host is on. Slots per provider (subscription 1, API 2) are changeable in the details; the cooldown of a pair lasts 15 minutes after a reported refusal. `getExecutorHostDetails` returns the reasons and the host's current tasks.
- **Capacity.** The unit is (run, `capacity_pool`). The advisory lock is taken on the pool in all four places, in ascending pool-key order: the claim, `_NEXT_JOB`, the comparison mirror (`comparison/spend/repository.py`) and the cell binding. Comparison calls count in the same pool. A host token's `max_claimed_tasks` is validated to be at least the sum of the host's slots.
- **Cell binding.** In the claim transaction, for a run with a `stage_plan`, every cell is bound to an eligible member of the system group of its (model, access), written once to `audit_run_cell_binding`; model I/O starts after commit. If one cell has no free eligible member nothing is bound, the run stays `pending` with `model_unavailable` naming the cells and the cause, and no attempt is spent; after 30 minutes it ends `no_executor_online` (`R-149c`).
- **Pull liveness.** The cell timeout travels in the task and bounds the response window by the watchdog's remainder minus a margin; the claim is extended only on a heartbeat that carries recent CLI output.
- **Call journal.** `jobs/repository.py` writes `host_id` and `access` of the bound member into the effect and call rows; `stage_key` arrives from the caller.
- **Upgrade guard.** The stand refuses to issue `--upgrade` for a pull agent whose connection rules or comparisons use, until `HOSTS-CMP-01`.
- Public functions are exported from `executors/public.py` and `jobs/public.py` for the integrator's wrappers; the stub adapters are filled.

## Required tests
- command: with the project's Python (`FOUNDATION_PYTHON` in the `Makefile`, the venv), `-m pytest tests/unit/executors tests/unit/jobs tests/unit/comparison/spend -q`; database-marked tests under `tests/integration/executors`, `tests/integration/jobs` and `tests/integration/comparison/spend` are written and not run by the lane
- expected: unit tests pass. Cases: availability for each reason; member choice and the pool lock (two calls cannot take one subscription slot, and the comparison mirror spells the same key); a run with one unavailable cell waits and spends no attempt; `cell binding` second write refused; a system object cannot be revised or archived; a token with both or neither target is refused; the cooldown ends after 15 minutes; a retry after a host move finds the saved reply (the idempotency key has no host)

## Integration contract
- The integrator wires the adapters in `adapters.py`/`composition.py` and the `stage_plan` branch of `DatabaseProviders`, and swaps the comparison at `executors/runner.py:606`, at `HOSTS-INT-1`.
- `HOSTS-LAYOUT-01` relies on: the cell binding existing before the first model call, `binding_for(cell)` reading `audit_run_cell_binding`, and the call journal accepting `stage_key`.
- `HOSTS-WEB-01` relies on the host operations of contract 1.45.0 only.

## Failure/idempotency/security cases
- an `outcome_unknown` effect is never sent to another member (`ADR-0026` decision 16)
- a stale heartbeat makes a host unavailable without any write
- reasons for unavailability are in the administrator's details and never in a list
- no secret in any host report or detail

## Rollback / feature flag
With the layout switch off no run carries a `stage_plan`, so the new binding path is not entered; hosts and system objects can be removed by archiving the host. Downgrade of migration `0062` refuses while they exist.

## Handoff
- changed files: the lane lists them; it does not run git
- commands/results: the unit tests above; no database, container or model run
- known limits: the database-marked tests are unexecuted until the integrator's narrow run
- integration notes: the public functions the wrappers call; the lock key constant; the tests that fail if the two lock spellings diverge
