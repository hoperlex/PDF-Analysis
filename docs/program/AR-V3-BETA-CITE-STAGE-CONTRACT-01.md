# AR-V3-BETA-CITE-STAGE-CONTRACT-01 — profile-specific CITE stage

The AR v3 beta profile now has its own versioned CITE stage manifest at `contracts/analysis/ar_v3_beta/v1/stage.json`. It declares `ar_v3_citation_review` after saved source preparation, names the saved text, verified set and private reply as inputs, and permits one `analysis.v3_beta_review` JSON output. The stage is review-only, with no partial/skipped success and no canonical finding publication. The sealed nine-stage legacy registry and global `1.2.0` analysis/API family remain unchanged.

`load_v3_cite_stage_contract` rejects missing, duplicate or drifting manifest fields, including the profile/bundle pair, prior stage, input/output roles and beta numeric policy. `require_v3_cite_stage_result` validates the future writer's StageResult identity, output artifact, call/digest/count metrics and explicit failure shape. It checks shape only; the writer must still prove current Attempt, saved call/set/reply custody, exact artifact readback and transaction binding.

## Verification and handoff

- Task: [AR-V3-BETA-CITE-STAGE-CONTRACT-01](tasks/AR-V3-BETA-CITE-STAGE-CONTRACT-01.md), frozen from `ed95bac634ba1a190ccf1415b732543d86b3e728`.
- Changed paths: `contracts/analysis/ar_v3_beta/v1/stage.json`, `src/auditmanager/runs/v3_cite_stage_contract.py`, `tests/contract/analysis_packages/test_ar_v3_cite_stage_extension.py`, this result, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Checks: new extension, existing StageResult contract and global contract seal — **73 passed**. The worktree's missing `.venv` was temporarily linked to the already installed root interpreter for the existing schema suite; the link was removed. Python compilation and `git diff --check` passed; task handoff checks run after commit.
- New/changed contracts: one new profile-specific `analysis.ar_v3_beta/v1` stage manifest; `contracts/analysis/v1/**`, domain/API/events contracts and migration head unchanged.
- Known limits: no CITE writer/StageResult, active executor or approved six-map/six-set pack. The new stage is not inserted into the legacy registry or automatically served. Local PostgreSQL/S3 acceptance remains open.
- Integration: future writer loads this manifest, validates its StageResult, publishes review bytes via the Attempt outbox, verifies readback, binds the review ref and commits under current authority. Failure creates an explicit failed stage with no review artifact; no model numeric conclusion becomes a finding.
- Rollback: unserved manifest and validator can be removed before writer activation without migration.
- Forbidden hotspots: sealed contract families, migration, root dependencies/lockfiles, composition root, active executor, transports, global styles and normative map/source/set data were untouched. The new profile contract path is explicitly owned by this task.
