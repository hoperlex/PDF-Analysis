# W56A-PREP-GOV-FIX-01 — premise declaration repair

**Task:** `tasks/W56A-PREP-GOV-FIX-01.md`. **Base:**
`290325315c72d384013466fb6259096ac3f5d0ac`.

## 1. Scope and reason

The governance inventory on the base returned exactly two findings:
`PREMISE_DECLARATION_REQUIRED` for `W56A-PREFREEZE-01.md` and
`W56A-LEGACY-SOURCE-01.md`. Both definitions already had dated P-01 commands,
outputs and interpretations. This task adds the explicit `- premise:` field
required by `test_wave_governance.py` to each draft definition. The source
observations, completed reports, frozen inputs and source digests are unchanged.

## 2. Checks

The task file records the complete before-fix `governed_task_findings()` map.
After the two declarations, the same function returns `{}`. The focused
governance and prose tests, post-commit `git diff --check`, exact changed-path
proof and clean-tree check are recorded in the handoff.

## 3. Integration, contracts and limits

This branch contains the W56a prefreeze inventory, the recovered legacy-source
addendum, W57a's independent corpus coverage inventory and this metadata fix.
The integrator should consume its tip as one document chain, then rebase on the
accepted W55b SHA and rerun state-dependent inputs before `W56A-FREEZE-01`.
The separate `W56A-RULE-01` branch is not in this chain; its task definition
requires the same explicit premise field before it is merged.

No API/domain/analysis contract, migration, dependency, composition root,
style, runtime or historical report changes. Reverting this document-only
commit is sufficient rollback. No branch is published or tagged here.
