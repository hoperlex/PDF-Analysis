# Task P2-INT-01 — backend composition root and final P02 wiring

> **Status: specified; not dispatchable.** Planned for P02. Sole owner of the backend
> composition root. It is a task in its own right rather than a second window of
> `P2-INT-00`, so no task ID is ever reopened.

## Outcome

One composition root constructs every accepted P02 module from configuration, the
application starts from a clean environment, and a missing or misconfigured dependency
fails explicitly at construction instead of at first use.

## Depends on

- none complete at plan time

Planned predecessors and dispatch conditions — this task is not dispatchable until each is
accepted and integrated, and it must complete **before** `P2-QA-01` so that QA exercises a
wired application rather than a hand-assembled one:

  - `P2-INT-00` — pins and the environment contract
  - `P2-META-01`, `P2-ENG-01`, `P2-AI-01`, `P2-FND-01`, `P2-RUN-01`, `P2-EXP-01` — every
    backend provider it wires
  - `P2-API-01` — the routers it mounts
  - owner decision `OD-07` naming this task the composition-root owner

## Frozen inputs

- the public seams of every accepted P02 module, at their accepted commits
- `docs/program/P02_LOCK.json` and the environment names from `P2-INT-00`, read only
- migration head: the P02 head, read only
- base commit: the accepted `P2-API-01` integration commit

## Allowed paths

- `src/auditmanager/bootstrap/**`
- `src/auditmanager/api/app.py`, `src/auditmanager/api/composition.py`
- `tests/integration/composition/**`
- `docs/program/tasks/P2-INT-01.md` status/handoff
- `docs/navigation/entries/p2-int-01.json`

## Forbidden hotspots

- root dependency locks and `.env.example`, owned by `P2-INT-00`
- `src/auditmanager/api/routers/**` and `api/schemas/**`, owned by `P2-API-01`
- every provider module, `db/migrations/**`, the `Makefile`, `contracts/**`, `fixtures/**`
- `docs/navigation/INDEX.md`, whose regeneration belongs to `P2-INT-02`

## Non-goals

- No domain logic, router, stage, schema or table.
- No service locator and no generic dependency-injection framework.
- No new dependency: a missing pin is returned to `P2-INT-00`.

## Deliverables

- a composition root constructing storage, database, ingest, analysis, findings, decisions,
  runs, exports and the API from settings, by constructor injection only
- explicit construction-time failure when a required dependency is unconfigured, including
  a missing provider key while the analysis mode is `live` — never a silent degrade to
  `recorded`
- an application entrypoint that starts from a clean environment with the documented
  commands, and the execution-process entrypoint the runbook uses
- composition tests under the directory this task owns, which is the directory
  `P2-INT-00`'s former wiring test referenced and nobody owned

## Required tests

- Command: `make foundation`
  Expected: exit `0`.
- Command: `.venv/bin/pytest tests/integration/composition`
  Expected: exit `0`; the container builds, every module resolves, and the
  unconfigured-dependency case fails explicitly with the expected typed error.
- Command: `.venv/bin/pytest tests/integration/composition -k "live_mode_without_key"`
  Expected: exit `0`; proves the live-mode misconfiguration fails at construction and does
  not fall back to recorded mode.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Every module receives its dependencies by constructor injection from this root; no module
builds an engine, an S3 client or a model client itself. `P2-QA-01` exercises the
application through this entrypoint.

## Failure/idempotency/security cases

- Construction is deterministic: the same settings build the same graph.
- No credential is logged, echoed or written to a tracked file.
- A partially configured environment fails loudly rather than starting a degraded process.

## Rollback / feature flag

Revert the wiring commit; the providers remain valid under their own acceptances and no
product data is affected.

## Estimate

Effort P50 1.0 person-day, P80 2.0 person-days. Basis: wiring existing modules from settings, plus composition tests. Calibration pending.

## Handoff

- the container construction signature and the two entrypoints
- commands and results, including the misconfiguration case
- any provider seam that had to be adapted, named with its owner
