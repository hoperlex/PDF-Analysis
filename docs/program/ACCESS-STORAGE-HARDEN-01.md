# ACCESS-STORAGE-HARDEN-01 — hand-back report

- Task: close or narrow `D-146`, `D-147`, `D-158` and `D-176` (`docs/program/DEBT_REGISTER.md`).
- Branch `agent/access-storage-harden-01`, base `origin/dev` `3a90f5b9` (migration head `0028`).
- Light acceptance (`AGENTS.md` section 8). No contract, migration, web, dependency, composition-root
  or register file was touched. The debt register is the integrator's: the rows below are proposals.

## 1. Outcome per debt

| Debt | State after this lane | Where |
|---|---|---|
| `D-146` | **Closed in code already** (`W54-CUSTODY-01`, `20c8f911`: per-blob advisory lock plus `ON CONFLICT (blob_id) DO NOTHING`, then a re-read). The register row is stale. This lane adds the proof that was missing for the lock. | `storage/blob_repository.py` (unchanged), `tests/integration/ingest/test_blob_concurrent_transitions.py` |
| `D-147` | **Closed.** One queue lock, taken first by submit, approval, profile completion and restore; the last two also refuse a login a pending request holds. | `access/queue_lock.py`, `registrations.py`, `accounts.py` |
| `D-158` | **Closed in code.** A fail-fast bulkhead of 4 concurrent searches per process, refusing the rest at the search entry as the typed `dependency_unavailable` (`dependency: norms_search_capacity`). | `norms/search/capacity.py`, `norms/search/service.py` |
| `D-176` | **Header half closed. Revocation half built here and wired afterwards** by `API-FOLLOWUPS-01` (section 4): the three lines in `api/app.py` this lane could not edit. | `api/routers/multipart.py`, `api/security.py`, `api/app.py` |

## 2. What was found

- **`D-146`.** The existing two-declarer test passes with the advisory lock removed, because the
  `INSERT ... ON CONFLICT` itself waits on the first writer's row. The lock is needed for the
  transitions after the row exists: two runs that both read `temporary` (or `verifying`) and then
  `UPDATE ... WHERE state = <what they read>` give the loser zero rows and
  `state_transition_not_allowed`. Two new tests arrange exactly that on a real PostgreSQL.
- **`D-147`.** The defect needs a submit to pass "no active account" before an approval commits and
  "no pending request" after it. Profile completion and restore could make the same pair with no
  race at all (a pending request for an e-mail the account then takes). A latent test defect sat
  beside it: `qa_w49/test_qa_w49_queue_cap.py` held the lock key as the decimal `1380272977`, which
  is `0x52454B51`, not the queue's `0x52454751` (`1380271953`), so its hold took a lock nothing
  waits on and the race was never forced. It now imports `QUEUE_LOCK_KEY` and fails when submit's lock
  is removed.
- **`D-158`.** Fail-fast, not a wait: a waiting search is a parked worker thread the API's other
  synchronous routes need, and `searchNorms` already declares `503 dependency_unavailable`. No new
  error code, no contract change. `Retry-After` cannot be set from the norms layer (the upload gate
  sets it in a middleware); noted as a possible follow-up.
- **`D-176`.** Starlette's `Headers` returns the first of a repeated header; the door returned the
  last, for `Authorization` and `Content-Type`. `Content-Length` is unchanged (servers refuse a
  conflicting pair before the application sees it).

## 3. Design decisions

- **Lock order.** The queue lock is always taken before any row lock this context takes; no path
  takes it after one. Reject takes only the request row, so approve-vs-reject cannot cycle.
- **Restore** is outside the debt's two named writers but makes the same pair, so it takes the same
  lock and check. `create_user` (the seed/CLI path) is deliberately left permissive: an existing test
  relies on it creating an account while a request is pending.
- **Cap of 4 of 10.** A constant, not a setting (a setting is an environment variable and a change
  to `bootstrap/settings.py`). A unit test fails if the pool shrinks or the cap grows past half of it.
- **Revocation memory** (`RevocationNotices`): per-application, not module state. Clones of one
  migrated template share the seeded account's `user_uid` and epoch, so process-wide state would
  carry one database's revocation into another's. The seam notes a `(user_uid, token_epoch)` pair
  when the standing refuses it (no account, archived, or an epoch **above** the credential's); the
  door refuses that pair afterwards with no read. An epoch **below** the credential's is not noted
  (a restored database, not a revocation). It is a negative cache only: the seam still reads the row
  for every request the door admits.

## 4. The revocation memory is wired (`API-FOLLOWUPS-01`, `D-176`)

This lane built `RevocationNotices` and could not wire it: the wiring is in `api/app.py`, which it
did not own. `API-FOLLOWUPS-01` made the change this section used to ask the integrator for. In
`_assemble`, one `notices = RevocationNotices()` is created per assembled application and passed to
both builders:

```python
notices = RevocationNotices()
... build_authorization_dependency(environ, standings=getattr(router, "credentials", None), notices=notices)
... verify_credential=build_credential_precheck(environ, notices=notices),
```

The first upload under a revoked credential still has its body read (the door cannot know); every
later one under the same credential is refused before its slot and body, with no database read. The
proof is `tests/integration/api/test_upload_door_revocation_is_wired.py`, which drives the assembled
application over real accounts (archived, credential epoch raised, row deleted) and asserts the body
is never asked for, the account port is not called and no SQL statement runs on the later attempts;
that an unrevoked account is unaffected; that a later generation of the same account is not caught
by the old entry; and that two applications in one process do not share the memory.

Options if the owner wants the first attempt closed as well, with cost:

1. **Event-fed set.** Archive, role change and reset publish after-commit notices. Cost: wiring through
   the composition root; and `python -m auditmanager.access.revoke` runs in another process, so an
   in-process feed never sees the operator's revocation.
2. **One primary-key read of the account at the door** (not database-free). Uploads are rare and
   the read follows a verified signature, so an unauthenticated caller cannot trigger it. Cost: the
   door becomes async-over-sync, and `standings` must be passed to the middleware (composition root).
3. **Shorter `TOKEN_LIFETIME_SECONDS`.** Cost: the web tier must renew credentials; a web change.

## 5. Checks (all on this lane's stack, one pytest process at a time)

New tests: `tests/integration/access/test_login_queue_lock.py` (7), `tests/integration/ingest/test_blob_concurrent_transitions.py` (2),
`tests/unit/norms/test_search_capacity.py` (13), `tests/integration/norms/search/test_search_bulkhead.py` (2),
`tests/integration/api/test_upload_front_door_credentials.py` (21).

Every guard was shown failing under a mutation (single textual replacement, then restored):

| Mutation | Result |
|---|---|
| approval without the queue lock | `test_an_approval_cannot_interleave...` fails |
| profile completion without the lock / without the pending check | race test / `...refused_while_a_pending_request_holds_the_email` fail |
| restore without the lock / without the pending check | race test / `...restoring_an_archived_account_is_refused...` fail |
| submit without the lock (queue-cap race, corrected key) | `201, 201` instead of `201, 409` |
| blob `INSERT` without `ON CONFLICT` and no per-blob lock (the pre-`W54` code) | 4 tests fail |
| per-blob lock alone made a no-op | the two new transition tests fail (the old tests stayed green) |
| `search()` without the slot / cap raised to the pool size | unit and integration tests fail; the control shows the 11th connection timing out |
| door reads the last header again | 6 tests fail |
| precheck ignoring the memory / seam never noting / seam noting a future epoch | 2 / 4 / 1 tests fail |

## 6. Known limitations

- The bulkhead and the revocation memory are per process, as the pool is. The freeze states one API
  process per stand.
- The restore refusal reuses `login_taken`; the web message for it says an active account holds the login,
  which is slightly off when the holder is a pending request.
- Skipped: the full gate, the e2e suites, the stand.
