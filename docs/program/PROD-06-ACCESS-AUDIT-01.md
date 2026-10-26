# PROD-06-ACCESS-AUDIT-01 — report

Task file: `docs/program/tasks/PROD-06-ACCESS-AUDIT-01.md`. Base `bfcb8a97`, branch `agent/prod-06-access-audit-01`.

## What was built

Six event types, appended to `audit_event` on the caller's own session (so they commit and roll back with the change), by a writer local to the `access` context, `src/auditmanager/access/audit.py`:

| Event type | Written by | Payload |
| --- | --- | --- |
| `access.sign_in_succeeded` | `UserRepository.authenticate`, after the counters are cleared | `subject_uid`, `source=api`, `default_credential` |
| `access.sign_in_blocked` | `UserRepository._note_a_failed_sign_in`, only when the attempt set `sign_in_blocked_until` | `subject_uid`, `source=api`, `failures` |
| `access.role_granted` | `RegistrationRepository.approve` (per role), `AccountRepository.set_roles` (per gained role), `AccountRepository.grant_role` (the host command) | `subject_uid`, `role`, `source` (`api` or `host_cli`), `actor_uid` unless the host command |
| `access.role_revoked` | `AccountRepository.set_roles` (per lost role) | `subject_uid`, `actor_uid`, `role`, `source=api` |
| `access.password_changed` | `UserRepository.change_password` | `subject_uid`, `actor_uid` (= subject), `source=api` |
| `access.password_reset` | `AccountRepository.reset_password` | `subject_uid`, `actor_uid`, `source=api` |

Aggregate type `Account`, aggregate id the account's `usr_` id, for all six. The product purge keeps the family (`access.` in `KEEP_EVENT_PREFIXES`).

How the payload is kept clean, three independent guards: a per-type allow-list of keys (`PAYLOAD_KEYS`), a closed rule per value (a `usr_` id parses, a role is in the vocabulary, `source` is one of two words, a count is a positive integer, the flag is a boolean), and typed entry points that take arguments rather than a mapping. No migration, contract or composition-root change: `audit_event` has no closed registry of event types (P-03, P-04 of the task file).

## Files changed

- new: `src/auditmanager/access/audit.py`, `tests/unit/access/test_access_audit_payloads.py`, `tests/integration/access/test_access_audit.py`, `docs/program/tasks/PROD-06-ACCESS-AUDIT-01.md`, this report
- edited: `src/auditmanager/access/{repository,accounts,registrations,grant,public}.py`, `scripts/recovery/product_purge.py` (the keep-prefix tuple and the two prose lines about it), `tests/integration/recovery/test_product_purge.py`

## Where `ADR-0023` section 4 is ambiguous, and what was chosen

1. **Which failed attempt is "a failed attempt starts a cooling-off period on a known account".** The password change's proof of the current password (`W53C-IDENTITY-01`, C-10) moves the same per-account brake as a sign-in, so it can start the cooling-off too. Chosen: the event is written in `_note_a_failed_sign_in`, the one place the brake is set, so both callers are covered and nothing else is; `source` is `api` for both. An attempt on a blocked account, below the allowance, on an unknown login or on a login that could not be stored writes nothing.
2. **`failures`.** The value of `failed_sign_ins` on the row that tripped the brake (5 with the current allowance).
3. **`default_credential`.** The row's `is_default_credential` as read after the password matched: true for the seeded account and for an administrator's temporary password, false after a change.
4. **`source` of a grant.** `AccountRepository.grant_role` already carries who is asking in `granted_by`: an administrator's id, or `None` for "the operator's command" (its docstring since `W49`). Chosen: `None` means `host_cli` and omits `actor_uid`; an id means `api`. The only other caller that passes `None` is `scripts/recovery/synthetic_drill_seed.py` (a host script on a synthetic stand), which therefore journals `host_cli` grants; its code is unchanged. A new caller is not forced to say where it comes from; if that matters, make `source` a required keyword in a later change.
5. **Registration approval.** Approval itself is not journalled (the ADR). The roles it grants are: one `access.role_granted` per role, aggregate the new account, `actor_uid` the approving administrator, written before the request is decided in the same transaction. The account's creation has no event.
6. **`role_revoked` carries `source`** as the table lists it, always `api` (the only removal is `set_roles`, which needs an administrator).
7. **The correlation id.** The ADR says `audit_event.correlation_id` carries the request's id. The id is a `ContextVar` in `src/auditmanager/api/routers/correlation.py`; `api` imports nothing from `access` and `access` may not import `api`, so the only bridge is the composition root. Delivered: the access side of the seam (`bind_correlation_id`, `reset_correlation_id`, `correlation_scope`, re-exported from `access.public`; the column carries the bound id, `NULL` otherwise; an id the column's CHECK would refuse is refused at bind time). **Not delivered:** the call that binds it (see the integration notes). Until then every API-written event has `correlation_id` `NULL`, and the host command's always does.
8. **Cost of "journal the accepted password".** `authenticate` had no write on the success path of a clean account (`_CLEAR_ONE` has a predicate for that reason); it now inserts one `audit_event` row per accepted sign-in. This is what the ADR asks and "retention: forever" accepts, but the table now grows with the number of sign-ins.

## Mutation table

Each mutation was applied by a script (`git checkout --` restored the file after every run; the tree was clean after each), then the audit tests (`tests/unit/access` plus `tests/integration/access/test_access_audit.py`, 112 tests, green before) were run; M10 and M10b ran `test_product_purge.py`.

| # | Mutation (applied in place, reverted by `git checkout --`) | Red | Which tests went red | Green after revert |
| --- | --- | --- | --- | --- |
| M1 | authenticate: `record_sign_in_succeeded` deleted | 4 (4 failed, 108 passed,  in 17.34s) | TestSignIn (accepted password, default flag), the served-API walk, the secrets scan (the walk is incomplete) | yes (tree clean: true) |
| M2 | `_note_a_failed_sign_in`: `record_sign_in_blocked` deleted | 4 (4 failed, 108 passed,  in 16.79s) | TestSignIn (cooling-off once per period; the password proof moves the same brake), the API walk | yes (tree clean: true) |
| M3 | `change_password`: `record_password_changed` deleted | 3 (3 failed, 109 passed,  in 17.21s) | TestPasswords (change appends one event), the API walk | yes (tree clean: true) |
| M4 | `reset_password`: `record_password_reset` deleted | 3 (3 failed, 109 passed,  in 16.49s) | TestPasswords (reset names both), the API walk | yes (tree clean: true) |
| M5 | `grant_role`: `record_role_granted` deleted (the host command's path) | 4 (4 failed, 108 passed,  in 15.43s) | TestTheHostCommand (subprocess and function), TestRoles host-style grant, the failing-event test | yes (tree clean: true) |
| M6a | `set_roles`: the granted loop deleted | 1 (1 failed, 111 passed,  in 16.92s) | TestRoles administrator's set | yes (tree clean: true) |
| M6b | `set_roles`: the revoked loop deleted | 3 (3 failed, 109 passed,  in 16.73s) | TestRoles administrator's set, the API walk (`updateUser`) | yes (tree clean: true) |
| M7 | `approve`: `record_role_granted` deleted (registration approval) | 4 (4 failed, 108 passed,  in 16.08s) | TestRoles approval, the approval-failure test, the API walk | yes (tree clean: true) |
| M8 | emit outside the transaction: the INSERT goes through the engine's own connection | 2 (2 failed, 110 passed,  in 16.43s) | rolled-back change leaves neither the change nor its event; accepted password not visible before the commit | yes (tree clean: true) |
| M12 | a failed event write swallowed (savepoint plus `except: pass`) | 2 (2 failed, 110 passed,  in 16.95s) | a change cannot commit when its event cannot be written (grant, approval) | yes (tree clean: true) |
| M9a | an IP address (the test's forwarded address) put into a `password_changed` payload (allow-list widened, rule added) | 4 (4 failed, 108 passed,  in 16.20s) | the stored-rows scan (`forwarded address appears in a stored access.* row`), the allow-list unit tests | yes (tree clean: true) |
| M9d | the stored password digest put into a `password_changed` payload | 3 (3 failed, 109 passed,  in 17.13s) | the stored-rows scan, the exact-payload test, the allowed-keys unit test | yes (tree clean: true) |
| M9b | the identity value rule neutered (any string passes as `subject_uid`) | 4 (4 failed, 108 passed,  in 16.32s) | value-rule unit tests (a login, a token-shaped string, a list, a mapping) | yes (tree clean: true) |
| M9c | value rule neutered and the login stored as the subject | 7 (7 failed, 105 passed,  in 14.61s) | the stored-rows scan plus the value-rule unit tests | yes (tree clean: true) |
| M11 | the per-type key allow-list check deleted | 54 (54 failed, 58 passed,  in 16.73s) | every `a key outside the allow-list is refused` case (54 red) | yes (tree clean: true) |
| M11b | the required-key check deleted | 6 (6 failed, 106 passed,  in 17.09s) | every `a required key cannot be left out` case (6 red) | yes (tree clean: true) |
| M13 | every failed attempt journalled, not only the one that starts a cooling-off | 6 (6 failed, 106 passed,  in 16.42s) | TestSignIn (below the allowance writes nothing; once per period), the served-API refusal test, the scan walk | yes (tree clean: true) |
| M14 | the bound correlation id ignored | 1 (1 failed, 111 passed,  in 16.83s) | the correlation seam test | yes (tree clean: true) |
| M15 | the host command's grant labelled `api` | 2 (2 failed, 110 passed,  in 16.46s) | TestRoles host-style grant, TestTheHostCommand | yes (tree clean: true) |
| M10 | `access.` removed from `KEEP_EVENT_PREFIXES` | 42 (42 failed, 24 passed in 31.47s) | test_product_purge.py: 42 red (the tool refuses the seeded access events as unclassified and the keep digests differ) | yes (tree clean: true) |
| M10b | the same, the three early tests alone | 3 (3 failed in 5.51s) | `test_the_access_journal_is_kept_by_a_product_purge`, `test_every_event_type_and_command_type_the_source_writes_is_classified`, `test_the_purge_removes_every_product_row_and_object_and_keeps_the_rest_byte_for_byte` | yes (tree clean: true) |

Not constructible: a **token** in a payload. Tokens are minted by `api.security` after the repository returns; the access context never holds one. The scan lists the three tokens the served walk was handed and fails on any of them appearing; the value rules (M9b: a token-shaped string under `subject_uid` is refused) are what keep one out.

## Modified tests: what each asserted before and after

Only `tests/integration/recovery/test_product_purge.py` existed before; no other existing test file was edited. Two of its tests changed; two were added.

- `test_a_dry_run_prints_the_classification_with_exact_counts_and_changes_nothing`. Before: the dry run prints `audit_event  (delete 24 rows, keep 3 rows)`. After: the same line with `keep 7 rows`, and the test now also asserts, with its own digest, that the stand holds exactly 3 `norm_custody.*` rows and 4 `access.*` rows. The delete count is unchanged (24); the keep count grew by the four access events the stand's seeds journal (three role grants in `synthetic_drill_seed`, one password change in `purge_seed`). The assertion is stronger (the 7 is decomposed), not looser.
- `test_the_purge_removes_every_product_row_and_object_and_keeps_the_rest_byte_for_byte`. Before: the whole `audit_event` table after the purge equals the digest of the `norm_custody.*` rows taken before, and that digest has 3 rows. After: the whole table after the purge equals the digest of the `norm_custody.*` plus `access.*` rows taken before (the test's own predicate, not the tool's), 7 rows; and the custody digest (3 rows) and the access digest (4 rows) are each equal before and after. "Nothing but the keep rows is left" is kept.
- added `test_the_access_journal_is_kept_by_a_product_purge` (no database): the prefix is in the tuple; every one of the six types starts with a keep prefix and no product prefix; the prefix reaches the keep predicate and the delete predicate is its negation.
- added `test_a_purge_keeps_each_of_the_six_access_event_types` (database): one event of each type is written by the real writer next to a product event; after the full purge the access rows are byte-for-byte the same and the product event is gone.

## Commands run, with counts

Environment: the lane `.env` copied from the integration worktree (untracked), `.venv` symlinked, own isolated databases only, one pytest at a time, no `make`, no docker, no `npm`.

All on the final tree (`.env` exported, `PYTHONPATH=src:$BS`, `-c pyproject.toml --rootdir=. -q -p no:cacheprovider`):

| Command (the path after `pytest`) | Result |
| --- | --- |
| `tests/unit/access` (new directory) | 88 passed in 0.24 s |
| `tests/integration/access` | 270 passed in 50.41 s (246 on the base, plus the 24 of `test_access_audit.py`) |
| `tests/integration/recovery/test_product_purge.py` | 66 passed in 46.57 s (64 on the base, plus 2 added) |
| `tests/integration/recovery/test_product_purge_script.py` | 7 passed in 36.75 s |
| `tests/integration/recovery/test_product_purge_run_group.py` | 5 passed in 4.24 s |
| `tests/integration/recovery/test_synthetic_drill_seed.py` | 5 passed in 10.49 s |
| `tests/integration/recovery/test_product_purge_executor_events.py` (**not edited**) | 2 failed, 1 passed in 6.19 s; with the one-line fix of integration note 1 applied to a scratch edit: 3 passed in 5.97 s |
| `tests/integration/auth`, `tests/integration/db/test_app_user_repository.py`, `test_accounts_operator_commands.py`, `test_accounts_migration.py` (neighbours that call the changed methods) | 215 passed in 99.90 s |
| `tests/integration/api/test_user_management.py`, `test_registration_flow.py`, `test_authorization.py`, `test_role_register.py`, `tests/integration/api/qa_w49` (the served operations) | 160 passed in 177.74 s |
| `tests/contract/architecture`, `tests/integration/norms/search/test_norms_roles_window.py`, `tests/integration/composition/test_edge_credential_gate.py`, `test_real_client_address_at_the_edge.py` | 95 passed in 52.87 s |
| mutation runs (table above) | each red as listed, each green after the revert |
| docs guards and `git diff --check` | see the line below |

`tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree: 105 passed in 21.17 s. The governance one-liner of the task template on `docs/program/tasks/PROD-06-ACCESS-AUDIT-01.md` prints `[]`. `git diff --check`: exit 0.

Not run, by the lane's rules: the full gate, the whole `tests/integration`, the web suites. The pre-existing red or green state of the rest of the repository was not measured.

## Integration notes

1. **Two tests outside this lane's paths go red until one line changes.** `tests/integration/recovery/test_product_purge_executor_events.py` defines `KEPT = "starts_with(event_type, 'norm_custody.') OR starts_with(event_type, 'executor.')"` and asserts that nothing but those rows is left (`test_the_purge_keeps_the_executor_and_custody_events_and_deletes_the_run_event`) and a dry-run count (`test_a_dry_run_counts_the_executor_event_as_a_row_that_stays`). The stand's seeds now journal four kept `access.*` rows, so both fail (measured: `2 failed, 1 passed`). Adding `OR starts_with(event_type, 'access.')` to `KEPT` makes the file `3 passed` (measured with the line applied to a scratch edit and reverted; the file is untouched on this branch). It was not edited here because it is not in the lane's allowed paths; apply it in the merge, or hand it to the owner of the recovery tests.
2. **The correlation binding belongs to the composition root.** The one place that opens every adapter's transaction is `_SessionHolder._write` in `src/auditmanager/bootstrap/adapters.py`; wrapping its `work(session)` in `with correlation_scope(current_correlation_id()):` (`correlation_scope` from `auditmanager.access.public`, `current_correlation_id` from `auditmanager.api.routers.correlation`, which the root already may import) ties every API-written event to the server log. It was not done here: `bootstrap/**` is a forbidden hotspot of this lane. It needs the composition-root owner of the wave and a test that a served request's `X-Correlation-Id` appears in the stored event; the access side of that test already exists (`TestTheCorrelationSeam`).
3. **`copy_record.py` / `copy-serve.sh`** compute the stand fingerprint over every `audit_event` row that is not `norm_custody.*`. A sign-in on the stand during an import window now changes that fingerprint, where it did not before (it wrote no `audit_event`). The procedure quiesces `web`, `api` and `worker` for the window, so a correct run is unaffected; a stand someone signs in to between the attest and the import will refuse as drifted. Not changed here (outside the paths).
4. **`PROD-07`** is the next editor of `scripts/recovery/product_purge.py` and depends on this task: merge this first.
5. The new event-type literals are written as `event_type="access...."` at their call sites on purpose: `test_every_event_type_and_command_type_the_source_writes_is_classified` scans `src/` for exactly that shape, so a seventh `access.*` type added later without a purge classification fails there, not on the stand.

## Known limits

- The correlation id is `NULL` on every event until item 2 above is done.
- `access.sign_in_succeeded` is one row per accepted sign-in with no retention bound (the ADR's choice: forever).
- A failed sign-in that starts nothing, and an attempt on an unknown login, are not journalled (the ADR's choice); the per-account counters and the edge limits are their only record.
- The events say what the repository did. A sign-in is recorded when the password is accepted; if the credential cannot be signed afterwards the event stays (the ADR defines it as "`issueToken` accepts a password").
- The host-command test runs `.venv/bin/python -m auditmanager.access.grant` as a subprocess through the sibling suite's `run_foundation_command`, which resolves the tree from the test file; under `make mutation-copy` it may run the pristine tree (the sibling `test_revocation.py` documents the trap). The in-process `run_grant` test beside it covers that case.
- The ADR's commitment 5 is phrased "a test per code path (API, registration approval, host command) that deletes the emission and goes red": the table above is that evidence, by hand-applied mutations, not by a harness in the suite.

## Forbidden paths: untouched

`git diff --name-only bfcb8a97` (this branch against its base, working tree included) lists exactly these twelve paths, all inside the allowed set:

- `docs/program/PROD-06-ACCESS-AUDIT-01.md`
- `docs/program/tasks/PROD-06-ACCESS-AUDIT-01.md`
- `scripts/recovery/product_purge.py`
- `src/auditmanager/access/accounts.py`
- `src/auditmanager/access/audit.py`
- `src/auditmanager/access/grant.py`
- `src/auditmanager/access/public.py`
- `src/auditmanager/access/registrations.py`
- `src/auditmanager/access/repository.py`
- `tests/integration/access/test_access_audit.py`
- `tests/integration/recovery/test_product_purge.py`
- `tests/unit/access/test_access_audit_payloads.py`

Two commands, both printing nothing:

- `git diff --name-only bfcb8a97 | grep -v -E '^(src/auditmanager/access/|scripts/recovery/product_purge\.py$|tests/unit/access/|tests/integration/access/|tests/integration/recovery/test_product_purge\.py$|docs/program/PROD-06-ACCESS-AUDIT-01\.md$|docs/program/tasks/PROD-06-ACCESS-AUDIT-01\.md$)'`
- `git diff --name-only bfcb8a97 -- contracts db infra src/auditmanager/api src/auditmanager/bootstrap web Makefile pyproject.toml uv.lock DEBT_REGISTER.md docs/program/CURRENT_STATE.md docs/program/PRODUCTION-READINESS-PLAN-01.md docs/program/OWNER_RULINGS_2026-09-17.md docs/architecture/adr`

The migration head, the contract set, the composition root, the root dependency and lock files, the register, the plan, the rulings and the ADRs are untouched. In `product_purge.py` only the keep-prefix tuple and the two prose lines about it changed; every `# >>> guard` / `# <<< guard` marker is as on the base.
