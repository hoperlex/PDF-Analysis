# W49-SEAL-01c — the adapters, the author's account, the suite accounts, and the slot's close

**Task:** `docs/program/tasks/W49-SEAL-01.md` (part c of three, and the slot's hand-back).
**Base:** `7912504`; amended task file merged at `7d06e67`; stacked on 01a `e86bfbe` and 01b
`633a83a`. **Branch:** `agent/w49-seal-01`. **Plan:** `W49-PLAN.md` §3.1–§3.4, §4
`W49-SEAL-01` 01c. **Lane:** `gate-w49seal`, Postgres `56570`, S3 `60170`/`60171`.

## 1. What 01c delivers

**The account and registration operations are served over the database.** The `me`,
`registrations` and `users` routers and their ports landed in 01a, because the conformance
guard compares the served document with the contract and the declarations could not wait.
01c gives them their shipped adapters and wires them:

* `src/auditmanager/bootstrap/adapters.py`: `AccountAdapter` (`AccountPort`) and
  `RegistrationAdapter` (`RegistrationPort`) over `auditmanager.access.public`'s
  `AccountRepository` and `RegistrationRepository`. Each call uses one session.
  `auditmanager.access` raises every rule: no act on oneself, the last administrator, the
  fixed login of a complete profile, a referenced purge, the queue and the brake. The
  adapter only maps records to views. Two things live here because they belong to the
  composition root and are not rules:
  * **`approveRegistration` claims its `Idempotency-Key`** through
    `auditmanager.ingest.public.CommandRepository`, in the approval's own transaction. The
    command type is `approve_registration`; the fingerprint is the request, the sorted roles
    and the actor. An identical repeat replays the decided request. A different payload
    under the same key is `idempotency_key_reuse`. A recorded outcome whose request is gone
    is `idempotency_key_stale`. Decisions already use this mechanism in
    `LedgerDecisionAdapter`.
  * **`readRegistrationStatus` commits.** The access boundary counts a refused pair on the
    request (this is the brake) and leaves the commit to its caller. A status read that did
    not commit would answer the same `401` but lose the count. A proven pair whose request
    is not `pending` is reported as `internal_error` and never shown (`R-56` addendum).
* `src/auditmanager/bootstrap/composition.py` wires both adapters from
  `auditmanager.access.public`.
* **The author's account.**
  * `src/auditmanager/api/routers/decisions.py` passes `author_user_uid=subject.user_uid`.
    `DecisionPort.append_decision` and the shipped `DecisionAdapter` carry it.
  * `src/auditmanager/decisions/ledger.py` drops the `= None` default from `record_decision`
    and `append_decision_under_key`. The parameter stays `str | None`, because rows written
    before migration `0015` and the ledger's own suites name no account.
  * Every granted call site passes the keyword, one per call and nothing else.
    Where the suite drives the ledger directly the value is `author_user_uid=None`.
  * `test_the_ledger_declares_no_default_author` covers both parameters of both functions,
    and checks that each is keyword-only.
* **`src/auditmanager/access/**`: the three granted edits.**
  * (a) `AccountInvariantViolation` for `last_admin` carries `conflict_reason: last_admin`.
  * (b) `UserUid` and `RegistrationId` validate and mint through the shared registry's
    `usr` and `reg` types, and keep this boundary's `validation_failed`.
  * (c) `access/name.py` is deleted.
  * `access/check.py` had a hint telling an operator to run the deleted module. It now names
    `access.profile`. This is the one line that (c) would otherwise leave dangling; it is
    flagged in §4.
* **Suite accounts are complete `expert` e-mail accounts** (decision 4, option a).
  `tests/support/accounts.py::complete_expert_account` creates an account with:
  * login `<label>@suite.invalid`;
  * names `Сьютова Ева` and display label `Сьютова Е.`;
  * role `expert`;
  * its epoch re-read after the grant.

  Every suite that mints through `provisioned_credential` gets this account without a change
  of its own. The API suite's own subject is `api-suite@suite.invalid` / `Стендова А. И.`
  (from 01b).
* **Characterization records 10 and 11 are re-captured.**
  * `author_label` moves from `"w13-baseline"` to `"Сьютова Е."`; the length grows by 6.
  * The exception blocks cite `2894951`.
  * `test_the_two_author_records_moved_by_the_label_and_nothing_else` puts the old label
    back and compares the SHA-256 with the pre-seal capture read from `7912504`.
* `web/FRONTEND_LOCK.json`: `content_commit` is `e86bfbe` and `dispatch_named_commit` is
  `7912504`. 01a could not set these, because a commit cannot name itself.
* `src/auditmanager/api/routers/users.py`: the module's first line stated an operation count
  ("seven operations"), which the prose count guard reads as a surface claim. It is
  rephrased. **The guard is red at `e86bfbe` and `633a83a` for this line.** The line is
  unchanged since `e86bfbe`; this was determined by reading, not measured. The
  contract-battery figure in `W49-SEAL-01a.md` §2 (`438 passed, 2 failed`) is true of the
  tree it was measured on. That tree was the working tree, with `users.py` still untracked,
  and the guard discovers files with `git ls-files`, so it never saw the file. This report's
  figures were measured with the commit's files staged. That is the same 438/2: the two
  failures are Q1.1 and the uncommitted-tree refusal.

## 2. Tests

New:

* `tests/integration/api/test_registration_flow.py` has 18 tests. They run over real rows,
  the shipped adapters and the shipped `CredentialAdapter`, and cover:
  * submission: `request_pending`, `login_taken`, the password policy, and the schema;
  * the status read, and the single refusal for a wrong, unknown or rejected pair. These
    answers are byte-identical apart from the correlation id;
  * **the brake's count reaches the row**;
  * the listing with `pending_total`, and the seam's `role:admin`;
  * approval: a complete account with the chosen roles, and the applicant's digest moved;
  * keyed replay and key reuse;
  * the machine refusing an already-decided request;
  * `minItems` and `uniqueItems`;
  * rejection and the bound on its reason;
  * `not_found`.
* `tests/integration/api/test_user_management.py` has 17 tests:
  * `getMe` reads the row;
  * a legacy account completes its profile in one write, and the e-mail is required for it;
  * a complete profile changes its names and never its login;
  * `login_taken`;
  * the archived filter;
  * a role change revokes credentials and a name change does not;
  * no act on oneself (`403`, no detail);
  * archive, restore, and `state_transition_not_allowed` on `app_user`;
  * an archived account gets `401`;
  * purge refuses an active account and an `account_referenced` one, and deletes an archived
    unreferenced one (`204`);
  * a password reset forces a change and revokes;
  * `not_found` with `aggregate_type: User`;
  * the `last_admin` envelope.
* `tests/integration/api/identity_surface.py` is the surface both suites drive.
* `tests/integration/auth/test_the_suite_account_is_a_complete_expert.py` asks the helper for
  an account that cannot already exist. The lane is shared and long-lived, so an account
  made by an earlier run would hide a helper that had stopped granting the role or
  completing the profile.

Changed:

* The authorship suite has three complete accounts (`Петрова А.`, `Смирнов Б. И.`) and one
  incomplete account (`403 profile_completed`). It asserts the stored `author_user_uid`.
* The query surface seeds accounts and requests for the two new listings.
* The composition sweeps know the two new ports.
* The ledger suites pass the keyword.

| Command (tree: the 01c working tree before this commit) | Result |
| --- | --- |
| `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests --ignore=tests/checkpoint --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` (before the `users.py` line and the two added tests) | `6 failed, 3024 passed, 5 skipped, 298 subtests passed in 897.21s`. The failures are the four of §4 Q1, the `users.py` prose line (fixed after this run), and `test_alpha_acceptance_command` (it refuses an uncommitted checkout) |
| `.venv/bin/python -m pytest tests/contract/api_v1/test_surface_counts_in_prose.py -q` (after the fix) | `33 passed` |
| `.venv/bin/python -m pytest tests/integration/auth/test_the_suite_account_is_a_complete_expert.py tests/integration/api/test_registration_flow.py tests/integration/api/test_user_management.py -q` | `36 passed` |
| `npm --prefix web run lint && npm --prefix web run typecheck && npm --prefix web test` | exit 0; `Test Files 83 passed (83)`, `Tests 1210 passed (1210)` |
| `git diff --check` | exit 0 |
| P-01's one-liner; `sha256sum contracts/api/v1/openapi.json web/openapi/openapi.json` | `27 34 77`; both `633a58a53baf6652625b59d3db9438ae01e8c4ac8da788160882f031123f2e37` |

`make gate` runs once, at this commit, after it is made. Its lines are in the hand-back.
Expected: red on the four tests of §4 Q1 and nothing else.

### Mutations

The copy is built with `make mutation-copy MUT=/root/w49seal-788b07cb-mut FULL=1`. `FULL=1`
is needed because Ma1–Ma4 mutate `contracts/` and Ma6 mutates `db/`; without it those
directories are symlinks into this worktree. It printed `MUTATION-COPY OK
/root/w49seal-788b07cb-mut/src/auditmanager/__init__.py`. Before the mutations:

* `diff -rq -x __pycache__` of `src`, `tests`, `contracts` and `db` against the worktree is
  empty;
* the unmutated baseline over every target below is `125 passed`.

The mutations run one at a time, with `PYTHONDONTWRITEBYTECODE=1`, every `__pycache__`
removed before each, and the file restored after each. Afterwards the same `diff -rq` is
empty. The driver is `--tb=line -rf`.

* **`Ma*`** are 01a's new guards, which are contract-only. The Ma rows below give the test
  file each one drives.
* **`Mc*`** are 01c's guards. Unless the row says otherwise, they drive
  `tests/integration/api/`.

| id | mutation | red (the failing test and its message) | summary |
| --- | --- | --- | --- |
| Ma1 | `submitRegistration` declares `401` | `test_openapi_document.py::test_every_operation_can_report_401_and_403`: "submitRegistration takes no credential, so it has none to refuse and no subject to deny" | 1 failed, 50 passed |
| Ma2 | `readRegistrationStatus` declares `403` | same test: "readRegistrationStatus presents no credential, so it has no subject a 403 could deny" | 1 failed, 50 passed |
| Ma3 | `RegistrationStatusResponse.status` becomes an enum of three | `test_the_unauthenticated_operation_is_the_one_that_hands_out_a_credential`: "the status read shows an applicant `pending` and nothing else (R-56 addendum)" | 1 failed, 50 passed |
| Ma4 | `pending_total` dropped from `RegistrationRequestPage.required` | `test_growing_lists_are_cursor_paginated`: `assert {'items', 'page'} == {'items', 'pa...ending_total'}` | 1 failed, 50 passed |
| Ma5 | `EDGE_ONLY_CODES` gains the stored `not_found` | `test_contract_vocabulary.py::test_error_code_domain_equals_the_frozen_catalog`: `AssertionError: ['not_found']` | 1 failed, 22 passed |
| Ma6 | migration `0002`'s `ERROR_CODES` gains `rate_limited` | same test: `AssertionError: ['rate_limited']` | 1 failed, 22 passed |
| Mc1 | `record_decision`'s `author_user_uid` gets `= None` back | `test_decision_authorship.py::…::test_the_ledger_declares_no_default_author`: "record_decision gives `author_user_uid` the default None. …" | 1 failed, 2 passed |
| Mc2 | the same for `append_decision_under_key` | same test: "append_decision_under_key gives `author_user_uid` the default None. …" | 1 failed, 2 passed |
| Mc3 | the router passes `subject.user_uid and None`; the source still contains the string the source guard looks for | `test_two_credentials_record_two_distinguishable_authors`: `assert [None, None] == ['usr_01M2545…']` | 1 failed, 13 passed |
| Mc4 | the shipped `DecisionAdapter` passes `author_user_uid=None` | same: `assert [None, None] == ['usr_01M2545…']` | 1 failed, 13 passed |
| Mc5 | `last_admin` raised without `conflict_reason` | `test_user_management.py::test_the_last_admin_refusal_carries_its_closed_reason`: `assert {} == {'conflict_re... 'last_admin'}` | 1 failed |
| Mc6 | the helper skips the `expert` grant | `auth/test_the_suite_account_is_a_complete_expert.py`: `assert set() == {'expert'}` | 1 failed |
| Mc7 | the helper skips the profile completion | same: `assert False is True` (`profile_complete`) | 1 failed |
| Mc8 | approval never replays (`if False and isinstance(claim, CommandReplay)`) | `test_an_identical_approval_replays_and_another_payload_is_a_reused_key`: the replay answers `state_transition_not_allowed` | 1 failed, 17 passed |
| Mc9 | the approval fingerprint drops the roles | same test: the other payload replays `200` instead of `idempotency_key_reuse` | 1 failed, 17 passed |
| Mc10 | the status read uses `_read` (no commit) | `test_a_refused_pair_is_counted_on_the_request`: `assert 0 == 1` | 1 failed, 17 passed |
| Mc11 | the router answers a refused pair `pending` | `test_a_wrong_password_and_an_unknown_login_are_one_refusal` with three others: `assert 200 == 401` | 4 failed, 14 passed |
| Mc12 | the account view's roles are `()` | `test_approval_creates_a_complete_account_with_the_chosen_roles`, `test_get_me_reads_the_row_the_credential_names`, `test_a_role_change_revokes_the_account_s_credentials`: `assert [] == ['expert']` | 3 failed, 32 passed |
| Mc13 | the account view's label is the login | the approval test, and four in the management suite: `assert 'applicant-e3...suite.invalid' == 'Заявкина М. П.'` | 5 failed, 30 passed |
| Mc14 | `listUsers` always includes archived accounts | `test_listing_excludes_archived_accounts_unless_asked` | 1 failed, 16 passed |
| Mc15 | `archiveUser` passes the target as the actor | `test_archive_restore_and_the_machine` with four others: `permission_denied` "an account cannot archive itself" | 5 failed, 12 passed |
| Mc16 | one byte of record 10 outside the label (`baseline` → `baselinE`) | `characterization/…/test_the_two_author_records_moved_by_the_label_and_nothing_else`: "10-appendDecision.success moved by more than its author label" | 1 failed |

## 3. Contracts

None changed in 01c. The slot's contract changes are 01a's (`W49-SEAL-01a.md` §3).

## 4. Risks, limits and open questions

1. **Four red tests sit outside the amended grant.** None is edited. Each needs the edit
   below, by whoever owns the path:
   1. `tests/contract/domain_p02/test_seam_register.py::test_the_api_operation_table_matches_the_frozen_document`.
      The table in `docs/program/P02_SEAMS.md` §7 needs these rows (the grant covers only
      that file's count sentences):
      ```text
      | `getMe` | `GET /me` |
      | `updateMyProfile` | `PATCH /me` |
      | `submitRegistration` | `POST /registrations` |
      | `readRegistrationStatus` | `POST /registrations/status` |
      | `listRegistrations` | `GET /registrations` |
      | `approveRegistration` | `POST /registrations/{request_id}/approve` |
      | `rejectRegistration` | `POST /registrations/{request_id}/reject` |
      | `listUsers` | `GET /users` |
      | `getUser` | `GET /users/{user_uid}` |
      | `updateUser` | `PATCH /users/{user_uid}` |
      | `archiveUser` | `POST /users/{user_uid}/archive` |
      | `restoreUser` | `POST /users/{user_uid}/restore` |
      | `purgeUser` | `DELETE /users/{user_uid}` |
      | `resetUserPassword` | `POST /users/{user_uid}/password` |
      ```
      The section's rule "every write takes a required `Idempotency-Key` header" is now
      false for the account writes. The contract's own keyed-write set
      (`WRITE_OPERATIONS`, five operations) is what holds.
   2. `tests/integration/access/test_password_hashing.py::TestTheUserIdentity::test_it_does_not_register_a_prefix_in_the_frozen_contract_catalog`
      asserts the opposite of grant item (b). The proposed replacement asserts
      `IDENTITY_TYPES_BY_PREFIX["usr"] is auditmanager.shared.identity.ids.UserUid` and
      `identity_type_for_prefix("usr").entity == "User"`, and keeps
      `not issubclass(access.models.UserUid, OpaqueId)` (the boundary class wraps the
      shared one).
   3. `tests/e2e/pc01/test_acceptance.py::test_c3_the_surface_declares_no_operation_that_can_mutate_a_version`
      (the grant covers only that file's route count). It reads "no PUT/PATCH/DELETE route
      at all", and now finds `updateMyProfile`, `updateUser` and `purgeUser`. The proposed
      replacement keeps its intent: the mutating set equals exactly those three, and no
      mutating route's path contains `/versions` or `/documents`.
   4. `tests/integration/db/test_durable_analysis_effects.py::test_provider_effect_error_code_is_the_closed_catalog`
      iterates `ErrorCode`, which now has `rate_limited`, against migration `0014`'s
      `ck_provider_effect_error_code`. Decision F3 says no migration, so the proposal is to
      skip `rate_limited` as edge-only, asserting it is **absent** from the CHECK, which
      mirrors `EDGE_ONLY_CODES`. This one was not found at the stop: the stop's sweep looked
      for the catalog JSON, and this test reads the Python enum.
2. The three family schemas still pin `candidate_revision` `const: 8`
   (`error-codes.schema.json`, `identifiers.schema.json`, `state-machines.schema.json`).
   They are outside the grant, and only the excluded `test_cp00_candidate.py` reads them.
   This was already raised in `W49-SEAL-01a.md` §4.
3. **The seam publishes the row's login and display label on the subject**, not the
   credential's copies (`W49-SEAL-01b.md` §1). Confirm or reverse this.
4. The standing is read with `AccountRepository.get_account`, not `account_standing`, which
   carries no login or label. Both are one statement.
5. Approval idempotency lives in the adapter (the composition root) through
   `ingest.public.CommandRepository`, as it does for decisions, rather than in
   `auditmanager.access`. This adds a new `command_record.command_type` value,
   `approve_registration`, which has no CHECK.
6. No operation declares `429`. `rate_limited` is in the `ErrorCode` enum and is answered
   only by the edge, the way nginx's `413` already is. Declaring it would make the PC01
   render-subset guard demand a `web/src/shared/api/errors.ts` entry, which is outside the
   grant.
7. Some references to the deleted module remain outside the grant:
   * `src/auditmanager/access/profile.py`'s docstring still cites
     `:mod:auditmanager.access.name`;
   * migration `0009`'s comments name it (migrations are forbidden);
   * `docs/program/W42-SEAL.md` step 4 tells an operator to run it.

   `access/check.py`'s hint, which was the executable one, was moved under (c). Confirm that
   reading.
8. `access/check.py` still lists every account whose `display_name IS NULL` as unnamed,
   including complete profiles, which are shown under their name form. This rule is in
   `access/repository.py` and is not this slot's.
9. `tests/integration/db/test_schema_shape.py` still excludes `user_uid`, `request_id`,
   `created_user_uid` and `author_user_uid` from the prefix sweep. Out of grant; green.
10. The `Role` values are new enum vocabulary that the rendered-language guard permits as
    visible text. This is for W50/W51.
11. `last_admin` cannot be reached through the API: the actor holds `admin`, so the target is
    never the last administrator. The API suite proves the envelope mapping; the access
    suite proves the rule.

## 5. Integrator

* The gate cannot print `GATE OK` until the four edits of Q1 land. They are outside this
  slot.
* Revert the slot's commits together (`e86bfbe`, `633a83a`, this one). The reseal is atomic.
* `W49-BFF-01` consumes `getMe`, `submitRegistration` and `readRegistrationStatus` from the
  regenerated client.

## 6. Changed files and forbidden hotspots

`git diff --name-only 7912504..HEAD` at this commit lists the files below. It is measured
on the staged tree, which is this commit's tree.

```text
contracts/api/v1/README.md
contracts/api/v1/openapi.json
contracts/domain/v1/README.md
contracts/domain/v1/error-codes.json
contracts/domain/v1/error-envelope.schema.json
contracts/domain/v1/identifiers.json
contracts/domain/v1/state-machines.json
docs/program/ALPHA_ROADMAP.md
docs/program/CONTRACT_PIN_REGISTRY.md
docs/program/CURRENT_STATE.md
docs/program/P02_SEAMS.md
docs/program/W49-SEAL-01a.md
docs/program/W49-SEAL-01b.md
docs/program/W49-SEAL-01c.md
docs/program/dispatch/IDENTITY-WAVES.md
docs/program/dispatch/W49-PLAN.md
docs/program/tasks/W49-SEAL-01.md
infra/deploy/README.md
infra/deploy/proxy/nginx.conf
infra/deploy/serve.py
src/auditmanager/access/accounts.py
src/auditmanager/access/check.py
src/auditmanager/access/models.py
src/auditmanager/access/name.py
src/auditmanager/api/README.md
src/auditmanager/api/app.py
src/auditmanager/api/health.py
src/auditmanager/api/routers/__init__.py
src/auditmanager/api/routers/auth.py
src/auditmanager/api/routers/decisions.py
src/auditmanager/api/routers/declarations.py
src/auditmanager/api/routers/errors.py
src/auditmanager/api/routers/handlers.py
src/auditmanager/api/routers/me.py
src/auditmanager/api/routers/ports.py
src/auditmanager/api/routers/registrations.py
src/auditmanager/api/routers/users.py
src/auditmanager/api/schemas/accounts.py
src/auditmanager/api/schemas/models.py
src/auditmanager/api/schemas/registrations.py
src/auditmanager/api/security.py
src/auditmanager/bootstrap/adapters.py
src/auditmanager/bootstrap/composition.py
src/auditmanager/decisions/ledger.py
src/auditmanager/shared/errors/codes.py
src/auditmanager/shared/identity/ids.py
tests/characterization/w13_baseline/records/10-appendDecision.success.json
tests/characterization/w13_baseline/records/11-listDecisionHistory.success.json
tests/characterization/w13_baseline/test_response_baseline.py
tests/contract/api_v1/test_doc_prose_facts.py
tests/contract/api_v1/test_openapi_conformance.py
tests/contract/api_v1/test_surface_counts_in_prose.py
tests/contract/domain_p02/test_contract_vocabulary.py
tests/contract/domain_p02/test_identifier_catalog.py
tests/contract/domain_p02/test_openapi_document.py
tests/contract/shared_kernel/test_error_kernel.py
tests/e2e/pc01/test_acceptance.py
tests/integration/api/conftest.py
tests/integration/api/driver.py
tests/integration/api/identity_surface.py
tests/integration/api/test_authorization.py
tests/integration/api/test_database_refusals.py
tests/integration/api/test_decision_authorship.py
tests/integration/api/test_decision_journal.py
tests/integration/api/test_envelope_screen_rules.py
tests/integration/api/test_operation_surface.py
tests/integration/api/test_query_surface.py
tests/integration/api/test_registration_flow.py
tests/integration/api/test_role_register.py
tests/integration/api/test_router_and_body_rules.py
tests/integration/api/test_served_document_and_health_plane.py
tests/integration/api/test_the_documentation_routes_are_behind_the_seam.py
tests/integration/api/test_user_management.py
tests/integration/auth/test_credential_tokens.py
tests/integration/auth/test_revocation.py
tests/integration/auth/test_sign_in_throttle.py
tests/integration/auth/test_the_exchange_over_real_users.py
tests/integration/auth/test_the_reviewer_name_is_visible.py
tests/integration/auth/test_the_standing_is_the_accounts_row.py
tests/integration/auth/test_the_suite_account_is_a_complete_expert.py
tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py
tests/integration/composition/test_api_token_channel.py
tests/integration/composition/test_composition_root.py
tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py
tests/integration/composition/test_every_port_implementation_is_whole.py
tests/integration/composition/test_the_run_leaves_the_request_thread.py
tests/integration/decisions/test_decision_ledger.py
tests/integration/decisions/test_keyed_append.py
tests/integration/decisions/test_rules_are_load_bearing.py
tests/integration/exports/test_verdict_columns.py
tests/integration/p02_journey/test_journey_figures.py
tests/integration/p02_journey/test_query_surface_over_the_corpus.py
tests/integration/p02_journey/test_truncated_end_to_end.py
tests/support/accounts.py
web/FRONTEND_LOCK.json
web/openapi/openapi.json
web/src/app/bff/v1/[...path]/route.ts
web/src/entities/audit-run/model/terminal-reason.ts
web/src/shared/api/authorization.ts
web/src/shared/api/catalog-message.ts
web/src/shared/api/errors.ts
web/src/shared/api/generated/client.gen.ts
web/src/shared/api/generated/index.ts
web/src/shared/api/generated/operations.gen.ts
web/src/shared/api/generated/types.gen.ts
web/tests/contract/catalog-message.contract.test.ts
web/tests/contract/pc01-error-codes.contract.test.ts
web/tests/contract/seam-operations.contract.test.ts
web/tests/unit/api/authorization-state.test.ts
web/tests/unit/api/failure-surface.test.ts
web/tests/unit/screens/run-terminal-reason.test.ts
```

Three of these files came in through the merge `7d06e67` of `integration/w49` at `2894951`
and are the integrator's, not this slot's:

* `docs/program/dispatch/IDENTITY-WAVES.md`
* `docs/program/dispatch/W49-PLAN.md`
* `docs/program/tasks/W49-SEAL-01.md`

`docs/program/W49-SEAL-01a.md` was first written by the stop (`2fae883`).

Every other path is inside the amended `allowed_paths`. Grant notes:

* `src/auditmanager/access/check.py` is listed under (c) above.
* `src/auditmanager/access/accounts.py` is item (a).
* `src/auditmanager/access/models.py` is item (b).

The slot did not touch:

* a migration;
* a root lock;
* `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md` or `PORT_REGISTRY.md`;
* `web/src/**` beyond the named lines;
* a ref or tag;
* a push.

## 7. Addendum: the second grant (after `48099d9`)

The integrator ruled on this report's §4 at `addbe6c`, merged here as `549042c`.

* **Granted:** Q1's four edits exactly as proposed, plus (e) and (f) below.
* **Confirmed as built:** Q3 (the subject's login and label come from the row), Q4
  (`get_account`), Q5 (approval idempotency through `ingest.public.CommandRepository`), Q6
  (no `429` on any operation) and Q7 (the `check.py` hint).
* **Accepted as stated:** Q9–Q12. The remaining stale references named in Q7 are registered
  at INT-CLOSE.

### 7.1 What changed

* **(a)** `docs/program/P02_SEAMS.md` §7 changes in two places.
  * The operation table gains the fourteen rows.
  * The rule "every write takes a required `Idempotency-Key` header" is rewritten. It now
    names the keyed writes (`createProject`, `uploadDocument`, `startRun`, `appendDecision`,
    `approveRegistration`, "and no others") and says what a repeat of every other write
    does.

  The repeat outcomes are measured, not read off the code. They are measured by
  `tests/integration/api/test_user_management.py::TestARepeatWithoutAKey`, which is new and
  covers profile completion, role change, restore, purge and reset. The rejection is
  measured by `test_registration_flow.py::test_a_repeated_rejection_is_a_refused_transition`,
  also new. The outcomes already covered elsewhere are:
  * `request_pending` (`test_a_second_pending_application_for_one_login_is_request_pending`);
  * the stale credential after `changePassword`
    (`tests/integration/auth/test_revocation.py::test_a_credential_minted_under_a_stale_epoch_is_refused`);
  * the status read's counter (`test_a_refused_pair_is_counted_on_the_request`).

  `readRegistrationStatus` is a `POST`, so the rule names it too, beside `issueToken`.

  **New guard:**
  `tests/contract/domain_p02/test_seam_register.py::test_the_idempotency_rule_names_exactly_the_keyed_writes`.
  It checks the rule against the frozen document in two ways:
  * the rule's first sentence names exactly the operations that declare a required
    `Idempotency-Key` header;
  * the rest of the rule names exactly the other writes.
* **(b)** `tests/integration/access/test_password_hashing.py`:
  `test_it_does_not_register_a_prefix_in_the_frozen_contract_catalog` becomes
  `test_its_prefix_is_the_shared_registry_s`. It checks that `usr` maps to
  `shared.identity.ids.UserUid` (entity `User`) in both the snapshot and the live registry.
  It also checks that the boundary's class still wraps that type rather than subclassing it.
* **(c)** `tests/e2e/pc01/test_acceptance.py::test_c3_…`: the set of mutating routes is
  exactly `{updateMyProfile, updateUser, purgeUser}`, and none of their paths contains
  `/versions` or `/documents`.
* **(d)** `tests/integration/db/test_durable_analysis_effects.py`: `EDGE_ONLY_CODES =
  {"rate_limited"}`. The test asserts three things:
  * every other `ErrorCode` is in migration `0014`'s `ck_provider_effect_error_code`;
  * every edge-only code is **absent** from it;
  * the count of literals equals the number of stored codes.
* **(e)** `contracts/domain/v1/{error-codes,identifiers,state-machines}.schema.json`: the
  `candidate_revision` const moves from 8 to 9 and nothing else. See Q12 for what that
  revealed.
* **(f)** `src/auditmanager/access/repository.py`: `_SELECT_WITHOUT_DISPLAY_NAME`, the
  predicate `access.check` reads, is now `display_name IS NULL AND (last_name IS NULL OR
  first_name IS NULL)`. That is exactly the case in which `UserRecord.display_label` falls
  back to the login. A complete profile always has both names
  (`ck_app_user_complete_profile_has_names`), so it counts as named. The method docstring
  says so.

  **New test:**
  `tests/integration/auth/test_the_reviewer_name_is_visible.py::test_a_completed_profile_drops_out_of_the_report`.
  It completes a legacy account's profile. Then it asserts that the account leaves
  `accounts_without_a_display_name`, and that `python -m auditmanager.access.check`, run
  as a subprocess, prints no `UNNAMED` line for it.

### 7.2 Checks

| Command (tree: the amended working tree, before this commit) | Result |
| --- | --- |
| `pytest tests/integration/api/test_user_management.py tests/integration/api/test_registration_flow.py tests/integration/access/test_password_hashing.py tests/integration/db/test_durable_analysis_effects.py` | `100 passed` (after one correction: a repeated purge's `not_found` carries no `aggregate_type`, Q14) |
| `pytest tests/e2e/pc01/test_acceptance.py::test_c3_…` | `1 passed` |
| `pytest tests/integration/auth/test_the_reviewer_name_is_visible.py tests/integration/db/test_reviewer_display_name.py` | `33 passed` |
| `pytest tests/contract/domain_p02/test_seam_register.py tests/contract/api_v1/test_surface_counts_in_prose.py` | `53 passed` |
| unmutated copy, every target below | `135 passed` |

### 7.3 Mutations (copy rebuilt with `FULL=1`; same discipline as §2; `diff -rq` of `src`, `tests`, `contracts`, `db` and `docs` empty after)

| id | mutation | red | summary |
| --- | --- | --- | --- |
| **Mf1** | (f) predicate reverted to `display_name IS NULL` | `test_a_completed_profile_drops_out_of_the_report`: `assert 'usr_01M47AJ1KB4PY6687X8KN9JH47' not in {…}` | 1 failed |
| Ms1 | `approveRegistration` dropped from the rule's first sentence | `test_the_idempotency_rule_names_exactly_the_keyed_writes`: "must name exactly the writes that require Idempotency-Key: missing ['approveRegistration'], extra []" | 1 failed, 19 passed |
| Ms2 | the `purgeUser` repeat clause deleted | same test: "must say what a repeat of every unkeyed write does: missing ['purgeUser']" | 1 failed, 19 passed |
| Ms3 | the contract makes `rejectRegistration` keyed | same test: "missing ['rejectRegistration'], extra []" | 1 failed, 19 passed |
| Md1 | `EDGE_ONLY_CODES` gains the stored `not_found` | `test_provider_effect_error_code_is_the_closed_catalog`: `AssertionError: ('not_found', "CHECK (…'not_found'::text…")` | 1 failed |
| Md2 | migration `0014`'s `ERROR_CODES` gains `rate_limited` | same test: `AssertionError: ('rate_limited', "CHECK (…'rate_lim…")` | 1 failed |
| Mp1 | the shared `UserUid` registered as entity `Account` | `test_its_prefix_is_the_shared_registry_s`: `assert 'Account' == 'User'` | 1 failed, 4 passed |
| Mt1 | `archiveUser` served as `DELETE` | `test_c3_…`: `{'updateMyProfile': '/me', 'updateUser': …, 'archiveUser': '/users/{user_uid}/archive', 'purgeUser': …}` | 1 failed |
| Mr1 | `set_roles` raises the epoch even when nothing changed | `test_a_repeated_role_change_writes_the_same_set_and_revokes_once`: `assert 3 == (1 + 1)` | 1 failed, 4 passed |
| Mr2 | a complete profile refuses any `email`, even its own login | `test_a_repeated_profile_completion_writes_the_same_state`: `validation_failed` "a complete profile's login is fixed" | 1 failed, 4 passed |
| Mr3 | restoring an active account returns it | `test_a_repeated_archive_or_restore_is_a_refused_transition`: answered `200` with the account | 1 failed, 4 passed |
| Mr4 | purging an absent account returns | `test_a_repeated_purge_is_not_found`: answered `204` (`b''`) | 1 failed, 4 passed |
| Mr5 | the reset no longer raises the epoch | `test_a_repeated_reset_repeats_its_effect`: `assert 1 == (1 + 2)` | 1 failed, 4 passed |
| Mr6 | rejecting a decided request returns it | `test_a_repeated_rejection_is_a_refused_transition`: answered `200` with the request | 1 failed, 18 passed |

### 7.4 New open questions (numbered after §4's eleven)

12. **`contracts/domain/v1/identifiers.schema.json` does not validate the revision-9
    catalog.** Moving the const was not enough. Measured with
    `.venv/bootstrap/bin/python` and `jsonschema`, `identifiers.json` fails at:
    * `properties.entities.additionalProperties.enum`, for the entities `User` and
      `RegistrationRequest`;
    * `properties.distinct_identities.items.properties.identifiers.items.enum`, for
      `user_uid` and `request_id`.

    Both enums list the 27 names of revision 8. `error-codes.json` and
    `state-machines.json` validate. The proposed edit adds `"user_uid"` and `"request_id"`
    to both enums. Optionally, it also adds them to `properties.identifiers.required` and
    adds `User` and `RegistrationRequest` to the entities' `required` list. This is outside
    grant (e), which is the const only, so it is not edited. No test in the gate reads
    these schemas; only the excluded `test_cp00_candidate.py` does.
13. In `P02_SEAMS.md` §7, the bullet "every operation but `issueToken` requires a bearer
    credential … the role vocabulary `T-6` forbids inventing" is false since the seal:
    `submitRegistration` and `readRegistrationStatus` are open, and `R-55` ruled the role
    vocabulary. It is outside the grant, which covers the table and the idempotency
    sentence.
14. `not_found` for an account that the access boundary cannot find carries no
    `aggregate_type`. This covers the writes: archive, restore, purge, update and reset. The
    adapter's own reads (`getUser`) carry `aggregate_type: User`. Both are legal, because
    the key is optional in the catalog. Making them uniform would mean either the adapter
    adding the key or `access` raising it.

### 7.5 Files added since `48099d9`

`git diff --name-only 48099d9..HEAD`:

```text
contracts/domain/v1/error-codes.schema.json
contracts/domain/v1/identifiers.schema.json
contracts/domain/v1/state-machines.schema.json
docs/program/P02_SEAMS.md
docs/program/W49-SEAL-01c.md
docs/program/dispatch/W49-PLAN.md
docs/program/tasks/W49-SEAL-01.md
src/auditmanager/access/repository.py
tests/contract/domain_p02/test_seam_register.py
tests/e2e/pc01/test_acceptance.py
tests/integration/access/test_password_hashing.py
tests/integration/api/test_registration_flow.py
tests/integration/api/test_user_management.py
tests/integration/auth/test_the_reviewer_name_is_visible.py
tests/integration/db/test_durable_analysis_effects.py
```

`docs/program/dispatch/W49-PLAN.md` and `docs/program/tasks/W49-SEAL-01.md` are the
integrator's, merged at `549042c`. Every other path is a site of the second grant, plus
this report and the two granted test files the repeat measurements live in
(`tests/integration/api/**`).
