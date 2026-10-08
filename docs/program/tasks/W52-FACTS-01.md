# Task W52-FACTS-01 — one independent expected-facts file

task_id: W52-FACTS-01

## Outcome

All registered surface, error-catalog and migration-head expectations and their symbolic
siblings use one hand-written `tests/support/expected_facts.json`; the inventory fails on a
new independent count literal outside that file.

## Depends on

- `W52-PINSWEEP-01` — integrated at `57237f458ee275aff3b786721a6811aa9775ff50`.
- `W52-INT-DEFER-01` — the docs-only deferral record is committed before executor dispatch.

## Frozen inputs

- Code base `57237f458ee275aff3b786721a6811aa9775ff50`, plus the docs-only dispatch SHA
  named by the integrator. Domain `1.0.0-draft.1` revision 9 / 29 identities; API 27 paths /
  34 operations / 77 schemas; error catalog 23; migration head
  `0015_accounts_roles_registration`.
- Proposed W52 plan §3.6 at `2b45a11ec558df1452a4822149e54d2fe0ddb57e`, current
  `CONTRACT_PIN_REGISTRY.md` version 1 and `W52-PINSWEEP-01`. The proposed schema is an
  implementation input, not a W52 freeze or owner-rule claim.
- Owner direction 2026-10-08: proceed without approval; QA, live checks and full gate deferred
  as D-137…D-140. Keep only focused tests and lint in this lane.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `tests/support/expected_facts.json`
- enumerator_owner: `W52-FACTS-01`
- totality_query: `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/api_v1/test_doc_prose_facts.py`

The task centralizes the independent expectation sets and owns the registry inventory update.
It does not add or remove any application operation, schema, error code or migration.

## Captured premise evidence

- premise: the development tree has a versioned registry and the planning branch proposes a
  hand-written facts schema.

### P-01 — base and registry

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n '"registry_version"' docs/program/CONTRACT_PIN_REGISTRY.md`
- captured_output:
  ```text
  57237f458ee275aff3b786721a6811aa9775ff50
  15:  "registry_version": 1,
  ```
- interpretation: this identifies the exact code base and current registry format; it does
  not prove completeness.

### P-02 — proposed schema and grant

- captured_at: 2026-10-08
- command: `git show 2b45a11:docs/program/dispatch/W52-PLAN.md | sed -n '192p;195p;294p'`
- captured_output:
  ```text
  ### 3.6 Expected-facts file (A5) — hand-written, with a fixed schema
  artifact it judges. So `tests/support/expected_facts.json` is **hand-written**, with this schema
  **`W52-FACTS-01`** (§3.6). Allowed: `tests/support/expected_facts.json` (new), the files of the 27
  ```
- interpretation: the plan proposes a central independent file; the W52 freeze and owner
  confirmations still remain separate.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/support/expected_facts.json`
- `tests/support/expected_facts.py`
- `tests/contract/api_v1/**`
- `tests/contract/domain_p02/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `tests/e2e/pc01/test_acceptance.py`
- `web/tests/contract/**`
- `web/tests/unit/api/failure-surface.test.ts`
- `web/tests/guards/frontend-lock.guard.test.ts`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/W52-FACTS-01.md`

## Forbidden hotspots

Everything else, especially `contracts/**`, migrations, root dependency/lock files,
`Makefile`, application code, composition root, global styles, web lock/source, and
`tests/contract/tools/fixtures/**`. The integrator has the separate debt-register slot.

## Non-goals

No contract reseal, runtime change, W52 owner-rule substitution, W52 freeze, QA, stand,
full gate, release/tag or `origin/main` publication. No generated expectation from the
artifact under test; the JSON values are manually copied from the already frozen W51 pins.

## Deliverables

- Facts file with the §3.6 schema, explicit operation triples/schema-name list, separate
  API/stored error counts, migration head and contract version.
- Existing registered pins and symbolic siblings compare their artifact with facts; the
  registry continues to identify each consumer once.
- Inventory refuses any new independent count literal for a surface/error/head value,
  independent of the number's actual value. Exclude fixture data and only the named
  unrelated `len(report)` assertion.
- Mutation evidence for each family using current values; executor report with limitations.

## Required tests

- Focused `pytest` for modified contract/integration test files; targeted Vitest where a
  web test changed; `npm --prefix web run lint`; Python syntax and `git diff --check`.
- No stand or full `make gate` under the owner direction. No gate result is claimed.

## Integration contract

Hand back a clean `agent/w52-facts-01` from the exact dispatch SHA with only allowed paths.
The integrator may publish preparation to `origin/dev` after basic checks; the W52 freeze
must re-sweep grants and resolve owner confirmations before the later SEAL lane.

## Failure/idempotency/security cases

Missing/malformed facts, duplicate operation or schema names, a stale registry needle and
an unregistered independent literal fail visibly. Reading the facts file never reads the
artifact under test or executes data. Re-running tests is idempotent.

## Rollback / feature flag

Revert the implementation merge. Only tests and planning records change; no runtime
feature flag applies.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
