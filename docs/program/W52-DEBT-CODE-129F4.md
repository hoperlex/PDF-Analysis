# W52-DEBT-CODE-129F4 — executor handoff

Task: `docs/program/tasks/W52-DEBT-CODE-129F4.md`. Exact code base:
`30bd27cbaa86ed2446227c4b7be56eb949286702`; expanded dispatch commit `a4a13f0`.
This repairs D-129 Y F-4 only.

The unused `AccountRepository.account_standing` management query, its SQL statement,
port declaration and access-side `AccountStanding` type/export are removed. Management
tests now assert against `get_account`, the read `CredentialAdapter.standing_of`
actually calls. The separate API `AccountStanding` and adapter are unchanged.

Changed files: `src/auditmanager/access/accounts.py`, `models.py`, `ports.py`,
`public.py`, `tests/integration/access/test_account_management.py`,
`tests/integration/access/test_roles.py`, and this report. The repository scan found
no production call to the removed method or access-side type.

Basic checks: 53 access/auth tests collected, changed Python files compiled,
frontend lint and `git diff --check` passed. PostgreSQL test execution was deferred
under D-139; the full gate remains D-140. The existing served-seam tests in
`test_the_standing_is_the_accounts_row.py` remain the behavioral check for the
unchanged adapter, to run in the validation wave.

No wire contract, migration, dependency/lock, router, composition root or global
style changed. The internal access port and public Python export lose an unused
member; untracked external importers of `access.public.AccountStanding` would need
the API-side type. Integrator may merge this clean branch to `origin/dev` after exact
ancestry and basic checks. Revert the code commit to roll back; no flag.
