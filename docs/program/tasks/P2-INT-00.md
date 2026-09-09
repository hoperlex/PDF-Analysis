# Task P2-INT-00 — P02 dependency pins and environment contract

> **Status: specified; not dispatchable.** Planned as the first P02 task. Sole P02 owner
> of the root dependency locks and the environment contract. It performs no wiring: the
> composition root belongs to `P2-INT-01`, so no task ID is reopened in a second window.

## Outcome

One locked P02 dependency set and one additive environment contract, fixed before any
provider lane starts, so no lane invents a pin or becomes a second lock writer.

## Depends on

- none complete at plan time

Planned predecessors and dispatch conditions — this task is not dispatchable until all of
these hold:

  - `P1-INT-01` accepted, that is `PF-01`
  - `P1-NAV-02` accepted, so the navigation layer resolves the foundation seams
  - this plan accepted and its forecast recalibrated against measured P01 throughput
  - owner decisions `OD-01` PDF library, `OD-02` model provider, `OD-03` cost ceiling and
    `OD-06` post-P1 root-lock owner recorded

## Frozen inputs

- domain contract: `contracts/domain/v1/**`, read only
- API contract: none; `contracts/api/v1/**` belongs to `P2-API-01`
- analysis contract: `contracts/analysis/v1/stage-registry.json`, read only
- migration head: the P01 baseline, read only; extended only by `P2-DOM-01`
- base commit: the accepted `P1-NAV-02` integration commit

## Allowed paths

- the root dependency manifests and lock files named in `FOUNDATION_LOCK.json`
- `.env.example` — additive P02 names only
- `docs/program/P02_LOCK.json`
- `docs/program/tasks/P2-INT-00.md` status/handoff
- `docs/navigation/entries/p2-int-00.json`

## Forbidden hotspots

- `src/auditmanager/**` in its entirety, including `bootstrap/**` and `api/**`, which
  belong to `P2-INT-01`
- `Makefile` and `FOUNDATION_LOCK.json`: the nine targets are frozen by FF-01 §3
- `infra/local/**`, `db/migrations/**`, `tests/**`, `web/**`
- `docs/navigation/INDEX.md`, `contracts/**`, `fixtures/**`, `scripts/**`, CP-00 evidence
  and Git tags

## Non-goals

- No wiring, composition root, container, router, domain logic, stage, schema or table.
- No new `make` target and no private command alias.
- No dependency needed only by P03 or later.

## Deliverables

- exact pins for the PDF text-extraction library, the model SDK and the web framework
  stack, recorded in `docs/program/P02_LOCK.json` with the command that resolved them and
  the licence of each library, so `OD-01` is answered with evidence rather than a name
- additive `.env.example` names: the analysis mode with values `recorded` and `live`, the
  model provider and model id, the provider API key and the per-run cost ceiling
- the ownership record naming this task the sole P02 writer of root locks and the
  environment contract, and `P2-INT-01` the sole writer of the composition root

## Required tests

- Command: `make bootstrap && make bootstrap`
  Expected: exit `0` twice; `git status --porcelain` is empty afterwards.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `.venv/bin/python -c "import importlib,json;[importlib.import_module(m) for m in json.load(open('docs/program/P02_LOCK.json'))['import_check']]"`
  Expected: exit `0`; every pinned runtime dependency imports in the locked environment.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Provider lanes may rely on exact locked dependencies and environment names. They may not
add or upgrade a root dependency; a new dependency is requested from this task. Nothing in
this task constructs an object, so no lane can import a container from it.

## Failure/idempotency/security cases

- A missing or invalid provider key in `live` mode is an explicit failure at construction
  time in `P2-INT-01`, never a silent degrade to `recorded`.
- Repeated bootstrap changes no tracked file.
- `.env.example` carries disposable placeholders only, and a credential scan runs before
  hand-off.

## Rollback / feature flag

The analysis mode defaults to `recorded`. Rollback is a revert of the pin commit; no
product data exists at this point.

## Estimate

Effort P50 0.5 person-day, P80 1.5 person-days. Basis: pinning and locking a known dependency set, with no code construction. Calibration pending.

## Handoff

- the pin table with licences and the command that resolved it
- the environment names added
- containment proof for the `Makefile`, `FOUNDATION_LOCK.json` and `src/auditmanager/**`
