# Task P2-INT-00 — P02 toolchain pins, composition root and wave ownership

> **Status: specified; not dispatchable.** Planned as the first P02 task. Sole P02 writer
> of the root dependency locks and the backend composition root, across two windows.

## Outcome

One locked P02 dependency set and one composition root that constructs every P02 module
from configuration, so no lane invents a wiring path or becomes a second lock writer.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — window 1 is not dispatchable until all of
these hold, and window 2 not until `P2-QA-01` is accepted:

  - `P1-INT-01` — `PF-01` accepted
  - `P1-NAV-01` — navigation layer accepted
  - `P0-PLN-01` — this plan accepted and its forecast recalibrated against measured P01
    throughput
  - owner decisions `OD-01` PDF library, `OD-02` model provider, `OD-06` root-lock owner
    and `OD-07` composition-root owner

## Frozen inputs

- domain contract: `contracts/domain/v1/**`, read only
- API contract: none in window 1; `contracts/api/v1/**` belongs to `P2-API-01`
- analysis contract: `contracts/analysis/v1/stage-registry.json`, read only
- migration head: the P01 baseline, read only; extended only by `P2-DOM-01`
- base commit: the accepted `P1-INT-01` integration commit

## Allowed paths

- the root dependency manifests and lock files named in `FOUNDATION_LOCK.json`
- `.env.example` — additive P02 names only
- `src/auditmanager/bootstrap/**`
- `src/auditmanager/api/app.py`, `src/auditmanager/api/composition.py`
- `docs/program/P02_LOCK.json`
- `docs/navigation/INDEX.md` — regeneration at wave close only
- `docs/program/tasks/P2-INT-00.md`
- `docs/navigation/entries/p2-int-00.json`

## Forbidden hotspots

- `Makefile` and `FOUNDATION_LOCK.json`: the nine targets are frozen by FF-01 §3 and this
  task adds none
- `infra/local/**`, `db/migrations/**` and every other module under `src/auditmanager/**`
- `contracts/**`, `fixtures/**`, `scripts/**`, CP-00 evidence and Git tags

## Non-goals

- No domain logic, router, stage, schema or table.
- No service locator and no generic dependency-injection framework.

## Deliverables

- exact pins for the PDF library, the model SDK and the web framework stack, recorded in
  `docs/program/P02_LOCK.json` with the command that resolved them
- additive `.env.example` names: `ANALYSIS_MODE` with values `recorded` and `live`, the
  model provider and model id, the provider API key and the per-run cost ceiling
- a composition root constructing storage, database, ingest, jobs, analysis, findings and
  API from settings, failing explicitly when a required dependency is unconfigured
- the ownership record naming this task the sole P02 writer of root locks and the
  composition root
- the regenerated navigation index at wave close

## Required tests

- Command: `make bootstrap && make bootstrap`
  Expected: exit `0` twice; `git status --porcelain` is empty afterwards.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `.venv/bin/pytest tests/integration/composition`
  Expected: exit `0`, including the unconfigured-dependency failure case.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Every lane receives its dependencies by constructor injection from the composition root;
no module builds an engine, S3 client or model client itself. A new third-party dependency
is requested from this task and never added by a lane.

## Failure/idempotency/security cases

- A missing or invalid provider key in `live` mode fails at startup with
  `dependency_unavailable` and never degrades to `recorded`.
- Repeated bootstrap changes no tracked file.
- `.env.example` carries disposable placeholders only, and a credential scan runs on every
  window.

## Rollback / feature flag

`ANALYSIS_MODE` defaults to `recorded`. Rollback is a revert of the wiring commit; no
product data exists at window 1.

## Estimate

P50 1 day across both windows, P80 2.5 days.

## Handoff

- the pin table and the command that resolved it
- the environment names added and the container construction signature
- the regenerated navigation index and containment proof for the `Makefile` and
  `FOUNDATION_LOCK.json`
