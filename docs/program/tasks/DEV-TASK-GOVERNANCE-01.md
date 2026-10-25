# Task DEV-TASK-GOVERNANCE-01 — give 17 task files real premise evidence

task_id: DEV-TASK-GOVERNANCE-01
status: completed in development candidate

## Outcome

`tests/contract/program/test_wave_governance.py::test_every_task_added_after_governance_activation_satisfies_the_rules` passes. The 17 task files that the guard names on the integration base carry premise evidence whose pasted output was obtained by running the stated command against the task's own base commit on 2026-10-26; where a file lacked governance sections altogether, the missing sections are added without editing any existing text.

## Depends on

- none; this repairs the evidence sections of already completed task files.

## Frozen inputs

- base commit: `0d218e38dd34cc34495bc26983af2f99789667c2`
- the base is the `integration/ar-close-1026` tip at dispatch.
- shared contract `1.4.0`, API 91 paths / 103 operations / 298 schemas, migration head `0032_ar_v3_run_group`, `VERSION` `0.8.0`: all unchanged; no file outside `docs/program` is touched.
- guard: `tests/contract/program/test_wave_governance.py`, activation tree `14caf886e78883ed771d81fbf463c98af727c938`: unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: on the base commit the governance guard reports findings for exactly 17 task files, and no other task file

### P-01 — guard findings on the base tree

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages:tests/contract/program /root/projects/PDF-Analysis/.venv/bin/python -c "import pathlib,subprocess,tempfile;import test_wave_governance as t;d=tempfile.TemporaryDirectory();subprocess.run('git archive 0d218e38dd34cc34495bc26983af2f99789667c2 docs/program/tasks | tar -x -C '+d.name,shell=True,check=True);f=t.governed_task_findings(pathlib.Path(d.name));print(len(f));[print(k,sorted(v)) for k,v in f.items()]"`
- captured_output:
  ```text
  17
  docs/program/tasks/AR-V3-BETA-CITE-LEASE-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-COST-REFUSAL-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-EXECUTOR-WIRE-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-GROUP-API-SEAL-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-GROUP-REVIEW-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-GROUP-REVIEW-SCREEN-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-PROVIDER-LEASE-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-REVIEW-READ-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-RUN-PROFILE-READ-01.md ['PREMISE_DECLARATION_REQUIRED']
  docs/program/tasks/AR-V3-BETA-RUN-REVIEW-BOUNDARY-01.md ['PREMISE_DECLARATION_REQUIRED']
  docs/program/tasks/AR-V3-BETA-RUN-STAGE-SEAL-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/AR-V3-BETA-SCREEN-GATE-REPAIR-01.md ['PREMISE_DECLARATION_REQUIRED']
  docs/program/tasks/AR-V3-BETA-SETTINGS-REPLAY-01.md ['PREMISE_OUTPUT_REQUIRED']
  docs/program/tasks/BETA-PB-PROFILE-TRUTH-01.md ['PREMISE_DECLARATION_REQUIRED']
  docs/program/tasks/EXEC-ENV-OPENROUTER-01.md ['HISTORY_SECTION_REQUIRED', 'PREMISE_DECLARATION_REQUIRED']
  docs/program/tasks/EXEC-SSH-CROPS-01.md ['ENUMERATOR_SECTION_REQUIRED', 'HISTORY_SECTION_REQUIRED', 'PREMISE_SECTION_REQUIRED', 'PUBLICATION_SECTION_REQUIRED']
  docs/program/tasks/EXEC-SSH-TUNNEL-CROPS-01.md ['ENUMERATOR_SECTION_REQUIRED', 'HISTORY_SECTION_REQUIRED', 'PREMISE_SECTION_REQUIRED', 'PUBLICATION_SECTION_REQUIRED']
  ```
- interpretation: The command exports the base commit's `docs/program/tasks` into a temporary directory and runs the unchanged guard function over it, so the result does not depend on this lane's edits. The first line is the count of files with findings; each following line names one file and its finding ids. The count and the names are the work list of this task. Not shown: the intermediate state of any file during the repair.

## Historical evidence

- correction_mode: addendum
- source_record: the 17 task files listed under Allowed paths (`docs/program/tasks/AR-V3-BETA-*.md`, `BETA-PB-PROFILE-TRUTH-01.md`, `EXEC-ENV-OPENROUTER-01.md`, `EXEC-SSH-CROPS-01.md`, `EXEC-SSH-TUNNEL-CROPS-01.md`)
- addendum_path: docs/program/DEV-TASK-GOVERNANCE-01.md

The dispatch brief of this lane asked for in-place repair of these sections, so the source files do change. Each rewritten premise keeps the original dispatch-time command, summary and interpretation verbatim inside the new `interpretation`, and the unedited originals remain at the base commit. The addendum lists, per file, what was re-captured, what differed from the dispatch-time record and what could not be re-run.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/AR-V3-BETA-CITE-LEASE-01.md`
- `docs/program/tasks/AR-V3-BETA-COST-REFUSAL-01.md`
- `docs/program/tasks/AR-V3-BETA-EXECUTOR-WIRE-01.md`
- `docs/program/tasks/AR-V3-BETA-GROUP-API-SEAL-01.md`
- `docs/program/tasks/AR-V3-BETA-GROUP-REVIEW-01.md`
- `docs/program/tasks/AR-V3-BETA-GROUP-REVIEW-SCREEN-01.md`
- `docs/program/tasks/AR-V3-BETA-PROVIDER-LEASE-01.md`
- `docs/program/tasks/AR-V3-BETA-REVIEW-READ-01.md`
- `docs/program/tasks/AR-V3-BETA-RUN-PROFILE-READ-01.md`
- `docs/program/tasks/AR-V3-BETA-RUN-REVIEW-BOUNDARY-01.md`
- `docs/program/tasks/AR-V3-BETA-RUN-STAGE-SEAL-01.md`
- `docs/program/tasks/AR-V3-BETA-SCREEN-GATE-REPAIR-01.md`
- `docs/program/tasks/AR-V3-BETA-SETTINGS-REPLAY-01.md`
- `docs/program/tasks/BETA-PB-PROFILE-TRUTH-01.md`
- `docs/program/tasks/EXEC-ENV-OPENROUTER-01.md`
- `docs/program/tasks/EXEC-SSH-CROPS-01.md`
- `docs/program/tasks/EXEC-SSH-TUNNEL-CROPS-01.md`
- `docs/program/DEV-TASK-GOVERNANCE-01.md`
- `docs/program/tasks/DEV-TASK-GOVERNANCE-01.md`

## Forbidden hotspots

- everything under `src/`, `tests/`, `contracts/`, `web/`, `infra/`, `db/`
- root dependency/lock files, `Makefile`, composition root, global styles
- every other task file and any text of the 17 files outside their governance sections
- `origin/main`, tags, deployment host

## Non-goals

- Changing the guard, the template or any rule they enforce.
- Judging whether a dispatch-time premise was wise; only whether its stated fact holds on the task's base commit.
- Re-running web typecheck or tests (no web toolchain in this lane); `AR-V3-BETA-SCREEN-GATE-REPAIR-01` therefore re-captures its static causes only.
- Using `premise: none` to silence a checkable premise.

## Deliverables

- Real, reproducible premise evidence in 14 files (`AR-V3-BETA-*`, `BETA-PB-PROFILE-TRUTH-01`) and in `EXEC-ENV-OPENROUTER-01`; added governance sections in the two `EXEC-SSH-*` files and the missing Historical evidence section in `EXEC-ENV-OPENROUTER-01`, in a separate commit.
- This task file and its addendum report.

## Required tests

- command: `PYTHONPATH=src:/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program/test_wave_governance.py`
- expected: 16 passed.
- command: the `governance_findings` one-liner over this file.
- expected: `[]`.

## Integration contract

Documentation only. The guard turns green for the integration branch once this lane is merged; there is no ordering dependency on any other lane. The three `EXEC-*` repairs live in one separate commit, so an integrator who does not want sections added to those task files can drop that commit and the guard stays red for exactly those three files.

## Failure/idempotency/security cases

- Every `captured_output` block of the 17 files was re-run from the repository root and compared byte for byte: 19 of 19 blocks reproduce.
- Mutation 1: renaming one `- captured_output:` line makes the guard fail with `PREMISE_OUTPUT_REQUIRED` for that file.
- Mutation 2: changing one pasted line number makes the re-run comparison report a mismatch.
- No pasted output was typed by hand; each was written into the file by the program that ran the command.

## Rollback / feature flag

Not applicable. Forward-revert the lane's commits; no runtime behaviour, data or contract is involved.

## Handoff

- changed files: see the report.
- commands/results: see the report.
- known limits: one file re-captures only static causes; three files received added sections beyond the premise section.
- integration notes: merge at any point; drop the second commit to leave the three `EXEC-*` files unrepaired.
