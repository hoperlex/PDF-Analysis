# Task W53-ALR05-REPAIR-01 — restore public context boundaries

## Outcome

Eliminate the three W53 deep cross-context imports reported by the executable ALR-05 guard through meaningful `runs.public` and `jobs.public` seams. Preserve startup, lease, and reclaim behavior.

## Depends on

- W53-SEAL-01
- W53-EXEC-01
- W53-EXEC-REPAIR-02
- W53-REHEARSAL-01

## Frozen inputs

- domain revision 9 / 29 identities; state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- API `1.0.0-draft.1`, 36/43/91; OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- analysis/comparison/event: frozen W53 SEAL set; migration head `0017_execution_queue`.
- base code before this dispatch amendment: `f69080608e6139bdd3ca0708b4960c2637fc4e1a`, after the independent QA report and proxy repair. Integrator assigns the exact post-amendment SHA.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — independent Y guard failure reproduced by integrator

- captured_at: 2026-10-09
- command: `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/architecture/test_alr05_boundaries.py`
- captured_output:
  ```text
  F.                                                                       [100%]
  =================================== FAILURES ===================================
  ____________ test_backend_cross_context_imports_use_public_modules _____________

      def test_backend_cross_context_imports_use_public_modules() -> None:
          assert SOURCE_ROOT.is_dir(), f"ALR-05 source root is absent: {SOURCE_ROOT}"
          violations = _violations()
  >       assert violations == [], "ALR-05 violations:\n" + "\n".join(
              violation.render() for violation in violations
          )
  E       AssertionError: ALR-05 violations:
  E         deep src/auditmanager/api/app.py:309 auditmanager.runs.carrier
  E         deep src/auditmanager/jobs/repository.py:338 auditmanager.runs.repository
  E         deep src/auditmanager/runs/executor.py:113 auditmanager.jobs.lease
  E       assert [Violation(ki....jobs.lease')] == []
  E
  E         Left contains 3 more items, first extra item: Violation(kind='deep', path='src/auditmanager/api/app.py', line=309, target='auditmanager.runs.carrier')
  E         Use -v to get more diff

  tests/contract/architecture/test_alr05_boundaries.py:135: AssertionError
  =========================== short test summary info ============================
  FAILED tests/contract/architecture/test_alr05_boundaries.py::test_backend_cross_context_imports_use_public_modules
  1 failed, 1 passed in 0.29s
  ```
- interpretation: full gate's architecture guard is red on the merged W53 code. The locations are exact current-tree hits; no claim about other checks follows.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/api/app.py` (only lifespan's carrier-start seam; exclusive composition-root grant)
- `src/auditmanager/runs/public.py`
- `src/auditmanager/jobs/repository.py` (only reclaim's Run seam)
- `src/auditmanager/runs/executor.py` (only lease import and calls)
- `src/auditmanager/jobs/public.py`
- `docs/program/W53-ALR05-REPAIR-01.md`

## Forbidden hotspots

- `contracts/**`, migrations, other app/composition files, root dependency/lock, global styles, generated client, tests, proxy, execution query, rehearsal scripts, release/backup/deployment files, working stand, refs/tags.

## Non-goals

- Silencing/changing the ALR-05 guard, moving business rules into router or generic utils, changing durable state/retry semantics or API shape.
- Fixing Y's separate journal/pagination findings.

## Deliverables

- Purposeful bounded-context public functions/exports for (1) serving-lifespan carrier start, (2) Job reclaim's Run operation, (3) lease heartbeat start/stop. Avoid new import cycles and mere filename indirection that broadens public surface without a cross-context contract.
- Six-item handback report with clean branch/HEAD, exact diff, verification and risks.

## Required tests

- The exact ALR-05 guard must pass 2/2. Run import/lifespan/reclaim/lease focused tests, including `tests/integration/runs/test_w53_execution.py` and the two-connection lease/watchdog tests where private services are available after QA's live window. Apply AGENTS.md §8 before heavy tests. `git diff --check`, frozen hashes and path audit required. Keep logs under `/tmp/w53-alr05-repair-01/`.
- The six independent `qa_w53` defects are separate; do not alter their source behavior or tests under this boundary repair. This lane's focused tests need to distinguish those known red guards from an ALR regression.

## Integration contract

All three cross-context calls go through stable public seams; behavior and frozen contracts remain unchanged. If a true cycle or extra path is required, return exact evidence for an amended grant before editing it. Integrator repeats ALR guard on merged SHA.

## Failure/idempotency/security cases

- Startup must start durable carrier only in entered serving lifespan; direct/no-lifespan paths must not claim DB-wide jobs. Lease watchdog must retain the same thread-local ownership and fencing. Reclaim must preserve lock order and typed outcomes.

## Rollback / feature flag

No flag; revert this narrow repair if import or behavior tests fail. No runtime schema change.

## Handoff

- changed files; commands/results; contracts; risks; integration instructions; forbidden-hotspot proof — all six AGENTS.md §5 items.
