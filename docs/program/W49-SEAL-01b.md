# W49-SEAL-01b — the seam: three registers, the role map, the widened standing

**Task:** `docs/program/tasks/W49-SEAL-01.md` (part b). **Base:** stacked on this branch's
01a commit `e86bfbe`. **Plan:** `W49-PLAN.md` §3.2, §4 `W49-SEAL-01` 01b.

## 1. What 01b delivers

**`src/auditmanager/api/security.py`** — four written registers, every operation named, no
defaults:

| Register | Value |
| --- | --- |
| `UNAUTHENTICATED_OPERATIONS` | `issueToken`, `submitRegistration`, `readRegistrationStatus` |
| `OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES` | `issueToken`, `changePassword`, `getMe` |
| `OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES` | `getMe`, `updateMyProfile`, `changePassword` |
| `OPERATION_ROLES` (any-of; empty = any active complete account) | 13 product reads and the account's own 3: `∅`; `createProject`, `uploadDocument`, `startRun`, `appendDecision`, `exportRunCsv`: `{expert}`; the 10 management operations: `{admin}` — 31 keys = 34 − 3 open |
| `ROLES_OF_A_ROUTE_WITHOUT_AN_OPERATION` | `∅` — the four documentation routes, which declare no `operationId` |

The evaluation order of §3.2, in `require_authorization`: open register → signature and
expiry → **standing** (no account, **archived**, or stale epoch: `authentication_required`) →
**default credential** (`required_capability: password_changed`) → **incomplete profile**
(`profile_completed`) → **roles** (`role:expert` / `role:admin`, via `role_capability`). A
guarded `operationId` absent from `OPERATION_ROLES` is `permission_denied` with no detail for
every role set: closed by default.

**`AccountStanding` widened** with `archived`, `profile_complete`, `roles`, `login`,
`display_label`, all required; the `AccountStandings` protocol is unchanged (one method). The
seam's vocabulary (`ROLE_EXPERT`, `ROLE_ADMIN`) is its own; the adapter translates by an
explicit table (`_SEAM_ROLE_OF`) that turns an unknown role into `internal_error` rather than
dropping it.

**The subject is published with the row's login and display label**, not the credential's
copies. This is beyond the plan's list and is recorded as a decision for the integrator to
confirm (question 1 of the hand-back): without it, an account that completes its profile
keeps recording decisions under its legacy login for up to an hour (the label is minted into
the credential), and an incomplete account whose login is an e-mail longer than 128
characters would, after completing, make `appendDecision` fail on `author_label`'s bound —
the case `W49-PLAN.md` §3.1 says the registers make impossible "by construction". The
credential format (`am2`) does not change; its `name` claim is still minted and required.

**`src/auditmanager/bootstrap/adapters.py`** — `CredentialAdapter` takes `accounts=` (the
access boundary's `AccountRepository`) and `standing_of` reads `get_account` — one statement:
the public columns and the role set — instead of the sign-in half's two-column read.
`AccountRepository.account_standing` (built by ACCESS-01b for this) carries no login or label,
which the decision above needs; `get_account` is equally one statement. **`composition.py`**
wires `accounts=AccountAccessRepository()` from `auditmanager.access.public`.

**Ports and docs.** `CredentialPort.standing_of`'s docstring; the seam's module, `Subject` and
`require_authorization` docstrings state the registers and the order; `auth.py`'s comments no
longer deny a role model.

## 2. Tests

* `tests/integration/api/test_role_register.py` (new): the literal pin of all four registers
  (written from `R-60`'s groups, never read back); totality (`OPERATION_ROLES` keys = served
  operations − open); **the sweep — every guarded operation × role set {∅, expert, admin,
  expert+admin} × {complete, incomplete} × {changed, default}: the served answer equals an
  independent restatement of §3.2** (16 parametrised cases × 31 operations); archived →
  `401` everywhere; the open operations read no standing; a role refusal's whole detail; the
  row's label on the subject; an unregistered operation refused to everyone.
* `tests/integration/api/test_authorization.py`: `GUARDED` gains the 12 guarded new
  operations (31), `OPEN` lists the three; the open-surface sweep now sends `{}` to every
  operation so an admitted operation answers its own `422`, distinguishable from the seam's
  `401` (the old sweep could not tell the exchange's own `401` from the seam's); the subject
  readers are `auth.py`, `decisions.py`, `me.py`, `registrations.py`, `users.py`; the
  default-credential register gains `getMe` and the sweep skips the open operations.
* `tests/integration/auth/test_the_standing_is_the_accounts_row.py` (new): the shipped
  adapter over real rows — a legacy account is incomplete and roleless; completion and roles
  reach the standing with the row's login and name form; an archive by another account
  reaches it with its epoch; no account is `None`; an unknown role is a fault.
* `tests/integration/api/driver.py`: the suite account is an e-mail account with a complete
  profile (`api-suite@suite.invalid`, label `Стендова А. И.`); `SuiteCredentialAdapter`
  carries every standing field as a mutable attribute (default role set `{expert}`);
  `SuiteAccountAdapter` and `SuiteRegistrationAdapter` stand in for the two new ports and
  refuse only with `not_found`/`conflict`, never `403`; the probe route declares no
  `operationId`. `conftest.py` wires the two stand-ins.
* `tests/integration/auth/*`: three wirings pass `accounts=`; the open-register literal is the
  three operations. `test_every_port_implementation_is_whole.py` knows the two new ports.

| Command (tree: the working tree committed as 01b) | Result |
| --- | --- |
| `.venv/bin/python -m pytest tests/integration/api/test_authorization.py tests/integration/api/test_role_register.py -q` | `59 passed` (36 + 23) |
| `.venv/bin/python -m pytest tests/integration/auth -q` | `118 passed` (113 + 5 new) |

### Mutations

Copy: `make mutation-copy MUT=/root/w49seal-788b07cb-mut` (`MUTATION-COPY OK
/root/w49seal-788b07cb-mut/src/auditmanager/__init__.py`; `PYTHONPATH=src` resolves
`auditmanager.api.security` and `auditmanager.bootstrap.adapters` under the copy). Unmutated
baseline over the three files: `64 passed`. One mutation at a time, `PYTHONDONTWRITEBYTECODE=1`,
every `__pycache__` removed before each, the file restored after; `diff -r` of the copy's
`src/` against the worktree empty afterwards.

| id | mutation | red | summary |
| --- | --- | --- | --- |
| Mb1 | `createProject` → `∅` in `OPERATION_ROLES` | `test_the_registers_are_the_ruled_ones`, sweep `[no-role-*]`, `[admin-*]` | 3 failed, 20 passed |
| Mb2 | `purgeUser` line deleted | literal pin, totality, sweep ×4 | 6 failed, 17 passed |
| Mb3 | role check never refuses | sweep ×3, `test_a_role_refusal_names_the_role_and_nothing_else` | 4 failed, 19 passed |
| Mb4 | incomplete-profile check moved before the default-credential check | sweep `[*-False-True]` ×4 | 4 failed, 19 passed |
| Mb5 | incomplete-profile check never refuses | sweep `[*-False-False]` ×4 | 4 failed, 19 passed |
| Mb6 | `standing.archived` dropped from the standing check | `test_an_archived_account_is_refused_as_unauthenticated_everywhere` | 1 failed, 22 passed |
| Mb7 | `submitRegistration` removed from `UNAUTHENTICATED_OPERATIONS` | `test_every_operation_but_the_register_is_behind_the_seam`, `test_the_served_document_declares_the_scheme_the_contract_declares`, `test_a_default_credential_reaches_exactly_the_register` | 3 failed, 33 passed |
| Mb7b | the seam opens only `issueToken` whatever the register says | `test_the_open_surface_is_exactly_the_register` | 1 failed, 35 passed |
| Mb8 | subject published with the credential's label | `test_the_subject_carries_the_label_the_row_holds_now` | 1 failed, 22 passed |
| Mb9 | adapter reports `roles=frozenset()` | `test_completion_and_roles_reach_the_standing` | 1 failed, 4 passed |
| Mb10 | adapter reports `archived=False` | `test_an_archive_reaches_the_standing_with_its_epoch` | 1 failed, 4 passed |
| Mb11 | an unregistered operation gets `∅` instead of a refusal | `test_an_operation_the_register_does_not_name_is_refused_to_everyone` | 1 failed, 22 passed |
| Mb12 | the role table passes an unknown role through | `test_a_role_the_seam_does_not_know_is_a_fault_and_never_dropped` | 1 failed, 4 passed |

## 3. Contracts

None changed in 01b.

## 4. Risks and limits

* The subject's label and login come from the row (above) — confirm or reverse.
* The seam's role vocabulary is spelled twice (here and in `auditmanager.access.models`),
  bridged by the adapter's table; a role added on one side fails closed (`internal_error`)
  until the table moves.
* The API suite's stand-in ports answer only what the seam sweep needs; the account and
  registration operations are driven against real rows in 01c.

## 5. Integrator

Intermediate commit; the integration suites that drive product operations with the shared
suite helper are expected red until 01c.

## 6. Forbidden hotspots

Inside the amended `allowed_paths`; the full list is in `W49-SEAL-01c.md`.
