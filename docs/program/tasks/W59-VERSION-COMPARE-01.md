# Task W59-VERSION-COMPARE-01 — served comparison of two versions of one document set

task_id: W59-VERSION-COMPARE-01

## Outcome

A user opens «Сравнение версий» for two versions of the same document set with the
same confirmed section and stage and sees the deterministic raw comparison: sheet
pairing (suggested matches with their evidence), per-sheet text differences
(added/removed/changed lines with page anchors) and the proposed matches between the
two versions' findings (unchanged / probably fixed / new). A pair with a different
section or stage, a foreign set or an unclassified version is refused with a reason.
The raw evidence is never altered by an AI layer; no AI summary in this slice.

## Depends on

- `W59-SECTION-SEAL-01` (version classification; phase B needs it merged).
- Completed preparations: `W59-INT-VERSION-PAIR-READ-01`, `W59-INT-VERSION-RAW-TEXT-PREP-01`,
  `W59-INT-SHEET-MATCH-SUGGESTIONS-02`, `W59-INT-FINDING-MATCH-SUGGESTIONS-01`,
  `W59-INT-SAME-SECTION-PAIR-PREP-01`, `W59-INT-COMPARISON-500-PAGE-01`.

## Frozen inputs

- base commit: `708d0d5d2f9bf356a28f0d063a443873bcf9a346` (`origin/dev`);
- API contract at base: 48 paths / 55 operations / 131 schemas; the seal lane moves
  it to 50/57/137 and migration head `0024_version_classification` before phase B;
- rulings: `R-135`, `R-139`; design: `W59-SECTION-IDENTITY-DECISION-01.md`
  (comparison section).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W59-VERSION-COMPARE-01 (phase B only, after the integrator hands over the contract slot)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['path_count'],len(d['operations']),len(d['schema_names']))"`

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/**`
- `tests/integration/comparison/**`
- `tests/unit/comparison/**`
- `contracts/api/v1/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/**`
- `tests/support/**`
- `tests/contract/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/**`
- `web/src/entities/**`
- `web/src/features/**`
- `web/src/widgets/**`
- `web/src/_pages/stage-comparison/**`
- `web/src/_pages/version-detail/**`
- `web/src/app/projects/**`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/tests/**`
- `web/docs/**`
- `tests/e2e/pc01/**`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/manual-tests/**`
- `infra/deploy/README.md`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/serve.py`
- `docs/program/W59-VERSION-COMPARE-01.md`
- `docs/program/tasks/W59-VERSION-COMPARE-01.md`

**Phasing (binding):** phase A may touch only `src/auditmanager/comparison/**`,
`tests/integration/comparison/**`, `tests/unit/comparison/**` and the two docs
files. Every other path above opens only after the integrator's message that the
contract slot is handed over, and from the integration commit it names.

## Lane resources

- foundation_instance: `auditmanager-w59-version-compare`
- postgres_port: `57500`
- s3_api_port: `61100`
- s3_console_port: `61101`
- postgres_db: `auditmanager_w59_version_compare`
- s3_bucket: `auditmanager-w59-version-compare`

## Forbidden hotspots

Migrations (no table in this slice — the comparison is computed from immutable
versions), dependency files, `web/src/_app/providers.tsx`, global styles,
`CURRENT_STATE.md`, the classification/run code of `W59-SECTION-SEAL-01`, refs,
tags, the stand.

## Non-goals

No AI summary, no decision carryover writes (proposals only, shown as such), no
stage (П/Р) comparison, no persistence, no live provider call, no full gate.

## Deliverables

Phase A: a comparison service with a stable read model over the prepared modules
and its tests. Phase B: read operation(s) with the reseal, router/adapter wiring, the
web page at `versions/[version_uid]/comparison` (choose the other version, see
pairing, diffs and finding matches). Report `docs/program/W59-VERSION-COMPARE-01.md`.

## Required tests

Phase A: focused unit/integration tests of the service on the lane's own containers.
Phase B: `tests/contract`, `api:verify`, typecheck, lint, the changed vitest files,
journey static conformance. No full gate, no live journey.

## Integration contract

The integrator merges phase A's commits only together with phase B (one vertical
slice). Response sizes stay bounded for 500-page versions (page/sheet paging or a
documented cap).

## Failure/idempotency/security cases

Different set, stage or section, unclassified version, same version twice,
missing/foreign version → explicit refusal; reads only; the AI layer cannot edit raw
evidence.

## Rollback / feature flag

Revert the merge; no data migration.
