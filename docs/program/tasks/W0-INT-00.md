# Task W0-INT-00 — clear W0.2 preflight blockers

## Outcome

Make all four W0.2 lane contracts portable and internally consistent after the
accepted dependency, evidence and validator remediations, so they can start in
parallel without an unowned root change, conflicting golden ID namespace, fixed ADR
count or mutable frozen-inventory read.

## Ownership

- implementation/integration owner: primary agent `/root`
- independent reviewer: assigned by the integrator; must not author reviewed files
- downstream consumers: owners of `W0-BHV-02`, `W0-ARC-01`, `W0-DOM-01` and
  `W0-ANA-01`
- product/domain approval authority: repository owner/user for `PD-01`–`PD-04` only

## Depends on

- Completed `W0-BHV-01`, accepted at
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`.
- Completed `W0-DEP-01`, accepted at
  `ab1cfdab0ec5c413b188a44ff82a99586ecd7994`.
- Completed `W0-EVD-01`, accepted at
  `134436502b7ee40ca9abb061e0080741a863ffda`.
- Completed `W0-QA-02`, accepted at
  `6c82004b35f49463c8e7fc8602fbced2f374167e`.

## Frozen inputs

- base commit: `6c82004b35f49463c8e7fc8602fbced2f374167e`
- domain/API/analysis/comparison/event contracts: read-only bootstrap drafts
- validation lock and validator CLI: completed inputs above; read-only
- accepted inventory semantics commit:
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`
- normalized evidence commit: `134436502b7ee40ca9abb061e0080741a863ffda`
- migration head: none

## Allowed paths

- `docs/INDEX.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/W0-INT-00.md`
- `docs/program/tasks/W0-BHV-02.md`
- `docs/program/tasks/W0-ARC-01.md`
- `docs/program/tasks/W0-DOM-01.md`
- `docs/program/tasks/W0-ANA-01.md`
- `docs/program/waves/W0.2_architecture_domain_contract.md`
- `docs/stages/S00_architecture_and_behavior_freeze.md`

No other path is writable.

## Forbidden hotspots

- every `contracts/**`, fixture/evidence and architecture document
- validator/tests and root dependency/lock files
- migrations, production source, composition root and global styles
- checkpoint registry/evidence and every legacy repository path/ref/worktree entry

## Non-goals

- No execution or acceptance of the four W0.2 lane deliverables.
- No machine-contract, ADR, golden fixture or legacy-evidence change.
- No approval of `PD-01`–`PD-04`, contract freeze, checkpoint or tag.
- No application dependency/toolchain selection.

## Deliverables

- Every W0.2 task depends on the completed remediation inputs it consumes and uses
  frozen base `6c82004b35f49463c8e7fc8602fbced2f374167e`.
- Every schema/validator command uses the repository-local hash-locked
  `.venv/bootstrap`; no task or wave gate references the ephemeral `/tmp` path.
- `W0-BHV-02` defines the exact lossless 11-candidate-to-5-selection mapping and a
  machine gate for full, duplicate-free coverage.
- `W0-ARC-01` requires ADR-0001–ADR-0018 as an immutable lower bound while allowing
  a unique, indexed superseding ADR in the owned architecture slot.
- `W0-DOM-01` requires schemas and positive/negative examples for the domain
  catalogs and externally visible error envelope.
- `W0-ANA-01` derives the 31-row expected ledger with immutable `git show` at the
  declared source inventory commit.
- Current state, wave plan, stage map and documentation index agree on the preflight
  status, ownership and downstream dependencies.

## Nine-defect remediation matrix

| # | Resolution | Evidence / remaining owner |
|---|---|---|
| 1 | Closed before lane start | `W0-DEP-01`; all W0.2 schema gates use the hash-locked `.venv/bootstrap`. |
| 2 | Closed in consuming task | `W0-BHV-02` table and machine assertion map every inventory `GJ-01`–`GJ-11` exactly once to five selection IDs. |
| 3 | Closed before lane start | `W0-QA-02` accepts indexed ADR additions and preserves the baseline; `W0-ARC-01` uses the same set-equality rule. |
| 4 | Closed and regression-tested | Git discovery omits ignored and unconditional private/dependency/cache sequences before reads and counts. |
| 5 | Closed and regression-tested | Expected malformed/missing inputs accumulate artifact-specific diagnostics without traceback. |
| 6 | Closed and regression-tested | `W0-QA-02` has 22 real-library tests across discovery, links, schemas, state, identifiers, errors and ADR evolution. |
| 7 | Non-blocking lane deliverable is explicit | Validator checks the current error catalog structurally; `W0-DOM-01` owns full catalog/envelope schemas and positive/negative examples before domain acceptance. |
| 8 | Closed in consuming task | `W0-ANA-01` reads the exact inventory blob with immutable `git --no-replace-objects show` at `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`. |
| 9 | Closed before lane start | `W0-EVD-01` normalized 137 references with zero unresolved locators and bound the 119-Markdown transcript to `0761df0f21ed415083503bef0218dc29da3585be`. |

## Required tests

- Command: `rg -n 'PYTHONPATH=/t[m]p/pdf-analysis-validator-deps|/t[m]p/pdf-analysis-validator-deps' docs scripts tests`.
  Expected: exit `1` and no output.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with standalone `PASS`.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract -p 'test_validate_bootstrap.py' -v`.
  Expected: exit `0`; all W0-QA-02 regressions pass with the real locked library.
- Command: `git diff --check`.
  Expected: exit `0` and no output.
- Independent review traces each of the nine reported defects to an implemented fix
  or an explicit schema-backed W0.2 deliverable and confirms the four lane writable
  sets remain disjoint.

## Integration contract

The integrator may start the four W0.2 lanes concurrently at the frozen base. Lane
owners can rely on one portable validator command, one explicit golden-ID fan-in,
an extensible indexed ADR registry, immutable inventory extraction and explicit
domain-schema/error-envelope acceptance gates. No lane may write another lane's
paths or treat a parallel draft as frozen.

## Failure/idempotency/security cases

- Missing locked environment fails visibly; there is no ambient dependency fallback.
- Any missing/duplicate inventory candidate, removed baseline ADR, unindexed new ADR,
  unknown external error code or working-tree inventory substitution fails closed.
- Re-running documentation integration over the same accepted commits produces no
  semantic change.
- No protected payload, credential, mutable legacy data or external side effect is
  involved.

## Rollback / feature flag

Documentation/task-contract integration only; no feature flag applies. Revert this
task's documentation commit if a lane contract is wrong. Accepted dependency,
validator and evidence commits remain independently revertible and are not rewritten.

## Handoff

- changed files: the exact Allowed paths above
- commands/results and nine-defect review matrix
- new/changed contracts: task/integration contracts only; no machine contract
- known limits: `PD-01`–`PD-04` and all four lane deliverables remain unresolved
- integration notes: provision the locked environment once, then start the four
  disjoint lanes; open `W0-QA-01` only after all four complete
