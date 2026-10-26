# ADR-0023: Production identity and access: one organisation, local accounts, audited access changes

- Status: accepted for production by the repository owner (`R-146d`, `R-146i`, `R-146n`); the implementation choices marked `AD-` are the architect's, proposed and not yet confirmed
- Date: 2026-10-26
- Owners: repository owner / `PRODUCTION-ADR-PACK-01`
- Supersedes: nothing; it settles `U-04` for 1.0 except the legal-hold authority (`R-146d`) and partly accepts `ADR-0014`
- Related principles: P-10, P-13, P-18

## Context

The owner chose one organisation, local accounts with administrator approval, no multi-tenancy, no
MFA and no external identity provider in 1.0 (`R-146d`). A deployment is not successful while the
seeded `admin`/`password` is valid (`R-146i`). Sign-in, role grant and password change are recorded
in `audit_event` (`R-146n` item 6). Facts read from the tree at `4d7b7c38` on 2026-10-26:

- **Accounts and roles.** `app_user` (migration `0006_app_user`) holds the login and a PBKDF2-HMAC-SHA256
  digest at 600,000 iterations (`src/auditmanager/access/passwords.py`); roles are `expert` and
  `admin` (`ROLES` in `src/auditmanager/access/models.py`, migration
  `0015_accounts_roles_registration`). A person registers without an account
  (`submitRegistration`), an administrator approves with at least one role (`approveRegistration`) or
  rejects. `app_user_role.granted_by` records who granted a role; a revocation, a sign-in and a
  password change leave no record.
- **What a subject may do** is decided by written registers evaluated in a fixed order on every
  guarded request (`src/auditmanager/api/security.py`): the credential and the account's standing
  (an archived account or a stale `token_epoch` is `authentication_required`); `R-50`, an account on a
  default credential reaches only `issueToken`, `changePassword` and `getMe`
  (`OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES`); an incomplete profile; then `OPERATION_ROLES`. An
  operation named in no register is refused to everyone, and
  `tests/integration/api/test_role_register.py` sweeps the served application against the register.
  Since `R-80` product data needs a role. There is no tenant, organisation or owner column in any
  migration: every active expert sees every project.
- **Credentials.** A bearer HMAC token lives 3600 seconds (`TOKEN_LIFETIME_SECONDS`); each account has
  a `token_epoch` (migration `0007_credential_epoch`) that a role change, an archive, a reset and a
  password change raise, which revokes every credential the account holds on its next request. Five
  failed sign-ins in 900 seconds start a 300-second cooling-off (`FAILED_SIGN_IN_ALLOWANCE`,
  `ATTEMPT_WINDOW_SECONDS`, `COOLING_OFF_SECONDS` in `src/auditmanager/access/repository.py`); the edge
  limits registration and token exchange to 6 requests per minute per address
  (`infra/deploy/proxy/nginx.conf`). The password policy is `R-48`: length 8 and a contextual blocklist,
  no expiry. The authorization seam was built so that the credential body can change without
  changing an operation; no OIDC body exists.
- **The browser session.** The web tier keeps the API credential server-side and gives the browser an
  `am_session` cookie, `HttpOnly`, `SameSite=Strict`, `Max-Age` equal to the lifetime, and `Secure` only
  when `X-Forwarded-Proto` says `https` (`web/src/app/bff/session/store.ts`). Behind the live outer terminator the
  cookie is issued without `Secure` (`D-144`, `D-191`, `EXPOSURE-REVIEW-01.md` E-2).
- **The seeded administrator.** Migration `0006_app_user` inserts login `admin`, password `password`
  and marks the row `is_default_credential`; migration `0015` gives it the `admin` role. The pair is
  published in the migration, in `src/auditmanager/access/policy.py` and in the runbook.
  `python -m auditmanager.access.check` reports accounts still on it without signing in: exit `0` none,
  `1` at least one, `2` unreadable. `infra/deploy/readiness.sh` runs it as a report (`R-46`: it blocks
  nothing); `deploy.sh` and `verify-deployed.sh` do not call it. `reset.sh` returns the seeded account,
  and a restore of an older dump brings back whatever state the dump had (`R-52`). Whether the live
  stand's `admin` password was changed is not readable from the tree (`D-75`, `D-217`).
- **Host-side tools.** `python -m auditmanager.access.grant` grants a role from the host and
  `python -m auditmanager.access.unlock` lifts a lockout; neither writes an audit record.
- **The audit table.** `audit_event` is append-only by trigger; its event type matches
  `^[a-z][a-z0-9_.]{2,127}$`, its aggregate id `^[a-z][a-z0-9]{1,7}_<ULID>$`, its payload is a JSON
  object. Each context that writes to it carries its own writer and key allow-list
  (`src/auditmanager/jobs/events.py` is the model). `product_purge.py` keeps the event families it
  lists and stops on one it does not know.

## Decision

### 1. One organisation, local accounts (`R-146d`)

There is one organisation. Accounts are local; a person registers, an administrator approves and
chooses the roles. The roles stay `expert` and `admin` under the existing registers. Every active
expert sees every project; there is no per-project access control and no organisation boundary in the
schema or the contract. Multi-tenancy, MFA and an external identity provider are **excluded from
1.0**, not deferred without a date. This settles `U-04` for 1.0 on the tenant model and the identity
provider; the retention half is `ADR-0022`; the legal-hold authority stays open.

### 2. Sessions and cookies (`R-146a`)

No change to the credential: lifetime 3600 seconds, `token_epoch` revocation, the lockout, the edge
limits and the password policy stay as measured above. What changes is the transport. Once TLS is
terminated by the stack (`ADR-0021` `AD-01`) the proxy forwards `https` and the session cookie carries
`Secure`; HSTS is sent on every TLS answer. Both have a mechanical check (`ADR-0021` rows 3 and 4).
The cookie rules are, in full: name `am_session`, `Path=/`, `HttpOnly`, `SameSite=Strict`, `Max-Age` no
longer than the credential's lifetime, `Secure` on every TLS answer.

### 3. The seeded administrator is closed by the deploy (`R-146i`)

`verify-deployed.sh` and `readiness.sh` run `python -m auditmanager.access.check` in the `api` image,
and a deployment is not successful while it reports a default credential.

`AD-11` (architect's implementation decision within `R-146i`, to be confirmed):

- `verify-deployed.sh` ends non-zero (inside its existing scheme: `0` this tree, `4` could not be
  answered, `6` not this tree; a new reason with its own refusal text) and names the logins, so the
  workflow's verify step fails and the release is not recorded as done. `deploy.sh` runs the same check after
  `migrations-at-head`, prints the logins and ends non-zero, **without stopping any service**: the
  precedent is `D-72` (a correct fail-closed repair took the stand down for a day) and `R-52`, where the owner
  chose to report rather than refuse after a restore. The consequence to be accepted: the public site
  stays up during the window in which the default credential is valid, and `R-50` limits what that credential can
  reach to a password change, which is exactly the account takeover of `EXPOSURE-REVIEW-01.md` E-1.
  Whether a failed check should also take the `proxy` down is a question for the owner.
- `readiness.sh` keeps `R-46` for its other six checks; `default-credential` becomes the one check
  whose finding is also a failure of the deploy.
- Order on a host that has never been published (or after `reset.sh` or a restore): the stack comes
  up bound to loopback, which is the default (`D-49`); the administrator signs in through an SSH tunnel and changes the
  password; only then is `ALPHA_BIND_ADDRESS` opened and the stack redeployed. A restore raises every
  `token_epoch` and reports default accounts (`R-52`); that report is the cue.

### 4. Audit events for access changes (`R-146n` item 6)

`AD-10` (architect's implementation decision within `R-146n` item 6, to be confirmed).

A writer local to the `access` context appends to `audit_event`, modelled on `jobs/events.py`, with
its own allow-list of payload keys. Identities, controlled classifiers and counts only; **never** a
password, a hash, a token, a cookie, a registration's names or e-mail, an IP address or a user agent.
(An IP address is deliberately left out: behind a terminator it is the proxy's unless
`ALPHA_TRUSTED_PROXY_CIDRS` is set correctly, so it would be a wrong fact written into an append-only
table.) `audit_event.correlation_id` carries the request's correlation id, so an event can be tied to
the server log.

| `event_type` | Written when | Aggregate | Payload keys |
| --- | --- | --- | --- |
| `access.sign_in_succeeded` | `issueToken` accepts a password | `Account`, the account's `usr_` id | `subject_uid`, `source` (`api`), `default_credential` (true when the account was still on the seeded or reset password) |
| `access.sign_in_blocked` | a failed attempt starts a cooling-off period on a known account | `Account` | `subject_uid`, `source`, `failures` |
| `access.role_granted` | `approveRegistration` grants, an administrator adds a role, `python -m auditmanager.access.grant` runs | `Account` | `subject_uid`, `actor_uid` (absent for the host command), `role`, `source` (`api` or `host_cli`) |
| `access.role_revoked` | an administrator removes a role | `Account` | `subject_uid`, `actor_uid`, `role`, `source` |
| `access.password_changed` | `changePassword` succeeds | `Account` | `subject_uid`, `actor_uid` (the same), `source` |
| `access.password_reset` | `resetUserPassword` by an administrator | `Account` | `subject_uid`, `actor_uid`, `source` |

Decisions inside the table, each the architect's: **a failed sign-in is journalled only when it starts
a cooling-off period**, which by construction happens at most once per account per 300 seconds, so an
attacker cannot grow the table by guessing; failed attempts that start nothing, and attempts on unknown
logins, stay out of the table (they are the per-account counters and the edge limits). `access.role_revoked` is added
beside the owner's "role grant" because a role set that can only grow in the record misstates the
state. Registration approval and rejection, archive, restore, purge and unlock are **not** journalled
by this ADR: the owner named three families, and they are listed as the first additions if the
audit is widened. The events are written in the same transaction as the change they describe, so a
change without its event cannot commit.

Retention: forever; `audit_event` is append-only and the 1.0 purge keeps these events. The purge tool's
`KEEP_EVENT_PREFIXES` gains `access.` in the same lane (it stops on an unclassified event type).

### 5. Out of scope, and what reopens it

| Excluded | Reopen when |
| --- | --- |
| Multi-tenancy | a second organisation needs the product, or a client demands that its experts see only its own projects; it needs an organisation column on `project` and a contract reseal, and the erase of `ADR-0022` gains a boundary |
| MFA | the owner or a client requires a second factor, or an account is compromised; the credential seam allows a different body without changing an operation |
| External identity provider | the organisation has one it requires, or account provisioning is a burden; same seam |
| Legal hold, classification labels | the owner names the authority (open since `ADR-0014`) |

## Commitments and their mechanical checks

`$DC` as in `ADR-0021`.

| # | Commitment | Mechanical check | Exists | Delivered by |
| --- | --- | --- | --- | --- |
| 1 | No account is on the seeded password after a deploy (`R-146i`) | `$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.check` exits `0`; `infra/deploy/verify-deployed.sh` exits `0` only then | the command yes; the wiring no | `PROD-02` |
| 2 | An operation named in no register is refused | `pytest -q tests/integration/api/test_role_register.py` | yes | none |
| 3 | A default credential reaches only the password change | `pytest -q tests/integration/api/test_authorization.py` | yes | none |
| 4 | The lockout is 5 failures in 900 s and 300 s of cooling-off | `grep -n "FAILED_SIGN_IN_ALLOWANCE: Final\[int\] = 5" src/auditmanager/access/repository.py` | yes | none |
| 5 | Sign-in, role grant and password change are journalled | `select event_type, count(*) from audit_event where event_type like 'access.%' group by 1` after one of each; a test per code path (API, registration approval, host command) that deletes the emission and goes red | no | `PROD-06` |
| 6 | No event payload carries a secret or a name | a test that every key an `access.*` event writes is in the writer's allow-list and every value is a scalar | no | `PROD-06` |
| 7 | The session cookie is `Secure` on TLS | `ADR-0021` row 4 | command yes | `PROD-01` |
| 8 | No MFA, IdP or tenant code exists | `rg -il "totp\|saml\|tenant_id\|organisation_id" src db web/src` prints nothing | yes (today it does; the OIDC mentions in `security.py` are comments about the seam) | none |

## Consequences

### Positive

- The account takeover window of `EXPOSURE-REVIEW-01.md` E-1 is detected by the deploy itself rather than by a
  person remembering a readiness run.
- Who signed in, who granted a role and who changed a password becomes a question the database
  can answer, and the answer survives every purge.
- The 1.0 scope stays small: no tenant model, no second factor, no provider.

### Negative / cost

- Every expert sees every project. A client who cannot accept that cannot be served by this version.
- A password-only product with a one-hour token and a lockout; a stolen password is a full account
  until the person or an administrator changes it.
- The deploy check does not close the window it detects (section 3); a fresh or restored host is exposed
  until the password is changed unless the operator follows the loopback order.
- Failed sign-ins on unknown logins and on accounts below the lockout threshold are not recorded.

## Alternatives considered

1. **A deploy that stops the proxy while a default credential is valid.** Closes the window; takes the
   public site down, the shape of `D-72`. Offered to the owner as the alternative to section 3.
2. **Random one-time seed password printed by the migration.** The longer-term fix `EXPOSURE-REVIEW-01.md` E-1
   suggests; needs a migration and changes `R-50`'s account story. Not asked; not built.
3. **Journal every failed sign-in.** Rejected: unbounded growth under attack in an append-only table.
4. **Record the client IP.** Rejected for 1.0: unreliable behind a terminator, personal data in an
   immutable table.

## Verification

- automated check/test: the eight rows above; `tests/integration/composition/test_readiness_command.py` pins that
  `readiness.sh` reports (`R-46`), which `PROD-02` changes for one check and must keep for the others
- manual/operational evidence: the release rehearsal (`PROD-17`) starts from a database in which the
  default credential is valid and shows `verify-deployed.sh` failing, then passing after the change;
  one sign-in, one role grant and one password change are made and the three families are read back

## Revisit trigger

Replace this ADR when a second organisation, a second factor or an identity provider is required, when
the legal-hold authority is named, when the product is opened to users outside the owner's
organisation (registration mail and licensing, `D-4.1`, `NORM-Q04`), or when an incident shows that the
journal of section 4 lacks the fact needed to explain it.
