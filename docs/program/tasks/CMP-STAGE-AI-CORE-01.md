# Task CMP-STAGE-AI-CORE-01 — strict Stage AI request and validation core

## Outcome
The future Stage AI runtime can prepare bounded reviewer/classifier/synthesis requests and accept only complete, source-bound responses over existing fragment/evidence identities, while the raw deterministic layer stays immutable.

## Depends on
- CMP-STAGE-TEXT-DIFF-01

## Frozen inputs
- domain contract: ADR-0025 decisions 3, 4, 5, 21 and A-9/A-10 in `COMPARE-MODULES-PLAN.md`; original reviewer/aggregation/synthesis inventory §1.9–1.11
- API contract: `1.12.0`, 204 paths / 230 operations / 570 schemas; this lane owns no API reseal
- comparison contract: immutable fragment IDs/content keys, raw differences and exact exclusions from completed Stage Text core/diff
- migration head: `0041_comparison_stage_core`; no migration change
- base commit: `9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e`
- shared runtime boundary: C2 `AiCallGroup` estimates and consent/spend orchestration are consumed later; this lane calls no model/provider

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: Stage Text pure evidence is present, C4 methods are not yet authored and the integration owner retains the contract/wiring slots.

### P-01 — clean frozen base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; git status --short; test ! -d src/auditmanager/comparison/stage_ai`
- captured_output:
  ```text
  9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e
  ```
- interpretation: this branch begins from a committed C3 base and adds a new pure module only.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_ai/**`
- `tests/unit/comparison/stage_ai/**`
- `docs/program/tasks/CMP-STAGE-AI-CORE-01.md`
- `docs/program/CMP-STAGE-AI-CORE-01.md`
- `.venv`

## Forbidden hotspots
- `contracts/**`, migration files/head, root dependency/lock files, composition root, global styles, comparison public/worker registry, C2 runtime, raw Stage Text modules, remote refs

## Non-goals
- no API, database, blob or model/provider call; no executor route/consent/spend implementation
- no canonical expert decisions, sheet-link mutation or raw evidence rewrite; no full Stage AI runtime claim

## Deliverables
1. Immutable source DTOs and pure requests with prompt/schema versions, source digests and <=40 reviewer items per chunk.
2. Atomic response validators: exact group/chunk identity, complete fragment/evidence coverage, no hallucinated IDs or unsupported numerical claims; SAME/MOVED require high confidence and cannot remove raw differences.
3. Closed class/category/system vocabulary; classifier cards and source-bound high-level synthesis with conservative one-sided/uncertain guards.
4. Pure runtime plan interface exposing request bytes, prompt size, output budget, parser and content key for the shared C2 caller.
5. Short unit checks, report and integration instructions.

## Required tests
- `.venv/bin/pytest -q tests/unit/comparison/stage_ai`
- `git diff --check`; package compile
- full gate/heavy checks deferred to tomorrow by the owner's direct 2026-10-30 instruction

## Integration contract
The C4 runtime supplies persisted immutable fragment/evidence DTOs, passes each returned request through the shared consent/spend/provider runtime, then submits the response to the matching pure parser. A parser either returns an entire validated chunk/group or raises `StageAiValidationError`; it never publishes a partial answer. Stored result IDs and migrations belong to the C4 seal. The closed system vocabulary must match that seal before runtime integration.

## Failure/idempotency/security cases
- duplicate, missing or foreign IDs, wrong digest, invalid schema and incomplete coverage refuse atomically
- low-confidence SAME/MOVED becomes UNCERTAIN; deterministic changed evidence cannot be hidden by SAME
- prompt/schema/model/source changes move the request content key; no provider or raw evidence side effect occurs here
- one-sided/uncertain evidence cannot become a confirmed high-level project change

## Rollback / feature flag
Pure code is not wired into a served adapter or worker; dropping this branch restores the prior state. No schema rollback or raw mutation.

## Handoff
- changed files: owned `stage_ai/**`, `tests/unit/comparison/stage_ai/**`, this task and its report; no forbidden hotspot edit
- commands/results: **30 unit tests passed**, package compile and `git diff --check` passed
- contracts: none
- known limits: pure source-bound methods; runtime, database, executor consent/spend and GRAPHIC crops are integration work
- integration notes: root is sole integrator and owns all shared wiring/publication; JSONB result shapes and closed vocabularies agreed with C4 seal owner
