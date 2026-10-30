# HOTFIX-FULL-ANALYSIS-1030 — automatic full-document extended review

task_id: HOTFIX-FULL-ANALYSIS-1030

## Outcome

A fresh section Run automatically plans every admitted image block and page for extended review. Finite per-request provider limits are handled by repeatable batches, and coverage remains explicit. The user does not configure document-size limits during beta. Old accepted Runs keep their frozen authority.

## Depends on

- `EXEC-CODEX-OPTIONAL-SCHEMA-1030` — completed Codex section-response repair, included in this candidate.
- `HOTFIX-AR-PIPELINE-INT-1030` — completed four-procedure extended workflow and cost authority.

## Frozen inputs

- Base `5d7567d4` (`origin/dev` at task start), plus merged `EXEC-CODEX-OPTIONAL-SCHEMA-1030` candidate; API 1.14.0, 233 paths / 259 operations / 620 schemas; migration head `0043_stage_ai_generations`.
- Existing v1/v2 accepted `max_blocks=16` authorities are immutable. Fresh v2 consent records an explicit full-document policy. Ingest accepts at most 500 pages and 1,000 image blocks; provider calls remain finite and metered routes retain explicit cost consent.

## Enumerator ownership

- enumerated_set_changed: no

## Captured premise evidence

- premise: the accepted v2 policy selects sixteen image blocks and preflight freezes that count
- captured_at: 2026-10-30
- command: `rg -n 'MAX_BLOCKS = 16|max_blocks.*16' src/auditmanager/analysis/extended/core.py src/auditmanager/runs/preflight.py`
- captured_output:
  ```text
  src/auditmanager/analysis/extended/core.py:19:MAX_BLOCKS = 16
  src/auditmanager/runs/preflight.py:184:            extended = {"enabled": True, "max_blocks": 16, "plan_version": "extended-review-v2"}
  ```

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

This hotfix owns the extended review implementation, cost preflight/reader, and the single `RunAdapter` composition slot that passes its existing Blob store into preflight in this isolated candidate. No simultaneous writer to those paths in this branch.

## Allowed paths

- `src/auditmanager/analysis/extended/**`
- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/bootstrap/adapters.py` (the named integration/composition slot, only preflight construction)
- `tests/unit/analysis_extended/**`
- `tests/unit/runs/test_cost_preflight.py`
- `tests/unit/runs/test_cost_policy.py`
- `web/src/widgets/extended-review/ui/extended-review.tsx`
- `web/tests/unit/**/extended-review*`
- `web/tests/unit/analysis-extended/workflow.test.ts`
- `docs/program/tasks/HOTFIX-FULL-ANALYSIS-1030.md`
- `docs/program/HOTFIX-FULL-ANALYSIS-1030.md`

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies/lockfiles, all other composition-root lines, global styles, model profiles and prompts, and `origin/main`.

## Non-goals

- No claim that an unavailable normative corpus, illegible source, or provider context failure can be made complete. No expert decision or changed deterministic evidence. No retroactive extension of accepted Runs and no automatic extra paid call outside accepted cost authority.

## Deliverables and checks

- New fresh authority for automatic document-wide review, with legacy 16-block behavior retained for old authority.
- Bounded provider requests cover every admitted block/page in repeatable batches; observation and normative processing preserve all originals and report any unavailable source.
- Source-bound preflight accounts for automatic calls conservatively and validates the accepted frozen policy.
- Focused extended/core/runtime/cost tests, Python compile, frontend focused test/typecheck if UI changes, and `git diff --check`.

## Integration and rollback

Integrate the exact reviewed candidate into `origin/dev`. `origin/main` needs a separate explicit owner instruction for the exact gated candidate and deployment verification. Disable new extended review via `AUDITMANAGER_EXTENDED_ANALYSIS=0` or revert this task while keeping old accepted policies readable. A run started before this change keeps its original frozen policy.
