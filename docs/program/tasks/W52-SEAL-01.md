# Task W52-SEAL-01 — seal the release API and migration boundary

task_id: W52-SEAL-01

## Outcome

The three release operations, their role/profile policy and append-only `0016_release_notes` schema are declared and served together. The generated client and every live surface/head pin agree with the new contract. This slot stops at the router/port skeleton; Stage C fills release storage, loader and UI behavior.

## Depends on

- `W52-GATE-01`, accepted on clean `integration/w51` and read back from `origin/dev` at `6d2ae471132e78268d3af8ca872560491ec57233`.

## Frozen inputs

- Base: `6d2ae471132e78268d3af8ca872560491ec57233`; W52 Stage-A freeze and `dispatch/W52-PLAN.md` §3.1–§3.3, §4 Stage B.
- Domain candidate revision 9 / 29 identities; API 27 paths / 34 operations / 77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`; `contract_version` remains `1.0.0-draft.1` under R-71.
- R-70/R-74 development exception: focused contract, client and integration checks now; complete gate and exact-candidate parity/timing at D-140. D-137–D-139 remain open.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`; `db/migrations/versions/20261008_0016_release_notes.py`
- enumerator_owner: `W52-SEAL-01` alone for Stage B
- totality_query: served operation set equals the document (`tests/integration/api/test_operation_surface.py`), and Alembic reports exactly `0016_release_notes` as head.

## Captured premise evidence

- premise: Stage A is published at the exact base and `origin/main` has not moved.

### P-01 — Stage-A result and current grant inventory

- captured_at: 2026-10-08
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  6d2ae471132e78268d3af8ca872560491ec57233 refs/heads/dev
  1e9bb1308b7b97cd75eef28e206b23c569871b68 refs/heads/main
  ```
- interpretation: Stage A is published; all sweep hits are review obligations, with the narrow grants below. A hit is not authority to change unrelated logic in its file.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `contracts/api/v1/openapi.json`, `contracts/api/v1/README.md`, `contracts/domain/v1/README.md` — new operations/schemas and directly affected surface prose only
- `db/migrations/versions/**` — solely the new `20261008_0016_release_notes.py` migration and head; existing migration files are read-only
- `src/auditmanager/api/**` — release router skeleton, port types, policy register and directly affected declarations
- `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/bootstrap/composition.py`, `src/auditmanager/access/references.py` — release port skeleton wiring and account mark reference only
- `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json` — generated mirror/client and exact lock reseal
- `tests/contract/**`, `web/tests/contract/**` — contract/surface pins only; no edits to the four already merged D-128 guard files
- `tests/integration/{api,auth,composition,db}/**` — new operation, role, migration and wiring checks only
- `tests/integration/p02_journey/journey.py`, `tests/e2e/pc01/test_acceptance.py`, `tests/e2e/pc01/journey/manifest.json` — measured table/surface inventories only
- `tests/integration/foundation/test_cross_provider_publication.py`, `tests/support/expected_facts.json`, `tests/support/expected_facts.py` — head/surface pins only
- `docs/program/CONTRACT_PIN_REGISTRY.md`, `docs/program/P02_SEAMS.md`, `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md` — exact current surface/head/register sentences and operation rows only
- `docs/manual-tests/PC-01_prototype.md`, `docs/manual-tests/README.md` — migration-head or surface sentence only
- `infra/deploy/README.md`, `infra/deploy/serve.py`, `infra/deploy/proxy/nginx.conf`, `infra/deploy/compose.server.yml`, `infra/deploy/deploy.sh`, `infra/deploy/reset.sh` — count/head/table references only; no deploy flow change
- `src/auditmanager/documents/refusals.py`, `src/auditmanager/shared/db/{__init__.py,check.py,errors.py,migrations.py,schema.py}`, `src/auditmanager/shared/statemachine/topology.py`, `src/auditmanager/storage/check.py` — migration-head comments/constants only
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`, `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/credentialed-forward.ts`, `web/src/shared/api/authorization.ts` — surface count sentences only; the last path was added by the exclusive integrator after the first contract test identified its live count comment outside the original grant
- `web/tests/guards/frontend-lock.guard.test.ts` — lock/surface pin only
- `docs/program/W52-SEAL-01.md` — six-item hand-back
- local `agent/w52-seal-01` branch/worktree and its own ignored environment

## Forbidden hotspots

Every path outside the list; root dependency/lock files; global styles; domain version or error catalog; `contracts/**` beyond the named files; any migration other than `0016`; product behavior in `infra/deploy/**`; `src/auditmanager/releases/**`, `VERSION`, `release-notes/**`, and release UI (Stage C); the four D-128 guard files; `origin/dev`, `origin/main`, tags and deployment. A sweep hit outside this grant is a stop for integrator correction, never an implicit grant.

## Non-goals

No release loader, SemVer sorter, build ID, user notes, web panel/banner, runbook translation, `contract_version` move, guest operation, full gate, JUnit parity, release verdict or live deployment.

## Deliverables

- The three operations of W52 §3.2, exact schemas and role/profile policy; `markReleaseNotesRead` accepts an administrator's own mark without the expert role.
- Migration `0016_release_notes`: append-only release/revision rows, monotone account mark, immutable version natural key and downgrade policy from §3.3.
- Router/port skeleton and generated client; complete reviewed pin changes, contract/API tests and report.

## Required tests

- `python3 tools/plan/pin_sweep.py reseal-surface migration table --check docs/program/tasks/W52-SEAL-01.md` must exit 0 before editing and at hand-back.
- `.venv/bin/python -m pytest tests/contract -q`; `npm --prefix web run api:verify`; focused API/auth/composition/DB real-service suites for changed paths; Python compilation, frontend lint/typecheck, `git diff --check`.
- Full `make gate`, JUnit outcome parity, timing, QA and built-stand validation are explicitly deferred to D-137–D-140 and cannot be claimed by this lane.

## Integration contract

Start from the exact Stage-B grant SHA after its remote readback; use only reserved `gate-w52s` services if needed (PostgreSQL `56790`, S3 `60390/60391`, database `audit_w52s`, bucket `audit-w52s`). One slot owns the contract, migration head, composition-root wiring and generated client. Hand back a clean branch with exact diff and checks; the integrator merges SEAL before Stage C grants and publishes only a checked development candidate to `origin/dev`.

## Failure/idempotency/security cases

Unknown or future `read_through` is a validation refusal; a lower known mark is a no-op. Release and revision rows reject updates/deletes. A guest, inactive account or incomplete profile never gains these operations. Any pin beyond this grant stops the lane. Do not log credentials or change another instance's services.

## Rollback / feature flag

Revert the atomic seal commit before Stage C; migration and contract are one candidate boundary. There is no runtime feature flag or production deployment in this task.

## Handoff

List changed files, exact check results, contract and migration changes, risks, integrator steps and forbidden-hotspot proof. No checkpoint/tag.
