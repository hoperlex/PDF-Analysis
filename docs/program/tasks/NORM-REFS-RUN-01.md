# Task NORM-REFS-RUN-01 — the run page lists the project's cited norms against the corpus

task_id: NORM-REFS-RUN-01

## Outcome

A finished run's page shows, for the normative documents the project text cites (СП, ГОСТ, СНиП, ФЗ, ПП … in the run's saved text), one of five outcomes against the run's pinned norms snapshot — in the corpus / a newer edition exists / not in the corpus / ambiguous / not recognised — with the page where each citation occurs and a link to the norm document; the list is computed per request, read-only, and publishes no findings (a deterministic, no-LLM, no-paid-call slice).

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
- enumerator_owner: NORM-REFS-RUN-01 (the API surface and, where stated, the migration head — only after the integrator hands over the contract slot; phase A is static and container-free)
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

- `src/auditmanager/norms/references/**`
- `src/auditmanager/runs/reference_pipeline.py`
- `tests/unit/norms/references/**`
- `tests/integration/norms/references/**`
- `tests/integration/runs/test_reference_pipeline.py`
- `tests/integration/runs/test_reference_*`
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
- `web/src/_pages/run/**`
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
- `docs/program/NORM-REFS-RUN-01.md`
- `docs/program/tasks/NORM-REFS-RUN-01.md`
Phase A: unit tests container-free; integration on the lane's own containers (staggered; the local real-corpus stand no longer exists — use the fixtures the existing references tests use). Phase B: `tests/contract` (whole dir), `api:verify`, lint, typecheck, changed vitest files, rendered-language guard, journey conformance. No full gate.
## Forbidden hotspots

Migrations (none in this task), the finding categories and publication (no `normative_refs` finding), `rule_id`, dependency files, `web/src/_app/providers.tsx`, global styles, the snapshot rows and the bundle, `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No finding is published; no `normative_refs` category; no migration; no model call; no reviewed slug source (the unparsed slugs are computed by the same parser and listed explicitly as 'not recognised' on the screen).

## Deliverables

NORM-REFS-RUN-010

## Required tests

Phase A (static, container-free where possible): build the `PinnedCatalogue` that `resolve_references` already accepts from the run's pinned `norms_snapshot_id` documents (slug, designation tokens) — a read over the norms snapshot, bounded and paged; compose it with the existing chain (`norms/references/*`, `runs/reference_pipeline.py`) into a per-request read model (outcomes, counts, page anchors, the unparsed-slug list) with tests on recorded text and a small seeded snapshot. Phase B: one read operation `getRunNormReferences` with the reseal (+1 path), router/adapter/role table (any role reads), and a «Нормативные ссылки» section on the run page with the five outcomes, counts and links. Report `docs/program/NORM-REFS-RUN-01.md`.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020`. **Phasing (binding):** phase A (pure/domain code and container-free unit tests) starts now and touches only the first group of allowed paths; the contract, router, composition-root, web and migration paths open only after the integrator's "go phase B from <sha>", from the commit it names. Other lanes reseal in parallel: before hand-back do a REAL merge of the newest integration tip (`git merge-base --is-ancestor <tip> HEAD`), keep both sides in the contract, and RE-DERIVE every generated artifact and surface count (never hand-merge them).

## Failure/idempotency/security cases

Stated per behaviour in the report; every new guard is shown failing under a quoted mutation.

## Rollback / feature flag

Revert the merge.
