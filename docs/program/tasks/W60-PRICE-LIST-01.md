# Task W60-PRICE-LIST-01 — project price lists and vendor lists: the storage of «Оптимизация проекта»

task_id: W60-PRICE-LIST-01

## Outcome

On a project's «Оптимизация» tab an expert uploads the project's price list (CSV or
XLSX, first sheet); each upload is an immutable revision with its parsed positions
(name, unit, unit price, currency, optional code/vendor/section), shown with parse
warnings for skipped rows; the latest revision is current and earlier ones stay
readable. An administrator keeps a global vendor list per section and an expert may
set a project override per section; each change is a new revision with actor and
time. No money figure appears anywhere without a matched price-list position — this
slice stores and shows prices; optimisation proposals and totals are the next slice.

## Depends on

- `W61-DISPATCHER-01` phase A (`3461747c`, migration `0025_work_assignments`) — this
  task chains `0026` on it and merges after it.

## Frozen inputs

- base commit: `0f0903f2d3c91504148995414f42268ea458d2f1` (`origin/dev`) plus `3461747c`;
- API at base: 52 paths / 59 operations / 153 schemas;
- roadmap: `CODE-FIRST-SCOPE-W58-W63.md` W60 PROJECT-OPT (prices only from the project's
  Excel/CSV; vendor list per section with override and version; no sum without a
  price); memory of the owner's poll (vendor list global + per project; money only
  from an uploaded price list); rulings `R-135`, `R-139`; no new dependency (stdlib
  CSV/XLSX reading only).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W60-PRICE-LIST-01 (migration 0026 in phase A; API surface in phase B after the integrator hands over the contract slot)
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
- `src/auditmanager/optimisation/**`
- `src/auditmanager/access/references.py`
- `tests/integration/optimisation/**`
- `tests/integration/db/**`
- `tests/unit/optimisation/**`
- `tests/support/expected_facts.json`
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
- `web/src/entities/**`
- `web/src/features/**`
- `web/src/widgets/**`
- `web/src/_pages/project-detail/**`
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
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/serve.py`
- `docs/program/W60-PRICE-LIST-01.md`
- `docs/program/tasks/W60-PRICE-LIST-01.md`

**Phasing (binding):** phase A may touch only the first seven paths and the two docs
files. Every other path opens only after the integrator's message that hands over
the contract slot.

## Lane resources

- foundation_instance: `auditmanager-w60-price-list`
- postgres_port: `57570`
- s3_api_port: `61170`
- s3_console_port: `61171`
- postgres_db: `auditmanager_w60_price_list`
- s3_bucket: `auditmanager-w60-price-list`

## Forbidden hotspots

Dependency files, `web/src/_app/providers.tsx`, global styles, other contexts'
internals, the dispatcher's `dispatch/**` and migration `0025`, `CURRENT_STATE.md`,
refs, tags, the stand.

## Non-goals

No optimisation proposals, no totals, no LLM call, no price inference, no currency
conversion, no section optimisation (Form 7), no full gate.

## Deliverables

Phase A: migration `0026_price_lists` (price-list revision + positions, vendor-list
revisions global/project per section; append-only/immutable like other evidence
tables; the uploaded file kept as a Blob with a PostgreSQL binding through the
existing storage/outbox discipline), the `optimisation` context (parse CSV/XLSX with
stdlib, bounded size/rows, deterministic parse report; commands and queries) and
tests. Phase B: operations with the reseal, the «Оптимизация» project tab. Report
`docs/program/W60-PRICE-LIST-01.md`.

## Required tests

Phase A: focused integration tests on the lane's own containers, migration upgrade,
parser unit tests (CSV encodings cp1251/utf-8, decimal comma, XLSX shared strings,
malformed rows reported not guessed). Phase B: `tests/contract`, `api:verify`, lint,
typecheck, changed vitest files, rendered-language guard, journey static conformance.

## Integration contract

Phases A and B merge as one slice, after `W61-DISPATCHER-01`.

## Failure/idempotency/security cases

Oversized or unreadable file refused with a reason; exact re-upload with the same
idempotency key returns the same revision; admin-only global vendor list; expert-only
project override and price-list upload; foreign project refused.

## Rollback / feature flag

Revert the merge; migration 0026 downgrade drops only its tables.
