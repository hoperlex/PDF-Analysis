# Task W48-PORTS — verify the already-landed narrow existence semantics

## Outcome

The Stage-B premise for D-74 is reconciled with the repository: the four required
implementations are present, callers use the narrow operations, focused tests prove that full
projections are not assembled, and no duplicate runtime repair is introduced.

## Depends on

- `W48-JUDGE-A` — completed at `d5655ec`
- `W48-FIX` — completed at `fad3c28748ef52bc9b5f711191ff0130483e0055`

## Frozen inputs

- Stage-B base: `fad3c28748ef52bc9b5f711191ff0130483e0055`
- API: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`
- error catalog: 22; migration head: `0013_norm_embeddings`
- implementation provenance: `8877d5de` (`feat(A3): D-74`)

## Allowed paths

- `docs/program/W48-PORTS.md`

Production and test paths are read-only subjects of this verification task.

## Forbidden hotspots

- all runtime and test code
- `contracts/**`, generated clients, error catalog and migrations
- root dependencies/locks, `Makefile`, composition root and global styles
- `CURRENT_STATE.md`, `DEBT_REGISTER.md`, historical reports, refs, tags and deployment state

## Non-goals

- no second implementation of an operation already present
- no generic repository/base service and no SQL in routers
- no API response, error, contract or migration change
- no canonical debt-register edit outside `W48-INT-CLOSE`

## Deliverables

- completion report proving the port/adapter/test/caller matrix and commit provenance
- focused test result and allowed-path-only diff proof

## Required tests

- `.venv/bin/python -m pytest tests/integration/api/test_existence_is_not_a_full_read.py
  tests/integration/composition/test_every_port_implementation_is_whole.py -q`
- `git log`/`git blame` evidence tying all semantic methods to `8877d5de`
- source query proving `list_findings` and `list_decision_history` call the narrow methods
- `git diff --check` and an allowed-path-only diff

## Integration contract

`RunPort.run_exists` and `FindingPort.finding_exists` are the sole semantic checks used by the
two parent-existence paths. Both production adapters and both API test implementations satisfy
the ports. Unknown parents keep the established typed refusal. Integration may fast-forward this
report only; no runtime byte is expected to change.

## Failure/idempotency/security cases

- a full projection method called by either list router fails the focused regression
- a missing implementation fails the whole-port composition check
- unknown parent behaviour remains covered by the existing API integration suite
- verification uses no host, credential, provider or persistent external side effect

## Rollback / feature flag

Documentation-only verification. Revert the report commit if its evidence is wrong; no feature
flag or data rollback applies.

## Handoff

- changed files/checks: recorded in `docs/program/W48-PORTS.md`
- contracts/runtime: unchanged
- known limit: the stale register row is closed only by `W48-INT-CLOSE`
- integration note: do not manufacture a runtime diff merely to satisfy the old dispatch premise
