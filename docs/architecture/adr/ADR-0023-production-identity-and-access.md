# ADR-0023: Production identity and access: one organisation, local accounts, audited access changes

- Status: accepted (nothing in this ADR is still proposed)
- Date: 2026-10-26; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: `PRODUCTION-ADR-PACK-01`; owner rulings `R-146d`, `R-146i`, `R-146n`, `R-146s`, `R-146aj`, `R-146al`; `AD-11` confirmed by `R-146s`, `AD-10` by `R-146w` as written at commit `83600aed`, `AD-19` settled by `R-146z`; `SESSION-RENEW-01` (owner, 2026-11-18)
- Amends: settles `U-04` for 1.0 (the legal-hold authority by `R-146aj`, as a rule of procedure) and partly accepts `ADR-0014`; supersedes nothing

## Context

The owner chose one organisation, local accounts with administrator approval, no multi-tenancy, no MFA
and no external identity provider in 1.0 (`R-146d`); a deployment is not successful while the seeded
`admin`/`password` is valid (`R-146i`); sign-in, role grant and password change are recorded in
`audit_event` (`R-146n` item 6). Forces: authorization is a written register per operation (`R-50`: a
default-credential account reaches only `issueToken`, `changePassword` and `getMe`; `R-80`: product data
needs a role); a restore of an older dump brings back its credentials, the seeded pair included
(`R-52`); behind the live outer terminator the session cookie lacks `Secure` (`D-144`, `D-191`,
`EXPOSURE-REVIEW-01.md` E-2); whether the live stand's password was changed is unknown (`D-75`,
`D-217`).

## Decision

### 1. One organisation, local accounts (`R-146d`)

There is one organisation. Accounts are local; a person registers, an administrator approves and chooses
the roles, which stay `expert` and `admin` under the existing registers. Every active expert sees every
project; there is no per-project access control and no organisation boundary in the schema or the
contract. Multi-tenancy, MFA and an external identity provider are **excluded from 1.0**, not deferred
without a date. This settles `U-04` for 1.0 on the tenant model and the identity provider; the retention
half is `ADR-0022`; the legal-hold authority is settled by `R-146aj` as a rule of procedure (`ADR-0022`
decision 2).

### 2. Sessions and cookies (`R-146a`)

The credential is a bearer HMAC token that lives 29 400 seconds, eight hours and ten minutes
(`TOKEN_LIFETIME_SECONDS`): the sliding session's idle window of eight hours plus the ten-minute cadence
at which the web tier renews a held credential (`renewToken`); a session ends after eight hours without
a request or thirty days after sign-in. A role change, an archive, a reset and a password change raise
the account's `token_epoch`, which revokes every credential it holds on its next request. Five failed
sign-ins in 900 seconds start a 300-second cooling-off; the edge limits registration and token exchange
to 6 requests per minute per address; the password policy is `R-48` (length 8, a contextual blocklist,
no expiry). Once TLS is terminated by the stack (`ADR-0021` `AD-01`) the session cookie carries `Secure`
and HSTS is sent on every TLS answer (`ADR-0021` rows 3 and 4). The cookie rules, in full: `am_session`,
`Path=/`, `HttpOnly`, `SameSite=Strict`, `Max-Age` no longer than the credential's lifetime, `Secure` on
every TLS answer.

### 3. The seeded administrator is closed by the deploy (`R-146i`, `R-146s`)

`verify-deployed.sh` and `readiness.sh` run `python -m auditmanager.access.check` in the `api` image,
and a deployment is not successful while it reports a default credential (`R-146i`).

`AD-11`, confirmed by `R-146s`: when the check reports a default credential, the deploy ends non-zero
**and the public listener is not opened** until the password is changed; the stack stays on loopback.

- `deploy.sh` runs the check after `migrations-at-head`, prints the logins, ends non-zero and does not
  add the overlay that publishes port 443 (`ADR-0021` decision 2); it stops no service.
  `verify-deployed.sh` ends non-zero (a new reason with its own refusal text) and names the logins.
  `readiness.sh` keeps `R-46` for its other checks; `default-credential` is the one whose finding also
  fails the deploy. The choice is bounded: services keep running, only the outside door stays shut
  (`R-146s`; a fail-closed repair once took the stand down for a day, `D-72`).
- **Fresh host and restore** (`ADR-0021` decision 2): a fresh host stays on loopback until the password
  is changed through an SSH tunnel. A restore brings back the credentials as the dump held them
  (`R-52`); both restore paths raise every `token_epoch`, run the check and, on a finding, close 443:
  the site is unreachable from outside until an administrator changes the password through loopback (the
  consequence `R-146s` accepts).
- **Which accounts count (`AD-19`, settled by `R-146z`).** Only the published seeded pair,
  `admin`/`password`: the gate fails only when the seeded `admin` account is active and its stored
  credential still verifies against the published password. Every other must-change account, an
  administrator's temporary password included, is a `WARNING` line without moving the status (`R-46`).

### 4. Audit events for access changes (`R-146n` item 6)

`AD-10`, confirmed by `R-146w` (an implementation decision within `R-146n` item 6): a writer local to
the `access` context appends to `audit_event`, with its own allow-list of payload keys
(`src/auditmanager/access/audit.py`). Identities, controlled classifiers and counts only; **never** a
password, a hash, a token, a cookie, a registration's names or e-mail, an IP address (behind a
terminator it is the proxy's, a wrong fact in an append-only table) or a user agent.
`audit_event.correlation_id` carries the request's correlation id; every event has aggregate `Account`
(the account's `usr_` id).

| `event_type` | Written when | Payload keys |
| --- | --- | --- |
| `access.sign_in_succeeded` | `issueToken` accepts a password | `subject_uid`, `source` (`api`), `default_credential` (true when the account was still on the seeded or reset password) |
| `access.sign_in_blocked` | a failed attempt starts a cooling-off period on a known account | `subject_uid`, `source`, `failures` |
| `access.role_granted` | `approveRegistration` grants, an administrator adds a role, or the host command `access.grant` runs | `subject_uid`, `actor_uid` (absent for the host command), `role`, `source` (`api` or `host_cli`) |
| `access.role_revoked` | an administrator removes a role | `subject_uid`, `actor_uid`, `role`, `source` |
| `access.password_changed` | `changePassword` succeeds | `subject_uid`, `actor_uid` (the same), `source` |
| `access.password_reset` | `resetUserPassword` by an administrator | `subject_uid`, `actor_uid`, `source` |

Each the architect's: **a failed sign-in is journalled only when it starts a cooling-off period** (at
most once per account per 300 seconds); other failed attempts and attempts on unknown logins stay out.
`access.role_revoked` is added beside the owner's "role grant" because a role set that can only grow in
the record misstates the state. Registration approval and rejection, archive, restore, purge and unlock
are **not** journalled; they are the first additions if the audit is widened. Events are written in the
same transaction as the change they describe. Retention: forever; the 1.0 purge keeps them. Contract
1.36.0 adds a seventh type, `access.sessions_ended` (an administrator ended every session of an account;
keys `subject_uid`, `actor_uid`, `source`), under the same rules.

### 5. Out of scope, and what reopens it

| Excluded | Reopen when |
| --- | --- |
| Multi-tenancy | a second organisation needs the product, or a client demands that its experts see only its own projects (it needs an organisation column on `project`, a contract reseal and a boundary in the erase of `ADR-0022`) |
| MFA | the owner or a client requires a second factor, or an account is compromised |
| External identity provider | the organisation has one it requires, or account provisioning is a burden |
| Legal-hold mechanism, classification labels | the owner wants a hold mechanism in the product (`R-146aj`: none in 1.0) or decides labels (`R-146ak`: open) |

The credential seam allows a different body for MFA or an identity provider without changing an
operation.

## Commitments and their mechanical checks

| # | Commitment | Mechanical check |
| --- | --- | --- |
| 1 | No account is on the seeded password after a deploy, and the public listener stays shut while one is (`R-146i`, `R-146s`) | `tests/integration/composition/test_default_credential_gate.py`; on the VPS `access.check` exits `0` and `verify-deployed.sh` passes only then; while it exits `1` 443 is unpublished (`ADR-0021` row 6) |
| 2 | An operation named in no register is refused | `tests/integration/api/test_role_register.py` |
| 3 | A default credential reaches only the password change | `tests/integration/api/test_authorization.py` |
| 4 | The lockout is 5 failures in 900 s and 300 s of cooling-off | `FAILED_SIGN_IN_ALLOWANCE`, `ATTEMPT_WINDOW_SECONDS`, `COOLING_OFF_SECONDS` in `src/auditmanager/access/repository.py` |
| 5 | Sign-in, role grant and password change are journalled | `tests/integration/access/test_access_audit.py`: a test per code path (API, registration approval, host command) goes red when the emission is deleted |
| 6 | No event payload carries a secret or a name | `tests/unit/access/test_access_audit_payloads.py`: every written key is in the writer's allow-list and every value is a scalar |
| 7 | The session cookie is `Secure` on TLS | `ADR-0021` row 4 |
| 8 | No MFA, IdP or tenant code exists | `rg -il "totp\|saml\|tenant_id\|organisation_id" src db web/src` prints nothing |
| 9 | Only the published pair closes the deploy; a temporary password issued by an administrator only warns (`R-146z`) | `tests/unit/access/test_access_check_gate.py` and `test_default_credential_gate.py`: a seeded `admin` on `password` gives the gate's non-zero status; an administrator-reset account alone gives a `WARNING` line and status `0` |

## Consequences

- Positive: the takeover window of `EXPOSURE-REVIEW-01.md` E-1 is closed by the deploy itself; who
  signed in, who granted a role and who changed a password is a question the database can answer, and
  the answer survives every purge.
- Cost: every expert sees every project; a password-only product (a stolen password is a full account
  until changed); a deploy or restore that finds the published pair valid closes the outside door, so
  the operator must reach the host over SSH; failed sign-ins on unknown logins and below the lockout
  threshold are not recorded.

## Alternatives considered

1. **A deploy that stops every service while a default credential is valid** — rejected by `R-146s`,
   which closes only the public listener (`D-72`).
2. **Random one-time seed password printed by the migration** — the fix `EXPOSURE-REVIEW-01.md` E-1
   suggests; needs a migration and changes `R-50`'s account story; not asked, not built.
3. **Journal every failed sign-in** — rejected: unbounded growth in an append-only table.
4. **Record the client IP** — rejected for 1.0: unreliable behind a terminator, personal data in an
   immutable table.

## Verification

The commitment rows and the tests they name; `tests/integration/composition/test_readiness_command.py`
(`readiness.sh` reports, `R-46`); the release rehearsal (`PROD-17`): a database with the default
credential valid makes `verify-deployed.sh` fail with the application port unpublished and pass after
the change; one sign-in, role grant and password change are read back.

## Revisit trigger

Replace this ADR when a second organisation, a second factor or an identity provider is required, when
the product is to have a legal-hold mechanism, when the product is opened to users outside the owner's
organisation (`R-146al`: 1.0 users are the organisation's employees; registration mail, licensing,
`D-4.1` and `NORM-Q04` reopen before outside access), or when an incident shows that the journal of
decision 4 lacks the fact needed to explain it.

## History

- 2026-10-26 — accepted for production by the repository owner; `AD-11` confirmed by `R-146s`, `AD-10`
  by `R-146w`, `AD-19` settled by `R-146z`.
- 2026-11-18 — credential lifetime 29 400 s, the sliding session (release of fb6c2203e)
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0023-production-identity-and-access.md
- 2026-11-18 — status statements updated to dev fb6c2203e: the credential gate, the `access.*` journal
  and the restore token raise exist (`PROD-01`, `PROD-02`, `PROD-06`); legal hold settled by `R-146aj`;
  users are the organisation's employees (`R-146al`); a seventh event type `access.sessions_ended`
  (contract 1.36.0); the table's snapshot columns dropped.
