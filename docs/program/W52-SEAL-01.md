# W52-SEAL-01 — release API and migration seal hand-back

## 1. Changed files and result

The contract now has **30 paths, 37 operations and 83 component schemas**. The three
new operations are `getProductVersion`, `listReleases` and
`markReleaseNotesRead`. Their router and `ReleasesPort` are wired to an explicit
Stage-B adapter that answers `dependency_unavailable` until Stage C installs the
release context. All three require an active account with a complete profile;
the account's own mark is available to an `admin` without `expert`.

The exact changed path inventory is:

```text
contracts/api/v1/README.md
contracts/api/v1/openapi.json
contracts/domain/v1/README.md
db/migrations/versions/20261008_0016_release_notes.py
docs/manual-tests/PC-01_prototype.md
docs/program/ALPHA_ROADMAP.md
docs/program/CURRENT_STATE.md
docs/program/P02_SEAMS.md
docs/program/W52-SEAL-01.md
docs/program/tasks/W52-SEAL-01.md
infra/deploy/README.md
infra/deploy/proxy/nginx.conf
infra/deploy/serve.py
src/auditmanager/access/references.py
src/auditmanager/api/README.md
src/auditmanager/api/app.py
src/auditmanager/api/health.py
src/auditmanager/api/routers/__init__.py
src/auditmanager/api/routers/declarations.py
src/auditmanager/api/routers/errors.py
src/auditmanager/api/routers/ports.py
src/auditmanager/api/routers/releases.py
src/auditmanager/api/schemas/models.py
src/auditmanager/api/security.py
src/auditmanager/bootstrap/adapters.py
src/auditmanager/bootstrap/composition.py
tests/contract/api_v1/test_surface_counts_in_prose.py
tests/contract/domain_p02/test_openapi_document.py
tests/e2e/pc01/test_acceptance.py
tests/integration/api/identity_surface.py
tests/integration/api/test_authorization.py
tests/integration/api/test_release_routes.py
tests/integration/api/test_role_register.py
tests/integration/db/test_accounts_migration.py
tests/integration/db/test_migration_lifecycle.py
tests/integration/db/test_release_notes_migration.py
tests/integration/db/test_schema_invariant_inventory.py
tests/integration/p02_journey/journey.py
tests/support/expected_facts.json
web/FRONTEND_LOCK.json
web/openapi/openapi.json
web/src/app/bff/v1/[...path]/route.ts
web/src/shared/api/authorization.ts
web/src/shared/api/generated/client.gen.ts
web/src/shared/api/generated/index.ts
web/src/shared/api/generated/operations.gen.ts
web/src/shared/api/generated/types.gen.ts
```

## 2. Checks

- The required `pin_sweep.py reseal-surface migration table --check` exited 0
  before editing and after reseal.
- `.venv/bin/python -m pytest tests/contract/api_v1 tests/contract/domain_p02 -q`:
  **318 passed**. The served FastAPI document conforms to the contract.
- Real-service PostgreSQL/API/auth/composition tests on the isolated `gate-w52s`
  instance (`56790`, `60390`, `60391`): migration/head/invariant group **67
  passed**, additional table/head group **16 passed**, role/router/composition
  group **85 passed**, release route group **2 passed**, auth standing/revocation
  group **26 passed**. After the cascade and downgrade tests were added, the new
  migration file alone passed **4 tests**. `make migrate` applied `0016` on a
  clean isolated database.
- `npm --prefix web run api:verify`: OK at 37 operations; web contract suite:
  **121 passed**; frontend lock guard: **8 passed**; web typecheck and lint:
  both exit 0; Python compilation and `git diff --check`: exit 0.
- The exact full `.venv/bin/python -m pytest tests/contract -q` was run on the
  clean commit: **664 passed, 70 failed, 126 errors, 452 subtests passed**. It is
  not green. The historical CP-00 candidate/final-state suites demand the
  2026-09-01 candidate's byte-identical contracts and unpublished checkpoint
  tag/evidence; 126 setup errors come from a CP-00 test copying `.git` as a
  directory although this isolated Git worktree has a `.git` file. Several
  bootstrap-validation tests import `jsonschema` from the runtime `.venv`,
  where only the governance interpreter carries it. These are outside the
  SEAL grant. No full gate or `GATE OK` is claimed; those remain D-137–D-140.

## 3. Contracts and migration

`contracts/api/v1/openapi.json` and its byte-identical web mirror add six
schemas: `ProductVersion`, `ReleaseNoteKind`, `ReleaseNoteItem`, `ReleaseEntry`,
`ReleaseList`, `MarkReleaseNotesReadRequest`. The generated TypeScript client,
expected facts and `FRONTEND_LOCK.json` were resealed. `contract_version`
remains `1.0.0-draft.1`; the domain candidate stays revision 9 with 29
identities and 23 error codes.

Migration `0016_release_notes` is the sole Alembic head. It creates `release`
with an immutable unique version and C-collated sort key,
`release_revision` with append-only authored revisions and canonical-content
hash storage, and `account_release_mark` with a cascading account FK. Triggers
reject release/revision UPDATE/DELETE, make lower/equal marks no-ops, and allow
the account purge cascade. An empty `0016` can downgrade to `0015`; a
populated one refuses and requires database restore.

## 4. Risks and known limits

The Stage-B adapter deliberately answers 503 for authorized release requests.
Stage C must supply `VERSION`, build ID, loader, storage projection, unknown/future
`read_through` validation, `whats_new` rules and the UI before the new operations
return release data. The migration stores JSONB content as an object; the loader's
shape and canonical SemVer validation are Stage-C obligations. This branch has no release verdict and
is not a deployable product-version feature by itself.

## 5. Integrator instruction

Review the exact diff on `agent/w52-seal-01`, including the narrow integrator
grant correction below. Re-run the pin sweep and the focused checks on the merge
candidate. Merge SEAL before issuing Stage-C grants; re-sweep Stage C/C2 on that
tree. The executor has no `origin/dev`, `origin/main`, tag or deployment
authority. Development publication, if separately granted, is to `origin/dev`;
`origin/main` still requires the owner's direct exact-candidate instruction.

## 6. Forbidden-hotspot proof

The changed-path inventory above contains no root dependency/lock file, global
style, domain version/error catalog, earlier migration, `VERSION`,
`release-notes/**`, release context implementation, release UI or origin ref.
`docs/program/tasks/W52-SEAL-01.md` is the exclusive integrator's grant
correction: the first contract test identified a live operation-count comment
in `web/src/shared/api/authorization.ts` outside the original grant. The
amended grant names that one path for its count sentence only; its sole code
diff is `thirty-four` to `thirty-seven` in that comment. The executor made no
other change outside the granted paths. No checkpoint or tag was created.
