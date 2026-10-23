# Task V2-FINDING-MERGE-READ-01 — return one Finding per published v2 merge group

task_id: V2-FINDING-MERGE-READ-01

## Outcome

The served list, detail and published count of a recorded AR v2 finding use one persisted Finding identity; reads return its canonical observation once and its other grounded group members in `merged_observations`, with each member's proposed severity and evidence.

## Depends on

- `WEB-REVIEW-FOLLOWUPS-01` — completed v2 severity UI.
- `AR-V3-BETA-SAVED-SOURCE-01` — completed development base; no overlapping files.

## Frozen inputs

- domain/API/event contracts: `1.2.0`; existing optional `Finding.merged_observations` and `FindingObservation.proposed_severity`.
- migration head: `0032_ar_v3_run_group`; no migration.
- base: `9dfa2691c8bfe0f33f206bdabc736aab96ae0f2c` on `origin/dev`.
- product version: `0.8.0`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: v2 publisher links several observations to one finding but the served adapter returns one FindingView per observation without merged members.

### P-01 — read projection and producer

- captured_at: 2026-10-23
- command: `rg -n 'merged_observations=|_finding_view\(r, evidence|run_recorded_v2_merge_stage|publish_v2_merge_plan' src/auditmanager/bootstrap/adapters.py src/auditmanager/runs/executor.py src/auditmanager/runs/recorded_v2_publication.py`
- captured_output:
  ```text
  src/auditmanager/bootstrap/adapters.py:1628:                _finding_view(r, evidence, current_verdict(session, r.finding_uid))
  src/auditmanager/runs/executor.py:1091:        from auditmanager.runs.recorded_v2_merge import run_recorded_v2_merge_stage
  src/auditmanager/runs/executor.py:1114:            run_recorded_v2_merge_stage(
  src/auditmanager/runs/recorded_v2_publication.py:21:    publication_rows_exist, publish_v2_merge_plan, select_terminal,
  src/auditmanager/runs/recorded_v2_publication.py:192:        published = publish_v2_merge_plan(
  ```
- interpretation: the persisted v2 producer exists; the read adapter does not group its rows or set `merged_observations`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/findings/queries.py`
- `src/auditmanager/findings/__init__.py`
- `src/auditmanager/bootstrap/adapters.py`
- `tests/integration/findings/test_v2_merged_read_projection.py`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/V2-FINDING-MERGE-READ-01.md`
- `docs/program/V2-FINDING-MERGE-READ-01.md`

## Forbidden hotspots

- `contracts/**`, migration head, root dependencies/lockfiles, other composition files, global styles, v2/v3 writer and provider code, `origin/main`.

## Non-goals

- Changing merge membership, deterministic evidence, v3 CITE, expert verdicts or the comparison/export raw-observation reader.

## Deliverables

- Findings-domain group projection with canonical validation and identity count; list/detail adapter mapping; focused regression; debt correction and report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/findings/test_v2_merged_read_projection.py -x --tb=short` — expected green after failing-first test.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/findings/test_merge_publication_plan.py tests/integration/decisions/test_v2_severity_semantics.py -x --tb=short` — expected green.
- `git diff --check` and exact allowlist — expected green.

## Integration contract

This task owns the `FindingAdapter` integration slot in `bootstrap/adapters.py` for this wave. `published_findings` remains raw and ordered for comparison/export consumers. The served list/detail views group those rows by persisted `finding_uid`, use `finding.canonical_observation_id`, and fail closed on inconsistent groups. The exact legacy v1 shape (one member, no severity, no v2/v3 profile) remains readable when its canonical column is null. No API reseal.

## Failure/idempotency/security cases

- A missing/foreign canonical ID, duplicate member or mismatched group attributes cannot be shown as separate findings. The read performs no writes or effects. The same persisted rows produce the same order.

## Rollback / feature flag

- Revert the commit. No flag; the task corrects the existing read path.

## Handoff

- Changed files, checks, limits and integration notes: `docs/program/V2-FINDING-MERGE-READ-01.md`.
