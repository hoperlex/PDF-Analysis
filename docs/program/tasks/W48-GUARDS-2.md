# Task W48-GUARDS-2 — make closure guards fail for the claimed defect

## Outcome

Every G-1 through G-6 guard rejects its named mutation and alpha evidence is described as
attestation rather than proof of an unserved SHA.

## Depends on

- `W48-RULE-01`

## Frozen inputs

- domain/API/analysis contracts: unchanged W48 set
- migration head: `0014_durable_analysis_effects`
- base commit: `03c04a1d87fda862d085a6a49d0a46f2692f7ffd`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the branch contains the Stage A/B guard files this task repairs

### P-01 — exact base

- captured_at: 2026-10-05
- command: `git rev-parse agent/w48-stage-a`
- captured_output:
  ```text
  03c04a1d87fda862d085a6a49d0a46f2692f7ffd
  ```
- interpretation: the base is exact; it does not establish guard quality.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/tests/guards/screen-set.guard.test.ts`
- `web/tests/guards/dashboard-invalidation.guard.test.ts`
- `tests/contract/api_v1/test_surface_counts_in_prose.py`
- `tests/contract/program/test_wave_governance.py`
- `tests/contract/test_alpha_acceptance_command.py`
- `tests/contract/test_deploy_auto_workflow.py`
- `tests/e2e/pc01/journey/verify-acceptance.mjs`
- `scripts/manual-alpha-check.sh`
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
- `tests/contract/api_v1/test_doc_prose_facts.py` (head discovery only)
- `docs/program/W48-GUARDS-2.md`

## Forbidden hotspots

- workflow/runtime/contract/migration/dependency changes and any other path

## Non-goals

- no version endpoint and no deploy-workflow change

## Deliverables

- repairs and mutation evidence exactly as `W48-CLOSE.md` section 4 specifies

## Required tests

- `npm --prefix web test -- --run tests/guards`
- `.venv/bin/python -m pytest tests/contract -q`
- all G-1..G-6 mutations red for their stated reason; `git diff --check`

## Integration contract

The merged tree can rely on these guards detecting semantic regressions rather than comments,
hard-coded partial inventories or unvalidated status strings.

## Failure/idempotency/security cases

- mutations run in unique scratch copies; no credential or public host is required

## Rollback / feature flag

Test/evidence-only change; revert is the rollback and no flag applies.

## Handoff

- changed files: allowed list only
- commands/results: include every red mutation
- known limits: no served revision identity exists
- integration notes: merge after durable fix and before tails
