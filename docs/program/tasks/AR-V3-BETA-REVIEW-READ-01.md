# Task AR-V3-BETA-REVIEW-READ-01 — verify the saved v3 review for a read API

## Outcome
A read-only Runs service returns one saved AR v3 beta review document only after verifying the terminal Run, unique successful CITE stage, settled Blob bytes and six-Run group membership. It works for historical groups without a currently installed pack and never treats the review as canonical findings.

## Depends on
- `AR-V3-BETA-COST-REFUSAL-01`

## Frozen inputs
- shared domain/API/analysis/events contract: `1.3.0`, unchanged
- AR v3 beta stage extension: `1.0.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `0d0626111ad969dda525677fae45d4387b360ebd`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: CITE persists a bounded canonical JSON review Blob and stage metrics, but no service reads it for a historical terminal Run
### P-01 — artifact and existing API
- captured_at: 2026-10-26
- command: `git grep -n -E 'MAX_REVIEW_BYTES|analysis\.v3_beta_review|build_v3_beta_review_artifact|v3_review_reader|read_v3_saved_review' 0d0626111ad969dda525677fae45d4387b360ebd -- src; git grep -n -A 7 'def get_norm_verification' 0d0626111ad969dda525677fae45d4387b360ebd -- src/auditmanager/bootstrap/adapters.py`
- captured_output:
  ```text
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/runs/v3_cite_stage.py:24:from auditmanager.runs.v3_review_artifact import build_v3_beta_review_artifact
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/runs/v3_cite_stage.py:123:        artifact = build_v3_beta_review_artifact(preflight)
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/runs/v3_cite_stage_contract.py:99:            or stage["output_role"] != "analysis.v3_beta_review"
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/runs/v3_review_artifact.py:13:ROLE = "analysis.v3_beta_review"
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/runs/v3_review_artifact.py:15:MAX_REVIEW_BYTES = 2_097_152
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/runs/v3_review_artifact.py:35:def build_v3_beta_review_artifact(value: V3CitePreflight) -> BuiltV3ReviewArtifact:
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/runs/v3_review_artifact.py:197:    if len(payload) > MAX_REVIEW_BYTES:
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/runs/v3_review_artifact.py:204:__all__ = ["BuiltV3ReviewArtifact", "build_v3_beta_review_artifact"]
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/bootstrap/adapters.py:1067:    def get_norm_verification(self, *, run_id: str) -> models.NormVerificationReport:
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/bootstrap/adapters.py-1068-        """Refuse until a reader proves the 0023 partition and the pinned set.
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/bootstrap/adapters.py-1069-
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/bootstrap/adapters.py-1070-        An empty citation SELECT is not a certificate of zero. CITE will replace this
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/bootstrap/adapters.py-1071-        seam after it checks stage success and every canonical/member partition.
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/bootstrap/adapters.py-1072-        """
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/bootstrap/adapters.py-1073-        raise DomainError(
  0d0626111ad969dda525677fae45d4387b360ebd:src/auditmanager/bootstrap/adapters.py-1074-            ErrorCode.DEPENDENCY_UNAVAILABLE,
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 0d0626111ad969dda525677fae45d4387b360ebd with git grep against that tree (not at dispatch time). At the base, v3_cite_stage.py imports (24) and calls (123) build_v3_beta_review_artifact, defined at v3_review_artifact.py:35; the artifact role is analysis.v3_beta_review (v3_review_artifact.py:13, also checked as the stage output_role at v3_cite_stage_contract.py:99) and its size is bounded by MAX_REVIEW_BYTES = 2_097_152 (15), enforced at 197. No line under src/ mentions read_v3_saved_review or v3_review_reader, so no reader existed under those names (absence of hits; a reader under another name is not excluded). bootstrap/adapters.py:1067 get_norm_verification raises ErrorCode.DEPENDENCY_UNAVAILABLE (1073-1074) and its docstring says it refuses until a reader proves the 0023 partition. Not shown: the stage metrics and the frozen schema of the norm-verification response; those parts rest on the dispatch-time record. Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `rg -n 'MAX_REVIEW_BYTES|analysis.v3_beta_review|get_norm_verification' src/auditmanager/runs/v3_review_artifact.py src/auditmanager/runs/v3_cite_stage.py src/auditmanager/bootstrap/adapters.py`; captured_output was a prose summary: the writer saves the review as an `analysis.v3_beta_review` StageResult artifact; `get_norm_verification` still returns `dependency_unavailable` and its frozen schema describes canonical finding partitions, not this review-only artifact. Original interpretation: add a verified Runs reader first; a later API contract must name a separate review-only response shape.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_review_reader.py`
- `tests/integration/runs/test_v3_review_reader.py`
- `docs/program/tasks/AR-V3-BETA-REVIEW-READ-01.md`
- `docs/program/AR-V3-BETA-REVIEW-READ-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles, composition root and global styles
- router, React, provider transports, normative map/source/set data, product VERSION
- `origin/main`, tag and deployment host

## Non-goals
- Changing the existing `getRunNormVerification` meaning or exposing a new public operation in this task.
- Reconstructing raw model answers, canonical findings or expert decisions.
- Real PostgreSQL/S3 acceptance on this host.

## Deliverables
- Read-only, fail-closed verified review loader with Run/stage/Blob/group/call-metric binding.
- Positive and corruption/refusal tests, result note, queue update.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_review_reader.py -x --tb=short`
- expected: all pass, handoff path check passes; full make gate deferred by R-135.

## Integration contract
The reader accepts a terminal exact-v3 Run ID and returns the bounded review document after validating it against the saved CITE StageResult and the durable six-member group. It does not consult the current trusted-pack registry. A later contract owner may expose only this verified output under a distinct review operation; the older normative-verification report keeps its existing semantics.

## Failure/idempotency/security cases
- Unknown or legacy Run, incomplete/failed CITE, duplicate stage, unavailable or changed Blob, noncanonical JSON, mismatched group/member/set/call digests or canonical finding row refuse.
- Read performs no writes or provider effect. A changed saved row after Blob I/O refuses.

## Rollback / feature flag
Uncalled reader adds no served behavior. Remove it if the review API is abandoned; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: review read API/UI and full stand acceptance remain
- integration notes: a later API contract needs a distinct review-only response, not `NormVerificationReport`
