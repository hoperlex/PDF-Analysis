# Task GATE-OPT-INT-01 — integrate the local gate optimization and suite audit

task_id: GATE-OPT-INT-01

## Outcome

A clean local `integration/gate-opt-01` branch fast-forwards the verified
`origin/dev` base to the completed gate optimization and audit, with the
required bounded checks green on that integrated tree. No remote ref changes.

## Depends on

- `GATE-PKG-01` — completed on the base; owns the existing gate selector and slot.
- `GATE-OPT-01` — completed at `5842d01ce9a1a38fe2097dae080f9792c213ff37`.
- `GATE-SUITE-AUDIT-01` — completed at `f502026b965773ab55fa0b492d193b5c7dd10d4b`.

## Frozen inputs

- remote `origin/dev`: `8069220909e40c39e2329d5f5cb9585a5a5714ec`,
  rechecked with `git ls-remote --heads origin dev` before integration;
- source branch `task/gate-opt-01`: `8db6201139ef431f4e1479a20517f5e4b5100d72`;
- API 47 paths / 54 operations / 124 schemas, OpenAPI SHA-256
  `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog 25; domain candidate revision 13 / 32 identities;
  migration head `0022_findings_v2`; product version `0.6.0`;
- `R-135` defers the complete gate to the final beta candidate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the remote development ref still matched the source branch base

### P-01 — remote ref before integration

- captured_at: 2026-10-15
- command: `git ls-remote --heads origin dev main`
- captured_output:
  ```text
  8069220909e40c39e2329d5f5cb9585a5a5714ec refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: dev matched the frozen base when the local fast-forward began.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

This task owns the isolated local integration branch and these two integration
documents. It has no authority to push `origin/dev` or `origin/main`, create a
tag, run a deployment or claim `GATE OK`.

## Allowed paths

- `Makefile`
- `tests/contract/test_gate_tiers.py`
- `docs/program/tasks/GATE-OPT-01.md`
- `docs/program/GATE-OPT-01.md`
- `docs/program/tasks/GATE-SUITE-AUDIT-01.md`
- `docs/program/GATE-SUITE-AUDIT-01.md`
- `docs/program/tasks/GATE-OPT-INT-01.md`
- `docs/program/GATE-OPT-INT-01.md`
- `.local/tasks.md`
- `.local/handoff/gate-optimization-2026-10-15.md`

The first six paths are the exact source diff. The last two are ignored local
coordination files.

## Forbidden hotspots

`contracts/**`, migrations, root dependencies and locks, composition roots,
global styles, runtime code, deployment files, `AGENTS.md`, owner rulings,
release refs, tags and the deployment host.

## Non-goals

No further test reduction, optimization, full frontend suite, complete gate,
live journey, acceptance or release publication in this stage.

## Deliverables

- Clean local integration branch containing the two completed task commits.
- Integration report with exact SHA, checks, changed paths and limitations.
- Updated local card and handoff for the later beta-gate stage.

## Required checks

- `git ls-remote --heads origin dev` equals the frozen base before merge;
  `git merge --ff-only task/gate-opt-01` succeeds.
- `make -n gate-fast gate-affected gate` exits zero.
- Run the three focused contract files named by `GATE-OPT-01` and the bounded
  `tests/unit` plus two API prose/surface guard files, using the equipped
  parent checkout interpreter from the isolated worktree.
- `git diff --check origin/dev..HEAD`; changed-path/forbidden-hotspot proof;
  clean `git status` after the evidence commit.

## Integration contract

The integrated branch retains the complete gate graph and literal `GATE OK`.
`gate-fast` and `gate-affected` have distinct success markers and remain local
feedback. A later authorized task may publish a freshly verified development
candidate. The final beta task must run the complete gate on its exact clean SHA.

## Failure, idempotency and security

Remote movement or a non-fast-forward source stops integration. A failed check
is recorded, not called a pass. No credentials, corpus data or external state
are written by this task.

## Rollback / feature flag

Delete or reset the local integration branch; the source task branch remains.
The Makefile behavior is opt-in except for duration output in the complete
gate. No data, contract or migration rollback is needed.
