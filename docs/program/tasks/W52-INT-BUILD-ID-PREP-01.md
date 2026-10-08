# Task W52-INT-BUILD-ID-PREP-01 — compute API build identity from content

task_id: W52-INT-BUILD-ID-PREP-01

## Outcome

The releases context can compute a stable `b`-prefixed API build identifier
from exactly the file roots W52 specifies, independent of checkout location
and working directory, with a changed included byte changing the identifier.

## Depends on

- `W52-INT-SEMVER-PREP-01` — completed on `origin/dev` at
  `7f401d19ffe71a8b8344f94d00552ad4984fc05d`.

## Frozen inputs

- Exact development base `7f401d19ffe71a8b8344f94d00552ad4984fc05d`.
- Domain candidate revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `docs/program/dispatch/W52-PLAN.md` §3.1, read from the planning-owned
  `plan/roadmap-to-beta` worktree. This is pure preparation for
  `W52-RELEASES-API`, not its Stage C completion or a W52 freeze.
- Owner's code-first direction: basic tests and lint; QA/live and full gate
  remain D-139/D-140. No temporary stand.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the plan specifies an API build hash rooted at
  `auditmanager.__file__`; the current API Dockerfile has not yet copied
  `VERSION` and `release-notes/`, so a real-tree call must wait for Stage C.

### P-01 — algorithm and missing image inputs

- captured_at: 2026-10-08
- command: `rg -n 'API .build_id. is computed|every regular file under the roots|with the root taken from|Dockerfile.api.*COPY lines only for' /root/projects/PDF-Analysis/.local/worktrees/plan-roadmap-to-beta/docs/program/dispatch/W52-PLAN.md; rg -n '^COPY (VERSION|release-notes/|uv.lock) ' infra/deploy/Dockerfile.api || true; git rev-parse HEAD; git status --short`
- captured_output:
  ```text
  57:- **API `build_id` is computed by the API process at start-up over its own files**, not stamped by
  59:  every regular file under the roots `src/`, `db/`, `contracts/`, `fixtures/recorded/`,
  64:  `auditmanager.releases.public` function, with the root taken from `auditmanager.__file__`, never
  7f401d19ffe71a8b8344f94d00552ad4984fc05d
  ```
- interpretation: the plan fixes the root and file selection; the current
  Dockerfile has no three release COPY lines, and status was empty.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/releases/build_id.py` (new)
- `src/auditmanager/releases/public.py` (one export)
- `tests/integration/releases/test_build_id.py` (new)
- `docs/program/tasks/W52-INT-BUILD-ID-PREP-01.md`
- `docs/program/W52-INT-BUILD-ID-PREP-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`

## Forbidden hotspots

Everything else, especially `VERSION`, release-note data/schema, API contracts,
migration head, root dependency/lock files, composition root, Dockerfiles,
global styles, deployment files and `origin/main`.

## Non-goals

No startup wiring, image COPY, `.dockerignore` guard, `VERSION` parsing,
contract reseal, loader, live stand, full gate, QA, tag or deployment.

## Deliverables

- One public `compute_build_id()` that derives the root from
  `auditmanager.__file__`, hashes the exact manifest lines and fails if a
  required root or file is absent.
- Pure tests for exact manifest digest, location independence, included-byte
  changes, ignored caches/extra trees and missing required roots.
- Handoff stating the Stage C image and startup integration work left open.

## Required tests

- `.venv/bin/pytest -q tests/integration/releases/test_build_id.py`
- Programme governance/prose tests, frontend lint, Python compilation and
  `git diff --check`.
- Built-image parity and the full gate remain deferred.

## Integration contract

The future composition root calls `auditmanager.releases.public.compute_build_id()`
once at application build. The future image includes every required root/file
under `/app`, and its `.dockerignore` guard proves no tracked input is omitted.
The integrator publishes a fast-forward to `origin/dev` after focused checks
and exact remote-ref review.

## Failure/idempotency/security cases

- Missing required roots or files raise `FileNotFoundError`; no fallback to
  working directory or a partial hash.
- Symlinks and bytecode caches do not enter the regular-file manifest.
- The function reads files only and does not disclose their bytes.

## Rollback / feature flag

Revert this integration commit to remove the unused helper. No runtime
feature flag is needed until startup wiring is owned by Stage C.

## Handoff

- Changed files, checks/results, contracts, risks, integration instruction
  and forbidden-hotspot proof are in `docs/program/W52-INT-BUILD-ID-PREP-01.md`.
