# Task AR-V3-BETA-STATUS-VERSION-01 — visible AR v3 beta source status and product version

task_id: AR-V3-BETA-STATUS-VERSION-01
status: completed (read-only preview and development version; v3 runtime remains open)

## Outcome

An authenticated user can inspect the C01–C22 F1.3 beta source dispositions in «Настройки анализа» without mistaking them for a running v3 profile or a normative verdict. The development tree reports product version `0.8.0` and has a truthful release note and technical record. The owner will decide any `origin/main` publication separately.

## Depends on

- `AR-BETA-AVAILABLE-SOURCE-GATE-01` — completed source policy.
- `AR-BETA-CITATION-REVIEW-GATE-01` — completed unserved review-only citation plan.
- `AR-BETA-LOCAL-CUSTODY-01` — completed isolated corpus qualification.
- `W59-ANALYSIS-SETTINGS-01` — completed authenticated settings screen.

## Frozen inputs / contract versions

- Development base `4b2ff2d8aa65ef959bfdebc432e40484047709e6`; contract `1.1.0`, migration head `0031_executor_pull_channel`, product `VERSION=0.7.0`.
- F1.3 policy SHA-256 `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`; six-group composition `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`.
- Owner requested product `v0.8.0` on `dev`, with release description; owner will perform any `main` push themself. The existing policy still forbids this task from updating `origin/main`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: v3 has an unserved policy and citation bridge, but the active AR route still uses v1 and no verified six-set pack exists.
- captured_at: 2026-10-23
- command: `git rev-parse HEAD; rg -n 'AR_TEXT_PROFILE|plan_v3_beta_citation_review' src/auditmanager/analysis/text/profile_registry.py src/auditmanager/runs/v3_citations.py`
- captured_output:
  ```text
  4b2ff2d8aa65ef959bfdebc432e40484047709e6
  profile_registry.py:49:from auditmanager.analysis.text.profile import AR_TEXT_PROFILE, AnalysisProfile
  v3_citations.py:193:def plan_v3_beta_citation_review(
  ```
- interpretation: a version note may describe a visible source-status preview, but cannot say that v3 model Runs or verified citations are already served.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `VERSION`
- `release-notes/0.8.0.json`
- `docs/program/CURRENT_STATE.md`
- `docs/program/RELEASES.md`
- `docs/program/tasks/AR-V3-BETA-STATUS-VERSION-01.md`
- `docs/program/AR-V3-BETA-STATUS-VERSION-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`
- `docs/program/dispatch/ROADMAP-TO-BETA.md` (only the owner-directed `v0.8.0` development-candidate status note)
- `web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx`
- `web/src/widgets/ar-v3-beta-status/**`
- `web/tests/unit/analysis-settings/analysis-settings.test.ts`
- `tests/contract/norm_map/test_beta_status_mirror.py`
- `tests/contract/release_notes/test_release_notes_form.py`
- `tests/integration/releases/test_release_loader.py`
- ignored `.venv` and `web/node_modules` symlinks in this worktree for focused checks; remove after checks.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root, global styles, provider transports, Run execution and publication, other lanes' data, `origin/main`, tags and deployment host.

## Non-goals

No expert approval of legal editions or map bytes, no verified six-set pack, no v3 provider call, six-Run launch, CITE StageResult or numerical conclusion. This is a visible status preview and a development version candidate, not a v3 execution or production acceptance claim.

## Deliverables

- Read-only C01–C22 status panel in the existing authenticated settings screen, mirrored byte-for-byte from the backend beta source policy and grouped by the frozen six-scope composition.
- `VERSION=0.8.0`, truthful authored release note, technical candidate record, and follow-on code queue with specific acceptance gates.
- Focused UI, policy-totality and release-note checks and exact changed-path proof.

## Checks

- `python -m pytest -q tests/contract/norm_map/test_beta_status_mirror.py tests/contract/release_notes/test_release_notes_form.py tests/contract/program/test_wave_governance.py`
- `npm run typecheck` and focused `vitest` analysis-settings test using lock-matched `node_modules`.
- `git diff --check`, changed-path and remote fast-forward proof. Complete `make gate` is deferred by R-135 on `dev`; any `main` candidate needs its own exact-tree gate and deployment checks.

## Integration contract

The settings panel is a read-only mirror of the frozen source policy, never a source of model or expert authority. A later runtime must use the server policy digest, reviewed exact map pack and Run-pinned verified sets; it cannot infer activation from the product version or panel. If map or set is absent, v3 execution refuses before provider effect. Existing AR v1 routing remains until a separate runtime integration task owns the switch.

## Rollback / feature flag

Revert this task's version/note/UI/doc changes before any production publication; it writes no data. Later v3 activation needs an explicit reversible profile switch preserving historical v1 Run identities.
