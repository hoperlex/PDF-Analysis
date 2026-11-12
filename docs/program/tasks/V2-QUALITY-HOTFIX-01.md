# Task V2-QUALITY-HOTFIX-01 — input custody, related context, substantive critic and linked summary groups

## Outcome
Fresh v2 runs retain an input passport and sheet-register coverage, supply related source
context to the existing comprehensive check, perform substantive evidence/alternative/impact
review inside the existing critic, and display accepted match/extension pairs as one group
with every original observation retained. The owner approved proposal items 1–4 as a hotfix;
item 5 (the proposed expert benchmark/annotation collection) is explicitly excluded.

## Depends on
- BLOCK-ANALYSIS-LIMITS-01 — implemented and independently accepted after J-01 repair.

## Frozen inputs
- base commit: `0b9b44a1f0fa859c083bf5c72a5bfd6bf506b02f`
- The exact base is recorded by `git rev-parse HEAD` before changes; runtime is the accepted
  `c7c9d5273e1e0d2021905022dafc616a7b9732f8` plus review/hold metadata.
- API/domain/analysis contract 1.54.0; migration `0067_precedents_wave5`, unchanged.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

The owner subsequently revoked the integration hold: publish after basic necessary checks,
without full runs or make gate; independent review is limited to significant defects.
This task owns development publication only, never the auto-deploy main ref.

## Allowed paths
- `src/auditmanager/analysis/extended/**`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/runs/v2_quality.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/stage_layout.py`
- `tests/unit/analysis_extended/**`
- `tests/unit/runs/**`
- `tests/unit/stage_v3/test_consolidation.py`
- `web/src/widgets/extended-review/**`
- `web/src/entities/audit-run/lib/**`
- `web/tests/unit/analysis-extended/**`
- `web/tests/unit/stage-v3/**`
- `release-notes/0.25.1.json`
- `tests/contract/release_notes/test_release_notes_form.py`
- `docs/program/tasks/V2-QUALITY-HOTFIX-01.md`
- `docs/program/reviews/V2-QUALITY-HOTFIX-01-JUDGE.md`

## Forbidden hotspots
- `contracts/**`, migrations, root dependencies/lockfiles, composition roots, global styles.
- Stored run artifacts, expert decisions, unrelated checkouts, remote refs other than the
  authorized fast-forward publication to `origin/dev`, and deployment.

## Non-goals
- New visible stages, a new provider service, OCR/re-rendering the PDF, enabling v3,
  annotation/benchmark collection, rewriting old runs or normative-currency claims.

## Deliverables
- Pure source/coverage/context/grouping helpers; versioned v2 runtime and cost authority;
  existing-panel presentation; focused regression tests and a patch revision note.

## Required tests
- Focused backend passport/context/grouping/parser/runtime and preflight/consent regressions.
- Focused web panel/group/origin/critic regressions and touched-package type/lint checks.
- Independent review of the exact candidate; `git diff --check` and allowlist proof.
- No full gate or external model calls on this shared development host.

## Integration contract
Legacy frozen consents keep their original behaviour. New estimates freeze a quality-policy
digest and price the review cell. Only fresh accepted policies enable new calls. Source and
crop hashes are verified before review; every raw observation survives grouping and failed
reviews. A substantive pass requires checked evidence, alternatives and impact with valid
source bindings; otherwise advice is explicitly uncertain. Expert decisions remain external.

## Rollback / feature flag
`AUDITMANAGER_V2_QUALITY=0` disables the new policy for future estimates. Existing accepted
policies remain frozen and cannot silently switch to another workflow. Reverting the code
requires pausing incompatible new work; saved reports remain immutable.

## Handoff
Implementation complete; independent significant-defect review and dev publication pending.
No code or benchmark work for proposal item 5.

- Changed runtime: `analysis/extended/{input_passport,related_context,substantive_review,
  v2_quality,consolidation,workflow}.py`, `analysis/public.py`,
  `runs/{v2_quality,extended_review,preflight,cost_policy,stage_layout}.py`.
- Changed presentation: extended-review passport, group/origin view and search, candidate
  counts, substantive advice and execution reasons; existing route and stages retained.
- Changed checks: focused quality helper/runtime/component tests; old preflight/consent
  tests explicitly pin rollback authority, with fresh default/readiness/pricing covered
  separately. Release 0.25.1 revision 3 describes the user-visible changes.
- Focused backend: quality helpers/runtime + preflight/consent **120 passed**;
  original-v2/workflow/consolidation/answer-limit compatibility **64 passed**;
  release-note form **23 passed**; original unbounded-response regressions **28 passed**.
  Commands use `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`
  and the existing `plan-exec2/.venv/bin/python -m pytest -q -p no:cacheprovider`.
- Focused web: `vitest run tests/unit/analysis-extended/{v2-quality,original-review,
  workflow,critic-queues}.test.ts` — **29 passed**. ESLint on changed components/test —
  exit 0; `tsc --noEmit --incremental false` — exit 0 using the existing compatible
  dependency installation. No dependency or lockfile modification.
- Read-only probe of the owner's attachment: **171 raw records → 139 groups**, all 32
  accepted match/extension links applied; each original index occurs exactly once and
  the input JSON remains byte-equivalent after canonical serialization.
- `git diff --check` clean. No contract, migration, composition root or global-style
  change; no paid model calls, full run, full gate, main update or deployment.
- Known limits: sheet labels that cannot be resolved from prepared text stay unresolved;
  coverage does not certify engineering completeness. Model advice still requires expert
  judgment. New quality calls require a fresh priced consent; old stored reports are not
  rewritten. Rollback flag applies to future estimates.
- Integrator: publish the independently accepted candidate by fast-forward to `origin/dev`
  after re-reading the remote ref, then verify the remote SHA. `origin/main` is not owned.
