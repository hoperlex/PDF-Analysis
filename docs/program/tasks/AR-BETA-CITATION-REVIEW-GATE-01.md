# Task AR-BETA-CITATION-REVIEW-GATE-01 — review-only v3 beta citation plan

task_id: AR-BETA-CITATION-REVIEW-GATE-01
status: completed (unserved review-only gate)

## Outcome

The unserved v3 Run bridge can produce a beta review plan from an exact Run-pinned set. It reports every topic in its F1/F2/A1/A2/S1/S2 scope and only supplies grounded provisional proposals for expert review. A context-only label never becomes a normative publication candidate, including when mixed with a provisional label.

## Depends on

- `AR-CORPUS-CITATION-BRIDGE-01` — completed Run/Attempt/set draft boundary.
- `AR-BETA-AVAILABLE-SOURCE-GATE-01` — completed, exact policy digest `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`.

## Frozen inputs / contract versions

- Base `b8fc2744`; contract `1.0.0`, migration head `0031_executor_pull_channel`.
- Snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`; six-group composition `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`.
- Beta scenario: new multi-apartment residential building Ф1.3; every numeric conclusion requires expert review.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json`
- enumerator_owner: `AR-BETA-AVAILABLE-SOURCE-GATE-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/norm_map tests/integration/runs/test_v3_corpus_citation_bridge.py`

## Captured premise evidence

- premise: the unserved Run bridge can ground a supplied v3 response, but it has no beta source-disposition replay gate.
- captured_at: 2026-10-23
- command: `git rev-parse HEAD; rg -n 'def plan_v3_corpus_citations|class V3CorpusCitationPlan' src/auditmanager/runs/v3_citations.py`
- captured_output:
  ```text
  b8fc2744
  51:class V3CorpusCitationPlan:
  128:def plan_v3_corpus_citations(
  ```
- interpretation: the bridge produces publication candidates, but beta source dispositions have no replay gate yet.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/v3_citations.py`
- `src/auditmanager/analysis/public.py` (single owner for the review-only policy/set reader export)
- `tests/integration/runs/test_v3_corpus_citation_bridge.py`
- `docs/program/tasks/AR-BETA-CITATION-REVIEW-GATE-01.md`
- `docs/program/AR-BETA-CITATION-REVIEW-GATE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles, served profile registry, router/UI, provider transport, norm corpus and source bytes, `origin/main`, tags and deployment host.

## Non-goals

No legal-edition approval, qualified `nrs_` creation, provider call, StageResult, saved citation/finding, automatic numeric verdict or served profile switch.

## Deliverables

- Review-only plan with complete scope topic statuses and grounded provisional proposals.
- Context-only and mixed citation suppression with exact proposal ordinals.
- Focused tests, report and integrator instructions.

## Checks

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/norm_map tests/integration/runs/test_v3_corpus_citation_bridge.py tests/contract/program`
- `git diff --check` and exact allowed-path proof.

## Integration contract

A later beta runtime may consume only this review-only plan and must display its topic statuses and six Run IDs; it must not pass provisional observations to the existing normative publication path before the expert's explicit decision and applicable edition check. Recheck Attempt and set authority after any model effect. A policy digest or scope mismatch refuses. No fallback to v1 is allowed for a selected v3 beta Run.

## Rollback / feature flag

This plan is unserved; revert the two code/test files before activation. A later served profile switch must be separately owned and reversible while preserving immutable historical Runs.
