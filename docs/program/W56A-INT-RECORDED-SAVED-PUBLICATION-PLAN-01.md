# W56A-INT-RECORDED-SAVED-PUBLICATION-PLAN-01 — saved recorded finding plan

## Result

An unactivated read-only bridge builds a complete `MergePublicationPlan` from
one saved AR v2 observation Blob and one saved `findings.merged` Blob. The v2
observation reader now retains accepted proposal text, recommendation,
severity, resolved PDF anchors, rejected quote diagnostics and complete
recorded call facts alongside its existing merge input. Nullable or malformed
rejected diagnostics fail closed.

The bridge requires successful registry-versioned text and merge StageResults,
exact content-addressed Blob bytes, canonical JSON, expected run/version and
registered profile, source references, model ID/call ID and request, response
and source-binding checksums. It verifies the merge StageResult's text SHA and
counts, then calls the existing pure publication planner, which recomputes the
deterministic grouping. Each saved Blob is read once. No recording or provider
is read, and no finding ID or DB row is created.

## Changed files

- `src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py` — complete
  typed saved projection and stricter diagnostics;
- `src/auditmanager/analysis/public.py` — additive boundary exports;
- `src/auditmanager/findings/recorded_saved_plan.py` — read-only saved plan;
- `tests/integration/analysis/test_ar_v2_recorded_artifact.py` — typed projection
  and nullable diagnostic checks;
- `tests/integration/findings/test_v2_recorded_saved_plan.py` — exact Blob,
  provenance, multi-member, empty, forged merge and repeat tests;
- `docs/program/tasks/W56A-INT-RECORDED-SAVED-PUBLICATION-PLAN-01.md`;
- this report.

## Checks

- Focused recorded artifact, saved plan, merge planner, SQL publisher,
  recorded chain, durable merge stage and program governance suites:
  **82 passed**.
- Python compilation, direct task governance, frozen SHA-256 values,
  `git diff --check` and exact allowed-path proof: passed.
- Real PostgreSQL/S3 acceptance and full `make gate` were deferred under R-135
  while the separate W55 release gate ran.

## Contracts and limits

No contract, migration, executor, active publisher, run/job repository,
composition root, provider lock, recording, root dependency file, global
style, remote ref or tag changed. The bridge receives StageResult values and
expected call/source facts from a future trusted run-side caller; it does not
read persisted rows or fence an Attempt. Actual PDF quote content relies on
the earlier durable text-stage seal; this bridge checks saved spans and
provenance without rereading the source text Blob. It returns rejected
diagnostics in the plan but does not persist diagnostic rows.

## Integration instruction

Cherry-pick the local task commit after exact path review. The later durable
finding gate must load and recheck persisted StageResults and current Attempt
authority, pass journaled model/call/request/response/source facts into
`plan_recorded_saved_publication`, and atomically combine finding publication
with a terminal transition. This is required for duplicate delivery,
including zero-finding runs. Prove that gate with real migration-head
PostgreSQL/S3 and failure-recovery tests before executor activation.
