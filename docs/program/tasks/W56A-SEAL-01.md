# Task W56A-SEAL-01 — seal the recorded-only AR v2 contract

## Outcome

The W56a v2 wire/domain/stage contract, forward migration `0022_findings_v2`,
generated client and direct guards exist on one development SHA. Existing v1
responses and recordings remain byte-compatible. No live model is selected
and no v2 proxy mode is activated.

## Depends on

- `W55B-INT-CLOSE` — complete;
- `W56A-RULE-01` — complete, R-129…R-134;
- `W56A-DEV-FREEZE-01` — complete on the published dispatch tip.

## Frozen inputs

- code base: `d600fe69777c923e246d89bc4a9451c3974eaf53`; resolve the
  documentation-only `origin/dev` dispatch tip after the freeze and record it;
- domain candidate revision 12, error-code SHA-256
  `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`;
- API SHA-256
  `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`;
- analysis stage-registry SHA-256
  `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`;
- migration head `0021_portal_bundles`; the new sole head is
  `0022_findings_v2` in `20261015_0022_findings_v2.py`;
- model lock SHA-256
  `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`,
  **read-only** under R-136;
- check cadence R-135; function rules R-129…R-134; W56 plan Part A
  as amended by R-136.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: `W56A-SEAL-01`
- totality_query: `.venv/bin/python tools/plan/pin_sweep.py reseal-surface migration table error-code`

SEAL is the sole W56a owner of the API/error/category/stage enumerators,
generated client and migration head. `P02_LOCK.json` is a distinct enumerator
owned later by `W56A-MODEL-PIN-01`.

## Captured premise evidence

- premise: frozen W55b contract set and 98-path pin inventory are unchanged
  by documentation-only integration

### P-01 — four frozen files

- captured_at: 2026-10-15
- command: `sha256sum contracts/api/v1/openapi.json contracts/domain/v1/error-codes.json contracts/analysis/v1/stage-registry.json docs/program/P02_LOCK.json`
- captured_output:
  ```text
  8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482  contracts/api/v1/openapi.json
  b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16  contracts/domain/v1/error-codes.json
  845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5  contracts/analysis/v1/stage-registry.json
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: those bytes are the pre-SEAL input, not the expected
  output. Any movement before the lane starts requires a new freeze.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

Do not edit `W56A-FREEZE-01.md` or the failed `W56A-PROBE-01.md`.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

**Contract and migration owner, exclusive:**

- `contracts/api/v1/openapi.json`, `contracts/domain/v1/**`,
  `contracts/analysis/v1/stage-registry.json`,
  `contracts/analysis/v1/stage-registry.schema.json`;
- `db/migrations/versions/20261015_0022_findings_v2.py` (new only);
- `web/openapi/openapi.json`, `web/src/shared/api/generated/**`,
  `web/FRONTEND_LOCK.json`;
- `src/auditmanager/shared/errors/{codes,catalog}.py`,
  `src/auditmanager/shared/db/{check,migrations,schema}.py`,
  `src/auditmanager/shared/statemachine/topology.py`;
- `src/auditmanager/api/{app.py,health.py,README.md}`,
  `src/auditmanager/api/schemas/{common,decisions,findings,runs,models}.py`,
  `src/auditmanager/api/routers/{ports,errors,findings,decisions,runs}.py`
  (schema/port/refusing-stub work only; no business rule in router);
- `src/auditmanager/bootstrap/{adapters,composition}.py` (only typed
  refusing stub and port wiring, sole composition-root owner in Stage A).

**Direct consumers, pins and focused tests:**

- `web/src/shared/api/catalog-message.ts`,
  `web/src/entities/audit-run/model/terminal-reason.ts`,
  `web/src/entities/expert-decision/model/category-labels.ts`,
  `web/src/entities/finding/model/severity-labels.ts` (new),
  `web/src/widgets/finding-list/ui/finding-list.tsx` (label only),
  `web/tests/guards/rendered-language.guard.test.ts` (new seed only);
- `tests/support/expected_facts.{json,py}`;
- `tests/contract/api_v1/**`, `tests/contract/domain_p02/**`,
  `tests/contract/analysis/**`, `tests/contract/fixtures_ar/**`,
  `tests/integration/api/{test_authorization,test_operation_surface,test_role_register,test_router_and_body_rules,test_served_document_and_health_plane}.py`,
  `tests/integration/db/{test_migration_lifecycle,test_schema_shape,test_open_items_migration}.py`,
  `tests/integration/analysis/test_ungrounded_reason_vocabulary.py`,
  `tests/integration/composition/{test_composition_root,test_every_port_implementation_is_whole,test_router_answers}.py`,
  `web/tests/contract/**`, `web/tests/guards/frontend-lock.guard.test.ts`;
- `docs/program/{CONTRACT_PIN_REGISTRY,P02_SEAMS,ALPHA_ROADMAP}.md`,
  `docs/manual-tests/{PC-01_prototype,README}.md`,
  `infra/deploy/{README.md,serve.py}` (only direct surface/head literals);
- `docs/program/W56A-SEAL-01.md` (new lane report).

The 98-line pin sweep in `W56A-FREEZE-01.md` §4 is a review register.
Every listed path is classified as changed or review-only in the report.
If an actual required edit falls outside this grant, stop for an integrator
amendment; do not silently widen the diff. `CURRENT_STATE.md` and debt
register updates belong to the later integration slot.

## Forbidden hotspots

- **`docs/program/P02_LOCK.json`** and every other root dependency/lock file;
- old migrations, `VERSION`, release notes, generator corpus or recordings;
- `docs/program/{CURRENT_STATE,DEBT_REGISTER,OWNER_RULINGS_2026-09-17}.md`;
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`
  (`CATEGORY_CHOICES` is WEB's later path);
- provider model selection and runtime publication, global styles,
  `origin/dev`, `origin/main`, tags and stand state.

## Non-goals

- no gateway name or live response claim; no paid call;
- no v2 analysis implementation, merge algorithm, decision folding or UI
  workflow beyond the exhaustive labels;
- no full local gate or beta release.

## Deliverables

- additive 4-artifact API reseal, closed error/category vocabulary, stage
  registry and port signatures;
- forward `0022` migration: widen category and ungrounded-reason CHECKs;
  add proposed severity, expert decided severity with accept-only CHECK;
  backfill canonical observation identity and redefine current-verdict view;
  widen all stored-error CHECKs for the new code;
- typed refusal `model_identity_mismatch` and safe severity-only-on-accept
  constraint, without guessing a gateway name;
- focused tests and a report of each reviewed pin path.

## Required tests

- API generation once with `npm --prefix web run api:generate`, then
  `npm --prefix web run api:verify`; mirror and lock digests agree;
- changed contract validation, OpenAPI conformance, served-operation and
  error-catalog tests relevant to the reseal; typecheck and lint for changed
  frontend files;
- fresh upgrade and upgrade from `0021` **with rows**, on an isolated
  PostgreSQL database; backfill and CHECK/view assertions; refused downgrade
  with retained data; no old migration edited;
- v1 recorded response/baseline cases 03–11 unchanged; new optional fields
  absent on v1;
- one mutation per new closed vocabulary/refusal; `git diff --check` and
  exact allowed-path proof. No full local `make gate` under R-135.

## Integration contract

Later PROVIDER, PROFILES, MERGE, DECIDE and WEB tasks consume this exact
contract and migration after the integrator merges SEAL. A model mismatch
is a typed failure with zero published findings; the provider implementation
and durable effect recording are later tasks. No new model identifier is
accepted until the separate MODEL-PIN proof. v1 callers see no new required
field or changed existing response byte.

## Failure/idempotency/security cases

- Migration conflict, non-idempotent backfill, count pin outside grant or
  v1 byte change stops the lane; no silent fallback.
- The migration must not assign canonical identity by filename/path or
  display label.
- Error details never include proxy body, URL, credential or raw exception.
- A missing model pin does not select a default model.

## Rollback / feature flag

Default profile remains v1. Before data exists, revert SEAL. After a
successful migration with data, use a forward correction; no destructive
downgrade. v2 activation requires a later owner act and model pin.

## Handoff

- report exact changed files, focused test outcomes, new contract digests
  and migration head;
- list every pin-sweep path as changed or review-only;
- prove `P02_LOCK.json`, old migrations, root locks, global styles,
  `CURRENT_STATE.md` and unrelated code untouched;
- hand branch and exact SHA to the integrator; do not push any ref.
