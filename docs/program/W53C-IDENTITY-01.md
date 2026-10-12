# W53C-IDENTITY-01 — report

Task: `docs/program/tasks/W53C-IDENTITY-01.md` at `04de50c`. Branch `agent/w53c-identity`,
worktree `.local/worktrees/w53c-identity`, base `04de50c` on `integration/w53-close`.
Implementation commit `6a928f5`; this report is the commit after it. Private lane
`gate-w53c-identity` (PostgreSQL `57030`, S3 `60630/60631`) was started once, used for the
runs below one pytest at a time, and removed.

| Finding | Status |
|---|---|
| C-07 (`R-80`) | Reproduced; fixed. |
| C-08 | Reproduced; fixed (roles first). |
| C-09 | Reproduced; fixed. |
| C-10 | Reproduced; fixed. Amends a deliberate `W40-LIMIT` choice (see Risks 1). |
| C-11 | Reproduced; `revoke_role` deleted. |

## 1. Changed files

Source:

- `src/auditmanager/api/security.py` — C-07. New `_ANY_ROLE = {expert, admin}`. The 15
  product reads (`listProjects`, `listDocuments`, `getDocumentVersion`,
  `streamDocumentVersionContent`, `getVersionBlocks`, `listVersions`, `listRuns`,
  `listExecutionQueue`, `listExecutionJournal`, `getRunStatus`, `listRunFindings`,
  `getFinding`, `listDecisionHistory`, `listDecisions`, `getDashboardSummary`) now require
  `_ANY_ROLE`. The empty set (any complete account) now covers only `getMe`,
  `updateMyProfile`, `changePassword`, `markReleaseNotesRead`, `getProductVersion` and
  `listReleases`, plus the four documentation routes that have no `operationId`
  (unchanged). A refusal is the existing `permission_denied` with
  `required_capability: role:admin|expert`, the value `role_capability()` already gives
  `cancelRun`/`reauditRun`. Docstrings were updated.
- `src/auditmanager/bootstrap/adapters.py` — only `AccountAdapter.update_account`. C-08:
  `set_roles` (which locks the administrator set, then the target) now runs before
  `update_names`. C-09: the account is read back and answers `not_found`
  (`aggregate_type: User`) when it is missing or archived, including when both halves are
  absent.
- `src/auditmanager/access/repository.py` — C-10. `_SELECT_CREDENTIAL_BY_UID` also projects
  `COALESCE(sign_in_blocked_until > now(), false)`. `change_password` then works like this:
  - while the account is shut, it does not consult the password, spends a derivation,
    writes nothing and returns `None`;
  - a wrong current password, or an empty or over-long one, calls
    `_note_a_failed_sign_in`, which is the same per-account allowance that `authenticate`
    counts against.

  Module docstrings and comments were updated.
- `src/auditmanager/access/ports.py`, `src/auditmanager/access/unlock.py`,
  `src/auditmanager/access/__init__.py` — docstrings only. They describe the C-10 brake and
  the narrower "password change" route back from a lockout.
- `src/auditmanager/access/accounts.py` — C-11: `AccountRepository.revoke_role` deleted. It
  had no production caller, and it is not on the `AccountRepository` port or in
  `access.public`. The `set_roles` docstring now cites `R-80`.

Tests:

- `tests/integration/api/test_role_register.py` — the `EXPECTED_ROLES` literals for the 15
  reads are now `_ANY_ROLE`, with a comment citing `R-80`. New
  `test_a_roleless_account_reads_no_product_data`.
- `tests/integration/api/test_user_management.py` — `ARCHIVED_UPDATES["empty"] = {}` (C-09)
  and the counter-case `test_an_empty_change_on_an_active_account_answers_it_and_writes_nothing`.
- `tests/integration/access/test_account_management.py` — new two-connection
  `test_a_names_and_roles_update_locks_the_administrator_set_before_its_target` (C-08). The
  test works as follows:
  1. Another session holds the administrator-set lock.
  2. `AccountAdapter.update_account(names + roles)` runs in a thread and must wait.
  3. While it waits, a third connection must still be able to take
     `SELECT … FOR UPDATE NOWAIT` on the (non-admin) target.
- `tests/integration/auth/test_sign_in_throttle.py` — C-10:
  - `test_a_wrong_current_password_does_not_move_the_sign_in_brake` (which pinned the old,
    opposite design) and `test_a_password_change_clears_the_brake` (which changed a password
    on a shut account) are replaced by four tests:
    - `test_a_password_change_clears_a_count_that_has_not_shut_the_account`;
    - `test_a_wrong_current_password_counts_against_the_sign_in_brake` (measured at 5, as
      the allowance itself is measured);
    - `test_sign_in_and_password_change_refusals_share_one_count`;
    - `test_a_shut_account_cannot_change_its_password_and_is_not_consulted`.
  - `test_a_lockout_does_not_touch_a_credential_anybody_already_holds` now ages the row past
    the block before its `changePassword` probe. The handler now refuses while the account
    is shut, so the probe instead proves that the credential minted before the lockout
    survived it.
- `tests/integration/access/test_roles.py` — C-11: the `revoke_role` cases are rewritten
  onto `set_roles`, including the two-session last-two-administrators race. New
  `test_there_is_no_single_role_revocation`.
- `tests/integration/access/qa_w49/test_qa_w49_invariants_without_a_router.py` — C-11: the
  two `revoke_role` rows were removed. Their `set_roles` equivalents already sit beside them.

## 2. Checks

| Command | Result |
|---|---|
| `git diff --check 04de50c..HEAD` | clean |
| `.venv/bin/python -m compileall -q <13 changed .py>` | exit 0 |
| `ruff check <13 changed .py>` | No new finding (see below). |
| `make up && make migrate` (`.env` from `.env.example`, instance/DB/ports/bucket = `gate-w53c-identity`/`gate_w53c_identity`/57030/60630/60631, DATABASE_URL and S3_ENDPOINT_URL matching) | healthy; head `0017_execution_queue` |
| `pytest tests/integration/api/test_role_register.py` | 24 passed |
| `pytest tests/integration/access` | 239 passed |
| `pytest tests/integration/auth` | 121 passed, 1 failed (`test_a_lockout_does_not_touch_…`, the probe described above). After the probe fix, `pytest tests/integration/auth/test_sign_in_throttle.py`: 35 passed. |
| `pytest tests/integration/api/test_user_management.py` | 29 passed |
| `pytest tests/integration/api/test_authorization.py tests/integration/api/test_identity_rules.py tests/integration/api/qa_w49 tests/integration/api/test_release_routes.py tests/integration/api/test_registration_flow.py tests/integration/api/test_decision_authorship.py tests/integration/qa_w52` | 148 passed |

The DB-backed runs need the lane env exported (`set -a; . ./.env; set +a`). The `db`
fixtures read `DATABASE_URL` from the process environment.

**Ruff.** `.venv` has no ruff. I used a standalone ruff 0.17.0 binary from the session
scratchpad (`scratchpad/ruffx/…/ruff`). I ran it on the changed files and on their `04de50c`
copies and compared the findings per file and rule. Every finding on HEAD also exists at
base: 27 at HEAD, 37 at base. The extra base findings are `I001`, an artefact of checking the
copies outside the repository. None of my changes introduces one.

**Each new test fails without its fix.** For each check I put back one source file from base
with `git checkout 04de50c -- <file>`, ran the tests, and restored the file from `HEAD`:

- `api/security.py` → 3 failed: `test_the_registers_are_the_ruled_ones`, the
  `no-role-True-False` matrix row and `test_a_roleless_account_reads_no_product_data`.
- `bootstrap/adapters.py` → the C-08 test failed with "the update locked its target before
  the administrator set", and `…archived…[empty]` failed with `assert 200 == 404`.
- `access/repository.py` → 3 failed: `…counts_against_the_sign_in_brake`, `…share_one_count`
  (`3 == 4`) and `…shut_account_cannot_change_its_password…`.
- `access/accounts.py` → `test_there_is_no_single_role_revocation` failed.

## 3. Contracts

None changed. `contracts/**` is untouched.

The OpenAPI prose now describes the old rule. The integrator should not edit it in this
wave (frozen SHA `008a7932…`); it should be recorded as a deferred row:

- the root `info.description`, in the `W49-SEAL-01` paragraph, says "Reading product data
  needs any active account with a complete profile";
- the `W52-SEAL-01` paragraph says "All require an active complete account". That is still
  true for the release operations;
- `components.securitySchemes.bearerAuth.description` lists `role:expert` or `role:admin`
  as capability values. `role:admin|expert` already existed for `cancelRun` and
  `reauditRun`.

`docs/program/P02_SEAMS.md` ~line 715 says the same thing ("product data is read by any
active account with a complete profile"). It is outside my paths.

## 4. Risks and known limitations

1. **C-10 narrows `W40-LIMIT`'s second route back from a lockout.** A password change used
   to open a shut account. Now a shut account's `changePassword` is refused even with the
   right password until the cooling-off period (300 s) passes or the operator runs
   `access.unlock`. A change on an account that is not shut still clears the count.

   Without this refusal, counting alone brakes nothing. The note statement keeps extending
   the block, but the password would still be checked on every try, so a stolen credential
   would remain an unlimited oracle for the password it was minted under.

   The cost: an unauthenticated caller who shuts a reviewer's sign-in also blocks that
   reviewer's password change for ≤300 s. Their existing credential keeps working, because
   the lockout still does not touch `token_epoch`.

   I read the task's "same per-account brake … test the lockout" as requiring this. **If
   the owner wants the old route back, it is a ruling.**
2. **C-07 and the web/e2e side.** WEB-ID owns the screens. A role-less account now gets
   `403 role:admin|expert` on every product read. `tests/e2e/pc01/qa_w50/r66.mjs` drives a
   `none` (`roles: []`) account through the menu and `/optimisation`. It is a manual stand
   script and is not part of the gate, but its expectations may need WEB-ID's update. The
   BFF and the frontend battery were not run in this lane.
3. The C-09 refusal carries `details.aggregate_type: User`, as the adapter's other
   missing-account answers do. The access layer's names-only and roles-only refusals carry no
   detail, as before. Both are `404 not_found`.
4. The C-08 test runs on the access suite's fresh database and imports
   `auditmanager.bootstrap.adapters`. This is the same pattern `tests/integration/auth`
   already uses. It proves the lock order. It does not reproduce the deadlock itself.

## 5. Integrator instructions

- Merge `agent/w53c-identity` as is. It does not touch `ExecutionAdapter`, `RunAdapter` or
  `_run_status_view`, so it should merge cleanly with EXEC's `adapters.py` hunks. The only
  hunk in `adapters.py` is inside `AccountAdapter.update_account`.
- No test pin outside my paths should go red in the Python battery. I searched `tests/**`
  for literal copies of the role map, for `revoke_role` and for role-less product reads
  (`roles=()`, `"roles": []`, `credentials.roles = frozenset()`). The only literal register
  is `test_role_register.py`. `test_release_routes.py` and `qa_w52/test_release_access_matrix.py`
  use role-less accounts only for version/releases/release-notes, which stay open, and both
  passed. `SuiteCredentialAdapter` defaults to `expert`, so no `tests/support` or `conftest.py`
  fixture needs a role.
- Run `tests/integration/access`, `tests/integration/auth` and `tests/integration/api` on the
  integration lane with the env exported.
- Deferred rows to write (OpenAPI and P02_SEAMS prose) are listed in §3. The `R-80`/C-10
  narrowing of the route back (§4.1) belongs in the wave record.

## 6. Containment

```text
$ git diff --name-only 04de50c..HEAD
docs/program/W53C-IDENTITY-01.md
src/auditmanager/access/__init__.py
src/auditmanager/access/accounts.py
src/auditmanager/access/ports.py
src/auditmanager/access/repository.py
src/auditmanager/access/unlock.py
src/auditmanager/api/security.py
src/auditmanager/bootstrap/adapters.py
tests/integration/access/qa_w49/test_qa_w49_invariants_without_a_router.py
tests/integration/access/test_account_management.py
tests/integration/access/test_roles.py
tests/integration/api/test_role_register.py
tests/integration/api/test_user_management.py
tests/integration/auth/test_sign_in_throttle.py
$ git status --porcelain -uall
(empty)
```

Every path is inside the allowed paths: `access/**`, `api/security.py`, `AccountAdapter`
only, `tests/integration/{access,auth}/**`, the two named api test modules and this report.

Untouched: `contracts/**`, `db/migrations/**`, lock and dependency files, `Makefile`,
`tests/support/**`, every `conftest.py`, `VERSION`, `release-notes/**`, `CURRENT_STATE.md`,
`DEBT_REGISTER.md` and `web/**`.

Lane teardown:

- `make down` was run.
- `docker volume rm gate-w53c-identity-postgres-data gate-w53c-identity-s3-data` was run.
- No `gate-w53c-identity` container, network, volume or image remains.
- `.env` was deleted.
- No process was killed.
