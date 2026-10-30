# Task CMP-STAGE-TEXT-CORE-01 — deterministic stage text evidence core

## Outcome
Stored page-profile words become bounded, box-anchored text fragments; a confirmed sheet relation can prove exact one-to-one text exclusions without a model call or a database write.

## Depends on
- CMP-SEAL-C3
- CMP-STAGE-PAIR-01

## Frozen inputs
- domain contract: ADR-0025 A-9, `COMPARE-MODULES-PLAN.md` §1.2/§4 and `ORIGINAL-UNREAD-SOURCES.md` §1.6
- API contract: `1.12.0`, 204 paths / 230 operations / 570 schemas; no reseal
- source evidence: immutable `PageProfileData.words`, top-left PDF-point coordinates; no OCR or generated prose
- migration head: `0041_comparison_stage_core`; no migration change
- base commit: `9a35c888ff743a65363f63e59d06f34e5acee7aa`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the C3 migration already has fragment/exclusion tables while the stage text adapter remains a sealed refusal.

### P-01 — base and storage
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; rg -n 'CREATE TABLE stage_text_(fragment|exclusion)|^class ComparisonStageTextAdapter' db/migrations/versions/20261029_0041_comparison_stage_core.py src/auditmanager/bootstrap/adapters.py`
- captured_output:
  ```text
  9a35c888ff743a65363f63e59d06f34e5acee7aa
  db/migrations/versions/20261029_0041_comparison_stage_core.py:312:        CREATE TABLE stage_text_fragment (
  db/migrations/versions/20261029_0041_comparison_stage_core.py:335:        CREATE TABLE stage_text_exclusion (
  src/auditmanager/bootstrap/adapters.py:7085:class ComparisonStageTextAdapter(_StagesModuleGate):
  ```
- interpretation: pure computation can be built against sealed storage without claiming it is served.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-STAGE-TEXT-CORE-01.md`
- `docs/program/CMP-STAGE-TEXT-CORE-01.md`
- `docs/program/CURRENT_STATE.md`
- `src/auditmanager/comparison/stage_text/**`
- `tests/unit/comparison/stage_text/**`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependencies/locks, composition root, global styles, C2 and C3 pair/link internals, generated client, remote refs

## Non-goals
- no served API, stored fragments/exclusions, background run, UI, AI decisions or publication
- no claim of full CMP-STAGE-TEXT-01 or Stage Link plan parity

## Deliverables
1. Pure, bounded extraction from ready stored page profiles, with stable keys and top-left box anchors.
2. Conservative exact exclusion proof within caller-confirmed sheet links; repeated boilerplate or ambiguous occurrences remain unproven.
3. Unit tests for exact, moved, duplicate, missing and malformed evidence; report of the boundary to persistence.

## Required tests
- scoped `pytest tests/unit/comparison/stage_text`; `git diff --check`
- later integrated `make gate` on the exact C3 merge candidate

## Integration contract
The later `CMP-STAGE-TEXT-01` persistence/queue slice supplies confirmed link items and reads immutable profiles through the comparison public reader. It stores the returned content keys and only proof pairs; all unmatched fragments remain available for deterministic difference generation. This lane changes no served operation or contract.

## Failure/idempotency/security cases
- invalid/oversized profile evidence refuses before producing any partial result; no silent truncation
- a word without a valid finite in-page box refuses; scans without words produce no exact proof
- same profile and words yield the same stable fragment keys; a duplicate phrase is not automatically proof

## Rollback / feature flag
Pure code is unreachable from the served adapter until a later integration task; dropping this branch restores the sealed refusal.

## Handoff
- changed files: `docs/program/tasks/CMP-STAGE-TEXT-CORE-01.md`, `docs/program/CMP-STAGE-TEXT-CORE-01.md`, `docs/program/CURRENT_STATE.md`, `src/auditmanager/comparison/stage_text/**`, `tests/unit/comparison/stage_text/**`; exact SHA/path proof follows after commit
- commands/results: scoped unit tests **9 passed**; package compile and `git diff --check` passed
- contracts: none
- known limits: pure code only; no persistence, served API, masks, differences or UI
- integration notes: consume only through a confirmed map revision and profile custody checks
