# Task CFB-INT-DEV-PUBLISH-26 — integrate W57a API/stage seal

task_id: CFB-INT-DEV-PUBLISH-26

## Outcome

A clean fast-forward `origin/dev` candidate carries the W57a 01B atomic
API/stage reseal with a typed, role-guarded refusing report route. It does
not activate v3 citation publication or a verified report reader.

## Depends on

- `CFB-INT-DEV-PUBLISH-25` — complete at
  `3d131d2966e0efeea7b53d9662785f253165a9a4`;
- `W57A-SEAL-01B` — complete at
  `c08182cab78bed70afbc777019d43de6c0bd2e18`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `3d131d2966e0efeea7b53d9662785f253165a9a4`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- source parent `c71048f788e5d0bee39a312217dfd4c0912e5bc1`;
  source commit `c08182cab78bed70afbc777019d43de6c0bd2e18`;
- source diff exactly 51 paths; its formal task explicitly grants every
  path and holds the sole current API/stage contract and generated-client
  slot; this integration cherry-picks bytes without editing that payload;
- source API 48 paths / 55 operations / 131 schemas, API SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage SHA-256
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`,
  error catalog SHA-256
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`,
  migration 0023 SHA-256
  `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- R-135 defers complete beta gate; W55b main release gate is separate.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: `W57A-SEAL-01B`
- totality_query: `python3 tools/plan/pin_sweep.py reseal-surface migration table error-code route`

The completed source owner alone changed the API/stage enumerators. This
integration applies that exact source commit and owns only the programme
state/report addition.

## Captured premise evidence

- premise: dev25 has the 01A storage seal, and source 01B is a completed
  serial contract owner on 01A; no later API/stage writer has intervened.

### P-01 — source ancestry and scope

- captured_at: 2026-10-16
- command: `git show --format= --name-only c08182cab78bed70afbc777019d43de6c0bd2e18`
- captured_output:
  ```text
  contracts/analysis/v1/stage-registry.json
  contracts/api/v1/openapi.json
  docs/program/W57A-SEAL-01B.md
  docs/program/tasks/W57A-SEAL-01B.md
  infra/deploy/proxy/nginx.conf
  src/auditmanager/api/app.py
  src/auditmanager/api/routers/runs.py
  web/openapi/openapi.json
  web/FRONTEND_LOCK.json
  web/src/shared/api/generated/types.gen.ts
  [41 other paths are enumerated verbatim in source task § Allowed paths]
  ```
- interpretation: accept exactly the source commit, with full path-set
  equality checked before commit; the excerpt is illustrative, not a
  substitute for that check.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- All and only the 51 paths in
  `git diff --name-only c71048f788e5d0bee39a312217dfd4c0912e5bc1..c08182cab78bed70afbc777019d43de6c0bd2e18`,
  each individually granted by `docs/program/tasks/W57A-SEAL-01B.md`
  § Allowed paths;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-26.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-26.md`;
- `docs/program/CURRENT_STATE.md`;
- ignored `web/node_modules` link to the existing pinned W55b dependency
  tree for read-only frontend typecheck, and ignored `.venv` link to the
  existing bootstrap Python environment for JSON Schema contract tests;
  both are environment-only links and no lockfile is changed.

## Forbidden hotspots

All paths outside that exact frozen set; old and 0023 migrations, domain
IDs/error catalog, root dependencies/locks, executable deployment config,
ungranted composition wiring, W56 executor, global styles, live stand,
`origin/main`, tags and release workflow. The source's exact prose-only
exceptions in deployment/BFF/composition files are checked as inert.

## Non-goals

No qualified norm retrieval set, actual citation writer or reader, W57b
export, corpus publication, served v3 analysis, W55b deployment, beta
acceptance or full beta gate.

## Deliverables

Exact source payload, corrected live `CURRENT_STATE.md`, this task/report
and direct published-dev SHA readback.

## Required tests

- source contract/route/stage and frontend API verification evidence;
- integrated `tests/contract/api_v1` and addressed integration tests,
  frontend typecheck when pinned modules available, direct governance;
- exact 51-path equality, contract hashes, migration head, whitespace,
  clean-tree and remote fast-forward proof;
- complete W56–W63 beta gate deferred by R-135; W55b gate separate.

## Integration contract

Cherry-pick exact 01B commit after the already integrated 01A bytes. If
source conflicts or generated mirrors differ, stop and open a new owned
repair. New report route remains typed 503 until a later verified reader;
legacy v1/v2 JSON omits new citation fields. The v1 text-stage identity and
recorded v2 sealer both use registry 1.1.0; artifact version stays 1.0.0.
The integration updates live state pins and publishes only to `origin/dev`
after a fresh remote read; never force-push.

## Failure/idempotency/security cases

Unauthenticated and role-incomplete callers follow the existing role
register. Authorized callers receive a typed 503; no uncertified empty
report is returned. A moved remote ref, failing contract check or source
conflict stops publication.

## Rollback / feature flag

Route remains inert until verified-reader wiring. Revert this exact source
payload and integration documents through a reviewed forward commit if
abandoned; 01A storage seal remains independently owned.

## Handoff

- source files: exact 51-path 01B task grant;
- integration files: this task, report and bounded state update;
- contracts: API and stage reseal from 01B only;
- forbidden hotspots and `origin/main` remain untouched.
