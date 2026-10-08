# W49-SEAL-01a — the documents: the reseal, the catalog code, the identities, the machines, the pins

**Task:** `docs/program/tasks/W49-SEAL-01.md` (part a of three; one owner, three reports, one
gate). **Base:** `7912504`; the amended task file and plan merged from `integration/w49` at
`2894951` (merge commit `7d06e67`). **Branch:** `agent/w49-seal-01`. **Plan:** `W49-PLAN.md`
§3.1–§3.4, §3.6, §4 `W49-SEAL-01`. **Lane:** `gate-w49seal`, Postgres `56570`, S3
`60170`/`60171` (free under `ss -ltn` before `make foundation`).

## 0. The stop of 2026-10-06 and the resumption

The slot first stopped before any code (`2fae883`, this file's first version): a 23rd catalog
code broke the error kernel's import-time guard, two exhaustive frontend maps and a frontend
length pin; count prose sat in seven ungranted files; the suite accounts became incomplete
and roleless under §3.2; a frontend test pinned the open set; migration `0002`'s vocabulary
needed a ruling. The integrator widened the grant to exactly those sites and ruled the three
questions (`2894951`): the stored vocabulary is the catalog minus an explicit edge-only set;
`submitRegistration` declares neither `401` nor `403`, `readRegistrationStatus` `401` and no
`403`; the suite accounts become complete `expert` accounts through one helper. The
measurements of the stop are in `git show 2fae883:docs/program/W49-SEAL-01a.md`.

## 1. What 01a delivers

**The API reseal** (`contracts/api/v1/openapi.json`, the served application, the generated
client, the mirror and `web/FRONTEND_LOCK.json` move together):

| operationId | Method and path | Declared refusals |
| --- | --- | --- |
| `getMe` | `GET /me` | 401, 403, 500, 503 |
| `updateMyProfile` | `PATCH /me` | 401, 403, 409, 422, 500, 503 |
| `submitRegistration` | `POST /registrations`, `security: []` | 409, 422, 500, 503 (**no 401, no 403**) |
| `readRegistrationStatus` | `POST /registrations/status`, `security: []` | 401, 422, 500, 503 (no 403) |
| `listRegistrations` | `GET /registrations?status=&cursor=&limit=` | 401, 403, 422, 500, 503 |
| `approveRegistration` | `POST /registrations/{request_id}/approve`, `Idempotency-Key` | 401, 403, 404, 409, 422, 500, 503 |
| `rejectRegistration` | `POST /registrations/{request_id}/reject` | 401, 403, 404, 409, 422, 500, 503 |
| `listUsers` | `GET /users?include_archived=&cursor=&limit=` | 401, 403, 422, 500, 503 |
| `getUser` | `GET /users/{user_uid}` | 401, 403, 404, 500, 503 |
| `updateUser` | `PATCH /users/{user_uid}` | 401, 403, 404, 409, 422, 500, 503 |
| `archiveUser` | `POST /users/{user_uid}/archive` | 401, 403, 404, 409, 500, 503 |
| `restoreUser` | `POST /users/{user_uid}/restore` | 401, 403, 404, 409, 500, 503 |
| `purgeUser` | `DELETE /users/{user_uid}` → `204` | 401, 403, 404, 409, 500, 503 |
| `resetUserPassword` | `POST /users/{user_uid}/password` | 401, 403, 404, 422, 500, 503 |

Sixteen schemas: `UserUid`, `RegistrationRequestId`, `Role` (`expert`, `admin`),
`RegistrationStatus` (`pending`, `approved`, `rejected`), `Account`, `AccountPage`,
`PersonNames`, `UpdateMyProfileRequest`, `UpdateUserRequest`, `ResetUserPasswordRequest`,
`SubmitRegistrationRequest`, `RegistrationStatusResponse` (`{status: const "pending"}` — the
only status ever shown to an applicant), `RegistrationRequest`, `RegistrationRequestPage`
(`items`, `page`, `pending_total`), `ApproveRegistrationRequest` (roles, `minItems: 1`,
`uniqueItems`), `RejectRegistrationRequest` (reason 1–256). `readRegistrationStatus` takes
`IssueTokenRequest`: the pair it reads is the exchange's pair. Components added:
parameters `UserUid`, `RequestId`, `IncludeArchived`, `RegistrationStatusFilter`; responses
`StateConflict` (409: `conflict` with `conflict_reason`, or `state_transition_not_allowed`)
and `ApprovalConflict` (409 of the keyed approval). Tags `account`, `registrations`,
`users`. `ErrorCode` gains `rate_limited`.

**`rate_limited` is not declared on any operation.** It is answered by the edge before an
operation is reached, exactly like the edge's own `413`, which the document does not declare
either; declaring it made the PC-01 render-subset guard demand it in `PC01_ERROR_CODES`
(`web/src/shared/api/errors.ts`, granted for its count sentence only). The info block and both
operation descriptions say who answers it.

**Compatibility.** Every one of the twenty existing operations is unchanged on the wire:
`test_openapi_conformance_live.py` compares the served document with the contract after
normalisation, and the twenty rows of `FROZEN_OPERATIONS` are untouched. Prose that changed
on existing objects: `info.description`, `bearerAuth.description`, `changePassword`'s
description (the superseded denials below).

**The superseded denials (`R-55`).** `rg -n -i -e role -e 'rate limit' contracts/api/v1/openapi.json`
printed six lines at the base and prints 26 now. None denies a role vocabulary or rate limiting:

* 2785, 2788, 2794 — `InputManifestEntry.role` (description, `required`, property), unchanged;
* 7 (`info.description`) — the base denials rewritten: "does not have: ... roles, rate
  limiting" lost both words and now points at the reseal; the `W34-CONTRACT` and
  `W39-REVOKE` denials are now past tense and name `R-55` as superseding them; the new
  `W49-SEAL-01` paragraph states the role vocabulary and the edge throttle;
* 2063 (`bearerAuth`) — "no role, subject or capability vocabulary" replaced by "what a
  subject may do is ... the account's role set (`Role`), which the server reads ... on
  every request"; the `403` sentence names the four `required_capability` values;
* 136 (`changePassword`) — "a role model this document does not describe" and "the role
  vocabulary this document deliberately does not have" replaced by what is true now;
* the new role-vocabulary sentences: 70 (`users` tag), 1274 (`getMe`), 1545
  (`approveRegistration`), 1784–1785 (`updateUser`), 1846 (`purgeUser`), 4004/4006 (`Role`),
  4032/4092/4094/4097 (`Account.roles`), 4203/4209/4211/4214 (`UpdateUserRequest.roles`),
  4430/4433/4435/4439 (`ApproveRegistrationRequest.roles`).

**The domain family, candidate revision 8 → 9** (`error-codes.json`, `identifiers.json`,
`state-machines.json`, each with its revision note; `error-envelope.schema.json`;
`contracts/domain/v1/README.md`'s revision-9 section):

* `rate_limited` — 429, `retryable: true`, category `policy`, `safe_detail_keys: []`, with
  notes saying the edge answers it and nothing stores it; the envelope schema's `enum` and its
  per-code `retryable` `allOf` branch;
* `conflict.safe_detail_keys` gains `conflict_reason` (values `login_taken`,
  `request_pending`, `queue_full`, `account_referenced`, `last_admin`, in a note);
* identifiers `user_uid` → `usr` (entity `User`) and `request_id` → `reg` (entity
  `RegistrationRequest`), and a `account_identity` distinction; the shared registry
  (`src/auditmanager/shared/identity/ids.py`) gains `UserUid` and `RegistrationRequestId` in
  the same commit;
* machines `app_user` (`active → archived → active | purged`, terminal `purged`) and
  `registration_request` (`pending → approved | rejected`).

**The code in five places, and the sixth that does not move.** `codes.py` (`RATE_LIMITED`
and its count sentence), `api/schemas/models.py` (served `ErrorCode` enum),
`catalog-message.ts` (a sentence and its count sentences), `terminal-reason.ts` (an entry —
no run can end with the code, and the sentence says so), and the count pins below. Migration
`0002`'s `ERROR_CODES` stays at 22: `test_contract_vocabulary.py` declares
`EDGE_ONLY_CODES = frozenset({"rate_limited"})` and asserts the stored vocabulary equals the
catalog minus it, that the set is a subset of the catalog and disjoint from what is stored.

**The served application declares the fourteen operations.** The router modules `me.py`,
`registrations.py` and `users.py`, the ports `AccountPort` and `RegistrationPort`, the views
`schemas/accounts.py` and `schemas/registrations.py`, and the models land here and not in
01c, because 01a's required `tests/contract -q` includes `test_openapi_conformance_live.py`,
which compares the **served** document with the contract. They are declarations over ports
that nothing implements until 01c; the edge additions (`AGGREGATE_OF_PATH_PARAMETER` for
`user_uid`/`request_id`, the `status` and `roles` enum sentences, `unique_items`, and a list
refusal naming its property rather than its index) are the same declarations' refusals.

**Every surface pin of §3.6**, each measured, never quoted: the triple pin
(`SurfaceTriple(paths=27, operations=34, schemas=77)`), `FROZEN_OPERATION_COUNT = 34`,
`FROZEN_SCHEMA_COUNT = 77` and both frozen sets, `PATH_COUNT`/`OPERATION_COUNT`/`SCHEMA_COUNT`
of the served-document test, the router counts of `test_operation_surface.py` and
`test_router_and_body_rules.py`, the three composition pins, `test_acceptance.py:307`, the
lock's three counts, and the catalog pins (`== 23` in `test_openapi_document.py`,
`test_error_kernel.py`, `test_envelope_screen_rules.py`; `toHaveLength(23)` in both web
tests); `CONTRACT_PIN_REGISTRY.md` moved every row but the head's and the migration's
vocabulary row (still 22, by ruling); `_TS_ERROR_COUNT_ASSERTION` now also discovers 23, 27,
34 and 77. The live sentences of `CURRENT_STATE.md` and `ALPHA_ROADMAP.md`, and the count
sentences of `P02_SEAMS.md`, `infra/deploy/README.md`, `infra/deploy/serve.py`,
`infra/deploy/proxy/nginx.conf`, `src/auditmanager/api/**`, the two `web/src` comments,
`errors.ts` and `catalog-message.ts`.

## 2. Measured

| Fact | Command (tree: this commit's working tree) | Result |
| --- | --- | --- |
| triple | P-01's one-liner over `contracts/api/v1/openapi.json` | `27 34 77` |
| SHA-256 | `sha256sum contracts/api/v1/openapi.json web/openapi/openapi.json` | both `633a58a53baf6652625b59d3db9438ae01e8c4ac8da788160882f031123f2e37` |
| catalog | `len(codes)` | 23 |
| identities | `len(identifiers)` | 29 |
| served = contract | `pytest tests/contract/api_v1/test_openapi_conformance_live.py` | `1 passed` |
| client | `npm --prefix web run api:verify` | `OK - 34 operations`, exit 0 |
| typecheck | `npm --prefix web run typecheck` | exit 0 |
| web contract | `cd web && npx --no-install vitest run tests/contract tests/unit/api tests/unit/screens/run-terminal-reason.test.ts tests/unit/run/terminal-reason.test.ts tests/guards/frontend-lock.guard.test.ts` | `16 passed (16)`, `263 passed` |
| lint | `npm --prefix web run lint` | exit 0 |
| contract battery | `pytest tests/contract -q` with the gate's three ignores | `438 passed`, 2 failed — see §4 |

## 3. Contracts changed

`contracts/api/v1/openapi.json` and `README.md`; `contracts/domain/v1/{error-codes.json,
error-envelope.schema.json, identifiers.json, state-machines.json, README.md}`.

## 4. Risks, limits and open questions

1. **`docs/program/P02_SEAMS.md`'s operation table is outside the grant and its guard is red.**
   `tests/contract/domain_p02/test_seam_register.py::test_the_api_operation_table_matches_the_frozen_document`
   compares the table in §7 with the document; the grant names only the sentences of that
   file that state a count, and the table needs the fourteen rows. Not edited. This is the
   one red the slot cannot close; it is the first question of the hand-back.
2. `test_alpha_acceptance_command.py::test_release_command_cannot_turn_skips_recorded_mode_or_outage_into_pass`
   refuses an uncommitted checkout (`FAIL: checkout содержит незакоммиченные изменения`); it
   was measured on the working tree before this commit and is environment, not code.
3. **The three family schemas still pin `candidate_revision` `const: 8`.**
   `error-codes.schema.json`, `identifiers.schema.json` and `state-machines.schema.json` are
   outside the grant; the catalogs say 9 as ruled. Only `tests/contract/test_cp00_candidate.py`
   (excluded from the gate, red at the base) validates the catalogs against them. Question 2.
4. `Role`'s values are new enum vocabulary; `web/tests/guards/rendered-language.guard.test.ts`
   permits every contract enum value as visible text unless it lists the schema in
   `TRANSLATED_SCHEMAS`. Screens are W50/W51; noted for them.
5. `tests/integration/db/test_schema_shape.py` still excludes `user_uid`, `request_id`,
   `created_user_uid` and `author_user_uid` from the prefix sweep with a comment asking the
   seal to move them into `prefix_by_column`; the file is outside the grant and stays green.

## 5. Integrator

Intermediate commit; the integration suites are expected red until 01c. The lock's
`content_commit` is moved to this commit by a later one of the slot, because a commit cannot
name itself.

## 6. Forbidden hotspots

`git diff --name-only 7d06e67..<this commit>` lies inside the amended `allowed_paths`; the full
list is in `W49-SEAL-01c.md`. No migration, no `src/auditmanager/access/**`, no lock file of
the toolchain, no ref, tag or push.
