# W49-ACCESS-01b — names, `display_label`, the standing read, archive/restore/purge/reset, §3.2 invariants

**Task:** `docs/program/tasks/W49-ACCESS-01.md` (part b). **Base:** `dff1922`; stacked on
this branch's own 01a commit `18444a5`. **Plan:** `W49-PLAN.md` §3.1–§3.2, §4 `01b`.

## What 01b delivers

- **`access/models.py`** — `AccountStanding` (`token_epoch`, `is_default_credential`,
  `archived`, `profile_complete`, `roles`) — the row read `W49-SEAL-01` widens
  `api.security.AccountStanding` and `standing_of` with — and `Account` (record + role set).
  `UserRecord.display_label` follows `R-55`: the name form "Фамилия И. О." (≤ 66) when last
  and first names exist, else `display_name`, else the login. (The normalisation and name
  rules themselves landed in 01a because the profile command needs them; their exhaustive
  tests are here.)
- **`access/accounts.py`** — `AccountRepository` gains:
  - `account_standing` — one statement (asserted: exactly one SELECT), roles via
    `array_agg` over a LEFT JOIN, an unknown stored role is a raise (never dropped);
    answers `archived=True` for an archived account and `None` for a purged one;
  - `get_account`, `list_accounts(include_archived=…)`;
  - `update_my_profile` (completion in one UPDATE for an incomplete profile; names only for a
    complete one, whose login is fixed — `validation_failed` on `login`), `update_names`
    (administrator; never completes, never touches the login);
  - `archive_account`, `restore_account`, `purge_account`, `reset_password`, and
    `references_to` (the register's RESTRICT entries naming an account);
  - `AccountInvariantViolation` with `invariant ∈ {self_action, last_admin}` —
    `self_action` → `permission_denied`, `last_admin` → `conflict`, **no detail key** (the
    plan's closed `conflict_reason` set has no member for either; see open questions).
- **Invariants of §3.2, at repository level:** no self-archive, self-purge, self-reset
  (self-demote is 01c); the last active administrator cannot be archived; every change of
  rights (archive, restore, reset) raises `token_epoch` in the same UPDATE. Purge refuses a
  non-archived account against the `app_user` machine (`active → purged`, details
  `machine/current_state/requested_state`) and a referenced one with `conflict`,
  `conflict_reason: account_referenced`, checking the register first and keeping the
  database's RESTRICT keys as the backstop (a missed reference still maps to the same
  answer). Restore answers `login_taken` when an active account took the login meanwhile.
- **Concurrency:** every operation that can remove an administrator locks all active
  administrators (`FOR UPDATE OF u`, `user_uid` order) before the target, and recounts in a
  fresh statement after the lock — proven with two real sessions racing (below).
- **`access/repository.py`** (from 01a) — every login-addressed statement reaches only active
  accounts and `credential_standing` gives an archived account none; 01b proves both.
- **`access/ports.py`** — a second port, `AccountRepository`, separate from the credential
  port on purpose (the credential adapter must not be able to archive anybody).
- **`access/public.py`** — exports the above for `W49-SEAL-01` (ALR-05 guard green).
- **Tests:** `tests/integration/access/conftest.py` (re-exports the `db` suite's fresh-database
  fixtures), `test_account_names.py` (pure: e-mail, names, label precedence, roles, `reg`),
  `test_account_management.py` (repository-level, no router).

## 1. Changed files (01b)

```text
docs/program/W49-ACCESS-01b.md                               (this report)
src/auditmanager/access/accounts.py
src/auditmanager/access/models.py
src/auditmanager/access/ports.py
src/auditmanager/access/public.py
tests/integration/access/conftest.py                         (new)
tests/integration/access/test_account_management.py          (new)
tests/integration/access/test_account_names.py               (new)
```

## 2. Checks run (tree: the working tree committed as 01b, before this report was added)

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest tests/integration/access -q` (the 01b required command) | `159 passed in 37.19s`, exit 0 |
| `.venv/bin/python -m pytest tests/contract/architecture/test_alr05_boundaries.py tests/integration/db/test_accounts_migration.py tests/integration/db/test_accounts_operator_commands.py tests/integration/db/test_app_user_repository.py tests/integration/db/test_reviewer_display_name.py -q` | `113 passed`, exit 0 |
| `.venv/bin/python -m pytest tests/integration/auth -q` (outside the grant; read-only check that the sign-in half still behaves) | `113 passed, 1 warning`, exit 0 |
| `git diff --check` | clean |

### Mutations

Copy rebuilt at the 01b tree: `make mutation-copy MUT=/root/w49access-788b07cb-mut FULL=1`,
`diff -r src` against the worktree empty, unmutated baseline
`./.venv/bin/pytest tests/integration/access -q` → `159 passed`. One mutation at a time,
`PYTHONDONTWRITEBYTECODE=1`, caches cleared, restored after each.

| id | mutation | red test | evidence |
| --- | --- | --- | --- |
| M01b-1 | archive without the self rule | `test_an_account_cannot_archive_itself` | `assert 'last_admin' == 'self_action'` — 1 failed |
| M01b-2 | last-admin count never refuses | `test_the_last_active_administrator_cannot_be_archived` | `DID NOT RAISE AccountInvariantViolation` — 1 failed |
| M01b-3 | no lock on the administrator set | `test_two_concurrent_archives_of_the_last_two_administrators_leave_one` | `both administrators were archived` / `assert 0 == 1` — 1 failed |
| M01b-4 | purge consults no register entry | `TestPurge::test_a_referenced_account_stays_archived[archived_by]` | `assert ()` (no reference found) — 1 failed |
| M01b-5 | purge of an active account allowed | `test_a_non_archived_account_is_refused_against_the_machine` | `DID NOT RAISE DomainError` — 1 failed |
| M01b-6 | reset without the self rule | `test_an_account_cannot_reset_itself` | `DID NOT RAISE AccountInvariantViolation` — 1 failed |
| M01b-7b | `_ACTIVE` predicate becomes `true` (login-addressed statements reach archived rows) | `test_archive_names_the_administrator_revokes_and_shuts_sign_in` | `assert UserRecord(...) is None` — 1 failed |
| M01b-8 | `credential_standing` without the archive filter | `test_archived_is_reported_and_purged_is_none` | `the credential seam's read must give an archived account no standing` — 1 failed |
| M01b-9 | `display_name` outranks the names | `test_display_label_precedence[names-win]` | `assert 'Аня' == 'Петрова А.'` — 1 failed |
| M01b-10 | mixed-script rule removed | `test_refused_names_say_why[Иванoв-…]` | `DID NOT RAISE DomainError` — 1 failed |
| M01b-11 | archive without the epoch bump | `test_archive_names_the_administrator_revokes_and_shuts_sign_in` | `assert 2 == (2 + 1)` — 1 failed |
| M01b-12 | restore without the epoch bump | `test_an_archived_login_may_be_taken_and_restore_then_answers_login_taken` | `assert 3 == (3 + 1)` — 1 failed |
| M01b-13 | standing inverts profile completeness | `test_the_seed_after_0015` | `AccountStanding(...) == AccountStanding(...)` differs — 1 failed |
| M01b-14 | a complete profile may rewrite its login | `test_a_complete_profile_changes_names_but_never_its_login` | `DID NOT RAISE DomainError` — 1 failed |

**Two survivors on the first pass, both kept in the record:**

- **M01b-3 survived the first version of the race test** (`1 passed`). That version had the
  two administrators archive *each other*; each UPDATE's foreign-key check on
  `archived_by` takes `KEY SHARE` on the other administrator's row, which the other
  transaction had locked `FOR UPDATE`, so the two serialised by accident and the
  administrator-set lock was never needed. The test was rewritten with two third-party
  actors (X archives B, Y archives A); against it M01b-3 is red as shown.
- **M01b-7 (removing `AND archived_at IS NULL` from `_SELECT_CREDENTIAL` alone) survives**
  (`1 passed`): `authenticate` re-reads the row through `_SELECT_BY_LOGIN`, which carries
  the same filter, so an archived account is still refused (and both paths still cost one
  derivation — asserted). The filter is redundant inside one method by construction; the
  honest mutation is the shared predicate, M01b-7b, which is red.

## 3. Contracts

None changed. `auditmanager.access.public` grows (an internal Python surface, not a
contract file). No error code or detail key is added: `conflict_reason` values used here
(`login_taken`, `account_referenced`) are the plan's, and the catalog reseal that admits the
key is `W49-SEAL-01a`'s.

## 4. Risks and known limitations

- **Self-action and last-admin codes are this lane's choice** (`permission_denied` and
  `conflict` with no detail) because the plan names the invariants but not their codes; the
  seal may decide otherwise — open question.
- `reset_password` does not refuse a temporary password equal to the current one (that
  would cost a verification against a password the administrator does not know); the R-48
  policy (length, login, product name, shipped default) applies. That the administrator
  knows the temporary password is the registered limitation of §3.4.
- `access.name` still exists: `tests/integration/auth/test_the_reviewer_name_is_visible.py`
  (outside this grant) imports it. `display_name` retirement is a registered debt.
- The `author_user_uid` reference case inserts a decision event with FK enforcement skipped
  in that transaction (lane superuser), as in 01a.

## 5. Instructions to the integrator

- `W49-SEAL-01b` wires `AccountRepository.account_standing` into `standing_of`; an archived
  standing and a `None` standing both answer `authentication_required`.
- `AccountInvariantViolation.invariant` is the stable discriminator for the seal's sweep and
  refusal mapping.

## 6. Forbidden hotspots

`git diff --name-only 18444a5` lists only §1's files, all under `src/auditmanager/access/**`,
`tests/integration/access/**` and this report. No contract, router, composition root,
`web/**`, lock file, ref or tag.
