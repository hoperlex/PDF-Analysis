# Task CMP-STAGE-LINK-01 — stage sheet passports and revisioned map

## Outcome
An expert can inspect the page passports of a confirmed П↔Р pair, see deterministic nonbinding sheet suggestions, save many-to-many links or explicit unmatched pages, and review the append-only map history. The second tab of «Сравнение стадий» shows this map and opens the existing two-pane viewer.

## Depends on
- CMP-SEAL-C3
- CMP-STAGE-PAIR-01

## Frozen inputs
- domain contract: ADR-0025 A-9, plan §1.2 and §4 C3, `ORIGINAL-STAGE-COMPARISON-INVENTORY.md` §3.3
- API contract: `1.12.0`, 204 paths / 230 operations / 570 schemas; six sealed stage-link operations and all their schemas are frozen
- migration head: `0041_comparison_stage_core`; `stage_link_revision` and `stage_link_item` are frozen
- existing profile facts: `PageProfileReader` and `StampFields`, with no profile/schema change
- base commit: `bd4de371310209c2c253030bf37f31cfa0056fdb`
- base branch: `agent/cmp-stage-link-01`, after the completed stage-pair lane
- product `VERSION`: `0.9.0`; module value `versions,stages`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the stage-pair lane is committed, the sealed C3 surface is unchanged, and the link port still returns the sealed refusal.

### P-01 — committed base and frozen surface
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; git status --short; python3 -c 'import json;d=json.load(open("contracts/api/v1/openapi.json"));print(d["info"]["version"],len(d["paths"]),sum(k in {"get","post","put","patch","delete"} for p in d["paths"].values() for k in p),len(d["components"]["schemas"]))'`
- captured_output:
  ```text
  bd4de371310209c2c253030bf37f31cfa0056fdb
  1.12.0 204 230 570
  ```
- interpretation: this branch starts clean from the completed stage-pair task and does not own a contract reseal.

### P-02 — sealed link and storage
- captured_at: 2026-10-29
- command: `rg -n '^class ComparisonStageLinkAdapter|^        CREATE TABLE stage_link_(revision|item)' src/auditmanager/bootstrap/adapters.py db/migrations/versions/20261029_0041_comparison_stage_core.py`
- captured_output:
  ```text
  src/auditmanager/bootstrap/adapters.py:6949:class ComparisonStageLinkAdapter(_StagesModuleGate):
  db/migrations/versions/20261029_0041_comparison_stage_core.py:257:        CREATE TABLE stage_link_revision (
  db/migrations/versions/20261029_0041_comparison_stage_core.py:282:        CREATE TABLE stage_link_item (
  ```
- interpretation: this task replaces only the link adapter's six refusals and stores complete revisions in the sealed tables.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-STAGE-LINK-01.md`
- `docs/program/CMP-STAGE-LINK-01.md`
- `docs/program/CURRENT_STATE.md`
- `src/auditmanager/comparison/stage_links/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `web/src/widgets/stage-sheet-map/**`
- `web/src/_pages/stage-compare/**`
- `tests/unit/comparison/stage_links/**`
- `tests/integration/comparison/stage_links/**`
- `tests/integration/api/test_stage_link.py`
- `tests/integration/composition/test_comparison_stage_stub_operations.py`
- `.venv`
- `web/node_modules`

## Forbidden hotspots
- `contracts/**`, migration files/head, root dependencies and locks, global styles, C2 runtime and jobs, stage-pair service internals, comparison-viewer implementation, remote refs and deployment composition
- direct SQL/blob access in routers or React components; output of AI as canonical expert link

## Non-goals
- no text fragments/differences, AI repair, chain runs or C4 review; no live model calls
- no contract, migration, version or generated-client change; no remote publication

## Deliverables
1. Immutable page passports from ready stored page profiles for each current pair member; deterministic metadata parsing and safe refusal when required profile evidence is absent.
2. Nonbinding suggestions: unique exact type/building/floor or roof/level first, then the specified weighted score; a conflict in type, building or floor is never overcome by sheet number or ordinal. Suggestions are stable and carry reasons.
3. Keyed expert map revision that checks the base revision and pair scope, allows many-to-many links, records explicit `only_left`/`only_right`, and preserves every prior revision. Reads include current/history/by-ID.
4. Second stage-comparison tab with the map, candidate controls and existing viewer; unit, DB, API, composition and screen evidence.

## Required tests
- `git diff --check`; scoped passport/suggestion/map unit tests
- on an isolated `0041` stack: stage-link DB/API and composition module-on/off, keyed replay, stale base, cross-project profile refusal, many-to-many and explicit unmatched tests
- web lint, typecheck, generated-client verify and focused stage-map screen tests
- later integrated `make gate` on the exact merge candidate

## Integration contract
The six stage-link operations become served only with `AUDITMANAGER_COMPARISON_MODULES=versions,stages`. `CMP-STAGE-TEXT-01` reads confirmed map revision IDs and link item IDs, never modifies them. The sealed contract and migration stay byte-for-byte. Merge after stage-pair in the C3 integration candidate; this branch has no remote authority.

## Failure/idempotency/security cases
- unknown pair/profile and a profile outside the pair refuse without leaking another project's data
- same key and payload replays the same revision; same key with different payload refuses
- stale base revision refuses; a successful map writes all items and its command in one transaction
- an automatic hint never becomes a canonical link without an expert act; module-off remains typed 503

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none` or `versions` retains typed 503 and hides the second tab. Existing immutable revisions remain in storage. If the lane fails, leave the sealed adapter in place; no schema downgrade.

## Handoff
- changed files: the exact SHA-bound list and allowed-path proof are in `.local/handoff/CMP-STAGE-LINK-01-evidence.md`; implementation details are in `docs/program/CMP-STAGE-LINK-01.md`
- commands/results: scoped unit, PostgreSQL, HTTP and composition tests `78 passed`; stage screen/draft Vitest `8 passed`; web lint, typecheck and generated-client verification passed; full integrated gate remains for the merge candidate
- contracts: none; API `1.12.0`, migration `0041` and generated client unchanged
- known limits: existing `comparison-viewer` needs a version-comparison pair ID that a stage link lacks; this tab uses paired profile previews. Frozen API exposes no page words, so per-panel search currently filters stamp metadata. Browser refuses more than 1,000 passports and initially shows 100 suggestions; see report.
- integration notes: merge after stage-pair; C3 stage text consumes link revisions. The missing viewer/text-search seam must be resolved before claiming full plan parity. No remote publication authority belongs to this lane.
