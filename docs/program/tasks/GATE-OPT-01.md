# Task GATE-OPT-01 — measured gate stages and distinct development tiers

task_id: GATE-OPT-01

## Outcome

The exact development tree exposes `make gate-fast` and `make gate-affected BASE=<full SHA>`
without presenting either as the complete gate. The unchanged complete `make gate` reports
stage durations and pytest's twenty slowest tests, so later performance changes can be judged
against evidence.

## Depends on

- `GATE-PKG-01` — completed on the development line; it owns the existing preflight, shared
  Docker gate slot, static stage and changed-context battery order.

## Frozen inputs

- base commit and verified remote `origin/dev`: `8069220909e40c39e2329d5f5cb9585a5a5714ec`
- domain contract: candidate revision 13, 32 opaque identities
- API contract: 47 paths / 54 operations / 124 schemas; OpenAPI SHA-256
  `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`
- error catalog: 25 codes
- analysis/comparison/event contracts: unchanged by this task
- migration head: `0022_findings_v2`; product version: `0.6.0`
- owner instruction: implement the reviewed gate optimisation brief in this session

## Ownership and publication authority

- This task exclusively owns the root `Makefile` command surface for this change. The
  completed `GATE-PKG-01` is an input, not a parallel editor.
- No ref publication, tag or deployment authority. `origin/main` is forbidden.

## Allowed paths

- `Makefile` — tier targets, timing and pytest duration arguments only
- `tests/contract/test_gate_tiers.py` — tier and timer failure tests
- `docs/program/tasks/GATE-OPT-01.md`
- `docs/program/GATE-OPT-01.md` — measurements and handoff

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency and lock files
- `scripts/gate_host.py`, `scripts/light_acceptance.py` and their existing selection policy
- composition roots, global styles, runtime/product code, Dockerfiles and deploy scripts
- `AGENTS.md`, owner rulings, release refs, tags and the deployment host

## Non-goals

- Reusing a migrated database across tests, changing Docker build caching, or parallelising
  suites without measured isolation evidence.
- Reducing the complete gate's test set or changing the `GATE OK` success line.
- Claiming a real application-image deployment from stubbed deploy-script tests.
- Changing the code-first beta rule `R-135` that defers complete development gates.

## Deliverables

- `gate-fast`: frontend lint and typecheck, the unit suite, basic contract prose/surface
  guards, whitespace; prints `GATE FAST OK` only after every command succeeds.
- `gate-affected`: the existing R-70 `light-acceptance` selection, including its full-gate
  risk refusal and live-journey requirement; prints `GATE AFFECTED OK` only after success.
- Complete-gate timing lines for preflight, slot, static, foundation steps and battery,
  including failed steps, plus `pytest --durations=20` in its Python suites.
- Focused tests and a report with measured limits and deferred full-gate evidence.

## Required tests

- `make -n gate-fast gate-affected gate` parses and retains the complete gate graph.
- The focused tier tests demonstrate a failed command cannot print a success marker,
  `gate-affected` delegates to `light-acceptance`, and timing preserves failure status.
- `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q
  tests/contract/test_gate_tiers.py tests/contract/test_light_acceptance_command.py
  tests/contract/test_gate_host.py` is green in an equipped checkout.
- `git diff --check` is clean; compare the full-gate test graph and pytest paths with base.
- The complete `make gate` remains due on the final integrated beta candidate under `R-135`;
  this task cannot claim `GATE OK` from a local development run.

## Integration contract

`gate-fast` is local feedback. `gate-affected` is R-70 light acceptance under an explicit
full ancestor `BASE` and a clean tree. Neither substitutes for `make gate`, and neither emits
the exact `GATE OK` marker. An unknown or full-gate-risk change is refused explicitly by the
existing selector. The complete gate retains every required component and the same final
success line; duration output appears before that line.

## Failure, idempotency and security cases

- No absent interpreter, missing frontend dependencies, empty suite or failed command is a pass.
- Timing reports both success and failure and cannot replace a command's exit status.
- Repeated tier runs do not mutate product data; `gate-affected` retains the existing
  clean-tree and full-SHA checks.
- No new secret-bearing logs or external network/deployment calls are introduced.

## Rollback / feature flag

Revert this task's Makefile and test/report changes. New commands are opt-in. No data,
contract, migration or runtime rollback is needed.

## Handoff

- changed files: see Allowed paths
- commands/results: `docs/program/GATE-OPT-01.md`
- known limits: `docs/program/GATE-OPT-01.md`
- integration notes: no publication authority; full gate remains deferred under `R-135`
