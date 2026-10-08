# Task W52-INT-129REVOKE-01 — remove stale no-roles claim

task_id: W52-INT-129REVOKE-01

## Outcome

The operator revoke command's module docstring states why the command remains
host-only under the current role-aware API, without claiming the system has no
roles or unused `permission_denied`.

## Depends on

- `W52-INT-PROSE-134136` — published at
  `661756d8f39ab239ea5223ab35ce6a62d8953c08`.

## Frozen inputs

- Exact base `661756d8f39ab239ea5223ab35ce6a62d8953c08`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-129 `W49-FIX` residual in `docs/program/DEBT_REGISTER.md`, item 6 of
  `docs/program/W49-FIX.md`; current `api/security.py` role register.
- Owner direction 2026-10-08: basic tests/lint only; QA, stand and full gate
  deferred D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the module docstring still describes the pre-W49 no-role model.

### P-01 — exact base and contradictory claims

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n 'this system has no roles|OPERATION_ROLES: Final' src/auditmanager/access/revoke.py src/auditmanager/api/security.py`
- captured_output:
  ```text
  661756d8f39ab239ea5223ab35ce6a62d8953c08
  src/auditmanager/access/revoke.py:11:it, and this system has no roles: ``permission_denied`` is in the catalog precisely because
  src/auditmanager/api/security.py:304:OPERATION_ROLES: Final[Mapping[str, frozenset[str]]] = MappingProxyType(
  ```
- interpretation: the current API has role policy and uses typed permission
  refusals; the operator command itself remains separate from that surface.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W49-FIX.md` (immutable)
- addendum_path: `docs/program/W52-INT-129REVOKE-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/access/revoke.py` — module docstring only
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/W52-INT-129REVOKE-01.md`
- `docs/program/W52-INT-129REVOKE-01.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependencies/locks,
executable revocation code, composition root and global styles.

## Non-goals

No new API operation, role policy change, D-129 closure, QA, stand, full gate,
release, tag or `origin/main` publication.

## Deliverables

Correct the docstring, narrow D-129 and record checks/limits.

## Required tests

Python compilation, governance/prose tests, frontend lint and
`git diff --check`; no database or full gate.

## Integration contract

Only prose changes. Publish to `origin/dev` after exact remote-ref and
fast-forward verification.

## Failure/idempotency/security cases

Do not imply that an `admin` role alone authorizes bulk credential revocation
over HTTP. The command remains host-only until an explicit contract grants it.

## Rollback / feature flag

Revert this docs commit. No feature flag because no behavior changes.

## Handoff

- changed files, commands/results, contracts, risks, integration notes and
  forbidden-hotspot proof.
