# Task W52-RELEASES-API — implement the release backend and loader

task_id: W52-RELEASES-API

## Outcome

The sealed release operations serve the running version and database-backed
release history, the loader applies authored revisions with safe rollback
semantics, and deployment runs it after migration before starting the API.

## Depends on

- `W52-SEAL-01`, accepted at
  `0dd3f7b20623e51d7927dd0fc14a1fb12292b062`.

## Frozen inputs

- Start only from the Stage-C grant SHA read back from `origin/dev` by
  `W52-INT-B2C-01`; record that SHA in the lane report.
- W52 API 30 paths / 37 operations / 83 schemas, 23 error codes, domain
  revision 9 / 29 identities, migration head `0016_release_notes` and
  `contract_version=1.0.0-draft.1` stay fixed.
- `dispatch/W52-PLAN.md` §§3.1–3.5 and Stage C; R-71–R-74.
  The SEAL port and tables are frozen. D-137–D-140 own deferred QA and gate.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `release-notes/*.json` and the `release-notes` compose service
- enumerator_owner: `W52-RELEASES-API` for Stage C
- totality_query: the loader rejects unknown top-level files; compose, deploy
  and reset tests prove the one-shot service runs after migration

## Captured premise evidence

- premise: SEAL fixes the three release operations and `0016_release_notes`
  before this backend lane begins.

### P-01 — accepted contract boundary

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; python3 tools/plan/pin_sweep.py table | rg '^(db/migrations/versions/|infra/deploy/)'`
- captured_output:
  ```text
  0dd3f7b20623e51d7927dd0fc14a1fb12292b062
  db/migrations/versions/**	table: catalogue
  infra/deploy/compose.server.yml	table: catalogue
  infra/deploy/deploy.sh	table: catalogue
  infra/deploy/reset.sh	table: catalogue
  ```
- interpretation: the table event is advisory here: Stage C adds a loader
  service and uses the sealed tables, with no migration or API reseal.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `VERSION`, `release-notes/**` — schema and minimal `0.3.0.json` and
  `0.2.0.json` entries only; substantive release prose is Stage C2
- `src/auditmanager/releases/**`
- `src/auditmanager/api/routers/releases.py` — fill the sealed skeleton only
- `src/auditmanager/bootstrap/adapters.py`,
  `src/auditmanager/bootstrap/composition.py` — release wiring only
- `infra/deploy/Dockerfile.api`, `infra/deploy/compose.server.yml`,
  `infra/deploy/deploy.sh`, `infra/deploy/reset.sh`,
  `infra/deploy/README.md` — release service, copies and directly affected prose
- `tests/integration/releases/**`
- `tests/integration/composition/test_deploy_script_refusals.py`,
  `tests/integration/composition/test_deploy_image_identity.py`,
  `tests/integration/composition/test_deployed_stack_probe.py`,
  `tests/integration/composition/test_session_register_volume.py`,
  `tests/integration/composition/test_reset_script_refusals.py`
- `docs/program/W52-RELEASES-API.md` — six-item hand-back
- local `agent/w52-releases-api` branch/worktree and its ignored environment

## Forbidden hotspots

Every other path: `contracts/**`, `db/migrations/**`, API operation or
transport schema changes beyond the named router, shared error catalog,
root dependency/lock files except read-only `uv.lock`, generated client,
web UI, global styles, `origin/dev`, `origin/main`, tags and deployment.
Any sweep hit outside this grant is an integrator stop, not implicit authority.

## Non-goals

No contract reseal, new migration, `contract_version` move, release panel,
banner, web build ID, substantive user-facing notes, release judge, full gate,
QA, live stand or publication.

## Deliverables

- Root `VERSION=0.3.0`, schema and minimal valid release entries; shape
  validation and canonical SemVer sort keys.
- The content-derived API `build_id` over the exact §3.1 roots, bound once at
  startup from the package root; refusal when `VERSION` is absent or invalid.
- Release repository, one-shot loader and real `ReleasesPort` implementation.
  Versions above the running image are hidden; `whats_new` uses database
  creation/load clocks and the account's monotone mark.
- API image `COPY` lines and release-notes service between migrate and API;
  deploy and reset paths run the service as §3.3 states.
- Focused tests and a six-item hand-back on a clean branch.

## Required checks

- Each loader rule 1–4, two identical runs → one revision, authored revision
  conflict/lower-revision handling, forward-database rollback and unknown file
  refusal, on isolated PostgreSQL.
- `build_id`: equal content equals ID; one-byte change differs; checkout
  equals built image `/app`; tracked inputs do not match `.dockerignore`.
- Sealed API operations: version payload, visible history, unknown/future mark
  refusal, lower mark no-op, admin's own mark, and `whats_new` for old and new
  accounts. Test the compose/deploy/reset sequencing.
- `npm --prefix web run api:verify`, focused contract/composition tests,
  Python compilation, frontend lint/typecheck and `git diff --check`.
  State every unrun check. Complete gate and independent QA are D-137–D-140.

## Integration contract

Work from the exact read-back Stage-C grant SHA. Use only the reserved
`gate-w52r` PostgreSQL `56800` and S3 `60400/60401`, database
`audit_w52r` and bucket `audit-w52r`; check port availability again before
start. This lane alone fills release backend and deployment wiring. Hand back
the clean branch for integrator merge before RELEASES-WEB and TRANSLATE.

## Failure / idempotency / security

An equal revision with changed canonical content fails before commit; a lower
revision is reported and ignored. Missing files for a release at or below the
image version fail atomically; newer database releases survive rollback and
stay hidden. Unknown/future read marks refuse with the catalog validation
code. A guest or incomplete account cannot read or mark notes. Never log
credentials or modify another lane's containers.

## Rollback / feature flag

The application can roll back to an older image: future release rows remain
append-only and filtered. Loader rule 4 protects history; the restore path
reports its outcome. No runtime feature flag. No `origin/main` deployment.

## Handoff

Return changed files, checks/results, contract changes (expected none), risks,
integrator steps and forbidden-hotspot proof. No checkpoint or tag.
