# Task CLASSIFICATION-CORRECTION-01 — append-only correction of a version's stage and section

task_id: CLASSIFICATION-CORRECTION-01

## Outcome

An expert corrects a version's confirmed stage and/or section with a reason; the correction is an append-only event with actor, time and revision, the "current classification" is derived (latest correction, else the original confirmation), every read (versions, documents, dashboard, run start, comparison, section views, optimisation pass scope) uses the current one, runs already started stay pinned to the classification they started with, and the UI shows the history. Closes D-182.

## Depends on

- `NIGHT-1020-INT-01` and the first post-window wave (`GATE-FIX-*`, `SECTION-READ-MODEL-01`, `NORMS-DISPLAY-DESIGNATION-01`, `XLSX-RU-LABELS-01`) — merged into the base.

## Frozen inputs

- base commit: `f6a16a88a6c86fe2dc1066237134e027047472ad` (`origin/dev`);
- API 71 paths / 81 operations / 235 schemas, 25 error codes, migration head `0027_optimisation_proposals`;
0
- rulings `R-135`, `R-139`; AGENTS §4 (LLM output is never the canonical decision; AI never edits raw comparison evidence; no silent fallback).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: CLASSIFICATION-CORRECTION-01 (the API surface and, where stated, the migration head — only after the integrator hands over the contract slot; phase A is static and container-free)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['surface'],d['migration_head'])"`

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

- `src/auditmanager/sections/**`
- `src/auditmanager/documents/**`
- `tests/unit/sections/**`
- `tests/integration/sections/**`
- `tests/integration/documents/**`
- `db/migrations/versions/**`
- `tests/integration/db/**`
- `src/auditmanager/access/references.py`
- `src/auditmanager/dashboard/**`
- `src/auditmanager/runs/**`
- `src/auditmanager/comparison/**`
- `src/auditmanager/optimisation/**`
- `src/auditmanager/shared/identity/**`
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/**`
- `tests/support/**`
- `tests/contract/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `tests/integration/runs/**`
- `tests/integration/comparison/**`
- `tests/integration/optimisation/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/**`
- `web/src/entities/**`
- `web/src/features/**`
- `web/src/widgets/**`
- `web/src/_pages/version-detail/**`
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
- `docs/program/CLASSIFICATION-CORRECTION-01.md`
- `docs/program/tasks/CLASSIFICATION-CORRECTION-01.md`
Phase A: unit tests container-free. Phase B (on the lane's own containers, staggered): the migration upgrade and the round trip down/up (the db chain test of `GATE-FIX-DB-01` must stay green), the repointed reads' suites (documents, dashboard, runs, comparison, optimisation scope), `tests/contract` (whole dir), `api:verify`, lint, typecheck, changed vitest files, rendered-language guard, journey conformance. No full gate.
## Forbidden hotspots

Dependency files, `web/src/_app/providers.tsx`, global styles, other contexts' internals, the stored original confirmations (never updated — append only), `CURRENT_STATE.md`, refs, tags, the stand. Migrations `0001`…`0027` (this task adds `0028` only).

## Non-goals

No change of already started runs; no backfill; no admin-only correction (an expert corrects; admin alone is refused); no bulk correction; no change to the comparison rules except reading the current classification.

## Deliverables

CLASSIFICATION-CORRECTION-010

## Required tests

Phase A (static): the domain rules (who may correct, what a correction may change, revision numbering, idempotent repeat, conflicting concurrent corrections) as pure code with container-free unit tests, plus a design note in the report naming every read site to repoint (the three selects in `documents/repository.py`, the dashboard query, run start/re-audit routing, comparison pair guard, optimisation pass scope trigger `am_check_optimisation_pass_scope`). Phase B: migration `0028_classification_corrections` (append-only table + current-classification view, immutability trigger, FKs registered), repointed reads, the command `correctVersionClassification` with the reseal, and the correction control + history in the version screen. Report `docs/program/CLASSIFICATION-CORRECTION-01.md`.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020`. **Phasing (binding):** phase A (pure/domain code and container-free unit tests) starts now and touches only the first group of allowed paths; the contract, router, composition-root, web and migration paths open only after the integrator's "go phase B from <sha>", from the commit it names. Other lanes reseal in parallel: before hand-back do a REAL merge of the newest integration tip (`git merge-base --is-ancestor <tip> HEAD`), keep both sides in the contract, and RE-DERIVE every generated artifact and surface count (never hand-merge them).

## Failure/idempotency/security cases

Stated per behaviour in the report; every new guard is shown failing under a quoted mutation.

## Rollback / feature flag

Revert the merge.
