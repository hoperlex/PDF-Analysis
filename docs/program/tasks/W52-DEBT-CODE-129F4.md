# Task W52-DEBT-CODE-129F4 — remove the unused standing read

task_id: W52-DEBT-CODE-129F4

## Outcome

The access management port no longer offers a second `account_standing` query that the
served credential seam never calls. Management tests use `get_account`; the credential
adapter's one-statement standing read remains intact.

## Depends on

- `W52-INT-129F3-01` — published at
  `30bd27cbaa86ed2446227c4b7be56eb949286702`.

## Frozen inputs

- Exact base `30bd27cbaa86ed2446227c4b7be56eb949286702`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-129 Y F-4 in `reviews/W49-JUDGE-Y.md` identifies `account_standing` as test-only.
- Owner direction 2026-10-08: proceed without approval; only basic tests and lint;
  QA, stand and full gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: only test callers use the management standing method.

### P-01 — exact base and calls

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n 'account_standing\(' src/auditmanager tests/integration/access`
- captured_output:
  ```text
  30bd27cbaa86ed2446227c4b7be56eb949286702
  tests/integration/access/test_roles.py:74:        assert accounts.account_standing(session, uid).roles == frozenset({"admin"})
  tests/integration/access/test_account_management.py:75:        standing = accounts.account_standing(session, _seed(session))
  tests/integration/access/test_account_management.py:86:        standing = accounts.account_standing(session, uid)
  tests/integration/access/test_account_management.py:97:        standing = accounts.account_standing(session, uid)
  tests/integration/access/test_account_management.py:104:        assert accounts.account_standing(session, uid) is None
  tests/integration/access/test_account_management.py:116:            accounts.account_standing(session, uid)
  tests/integration/access/test_account_management.py:132:                accounts.account_standing(fresh, uid)
  src/auditmanager/access/accounts.py:335:    def account_standing(self, session: Session, user_uid: str) -> AccountStanding | None:
  src/auditmanager/access/ports.py:175:    def account_standing(self, session: Session, user_uid: str) -> AccountStanding | None:
  ```
- interpretation: the code method is not called by production; `CredentialAdapter.standing_of`
  uses `get_account`, independently covered by `test_the_standing_is_the_accounts_row.py`.

### P-02 — access-side standing type

- captured_at: 2026-10-08
- command: `rg -n 'AccountStanding' src/auditmanager/access/{accounts,models,ports,public}.py`
- captured_output:
  ```text
  src/auditmanager/access/public.py:30:    AccountStanding,
  src/auditmanager/access/public.py:74:    "AccountStanding",
  src/auditmanager/access/ports.py:56:    AccountStanding,
  src/auditmanager/access/ports.py:175:    def account_standing(self, session: Session, user_uid: str) -> AccountStanding | None:
  src/auditmanager/access/models.py:79:    "AccountStanding",
  src/auditmanager/access/models.py:499:class AccountStanding:
  src/auditmanager/access/models.py:502:    `W49-PLAN.md` §3.2. ``W49-SEAL-01`` widens ``api.security.AccountStanding`` and the
  src/auditmanager/access/accounts.py:44:    AccountStanding,
  src/auditmanager/access/accounts.py:335:    def account_standing(self, session: Session, user_uid: str) -> AccountStanding | None:
  src/auditmanager/access/accounts.py:346:        return AccountStanding(
  ```
- interpretation: removing the unused method also makes this type dead; the API's
  separate `api.security.AccountStanding` remains in use.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/access/accounts.py`
- `src/auditmanager/access/models.py`
- `src/auditmanager/access/ports.py`
- `src/auditmanager/access/public.py`
- `tests/integration/access/test_account_management.py`
- `tests/integration/access/test_roles.py`
- `docs/program/W52-DEBT-CODE-129F4.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependencies/locks,
`bootstrap/adapters.py`, routers, composition root and global styles.

## Non-goals

No change to `CredentialAdapter.standing_of`, authentication policy, role semantics,
API contracts, W52 freeze, QA, stand, full gate, release, tag or `origin/main`.

## Deliverables

- Remove `_SELECT_STANDING`, the management method, its port declaration and the
  now-unused access-side `AccountStanding` value/export. The API seam's distinct
  `api.security.AccountStanding` remains owned by that context.
- Keep the management assertions against the actual `get_account` result, including
  archived/purged and unknown-role cases; the served seam keeps its existing test.

## Required tests

- Python compilation, focused pytest collection of changed database test files,
  frontend lint and `git diff --check`; database execution stays D-139.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths. The
integrator may publish this internal-code removal to `origin/dev` after exact remote
ref and fast-forward verification. The management port loses an unused member.

## Failure/idempotency/security cases

No production caller can depend on the removed method. Unknown role rows must still
raise on `get_account`; archived and purged rows retain their distinct answers.

## Rollback / feature flag

Revert the code commit. No runtime feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
