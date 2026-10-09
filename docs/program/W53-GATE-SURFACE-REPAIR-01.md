# W53-GATE-SURFACE-REPAIR-01 handback

Branch: `agent/w53-gate-surface`. Dispatch base:
`8d94517e30c91564557d1f30ba98cd76cd559c62`. The integrator must read
back the exact committed HEAD from Git; this record cannot contain its own SHA.

## 1. Changed files

- `tests/e2e/pc01/test_acceptance.py`
- `tests/integration/api/test_authorization.py`
- `tests/integration/api/test_served_document_and_health_plane.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_every_port_implementation_is_whole.py`
- `docs/program/W53-GATE-SURFACE-REPAIR-01.md` (this handback)

The authorization sweep now names all six W53 operations and checks all 40 guarded
operations against the 43-operation router. It also includes the new execution
module in the exact `CurrentSubject` reader set and checks every HTTP method in
the served-document security sweep. The 422 sweep includes PATCH and PUT rather
than silently skipping them. PC-01 still rejects any PUT/PATCH/DELETE route on a
document or version and now explicitly accounts for the two execution controls.
The composition guards include the execution port and both new unaddressed GET
collections in their complete surface partition and page-shape sweep.

## 2. Checks and results

On disposable private `gate-w53surface` services (PostgreSQL `56920`, S3
`60520/60521`), `make up check-services migrate check-db check-storage` exited 0
and reached migration head `0017_execution_queue`. The setup log is
`/tmp/w53-gate-surface/setup.log` (SHA-256
`65cc52b876f68be3b9834ab25db6868db23780ff1a24b52d777402798ffe1211`).

The five owned test modules were run together. Result: 116 passed and one failed
in 145.85 seconds. That failure was this repair's literal sorted subject-reader
expectation, with `execution.py` placed after `me.py`; the observed import set was
correct. After fixing the order, that case plus four adjacent authorization,
reader anti-vacuity and schema cases passed 5/5 in 1.93 seconds. Logs:
`/tmp/w53-gate-surface/owned-five.log` (SHA-256
`c429cc98007b2dd576d489b5205dc6a5aa42fd4f2739509659bceaa169d8f542`)
and `/tmp/w53-gate-surface/security-rerun.log` (SHA-256
`e6d64048914e05a1b1512386d4371bcfbab96729ec50921feb4d1556e868eff3`).
The full five-module run is not represented as a single green rerun; the integrator
owns the subsequent complete gate.

AGENTS §8 capacity checks were recorded immediately before setup and both test
runs at `/tmp/w53-gate-surface/{preflight,tests-preflight,rerun-preflight}.log`.
Available bytes before setup were 8,261,332,992 on the shared worktree/Docker
filesystem, above the 1.5 GB expected setup peak plus 3 GiB margin. `git diff
--check` and `compileall` of all five owned modules passed. No full `make gate`
was run here.

## 3. Contracts

No contract or migration changed. OpenAPI SHA-256 is
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
domain state-machine SHA-256 is
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
The frozen API remains 36 paths, 43 operations and 91 schemas.

## 4. Risks and limitations

The test-only patch changes no runtime behavior. The combined five-module run
has one red expectation from this task, resolved in the focused rerun; the final
exact candidate still needs the integrator's full gate. W53 owner-stop decisions
and release readiness remain outside this grant.

## 5. Integrator instructions

Read back this branch's exact HEAD and changed paths against the dispatch base,
then integrate this test-only commit. Run the full gate on the final clean exact
candidate. Do not interpret this handback as W53 acceptance or publication
authority.

## 6. Allowed-path and forbidden-hotspot proof

`git diff --name-only 8d94517e30c91564557d1f30ba98cd76cd559c62 HEAD`
must return exactly the six files in §1. No `contracts/**`, production code,
migration, root dependency/lock, composition root, global style, stand, ref or tag
is part of the delta. The disposable local `.env` and `.venv` test tooling are
removed from this worktree before handback. The complete changed-path audit and
clean status are included in the agent's return message.
