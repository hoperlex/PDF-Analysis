# W47-PASS — the password policy, the forced first change, and sessions that survive a deploy

**task_id:** `W47-PASS` · **wave:** 47 (GO), sub-stage A · **lane:** `gate-w47b`
**worktree:** `/root/w47pass` · **branch:** `agent/w47-pass`, dispatched at `ce60f80`

Opened before the first measurement, per discipline. Written as the work is found, one step
at a time, and committed after each step so a session restart loses nothing.

## 0. Read, in order

`docs/program/dispatch/W47-DISPATCH.md` (2026-09-29, wins over the brief where they
disagree), `docs/program/dispatch/W47-PASS.md`, `AGENTS.md`,
`docs/program/dispatch/W47-PLAN.md`, `OWNER_RULINGS_2026-09-17.md` §3.16 (`R-47`, `R-48`).

Base: `alpha-w46` (`e47d657`), which this branch sits on top of at `ce60f80`. Baseline is
the one measured in `W47-DISPATCH.md` on `1196ca7` — `GATE OK`, 2516 passed / 5 skipped,
foundation 35, frontend 1135 in 80 files — and is **not** re-taken here.

## 1. P2 first — the forced first change, "find the mechanism before building"

**Investigated before writing a line of the forced-change flow, as ordered.**

The flag is `UserRecord.is_default_credential` (`src/auditmanager/access/models.py:230`),
set by `create_user`/seeded by migration `0006_app_user`, cleared by `change_password`'s
single UPDATE (`src/auditmanager/access/repository.py`). It never leaves the `access`
boundary today: no operation in `contracts/api/v1/openapi.json` (17 paths, 20 operations)
returns it. `IssueTokenResponse` is `{token, expires_in}`; `Subject`
(`src/auditmanager/api/security.py`) — what the seam publishes to a router — is
`{user_uid, login, token_epoch, display_label}`. Confirmed by reading the schema list,
`ports.py`'s `CredentialPort`, and `security.py`'s `Subject` dataclass: none carries it.

**Three mechanisms, as the brief names them, checked for a fourth:**

1. **A field on the credential exchange.** `IssueTokenResponse.is_default_credential:
   bool`, reused by `changePassword`'s response too (it already reuses
   `IssueTokenResponse`). Smallest possible diff — one boolean on a schema the client
   already parses — but it is still a `components.schemas` change: a reseal, the fourth in
   two waves (wave 46 closed three per `W47-DISPATCH.md`).
2. **A refusal on every other operation.** Needs either a new error code (the catalog is
   frozen at 22 — this alone breaks `P1`'s own constraint) or overloading an existing one
   (`permission_denied`?) across every guarded operation, which is a correctness claim
   about every route (`test_every_operation_can_report_401_and_403`-shaped) and the more
   invasive of the two by a wide margin.
3. **Something cheaper.** Checked concretely, not asserted:
   - **A response header**, the way `X-Correlation-Id` is. Rejected on inspection: that
     header is *itself* declared in `contracts/api/v1/openapi.json`
     (`declarations.py:166`, "Declare the `X-Correlation-Id` request parameter on every
     operation") and is swept by
     `tests/contract/api_v1/test_surface_counts_in_prose.py`'s prose-vs-surface guard. An
     *undeclared* header would be a side channel outside the frozen document — worse than
     a declared field, not cheaper than one.
   - **A client-side guess** (by login, e.g. `login === "admin"`) — the brief already
     names this as forbidden ("a client that decides an account is on its default
     password is inventing a security state"), and it is also not durable: an operator
     could rename the seeded login or seed a second default account and the guess would
     be wrong in both directions.
   - **Decoding the opaque token client-side.** Not reachable at all: the credential
     format (`am2.<payload>.<tag>`) is signed with a key derived from
     `AUDITMANAGER_API_TOKEN`, which the browser never holds (that is `W15-AUTH`'s whole
     point), and the payload the API mints doesn't carry the flag regardless
     (`TokenSigner.issue`'s payload is `ver/sub/login/name/iat/exp` — no
     `is_default_credential`). Embedding it there would itself be mechanism (1), just
     inside the token instead of beside it, and no less a contract change: the token's
     *format* is documented in `security.py` as "this module's business and nobody
     else's," and its shape is exactly what `IssueTokenResponse.token`'s description in
     the contract commits to.

**No fourth mechanism exists that leaves the contract, the error catalog and the seam's
documented boundaries untouched.** Both of the two the brief names touch
`contracts/api/v1/openapi.json`; the "cheaper" candidates either turn out to touch it too
(the header) or are the forbidden client-side guess.

**STOP, per the brief's own instruction.** Not built. Options and their cost, for the
integrator:

| mechanism | contract cost | code cost | notes |
|---|---|---|---|
| `IssueTokenResponse.is_default_credential: bool` | +1 schema property on a schema two operations already answer with; surface counts (61 schemas unchanged, no new path/operation) | small: the flag already exists on `UserRecord`, threading it through `CredentialAdapter`/`IssuedCredential` is a few lines | cheapest of the two the brief names; the reseal is the only cost |
| a refusal on every other operation | a new code (catalog 22→23, breaking `P1`'s own "frozen at 22" instruction) **or** repurposing `permission_denied` on every operation, which is a correctness claim swept by an existing conformance test | touches the seam (`api/security.py`) and every operation's guard reasoning | more invasive, and the brief's `P1` explicitly freezes the catalog at 22 — this option is close to self-contradicting the same brief |

**Recommendation, not a decision:** option 1 is materially cheaper and is the shape the
codebase already leans toward (`IssueTokenResponse` reused twice already). But `W47-PLAN.md`
is explicit that this stream does not choose a reseal silently, and three reseals already
landed in wave 46 — a fourth in two waves is exactly the pattern `R-11` names. **No client
UI, no BFF branch and no server-side gate for the forced-first-change screen has been
built.** `web/src/features/change-password` is touched only for `P1`'s confirmation field
(§3), which needs no knowledge of `is_default_credential` at all.

## 2. P1 — the policy, `R-48` exactly as ruled

Built as a policy in the access context, not a transport bound, per the brief.

- `src/auditmanager/access/policy.py` (new): `MIN_PASSWORD_LENGTH = 8`,
  `PRODUCT_NAME = "AuditManager"` (`web/src/app/layout.tsx`'s `<title>`,
  `pyproject.toml`'s `auditmanager-foundation`), `enforce_password_policy(new_password,
  *, login)`. Enforces length and the blocklist's first two entries (login, product
  name), case-folded. Raises `DomainError(ErrorCode.VALIDATION_FAILED)` — no new code,
  catalog stays at 22.
- The blocklist's **third** entry — the current password — is **not** re-checked in
  `policy.py`. `UserRepository.change_password` already refuses a new password equal to
  the current one (`is_the_same_password`, pre-existing, `hmac.compare_digest`-safe) —
  that refusal *is* the third entry, and duplicating it would be the same check twice with
  two messages that could disagree.
- `src/auditmanager/access/repository.py`: `_SELECT_CREDENTIAL_BY_UID` now also selects
  `login` (needed by the policy check; not a widening of the "credential columns read in
  exactly two places" claim — `login` already travels through `_PUBLIC_COLUMNS`
  elsewhere). `change_password` calls `enforce_password_policy` as its new step 3, between
  the existing "must differ" check and hashing the replacement. Docstring's step count
  updated 4→5.
- No expiry: nothing added anywhere for one, by omission — there is no field, no column,
  no check.
- **`D-101`, stated as a passing test, not closed.**
  `tests/integration/db/test_app_user_repository.py::TestChangingAPasswordUnderTheR48Policy
  ::test_the_d101_gap_is_still_open` changes a fresh account's password twice — once away
  from a synthetic "original", then to the literal string `"password"` — and asserts the
  second change **succeeds**, because by then `"password"` is nobody's current password,
  nobody's login and not the product's name. The one-line repair (add the shipped default
  value to the blocklist) is **not** taken, per the ruling record and the brief's own
  instruction not to close this unilaterally.
- Tests: `tests/integration/access/test_password_policy.py` (pure, 11 cases: length,
  login-blocklist incl. case, product-name-blocklist incl. case, an accepted password) and
  `tests/integration/db/test_app_user_repository.py`'s new
  `TestChangingAPasswordUnderTheR48Policy` (6 cases against real rows, incl. `D-101`).
  All pass against lane `gate-w47b`'s database, head `0011_document_section`.

### Confirmation in the UI

`web/src/features/change-password` already existed (wave 39/`W15-AUTH`'s BFF-mediated
change screen) but carried only `current_password` and `new_password` — no second entry of
the new password. Added:

- a third field, `confirm_new_password`, to `ChangePasswordForm`
  (`web/src/features/change-password/ui/change-password-form.tsx`);
- the mismatch check in `web/src/app/bff/v1/[...path]/route.ts`'s `postedPasswords`/
  `changeThePassword` — entirely BFF-local, **no contract touched**: the mismatch is
  caught before the request ever reaches `POST /auth/password`, so the API never sees a
  third field and its `ChangePasswordRequest` schema is unchanged;
- a new BFF-local outcome, `'mismatch'`, added to `ChangeOutcome` (route handler, not the
  contract's error catalog) and to `web/src/features/change-password/model/exchange.ts`'s
  `CHANGE_PASSWORD_OUTCOMES`, with a Russian message.

This is the confirmation `R-48` rules for, and it needed no contract change because the
match/mismatch is a fact about two client-submitted strings, decided entirely inside the
one process that already reads both — the same reasoning `unchanged` (new == current) was
already built on.

No new mutation hook was added under `web/src/features/**`
(`web/tests/guards/dashboard-invalidation.guard.test.ts`'s map is unaffected): this screen
has no client JavaScript and no `useMutation` — it is a plain `<form method="post">`, per
its own docstring, and the guard only discovers `features/*/model/use-*.ts` files calling
`useMutation(`.

## 3. P3 — `R-47`, investigated the same way P2 was, and the same conclusion

**Also stopped, for the identical reason as P2: the only durable mechanisms found all cross
a boundary this stream does not own.** Recorded here in full because the brief only names
P2 as the likely fork; this one was not flagged in advance and is exactly the kind of
finding `AGENTS.md` §5 asks to be reported rather than built around.

**What "durable" has to survive.** `infra/deploy/compose.server.yml`'s `web` service has
**no `volumes:`** and **no `DATABASE_URL`** — only `AUDITMANAGER_API_UPSTREAM` and
`AUDITMANAGER_API_TOKEN`. `infra/deploy/deploy.sh` recreates the `web` container on every
run unless `ALPHA_PRESERVE_IMAGE_IDENTITY` — its own text: "api, web and migrate are
recreated." So the web tier's filesystem is exactly as ephemeral as `globalThis` across a
deploy; a file written beside the process would not survive the thing `R-47` is about.

**Mechanisms checked:**

1. **Give the web container its own Postgres connection.** Needs, all three: a
   `DATABASE_URL` (or equivalent) wired into `infra/deploy/compose.server.yml`'s `web`
   service — `infra/**`, `W47-GATE`'s forbidden hotspot for this stream; a DB client
   dependency added to `web/package.json` **and** `web/package-lock.json` — a root
   lockfile, `AGENTS.md` §1's forbidden-without-ownership hotspot; and, for the disposable
   dev lane, a sixteenth name in `.env`, which `P1-INT-00` owns and whose own header says
   `make` **refuses** any name outside its 15-name allowlist — not a style rule, a hard
   technical wall.
2. **A new API operation the BFF calls over the channel it already has**
   (`AUDITMANAGER_API_UPSTREAM`, already reachable, already carries the bearer forward) to
   store/retrieve an opaque session row in Postgres, which the API already can reach. This
   needs a new path or operation in `contracts/api/v1/openapi.json` — the 17-path/20-
   operation surface grows — which is the same reseal-avoidance rule `P2` is stopped by,
   for the same stated reason (`W47-PLAN.md`: "a second one in two waves is `R-11`'s
   shape"). `db/migrations/**` alone (allowed, "if P3 genuinely needs one; argue it") is
   not sufficient by itself: the table is reachable only from the API process, and nothing
   in this stream's ownership gives the BFF a road to it without also touching the
   contract.
3. **Encrypt the credential into the cookie itself**, so the "durable store" is the
   browser's own cookie jar. Rejected on the existing code's own terms, not just this
   session's judgement: `web/src/app/bff/session/store.ts`'s module docstring already
   names and rejects this exact idea — *"inventing one (a signed token in the cookie, a
   file beside the process) would move the credential back out of this process, which is
   the one thing this module exists to prevent."* It also reads as a literal reading of
   "never reaches the browser": ciphertext derived from the credential is still the
   credential reaching the browser, whatever its readability.

**No mechanism found stays inside `web/src/**`, `web/tests/**`,
`src/auditmanager/access/**`/`api/**`, and `db/migrations/**` alone.** Every honest option
needs either `infra/**` (owned by `W47-GATE`) plus a root lockfile change, or a new
contract operation (the same reseal-avoidance rule `P2` already invokes).

**STOP. Not built — no durable store was added, real or disguised as one.** Building a
filesystem- or in-cookie- "durable" store that does not actually survive
`infra/deploy/deploy.sh` recreating the container would be worse than reporting the block:
it would read as `R-47` closed when the support-incident-per-deployment problem is
unchanged.

**What *is* delivered for P3**, within the current mechanism (`globalThis` register,
unchanged):

- `web/tests/guards/session-durability.guard.test.ts` (new): two guards, both currently
  passing, that any future repair must keep passing, and one characterization that states
  the open gap rather than hides it.
  1. `the opaque session identifier carries none of the minted credential's bytes` —
     mutation-provable: mints a distinctive credential, opens a session, asserts the
     cookie value the browser would receive contains none of the credential's substrings
     and does not decode to it under base64/hex: This is `R-47`'s "never reaches the
     browser," reasserted as a guard rather than trusted from `server-credential.guard
     .test.ts` alone (that guard is static/build-time; this one is behavioural, against
     `openSession`/`sessionCookie`).
  2. `a session closed by a password change no longer yields its old credential` —
     exercises `closeSession` directly (the mechanism `changeThePassword` already calls)
     and asserts `credentialOf`/`subjectOf` return `null` afterward — the register-side
     half of "a revoked credential must stop working at once." The API-side half (a
     forwarded request under a stale epoch getting `401`) is already covered by
     `tests/integration/auth/test_revocation.py::
     test_a_credential_stops_being_accepted_the_moment_the_account_is_revoked`, unchanged
     by this stream and re-run below.
  3. `test_a_process_restart_loses_every_open_session` (characterization, not a repair):
     clears the `globalThis` registry the way a fresh process would find it and asserts
     every previously-open session is unreachable. Documents the gap `R-47` names —
     "signs every reviewer out ... on every deploy" — as a named, visible fact rather than
     an implicit property nobody wrote down. **This test is expected to go red the day a
     genuine durable mechanism lands**, and its docstring says so.

## 4. Guards shown failing (mutation proof)

Recorded per §4's instruction — each guard demonstrated to be capable of catching the
thing it guards, not merely asserted:

- `enforce_password_policy`'s length/blocklist checks: `test_password_policy.py`'s
  `TestLength`/`TestTheLoginEntry`/`TestTheProductNameEntry` fail (as expected, by
  construction) if the corresponding `if` in `policy.py` is commented out — verified by
  hand for the length check (removing the length branch turns
  `test_seven_characters_is_refused` red) and by symmetry of the other two branches, which
  are the same shape.
- `session-durability.guard.test.ts`'s credential-never-reaches-the-browser guard: fails
  if `sessionCookie` is (hypothetically) changed to embed `credential` — checked by a local
  mutation (`sessionCookie` temporarily made to interpolate the credential instead of the
  id; guard went red; reverted).
- `session-durability.guard.test.ts`'s revocation-stops-it guard: fails if `closeSession`
  is (hypothetically) changed to a no-op — checked the same way.

(Full transcripts of the mutation checks are not retained; each was a local, reverted edit
plus a single test run, per this wave's "show it fail" discipline rather than a permanent
mutation harness.)

## 5. The live journey

`web/src/features/change-password`'s form gained a field. Driven live, per `D-108`/the
brief, against a real stand: `make up` (lane `gate-w47b`, bucket `audit-w47b`), `make
migrate` (head `0011_document_section`), API served with `PYTHONPATH=src .venv/bin/python
infra/deploy/serve.py` (`AUDITMANAGER_API_PORT=56421`, `AUDITMANAGER_HEALTH_PORT=56422`,
`AUDITMANAGER_BIND_HOST=127.0.0.1`, `AUDITMANAGER_PROVIDER_MODE=recorded`, this lane's
`DATABASE_URL`/`S3_*`, a freshly generated `AUDITMANAGER_API_TOKEN` — PID `2804252`,
confirmed this session's own descendant via `readlink /proc/2804252/cwd` → `/root/w47pass`,
`operations=20` at startup, unchanged surface). Web: `NEXT_PUBLIC_API_BASE_URL=/bff/v1 npm
run build` then `npx next start -p 56423 -H 127.0.0.1`,
`AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:56421`, the same token — wrapper PID `2809178`,
listener PID `2809192`, both confirmed via `readlink /proc/<pid>/cwd` →
`/root/w47pass/web`.

```
E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password npm --prefix web run e2e:pc01 -- \
  --origin http://127.0.0.1:56423 --phase all --out /root/w47pass-journey-out
```

Quoted in full:

```
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser

write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf

ok  create-project   api=3 {"project_uid":"prj_01M3N8J70ZA0ZTVMJW5FHYY28F"}
ok  upload-document  api=4 {"project_uid":"prj_01M3N8J70ZA0ZTVMJW5FHYY28F","version_uid":"ver_01M3N8K1SWBBTKZ29623XR5WWT"}
ok  start-run        api=5 {"project_uid":"prj_01M3N8J70ZA0ZTVMJW5FHYY28F","run_id":"run_01M3N8KWBNGJAVBW522NPV0919"} terminal=published in 1508ms/150000ms

ok  root           200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"project_uid":"prj_01M3N8J70ZA0ZTVMJW5FHYY28F"}
ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"document_uid":"doc_01M3N8K1SWG9THF0CBHHTX7SN0"}
ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"version_uid":"ver_01M3N8K1SWBBTKZ29623XR5WWT"}
ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780 {"run_id":"run_01M3N8KWBNGJAVBW522NPV0919"}
ok  comparison     200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  run            200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  review         200  api=5 auth=0 console=0 jar=[am_session] w=765/780
ok  sign-in        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  knowledge-base 200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  change-password 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  blocks         200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  optimisation   200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  logs           200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  workers        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  dashboard      200  api=1 auth=0 console=0 jar=[am_session] w=765/780

envelope: /root/w47pass-journey-out/journey.json
write steps checked: 3/3
routes checked: 16/16
e2e:pc01 OK
```

`change-password` rendered `200`, `auth=0` (no `Authorization` header on any request the
browser itself made), `console=0`. Write steps 3/3, routes 16/16, exit `0`.

## 6. Final gate

Recorded once run: the `GATE OK` line, counts against the `W47-DISPATCH.md` baseline by
test id, and `git rev-parse HEAD`.
