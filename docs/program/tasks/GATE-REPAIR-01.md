# Task GATE-REPAIR-01 — reproduce and repair the named reds before the complete gate

task_id: GATE-REPAIR-01

## Outcome

Every red that the debt register names for the development tree (`D-187`, `D-189`,
`D-190`) is reproduced on the lane's own containers, classified, and either repaired in
the tests or reported as a product defect with its evidence, so that the complete gate
the owner assigned for the coming night is not red for a reason already on record.

## Depends on

- `W59-SEAL-FOLLOWUP-01`, `API-FOLLOWUPS-01`, `BETA-CONTRACT-SEAL-01` — completed, merged.

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `41d4b7d4`,
  `integration/night-1020`);
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract and
  catalogue sealed at `1.0.0`;
- rulings: `R-135` (no complete gate in a lane), `R-126` (database suites run on the merged
  candidate), `R-141d/e`; the owner's direct instruction of 2026-10-21 assigning the night
  window for a complete gate and choosing «сначала чиним красные, потом gate»;
- debt rows: `docs/program/DEBT_REGISTER.md` `D-187`, `D-189`, `D-190` (and `D-181` where a
  named file is still red).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/integration/**`
- `tests/contract/**`
- `tests/characterization/**`
- `docs/program/GATE-REPAIR-01.md`
- `docs/program/tasks/GATE-REPAIR-01.md`

## Lane resources

- foundation_instance: `auditmanager-gate-repair`
- postgres_port: `57600`
- s3_api_port: `61400`
- s3_console_port: `61401`
- postgres_db: `auditmanager_gate_repair`
- s3_bucket: `auditmanager-gate-repair`
- qa_api_port: `28500` (`W55B_QA_API_PORT=28500`, outside the kernel's ephemeral range)

## Forbidden hotspots

Every `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and
lock files, `tests/support/**`, `tests/conftest.py`, `tests/e2e/**`, `web/**`,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and the
stand. A conftest inside an allowed directory may change only where the measured red is
caused by that conftest, and the report says so.

## Non-goals

No product change. A red that is a defect of `src/**`, a migration or a contract is not
repaired here: the lane stops that item, records the failing command, the output and the
suspected file, and hands it back. No complete `make gate`, no whole-directory run of
`tests/integration` (focused files and directories only: this host has one lane's worth of
memory), no paid provider call, no change that weakens an assertion to make it pass — a
pin is updated to the new truth only after the report names what the truth is and why.

## Work

1. Provision the worktree (see the brief): `make bootstrap
   FOUNDATION_PYTHON=/usr/bin/python3.12`, the lane `.env` with both sides rewritten.
2. **Measure first**, one measurement at a time, each with its command, exit status and
   counts, on the base tree and before any edit:
   - `tests/integration/db/test_downgrade_chain_round_trip.py` and every file that
     downgrades through `0022_findings_v2` (`grep -rl 0022_findings_v2 tests`);
   - `tests/integration/db/test_norms_corpus_migration.py`;
   - `tests/integration/api/test_query_surface.py` and
     `tests/integration/p02_journey/test_query_surface_over_the_corpus.py`;
   - the `DecisionAdapter` pre-decide test (`tests/integration/api/test_decision_authorship.py`
     and the files `grep -rln DecisionAdapter tests` names);
   - `tests/contract/shared_kernel/test_error_kernel.py` and
     `tests/contract/fixtures_seeded/test_ar_v2_seeded.py` including their database-backed
     variants (the container-free `pytest tests/contract` is already green: 983 passed);
   - `D-189`: `W55B_QA_API_PORT=28500 pytest tests/integration/qa_w55b` and the same without
     the override; `D-190`: `tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py`.
3. Classify each red: stale pin (the vocabulary or count moved legitimately), environmental
   (ports, timing), or product defect. Repair the first two; report the third.
4. `D-189`: move the default QA port pair outside the ephemeral range and probe by `bind`,
   with a quoted mutation that occupies the port. `D-190`: widen the margin or drive the
   clock through the lease module's knobs; the file passes 20 times in a loop.
5. Every new or changed guard is shown failing under a quoted mutation (`-o pythonpath=<copy>/src`
   and proof the copy was imported, `docs/program/dispatch/OPERATING_CONSTRAINTS.md` §2).
6. After each repaired group, commit on the lane branch; the report is the last commit.

## Deliverables

Repaired tests and `docs/program/GATE-REPAIR-01.md`: the measured list before, one row per
red with classification and fix (or the evidence of a product defect), the list after,
the commands with exit status, what was not exercised.

## Required tests

Each repaired file green on the lane's own containers, before/after counts quoted;
`git diff --check`; `pytest tests/contract` (container-free) still green. Nothing else.

## Integration contract

Merged as a real merge into `integration/night-1020` by the integrator; the dev tip after
the merge is the candidate the integrator freezes for the night's complete gate.
Hand-back by 22:30 +05 on 2026-10-21 with whatever is repaired: each group is a commit, so
a partial result merges cleanly. Product defects found are reported at once by message.

## Failure/idempotency/security cases

A red that passes on rerun without a change is recorded as flaky with its rate, not as
repaired. A red whose repair would need a hotspot is reported, not absorbed. The lane stops
its own containers (`make down` for its own instance) when it hands back and kills no
process it did not start (by confirmed PID, never by pattern).

## Rollback / feature flag

Revert the merge. Tests only; no flag.
