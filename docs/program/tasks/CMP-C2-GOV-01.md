# Task CMP-C2-GOV-01 — make the C2 task records pass executable governance

## Outcome
The C2 FIX and integration task records pass `tests/contract/program/test_wave_governance.py` without changing their captured facts or publication authority.

## Depends on
- CMP-C2-FIX-01

## Frozen inputs
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- migration head: `0040_comparison_ai_reports`
- base commit: `adcac54fcc4fc1830cf57c7fd1cf84af2772dd96`
- failed complete gate: `/tmp/cmp-c2-gate-first.log` on that exact commit

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `tests/contract/program/test_wave_governance.py`

## Captured premise evidence
- premise: P-01

### P-01 — exact governance failure
- captured_at: 2026-10-29
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent make gate`
- captured_output:
  ```text
  1 failed, 1309 passed, 19283 subtests passed in 243.95s
  CMP-C2-FIX-01.md: PREMISE_OUTPUT_REQUIRED, PUBLICATION_TARGET_INVALID
  CMP-WAVE-C2-INT.md: PREMISE_OUTPUT_REQUIRED
  ```
- interpretation: Vitest passed 3651 tests; the gate stopped at contract governance before foundation or backend battery.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-C2-GOV-01.md`
- `docs/program/tasks/CMP-C2-FIX-01.md`
- `docs/program/tasks/CMP-WAVE-C2-INT.md`
- `docs/program/CMP-C2-GOV-01.md`

## Forbidden hotspots
- application code, tests, contracts, migrations, root locks, composition, global styles, `web/**`, `infra/**`
- remote refs

## Non-goals
- no changed outcome or contract authority of either task
- no gate waiver or publication

## Deliverables
- fenced, substantive captured outputs in both task records and the closed publication target value `none` in FIX
- short correction report with the focused governance test result and the unchanged frozen contract proof

## Required tests
- `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program/test_wave_governance.py --basetemp=/tmp/pytest-cmp-c2-gov-01/contract`
- `git diff --check`
- the integration task reruns the complete `make gate` on the next clean commit

## Integration contract
This task corrects only the machine-readable presentation of already captured task evidence. `CMP-WAVE-C2-INT` still alone owns `origin/dev`; `origin/main` remains unauthorised.

## Failure/idempotency/security cases
- if the focused governance test stays red, do not resume the complete gate
- neither edit changes a product contract, runtime behavior or remote ref

## Rollback / feature flag
Not applicable: these are task-record formatting corrections. Reverting them restores the governance failure.

## Handoff
- changed files: `docs/program/tasks/CMP-C2-FIX-01.md`, `docs/program/tasks/CMP-WAVE-C2-INT.md`, this task and `docs/program/CMP-C2-GOV-01.md`.
- checks/results: focused governance test 16 passed; `git diff --check` clean.
- contracts: unchanged API `1.11.0` (176/198/517), migration `0040`.
- risks: none beyond the earlier gate's unfinished foundation/backend battery.
- integration notes: `CMP-WAVE-C2-INT` must run a fresh full `make gate` on a clean commit; no remote publication in this task.
- forbidden hotspots: `git diff --name-only adcac54f -- src tests contracts db web infra pyproject.toml uv.lock Makefile` prints nothing.
