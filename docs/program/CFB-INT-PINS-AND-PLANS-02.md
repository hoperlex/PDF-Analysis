# CFB-INT-PINS-AND-PLANS-02 — integration result

## Result

The dev candidate aligns the current CSV seam, manual text and guards with
the already implemented 19-column W56a exporter. The first 17 OD-11 columns
retain their order; `severity` and `severity_proposed` remain appended. It also
adds a pure, fail-closed AR v2 merge-publication plan and a pure W57b plan
that turns only newer-edition citations into PDF-text-anchored rule candidates.
Neither plan is connected to a runtime publisher.

## Changed files

- CSV pins and copy: the 17 tracked paths enumerated in
  `W56A-INT-CSV-PINS-SYNC-01.md`, including the integrator's correction to
  `test_frozen_column_list.py`.
- Pure code and tests: `src/auditmanager/findings/merge_publication_plan.py`,
  `tests/integration/findings/test_merge_publication_plan.py`,
  `src/auditmanager/norms/references/observation_plan.py`,
  `tests/integration/norms/references/test_observation_plan.py`.
- The three task files and reports, this task/report and `CURRENT_STATE.md`.

## Checks

- Merge planner/core/input plus reference planner/resolver: 59 passed.
- CSV seam and frozen-column no-DB guards: 26 passed, 2 DB cases deselected.
- Direct task governance for all four new task files: `[]`.
- Python compilation, frozen hashes, `git diff --check` and exact changed-path
  check: pass.
- The 19-column server/seam/web ordered lists match. PC-01's 4288 and 4562
  byte pins are derived from historical 4251/4525 bytes plus 27 header bytes
  and two delimiter bytes for each of five v1 rows; they are unmeasured.

## Contracts, risks and next work

No `contracts/**`, migration, provider lock, root dependencies/locks,
composition root, global styles, corpus source or `origin/main` changed.
The migration head remains `0022_findings_v2`.

`DATABASE_URL` is absent, so DB-backed CSV and publication behavior remains
untested. `web/node_modules` is absent, so web guards are unrun. Historical
characterization record 12 stores the old 17-column bytes; its live comparison
can fail until a separately owned compatibility exception or rebaseline is
implemented. The current 19-column byte pins need DB confirmation. W54's
heavy corpus steps remain behind the documented host capacity floor.

The later W56a publisher should consume the merge plan and insert all members
with one finding UID per group, setting canonical in the same savepoint.
The later W57b deterministic stage should consume the reference candidate
plan after the verified-set and contract grants. Both must keep expert
decisions separate from model or rule output.

## Publication

Target: `origin/dev` only after exact candidate checks and remote ref
fast-forward proof. No `origin/main` authority, release tag, full `make gate`
or beta verdict is claimed under R-135.
