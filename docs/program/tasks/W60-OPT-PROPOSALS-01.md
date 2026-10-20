# Task W60-OPT-PROPOSALS-01 — optimisation proposals for AR with expert decisions

task_id: W60-OPT-PROPOSALS-01

## Outcome

On the project's «Оптимизация» tab an expert starts an optimisation pass for the
current AR version of a document set; the pass is pinned to the version, its published
run, the current price-list revision and the effective AR vendor-list revision, and
persists immutable proposals of the deterministic kind «более дешёвый аналог»: a
specification row matched to a price-list position for which a cheaper position with
the same normalised unit exists from a vendor on the effective vendor list; the saving
is computed only when both prices and a numeric quantity exist, otherwise it is absent.
Experts append accept / reject / revise (with comment) decisions per proposal; the tab
shows proposal counts by decision, separate from finding counts, and a CSV export with
formula-escaped cells. Findings are never read for writing or changed. LLM proposal
generation is a later slice (contract family `contracts/optimization/v1` reserved).

## Depends on

- `W60-OPT-MATCH-01` phase A (`67fd24c0`), `W60-PRICE-LIST-01` (migration `0026`).

## Frozen inputs

- base commit: `67fd24c0` on `agent/w60-opt-match-01` (head `0026_price_lists`); this task
  alone takes migration `0027`;
- binding rules: `ROADMAP-TO-BETA.md` §10 A-2..A-5 (proposal is a separate entity with its
  own decisions, export and counts; vendor list global + project override, the run
  records the list version; money only from matched price-list positions, absent not 0),
  W60 PROJECT-OPT acceptance; AGENTS §4 (LLM output never the canonical decision; no
  state only in memory); rulings `R-60`, `R-135`, `R-139`; no LLM, no new dependency.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W60-OPT-PROPOSALS-01 (migration 0027 in phase A; API surface in phase B after the integrator hands over the contract slot)
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

- `db/migrations/versions/**`
- `src/auditmanager/optimisation/proposals/**`
- `src/auditmanager/access/references.py`
- `tests/integration/optimisation/proposals/**`
- `tests/unit/optimisation/proposals/**`
- `tests/integration/db/**`
- `tests/support/expected_facts.json`
- `src/auditmanager/optimisation/public.py`
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `src/auditmanager/shared/identity/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/**`
- `tests/support/**`
- `tests/contract/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/**`
- `web/src/shared/config/screen-registry.ts`
- `web/src/entities/**`
- `web/src/features/**`
- `web/src/widgets/optimisation-proposals/**`
- `web/src/_pages/project-detail/**`
- `web/src/_pages/optimisation/**`
- `web/src/app/projects/**`
- `web/src/app/optimisation/**`
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
- `docs/program/W60-OPT-PROPOSALS-01.md`
- `docs/program/tasks/W60-OPT-PROPOSALS-01.md`

**Phasing (binding):** phase A may touch only the first seven paths and the two docs
files. Every other path opens only after the integrator's message.

## Lane resources

- foundation_instance: `auditmanager-w60-opt-proposals`
- postgres_port: `57610`
- s3_api_port: `61210`
- s3_console_port: `61211`
- postgres_db: `auditmanager_w60_opt_proposals`
- s3_bucket: `auditmanager-w60-opt-proposals`

## Forbidden hotspots

Dependency files, `web/src/_app/providers.tsx`, global styles, `findings/**`,
`decisions/**`, migrations `0025`/`0026`, `specification.py`/`matching.py` (additive use
only), `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No LLM generation, no section optimisation/replication, no currency conversion, no
automatic acceptance, no full gate.

## Deliverables

Phase A: migration `0027_optimisation_proposals` (pass, proposal, proposal-decision
event; immutable/append-only), the `optimisation/proposals` package (start pass —
expert, idempotent; deterministic generator; decisions; counts; CSV with formula
escaping) and tests incl. migration upgrade. Phase B: operations with the reseal and the
proposals section on the «Оптимизация» tab; retire the hidden `/optimisation` stub
(redirect to the projects list) per R-66. Report `docs/program/W60-OPT-PROPOSALS-01.md`.

## Required tests

Phase A: integration on the lane's own containers and the migration upgrade; mutation
probes for the money rule. Phase B: `tests/contract`, `api:verify`, lint, typecheck,
changed vitest files, rendered-language guard, journey static conformance. No full gate.

## Integration contract

Phases A and B merge as one slice, after `W60-PRICE-LIST-01` and `W60-OPT-MATCH-01`.

## Failure/idempotency/security cases

Non-AR or unclassified version, no published run, no price list or no effective vendor
list → explicit refusal; exact repeat of a pass returns the same pass; admin alone
cannot decide; decisions append only; a saving never uses an unmatched or
unit-mismatched row.

## Rollback / feature flag

Revert the merge; migration 0027 downgrade drops only its tables.
