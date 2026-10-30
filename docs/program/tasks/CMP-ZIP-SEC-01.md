# Task CMP-ZIP-SEC-01 — code review of the comparison ZIP-set reader

## Outcome
An agent reviews the ZIP-set reader against ADR-0025 decision 12 before `CMP-STAGE-PAIR-01` first uses it. The review records a code-backed verdict, residual risks, and checks the owner's choice to keep rejecting `__MACOSX/` entries. The D-262 row points to the review and states whether first use is cleared.

## Depends on
- CMP-INGEST-ZIP-01
- CMP-SEAL-C2

## Frozen inputs
- domain contract: ADR-0025 decision 12 and `CMP-INGEST-ZIP-01`
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- analysis/comparison/event contract: unchanged from `CMP-SEAL-C2`
- migration head: `0040_comparison_ai_reports`
- base commit: `ac5ee5cc6d593bdb1089ad1f566494ec83794da3`
- owner choices: agent code review; continue rejecting `__MACOSX/` entries

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: P-01 and P-02 establish the frozen tree and the open decision.

### P-01 — frozen base and clean review worktree
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; git status --short; python3 -c 'import json;d=json.load(open("contracts/api/v1/openapi.json"));print(d["info"]["version"],len(d["paths"]),sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in d["paths"].values() for k in p),len(d["components"]["schemas"]))'; ls db/migrations/versions | tail -n 1`
- captured_output:
  ```text
  ac5ee5cc6d593bdb1089ad1f566494ec83794da3
  1.11.0 176 198 517
  20261029_0040_comparison_ai_reports.py
  ```
- interpretation: the review begins from a clean C2 candidate with its sealed API and migration.

### P-02 — D-262 and the existing `__MACOSX/` rule
- captured_at: 2026-10-29
- command: `rg -n 'D-262|__MACOSX/' docs/program/DEBT_REGISTER.md src/auditmanager/ingest/comparison_zip/policy.py tests/unit/ingest/comparison_zip/test_adversarial_archives.py`
- captured_output:
  ```text
  docs/program/DEBT_REGISTER.md:173:| **D-262** | **The security review of comparison ZIP sets owed by ADR-0025 decision 12 has not been held.** ... | owner | open |
  src/auditmanager/ingest/comparison_zip/policy.py:171:            if name.startswith(b"__MACOSX/"):
  tests/unit/ingest/comparison_zip/test_adversarial_archives.py:449:    assert refusal(build(pdf("a.pdf"), directory("__MACOSX/"))) == "comparison_zip_member_kind"
  ```
- interpretation: no review verdict exists, and the exact service-directory rule is implemented and tested.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-ZIP-SEC-01.md`
- `docs/program/compare/CMP-ZIP-SECURITY-REVIEW.md`
- `docs/program/DEBT_REGISTER.md` (D-262 row only)

## Forbidden hotspots
- all application source and tests; `contracts/**`, `db/migrations/**`, root dependencies and lockfiles, composition root, global styles, infrastructure, remote refs
- every debt row other than D-262

## Non-goals
- no executable archive probe, fuzzing campaign, production upload or first use of ZIP sets
- no change to ZIP behavior, API contract, migration or `__MACOSX/` policy
- no authority to publish C2 or C3 to a remote

## Deliverables
- a code-backed security review covering parser boundaries, resource ceilings, names, member kinds, nested ZIPs, PDF checks, cleanup and the first-use call boundary
- a D-262 update that cites the review, distinguishes reader verdict from caller obligations, and records the owner's two choices

## Required tests
- inspect the reader, shared parser, policy, refusal mapper, existing adversarial tests and their call sites with line references
- run the focused ZIP reader tests after the C2 gate releases the host; record the count and result
- `git diff --check`; prove only allowed paths changed

## Integration contract
The review is documentation of the frozen C0 reader, not a new security mechanism. `CMP-STAGE-PAIR-01` must cite its verdict and satisfy any first-use conditions before wiring an upload. The C2 publication candidate stays untouched while its gate runs; the review branch merges only after C2 publication.

## Failure/idempotency/security cases
- a concrete code defect or unbounded first-use exposure is recorded as a blocker, with a scoped repair task before any ZIP-set use
- the reader's existing refusal of exact `__MACOSX/` entries remains; a change needs a separate owner instruction and task
- a read-only verdict never substitutes for testing the eventual upload caller

## Rollback / feature flag
No runtime behavior changes. The comparison module flag remains off by default; if a first-use caller later violates the review conditions, it must stay disabled until repaired.

## Handoff
- changed files: this task, `docs/program/compare/CMP-ZIP-SECURITY-REVIEW.md`, and the D-262 row of `docs/program/DEBT_REGISTER.md` only.
- commands/results: read-only code and call-site review; focused `tests/unit/ingest/comparison_zip/` 183 passed in 5.19 s after C2 gate release; governance 16 passed; `git diff --check` clean.
- contracts: unchanged; API `1.11.0`, migration head `0040_comparison_ai_reports`.
- known limits: static review, no archive upload to a running service; the Unicode Path alias of exact `__MACOSX/` remains a first-use blocker, and the future caller must bound raw bytes, admission and disk use and validate each PDF.
- integration notes: merge this documentation after C2 publication. Give `CMP-ZIP-FIX-01` the separate source/test slot, then require `CMP-STAGE-PAIR-01` to satisfy the remaining first-use conditions. No remote publication is authorized here; forbidden source, contract, migration, root dependencies, composition root, styles and infrastructure are untouched.
