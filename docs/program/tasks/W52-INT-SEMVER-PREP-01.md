# Task W52-INT-SEMVER-PREP-01 — define canonical release precedence

task_id: W52-INT-SEMVER-PREP-01

## Outcome

The future releases context can reject a noncanonical product version and
produce a bytewise sortable key whose order follows SemVer 2.0 precedence,
including prereleases and multi-digit core components.

## Depends on

- `W52-INT-GATE-PC01-ENV-01` — completed on `origin/dev` at
  `b91138c6a4942959e5287df07193ea4d485b5776`.

## Frozen inputs

- Exact development base `b91138c6a4942959e5287df07193ea4d485b5776`.
- Domain candidate revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `docs/program/dispatch/W52-PLAN.md` §3.1 and §3.3, read from the planning-owned
  `plan/roadmap-to-beta` worktree. This is pure code preparation for
  `W52-RELEASES-API`, not its Stage C completion or a W52 freeze.
- Owner's code-first direction: basic tests and lint; QA/live and full gate
  remain D-139/D-140. The pending W52 owner confirmations do not change SemVer
  precedence or authorize a release.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W52 calls for a canonical SemVer parser and sort key, and no releases
  context exists yet on the development base.

### P-01 — planned function and absent context

- captured_at: 2026-10-08
- command: `git ls-tree -r --name-only HEAD src/auditmanager | rg '/releases/' || true; rg -n 'canonical SemVer 2.0|sort_key.*orders canonical SemVer|SemVer .sort_key. function' /root/projects/PDF-Analysis/.local/worktrees/plan-roadmap-to-beta/docs/program/dispatch/W52-PLAN.md; git rev-parse HEAD`
- captured_output:
  ```text
  49:- **`VERSION`** (root, one line, canonical SemVer 2.0, no build metadata) is the only source of
  110:- `release(pk, version UNIQUE, sort_key, is_archive)` — `sort_key` orders canonical SemVer
  408:SemVer `sort_key` function, the `build_id` function (§3.1), repository, loader (§3.3),
  b91138c6a4942959e5287df07193ea4d485b5776
  ```
- interpretation: the planning text assigns the parser/order to the releases
  context; the committed base has no releases path.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/releases/__init__.py` (new)
- `src/auditmanager/releases/versioning.py` (new)
- `src/auditmanager/releases/public.py` (new)
- `tests/integration/releases/test_version_order.py` (new)
- `docs/program/tasks/W52-INT-SEMVER-PREP-01.md`
- `docs/program/W52-INT-SEMVER-PREP-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`

## Forbidden hotspots

Everything else, especially `VERSION`, release-note data/schema, API contracts,
migration head, root dependency/lock files, composition root, global styles,
deployment files and `origin/main`.

## Non-goals

No release table, loader, API operation, build id, release note, VERSION file,
contract reseal, temporary stand, full gate, QA, tag or deployment.

## Deliverables

- One strict SemVer 2.0 parser/order function exposed through `releases.public`.
- Tests covering the SemVer precedence example, numeric width, numeric versus
  nonnumeric prerelease identifiers, and invalid noncanonical forms.
- A handoff noting the required bytewise database collation for this text key.

## Required tests

- `.venv/bin/pytest -q tests/integration/releases/test_version_order.py`
- Programme governance/prose tests, frontend lint, Python compilation and
  `git diff --check`.
- Full database sorting and `make gate` remain with W52 seal/validation debt.

## Integration contract

`canonical_semver_sort_key(version)` returns an ASCII text key that compares
correctly with bytewise/C collation for canonical SemVer without build metadata,
or raises `ValueError`. The later migration must use bytewise/C collation for its
`sort_key` column and the loader must call this public function. The integrator
publishes a fast-forward to `origin/dev` after focused checks and exact
remote-ref review.

## Failure/idempotency/security cases

- Reject whitespace, leading zero numeric components, empty identifiers,
  Unicode, prefixes and build metadata; do not silently normalize them.
- Input is authored release metadata, never an account-controlled route value.
- Equal versions give equal keys; no external state is read or changed.

## Rollback / feature flag

Revert this integration commit to remove the unused releases helper. No runtime
feature flag is needed before the releases context is wired.

## Handoff

- Changed files, checks/results, contracts, risks, integration instruction
  and forbidden-hotspot proof are in `docs/program/W52-INT-SEMVER-PREP-01.md`.
