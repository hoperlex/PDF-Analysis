# Task BETA-CONTRACT-SEAL-01 — the contract and error catalogue sealed at 1.0.0 (B9)

task_id: BETA-CONTRACT-SEAL-01

## Outcome

`contract_version` reads `1.0.0` everywhere it is declared and served (API, domain error
catalogue, analysis and events families, the edge's `429` body, the web forwarder, the generated
client and every pin), the error catalogue is `frozen: true` with `status` final, and the two
run-start refusals that today reuse `required_norm_unavailable` with
`details.reference_kind` `version_classification` / `analysis_profile` (`D-179`) have their own
dedicated error codes, so the frozen catalogue carries no known wart. `getProductVersion` served
from a stack reads `contract_version: "1.0.0"`. Nothing else about behaviour changes.

Integrator decisions taken for this closed-beta seal (the owner may overrule them before any
publication, because nothing here reaches `origin/main` without a separate exact-SHA instruction):

- the API, domain, analysis and events families move to `1.0.0` together, because one
  `contract_version` literal is shared by all of them and pinned in about 66 consumer paths
  (`python3 tools/plan/pin_sweep.py contract-version`); `contracts/comparison/v1` is a README only;
- `OPEN-RETENTION` (`U-04`) is not decided (criterion `B11` is deferred by `R-141c`): the freeze
  states that no retention window is declared, it does not invent one;
- `model_identity_mismatch` stays in the catalogue (its raise site waits on `W56A-MODEL-PIN-01`);
  `rate_limited` and `analysis_input_budget_exceeded` stay outside the stored vocabulary as their
  notes say.

## Depends on

- `NORM-REFS-RUN-01` merged on `origin/dev` (it reseals the same surface); `CLASSIFICATION-CORRECTION-01`
  is merged (head `0028`). Start from the `origin/dev` the integrator names in the dispatch.

## Frozen inputs

- `docs/program/BETA-MATRIX-01.md` section B9: the exact list of files, literals, generated
  artifacts and pins the seal changes, the catalogue debts (`D-179`; `D-151`, `D-161`, `D-172`,
  `D-163`, `D-145` are each done in the seal or carried on purpose, with the reason written in
  the report), and the evidence expected after the seal;
- `docs/program/dispatch/ROADMAP-TO-BETA.md` sections 8.2 and 9 (`B9`); rulings `R-135`, `R-139`,
  `R-141`; `VERSIONING_AND_FREEZE_POLICY.md` for what "frozen" obliges afterwards;
- `tools/plan/pin_sweep.py contract-version` as the totality query for the literal.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: BETA-CONTRACT-SEAL-01 (this task alone owns the contract slot, the migration head and the pin files for its duration)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['contract_version'],d['migration_head'])"`

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

- `contracts/**`
- `web/openapi/**`, `web/FRONTEND_LOCK.json`, `web/src/shared/api/**`
- `web/src/entities/**`, `web/src/shared/**` (only error messages, `catalog-message`, `errors`, `terminal-reason`)
- `web/tests/**`
- `src/auditmanager/api/**`, `src/auditmanager/shared/errors/**`, `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/runs/**`, `src/auditmanager/sections/**` (only the raise sites and messages of the two refusals)
- `db/migrations/versions/**` (one new migration widening the stored-error CHECKs, only if codes are added)
- `tests/**`, `fixtures/golden/**`, `artifacts/validation/PC-02/baseline/**` (re-captured only after asserting what they pin)
- `infra/deploy/proxy/nginx.conf`, `infra/deploy/proxy/tls-server.conf`
- `docs/program/CONTRACT_PIN_REGISTRY.md`, `docs/program/P02_SEAMS.md`, `docs/program/ALPHA_ROADMAP.md`, `docs/manual-tests/**`
- `docs/program/BETA-CONTRACT-SEAL-01.md`, `docs/program/tasks/BETA-CONTRACT-SEAL-01.md`

## Lane resources

- foundation_instance: `auditmanager-beta-contract-seal`
- postgres_port: `57710`
- s3_api_port: `61330`
- s3_console_port: `61331`
- postgres_db: `auditmanager_beta_contract_seal`
- s3_bucket: `auditmanager-beta-contract-seal`

## Forbidden hotspots

Dependency and lock files, `web/src/_app/providers.tsx`, global styles, `CURRENT_STATE.md`,
`DEBT_REGISTER.md`, `VERSION`, `release-notes/**`, refs, tags, the stand, and any behaviour
change outside the two refusals' error codes. `contract_version` literals inside historical
records are changed only after asserting what they pin.

## Non-goals

No new operation, no new schema, no new feature, no release notes, no full gate (the integrator
runs one on the exact tree afterwards), no change to `VERSION`.

## Deliverables

1. Phase A: dedicated codes for the two run-start refusals (catalogue entries with category,
   HTTP status, retryability and the Russian message under the rendered-language guard; the
   enum, `shared/errors/codes.py`, web `catalog-message`/`errors`/`terminal-reason`; a migration
   widening the stored-error CHECKs with a downgrade that refuses once rows use the new codes;
   tests including a quoted mutation per guard).
2. Phase B: the `1.0.0` seal: every literal and generated artifact from the matrix list,
   `frozen: true`, `OPEN-RETENTION` stated, `status` final, re-derived `FRONTEND_LOCK`,
   `expected_facts`, error-catalogue pins and prose counts; the characterization and baseline
   records re-captured only after asserting what they pin.
3. Report `docs/program/BETA-CONTRACT-SEAL-01.md` with the AGENTS section 5 list, the
   `pin_sweep` before/after, and for each of `D-151`, `D-161`, `D-172`, `D-163`, `D-145` whether it
   was done or carried and why.

## Required tests

`python3 tools/plan/pin_sweep.py contract-version` shows no consumer on the old literal;
`pytest tests/contract` (official invocation); `npm --prefix web run api:verify`; lint, typecheck
and the changed vitest files; the migration upgrade/downgrade on the lane's containers; the
integration directories whose literals moved (`api`, `runs`, `sections`, `db`, `composition`,
`characterization`) on the lane's containers; every new guard shown failing under a quoted
mutation. No full gate.

## Integration contract

One slice, one real merge into `integration/night-1020` by the integrator
(`git merge-base --is-ancestor <tip> HEAD`); all generated artifacts re-derived, never
hand-merged; the integrator then runs the full gate on the exact merged tree.

## Failure/idempotency/security cases

The new codes carry the same HTTP status and `retryable` rule as the code they replace for the
caller's retry logic; an old client reading `required_norm_unavailable` for these two cases is
documented as a changed behaviour of a draft contract; no error body leaks a path or a
credential; a stored run row with a new code survives upgrade and refuses downgrade.

## Rollback / feature flag

Revert the merge; the draft literal and the shared code return. Migration downgrade refuses once
rows carry a new code, so a revert after use is a forward fix through the gate.
