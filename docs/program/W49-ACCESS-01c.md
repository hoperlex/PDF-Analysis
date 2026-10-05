# W49-ACCESS-01c — the role set and the registration lifecycle

**Task:** `docs/program/tasks/W49-ACCESS-01.md` (part c). **Base:** `dff1922`; stacked on this
branch's own `18444a5` (01a) and `dc30e28` (01b). **Plan:** `W49-PLAN.md` §3.2–§3.3, §4 `01c`.

## What 01c delivers

- **Roles** (`access/accounts.py`): `revoke_role` and `set_roles` beside 01a's `grant_role`.
  Not a self-demotion (any loss of one's own role, even beside a gain → `permission_denied`,
  `invariant=self_action`); the last active administrator never loses `admin`
  (`conflict`, `invariant=last_admin`), decided under the administrator-set lock; every
  change raises `token_epoch` **once**; a call that changes nothing bumps nothing. An empty
  role set is allowed (`R-60`: such an account reaches what every complete account reaches).
- **Registration** (`access/registrations.py`, new): `RegistrationRepository` with
  - `submit` — e-mail (`normalize_email`), names, and `R-48`'s policy with the applicant's
    names and e-mail local part added to the contextual blocklist
    (`enforce_password_policy(..., context=...)`); then, under one transaction-scoped
    advisory lock: `conflict` `login_taken` (an active account holds it — an archived one
    does not), `request_pending`, `queue_full` (100 pending); the password stored hashed;
    the partial unique index is the backstop for `request_pending`;
  - `approve` — one transaction: the request locked `FOR UPDATE`; at least one known role
    (`validation_failed` on `roles`); `state_transition_not_allowed` against
    `registration_request` when not pending; `login_taken` when an active account took the
    login meanwhile (the request stays pending); the account created **with the request's
    digest**, its names and `profile_completed_at = now()`, `is_default_credential = false`;
    the roles granted by the administrator; the request decided with its password nulled;
  - `reject` — a reason stripped, 1–256 characters, no control character but a line feed;
    the password nulled;
  - `get`, `list_requests(status=…)`, `pending_total`;
  - `read_status` — **exactly one PBKDF2 derivation on every path** (unusable login, no
    request, braked, decided, wrong password, right password — asserted by counting
    derivations); failed reads are counted on the request's own throttle columns with the
    account brake's rules and a braked request is refused without consulting the password;
    a proven read clears the brake.
- **A failed exchange counts on the request** (`access/repository.py`): when no active
  account holds the login, `authenticate` still spends its one derivation and now also
  records the attempt on that login's request (no extra derivation — asserted equal with and
  without a request).
- **Ports and public surface:** `RegistrationRepository` port; `set_roles` on the account
  port; `auditmanager.access.public` exports the registration types and constants
  (`MAX_PENDING_REQUESTS`, `MAX_REJECTION_REASON_LENGTH`).
- **Tests:** `tests/integration/access/test_roles.py`, `test_registrations.py` (new); the race
  probe in `test_account_management.py` fixed (see below).

## The status read answers `pending` only — the open question this lane cannot close

§3.3 says the decision UPDATE **nulls the four password columns**, and the guard trigger
refuses any later write to them; §3.3 and `R-56` also say the status read answers
`rejected` with the reason **for a pair that matches a request**. After a rejection there is
no password left to match the pair against, so the two sentences cannot both hold. This
lane implements the reading that discloses nothing without proof: a decided request
answers the generic `None` (one derivation, attempt counted), and
`test_a_decided_request_is_not_disclosed_without_a_password_to_prove` pins it; mutation
M01c-17 shows the alternative (answering by login) is observable. The alternatives —
keep a verifier until the applicant has read the rejection, or answer by login alone — are
a product decision and are listed as the first open question in the hand-back. The change
is confined to the `digest is None` branch of `read_status`.

## 1. Changed files (01c)

```text
docs/program/W49-ACCESS-01c.md                             (this report)
src/auditmanager/access/accounts.py
src/auditmanager/access/policy.py
src/auditmanager/access/ports.py
src/auditmanager/access/public.py
src/auditmanager/access/registrations.py                   (new)
src/auditmanager/access/repository.py
tests/integration/access/test_account_management.py        (race probe only)
tests/integration/access/test_registrations.py             (new)
tests/integration/access/test_roles.py                     (new)
```

## 2. Checks run

| Command (tree: the working tree committed as 01c, before this report) | Result |
| --- | --- |
| `.venv/bin/python -m pytest tests/integration/access tests/integration/db tests/contract/architecture/test_alr05_boundaries.py tests/contract/api_v1/test_doc_prose_facts.py -q` | `504 passed in 361.80s`, exit 0 |
| `.venv/bin/python -m pytest tests/integration/access -q -k concurrent`, five consecutive runs | `3 passed` ×5 |
| `git diff --check` | clean |
| `make gate` at the 01c commit | **recorded in the hand-back against that SHA** — a gate is tied to the SHA it measured, and recording its lines here would need a commit after it |

### A defect in this branch's own 01b test, found and fixed here

The race tests poll `pg_stat_activity` to prove the second transaction waited. 01b's version
polled through **one connection in one transaction**, and `pg_stat_activity` is a
per-transaction snapshot (`stats_fetch_consistency = cache`): if the first poll ran before
the second session blocked, every later poll repeated that answer. It passed in 01b by
timing; the same probe in the new approval race failed (`the second approval never waited
on the request's lock`) while a standalone probe showed the session waiting on
`transactionid`. All three race tests now open a fresh connection per poll; five
consecutive runs green.

### Mutations

Copy rebuilt at the 01c tree (`make mutation-copy MUT=/root/w49access-788b07cb-mut FULL=1`),
unmutated baseline `./.venv/bin/pytest tests/integration/access tests/integration/db/test_accounts_migration.py -q`
→ `262 passed`. One mutation at a time, `PYTHONDONTWRITEBYTECODE=1`, caches cleared, restored.

| id | mutation | red test | evidence |
| --- | --- | --- | --- |
| M01c-1 | `revoke_role` without the self rule | `test_an_account_cannot_demote_itself` | `DID NOT RAISE AccountInvariantViolation` |
| M01c-2 | `revoke_role` without the last-admin rule | `test_the_last_active_administrator_cannot_lose_admin` | `DID NOT RAISE AccountInvariantViolation` |
| M01c-3 | `revoke_role` locks only its target | `test_two_concurrent_revocations_of_the_last_two_administrators_leave_one` | `both administrators lost the role` / `assert 0 == 1` |
| M01c-4 | `revoke_role` without the epoch bump | `test_a_revocation_bumps_and_the_standing_sees_it_at_once` | `assert 3 == (3 + 1)` |
| M01c-5 | `set_roles` lets an account demote itself | `test_a_self_loss_is_refused_even_beside_a_gain` | `DID NOT RAISE AccountInvariantViolation` |
| M01c-6 | approval without `FOR UPDATE` | `test_two_concurrent_approvals_one_wins_the_other_is_a_transition` | `{'second': conflict} == {'second': state_transition_not_allowed}` |
| M01c-7 | approval with no role allowed | `test_approval_grants_at_least_one_known_role[none]` | `DID NOT RAISE DomainError` |
| M01c-8 | approval keeps the request's password | `test_approval_creates_the_account_from_the_request_in_one_transaction` | the guard trigger: `a decision must null the request's password columns` |
| M01c-9 | no queue cap | `test_the_queue_holds_100_and_refuses_the_101st` | `DID NOT RAISE DomainError` |
| M01c-10 | submit ignores an active account's login | `test_a_login_an_active_account_holds_is_login_taken` | `DID NOT RAISE DomainError` |
| M01c-11 | status read with no request spends nothing | `test_every_status_read_path_costs_exactly_one_derivation` | cost map differs (`no-request: 0`) |
| M01c-12 | status read ignores the brake | `test_failed_reads_are_braked_and_the_brake_ignores_the_right_password` | `RegistrationStatus(status='pending', …) is None` |
| M01c-13 | a failed status read is not counted | same | `assert (0 == 5)` |
| M01c-14 | a failed exchange is not counted on the request | `test_a_failed_exchange_counts_against_the_request` | `assert 0 == 1` |
| M01c-15 | the applicant's facts leave the blocklist | `test_the_password_policy_includes_the_applicants_own_facts[local-part]` | `DID NOT RAISE DomainError` (1 failed, 4 passed under `-x`) |
| M01c-16 | a reason may carry control characters | `…control_characters_is_refused[tab]` | `DID NOT RAISE DomainError` |
| M01c-17 | a decided request discloses its status by login | `test_a_decided_request_is_not_disclosed_without_a_password_to_prove` | `RegistrationStatus(status='rejected', …) is None` fails |

**One survivor on the first pass:** M01c-15 survived (`7 passed`) because every context
password in the first version of the test was shorter than 8 characters, so the length
floor refused it before the blocklist was consulted. The test now uses facts of 9–29
characters and asserts the refusal's sentence; against it M01c-15 is red as shown.

## 3. Contracts

None changed. The detail values used (`conflict_reason` ∈ {`login_taken`, `request_pending`,
`queue_full`, `account_referenced`}; `machine` ∈ {`app_user`, `registration_request`}) are the
plan's and become contract with `W49-SEAL-01a`.

## 4. Risks and known limitations

- **Status read of a decided request** — see above; open question.
- `login_taken` and `request_pending` disclose a login's existence to a submitter (accepted
  and registered by the plan).
- Submissions serialise on one advisory lock for the length of the caller's transaction —
  cheap at this volume (queue capped at 100); the router must keep that transaction short.
- `reject` refuses tabs and other control characters but allows a line feed; the plan says
  only "1–256 characters".
- No bulk rejection and no retention of decided requests (registered debts); the guard
  trigger refuses DELETE outright.

## 5. Instructions to the integrator

- `W49-SEAL-01c` routes `submitRegistration`/`readRegistrationStatus`/`approveRegistration`/
  `rejectRegistration`/`listRegistrations` through `RegistrationRepository` and maps
  `DomainError.detail_fields` as given; `AccountInvariantViolation.invariant` discriminates the
  two §3.2 invariants. The router must commit `read_status` and failed-`authenticate`
  transactions, or the request brake does not survive (as for the account brake today).
- Before W51 renders a `rejected` notice, rule on the open question above.

## 6. Forbidden hotspots

`git diff --name-only dff1922..<01c>` stays inside the task's `allowed_paths` (listed in the
hand-back); no `contracts/**`, `src/auditmanager/{api,bootstrap,decisions}/**`, `web/**`, lock
file, ref, tag or push.
