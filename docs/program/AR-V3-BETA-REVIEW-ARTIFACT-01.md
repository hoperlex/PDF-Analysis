# AR-V3-BETA-REVIEW-ARTIFACT-01 — canonical review-only CITE bytes

`build_v3_beta_review_artifact` takes the verified CITE preflight and emits repeatable JSON bytes, SHA-256 and size. The payload names the Run/group/scope, saved set and policy, exact request/call/response digests and reply Blob reference. It includes every scoped C topic with its source disposition, grounded provisional citation labels and PDF/norm quotes, plus withheld and rejected proposal ordinals. Every topic remains marked `requires_expert_review`. It omits the model's `required_value`, `stated_value`, finding and recommendation text, so a context-only or unresolved item cannot acquire a numeric conclusion through this artifact.

The builder checks that request, set, policy, response and topic pins agree; refuses duplicate labels or classifications, salvaged/malformed replies and bytes beyond 2 MiB; and never writes a Blob or StageResult. The preflight's error stage label was corrected from the absent `citation_validation` to the registered `text_analysis`. The current registry's `norm_verification` stage depends on `finding_merge`; this review artifact is not silently assigned to that stage.

## Verification and handoff

- Task: [AR-V3-BETA-REVIEW-ARTIFACT-01](tasks/AR-V3-BETA-REVIEW-ARTIFACT-01.md), frozen from `4a03d25f22d04f962f8b00a549abd024a11f2639`.
- Changed paths: `src/auditmanager/runs/v3_cite_preflight.py`, `src/auditmanager/runs/v3_review_artifact.py`, `tests/integration/runs/test_v3_cite_preflight.py`, `tests/integration/runs/test_v3_review_artifact.py`, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_review_artifact.py tests/integration/runs/test_v3_cite_preflight.py -x --tb=short` — **26 passed**. With reply custody, request and grounding suites included, **64 passed**. `git diff --check` and Python compilation passed; handoff governance/changed-path check runs after commit.
- New or changed contracts: none in `contracts/**`; this is an internal, unpublished `analysis.v3_beta_review/1` artifact shape and builder.
- Known limits: no durable publication, StageResult, screen or served executor. A contract-owned CITE stage/output role and delayed-Blob/heartbeat test are needed before served activation. Local PostgreSQL and S3 are unavailable in this lane.
- Integration: publish these exact bytes through the Attempt outbox, verify readback and bind the review/ref plus completed call/reply under a current Attempt. Add an explicit CITE stage contract; do not reinterpret existing `norm_verification` as v3 pre-finding review.
- Rollback: pure, unserved builder can be removed without migration.
- Forbidden hotspots: contracts, migrations, root dependencies/lockfiles, composition root, active executor, transports, global styles and normative maps/source/set data were untouched.
