/**
 * `/bff/v1/*` — the route handler that holds the credential, and the only door in.
 *
 * The browser calls this, on the same origin it was served from; this calls the API with
 * `Authorization: Bearer <credential>`. The credential is read here, in the Node process,
 * and is never a `NEXT_PUBLIC_*` value, so it is not in the browser bundle and cannot be.
 *
 * **Why the path is `/bff/v1` and not `/api/v1`.** `infra/deploy/proxy/nginx.conf` sends
 * `/api/v1/` straight to the API container; only `location /` reaches Next. So a handler
 * mounted at `/api/v1` would never be called, and moving that `location` would be an
 * nginx change this session does not own. `/bff/v1` falls under `location /` and reaches
 * the Next server through the proxy wave 14 already deployed, unchanged.
 *
 * **Why every operation and not a route per operation.** `T-6` says the same operations
 * must keep working when the alpha's static token is replaced by a real issuer. A
 * catch-all forwards the contract rather than restating it: the paths, their methods,
 * their idempotency keys and their error envelopes are decided by
 * `contracts/api/v1/openapi.json` and the generated client, and nothing in the forwarding
 * knows how many operations there are. Swapping the credential later is an edit to the
 * credential selection below, not a sweep through a handler per operation.
 *
 * Those figures are **thirty-four operations across twenty-seven paths**, which is what the
 * frozen document declares after the `W49-SEAL-01` reseal that added the account and
 * registration operations.
 * This file said fifteen and twelve once, sixteen and thirteen after that, and nineteen and
 * sixteen after `W45-BLOCKS`, each true until the next reseal, and it is the fifth stale count in this programme, so it is no
 * longer corrected by hand:
 * `tests/contract/api_v1/test_surface_counts_in_prose.py` reads this tree and takes both
 * numbers out of `openapi.json` rather than writing either down, so a reseal moves the
 * expectation by itself. That guard separately refuses to let this paragraph vanish --
 * `test_the_bff_handler_still_makes_a_claim_this_guard_can_read` requires a claim here it
 * can check, because a file that stopped describing the surface would make the whole scan
 * a scan of prose with no claims in it. So the figures stay, stated once, and the guard
 * owns whether they are right.
 *
 * That guard refuses a *historical* count here as readily as a stale one -- a first draft
 * of this paragraph recalled the pre-`R-5` figures and reddened it. That is the right
 * answer and the sentence is gone rather than registered as an exception: a file that
 * narrates a surface the document no longer declares is how the fifth of these was made.
 *
 * ## Which credential is presented
 *
 * Two can reach the API through here, and the choice is explicit rather than layered:
 *
 *   **no session cookie** — NOTHING. This route answers `401` locally and forwards no
 *   credential at all.
 *
 *   This paragraph used to read *"the deployment's own credential, exactly as `W15-AUTH`
 *   left it. Nothing about the alpha's behaviour changes for a browser that has not signed
 *   in."* **That was true until wave 34 and became a description of a defect.**
 *   `AUDITMANAGER_API_TOKEN` stopped being a bearer clients present and became the key the
 *   API SIGNS credentials with, so forwarding it on an anonymous request put key material
 *   in an `Authorization` header on every anonymous page view — useless and leaking at
 *   once. `JUDGE-SEC` caught the forward; the code below was repaired and this paragraph
 *   was not, and `W37-CERT4` found it as `W37CERT4-3`.
 *
 *   **It is `OPERATING_CONSTRAINTS.md` §4.7 one level inward.** That section was written
 *   because two runbooks told an operator to hand out the signing key; both were repaired,
 *   and the same sentence went on standing **in the module that holds the key** — where a
 *   reader is likeliest to trust it and likeliest to be someone about to change this file.
 *
 *   **a live session** — the credential the API minted for that reviewer, held in
 *   `../../session/store.ts` and reachable only through `credentialOf`.
 *
 *   **a cookie naming no live session** — `401 authentication_required`, and the cookie is
 *   cleared in the same answer. It is deliberately **not** served with the deployment
 *   credential: a session that quietly downgraded to a shared one on expiry would answer
 *   as somebody else and look like it still worked, which is the silent fallback
 *   `AGENTS.md` §4 forbids.
 *
 * ## The reserved segment
 *
 * `/bff/v1/session`, `/bff/v1/session/end` and `/bff/v1/session/password` are this tier's
 * own, are answered here, and are **never forwarded**: no contract path begins `session`,
 * and a forwarder that passed them through would put a password on the wire to an operation
 * that does not exist.
 *
 * The exchange itself is a forward like any other — `POST /auth/token` — with one
 * difference that is the whole point of doing it here: the answer's body is read in this
 * process and is not returned. The browser receives a `303` and an opaque, `HttpOnly`
 * cookie. The minted token never crosses the network to the browser, so it is in no
 * bundle, no `localStorage` and no script's reach.
 *
 * `POST /bff/v1/session/password` is the same shape for the same reason, and the reason is
 * sharper there. `changePassword` answers with a **credential** — it has to, because it
 * revokes the one the caller presented in the act of succeeding — so a browser that reached
 * `/auth/password` through the catch-all would be handed a live credential in a page body.
 * That is exactly what `JUDGE-SEC` drove against `issueToken`, which is why the whole `auth`
 * segment is refused to the browser. Here the Node process reads the replacement, swaps it
 * into the register under a **new** session id, and answers a redirect and a cookie.
 *
 * **The old session row is deleted rather than updated**, and the cookie carries a new
 * number. The credential it held is dead the instant the API answers, so a row still naming
 * it is a row that authorises nothing; and a session id that survives a credential change is
 * one identifier standing for two credentials, which is the kind of thing that later turns
 * out to have been reused somewhere.
 *
 * ## Who the session belongs to (`W49-PLAN.md` §3.5)
 *
 * After a successful exchange this tier calls `getMe` with the credential it has just been
 * minted and opens the row with the subject that comes back — login, label, initials, roles,
 * the `R-50` flag and whether the profile is complete. A `getMe` answer this tier does not
 * understand is not a session: the sign-in is refused as `upstream`, never opened with a
 * guessed subject. After a successful `PATCH /me` through the catch-all, and after a
 * successful password change, `getMe` is read again and the row rewritten, so a completed
 * profile shows without signing in again. A refresh that fails closes the session rather
 * than keeping a subject this tier knows to be stale: signing in again is what re-reads it.
 *
 * ## An upstream 401 on a held credential closes the session
 *
 * A role change, an archive or an administrator's password reset raises the account's
 * `token_epoch`, and the next request presenting the old credential answers `401`. The
 * catch-all then **deletes the row and clears the cookie in the same answer**, and returns
 * the API's own `401` envelope — exactly what `staleSession` does for a row that is already
 * gone, and for the same reason it is not a redirect: the caller is the generated client's
 * `fetch`, which would follow a `303` into a page of HTML. The client's 401 handling renders
 * the signed-out state; the next server render finds no session.
 *
 * ## The registration door, and what the catch-all refuses under `registrations`
 *
 * `POST /bff/v1/registration` forwards `submitRegistration` exactly as the exchange is
 * forwarded: the form is read here, the password goes upstream once in a JSON body, and
 * nothing of the answer but a redirect reaches the browser — `303` to `/register/submitted`,
 * or to `/register?refusal=<value>` with a closed set of six values. The catch-all refuses
 * exactly the two public registration operations — `POST /registrations` and
 * `POST /registrations/status`, by method and path — as it refuses `auth`: `not_found`,
 * before the session is read. So those two are reachable only through the reserved doors and
 * their throttle, and never with a session's credential. **Everything else under the segment
 * is forwarded like any operation** — the administrator's `listRegistrations`,
 * `approveRegistration` and `rejectRegistration`, which `W50`'s home tile and `W51`'s queue
 * call through here, and which the API refuses to anyone without `admin`. (Corrected at this
 * task's hand-back, `W49-PLAN.md` §3.5 at `83987e5`: refusing the whole segment closed them
 * too.)
 *
 * ## The guest throttle
 *
 * The exchange and the registration door each take a token from the caller's bucket first
 * (`../../session/guest-throttle.ts`); an empty bucket answers the form's own `303` with
 * `throttled`, never a JSON body a form would render raw. The `rate_limited` envelope belongs
 * to the proxy, which answers direct callers of `/api/v1/`; this tier's own forwards go to
 * the API inside the compose network and never meet it.
 *
 * This file is deliberately thin. The forwarding rules — the two header allowlists, the
 * path-segment check, the verbatim status and body — are in
 * `@/shared/api/credentialed-forward`, where they are unit-testable without a server, and
 * the register is in `../../session/store.ts` for the same reason.
 */

import { getApiToken, getApiUpstreamUrl } from '@/shared/config/server-env';
import { isBehindProxy } from '@/shared/config/proxy-trust';
import { safeReturnPath } from '@/shared/config/screen-registry';
import {
  envelopeResponse,
  forwardWithCredential,
  mintForwardCorrelationId,
  synthesizedEnvelope,
} from '@/shared/api/credentialed-forward';
import { admitGuest, guestClientKey } from '../../session/guest-throttle';
import type { SessionAccount } from '../../session/store';
import {
  clearedSessionCookie,
  closeSession,
  credentialOf,
  openSession,
  readSessionId,
  refreshSubject,
  requestIsSecure,
  sessionCookie,
  subjectOf,
} from '../../session/store';
import { accountFromMe } from '../../session/subject';

/**
 * Node, not edge. The forward uses the platform HTTP client, the configuration read is an
 * environment lookup and the register is process memory; all three want the Node runtime.
 */
export const runtime = 'nodejs';

/** Nothing here is cacheable: every response depends on a credential and a request body. */
export const dynamic = 'force-dynamic';

/** The first segment this tier answers itself. No contract path begins with it. */
const SESSION_SEGMENT = 'session';
/** The contract's token exchange. Reachable from this tier, never from a browser. */
const EXCHANGE_SEGMENT = 'auth';

/**
 * The second door this tier answers itself: an application for an account. No contract path
 * begins with it — the contract's own segment is the plural, `registrations`.
 */
const REGISTRATION_SEGMENT = 'registration';

/** The second segment that ends a session, so the two intents are two addresses. */
const SESSION_END_SEGMENT = 'end';

/** The second segment that changes the password, for the same reason: one intent, one address. */
const SESSION_PASSWORD_SEGMENT = 'password';

/** The exchange the API publishes, addressed by path so no generated import is needed. */
const EXCHANGE_SEGMENTS = ['auth', 'token'] as const;

/** The password change the API publishes, addressed the same way and for the same reason. */
const CHANGE_PASSWORD_SEGMENTS = ['auth', 'password'] as const;

/** `getMe` and `updateMyProfile`'s path, addressed the same way. */
const ME_SEGMENTS = ['me'] as const;

/** `submitRegistration`, addressed the same way. */
const SUBMIT_REGISTRATION_SEGMENTS = ['registrations'] as const;

/** `readRegistrationStatus`, addressed the same way. */
const REGISTRATION_STATUS_SEGMENTS = ['registrations', 'status'] as const;

/**
 * The three strings the redirect answers are built from, and why they are written here
 * rather than imported from `@/features/sign-in`, which also declares them.
 *
 * This module is the one the deployment credential reaches, and its import graph is a
 * property `tests/guards/server-credential.guard.test.ts` checks. Importing the feature's
 * public API would pull a React component tree — and, through `shared/ui`, a `'use client'`
 * boundary — into the module that holds the secret, to obtain four constants. The seam is
 * kept narrow instead — three strings and a union — and the two copies are held together by
 * `web/tests/unit/session/bff-session.test.ts`, which imports both and asserts every
 * refusal this handler can answer is a refusal that screen can render. A drift between
 * them is red there rather than invisible here.
 */
const SIGN_IN_SCREEN = '/login';
const AFTER_SIGN_IN = '/';
const REFUSAL_PARAM = 'refusal';

/**
 * `W50-PLAN.md` §3.2. The sign-in form's hidden field that carries where the guest was going.
 * The value is validated again here, by the screen registry's own validator, before this
 * handler redirects to it: the field is part of a form the browser posts. An invalid value is
 * dropped — the redirect falls back to {@link AFTER_SIGN_IN} and the value is echoed nowhere.
 * The registry module is pure data and one function, so importing it brings no component
 * tree into the module that holds the credential.
 */
const NEXT_FIELD = 'next';

/**
 * The password screen's own three, held here for the reason the four above are: this module
 * is the one the deployment credential reaches, and importing `@/features/change-password`
 * would pull a React component tree — and, through `shared/ui`, a `'use client'` boundary —
 * into the module that holds the secret, to obtain three constants.
 * `web/tests/unit/session/bff-session.test.ts` imports both sides and asserts every outcome
 * this handler can answer is one that screen can render.
 */
const CHANGE_PASSWORD_SCREEN = '/account/password';
const OUTCOME_PARAM = 'outcome';

/**
 * The registration screens, written here for the reason the sign-in ones are. They are
 * `W51`'s to build; until then a redirect to them lands on the application's not-found page,
 * which is a missing screen and not a missing answer — the refusal value is in the address.
 */
const REGISTER_SCREEN = '/register';
const REGISTER_SUBMITTED_SCREEN = '/register/submitted';

/**
 * The six ways the exchange refuses. The sign-in feature translates each one.
 *
 * **A mirror, held to its original by a test.** `SIGN_IN_REFUSALS` in
 * `@/features/sign-in/model/exchange.ts` lists the same six values, and
 * `web/tests/unit/session/refusal-mirrors.test.ts` reads this union out of this file and
 * asserts the two sets are equal, so a value added on one side alone is red there.
 *
 * `pending` is `R-56` with its 2026-10-06 addendum: the pair proves a registration request
 * that is still pending. A decided request — approved, or rejected — proves nothing at
 * sign-in and is answered `credentials`, as if no request existed. `throttled` is the guest
 * bucket's refusal, about the caller and never about an account.
 */
type Refusal = 'credentials' | 'validation' | 'unconfigured' | 'upstream' | 'pending' | 'throttled';

/**
 * The seven ways the password change can end, success included.
 *
 * Success is a member of the same set because a redirect has no body, so "it worked" has to
 * survive as an address exactly as a refusal does; one set means one parameter and one
 * translation function that cannot disagree with a second one.
 *
 * `mismatch` is `R-48`'s confirmation -- the new password and its repeated entry disagree
 * -- and is not in `Refusal` because sign-in has no such field to disagree with itself.
 * `pending` and `throttled` are sign-in's alone: a session already exists here, so there is
 * no application to be pending and no guest to throttle.
 */
type ChangeOutcome = 'changed' | 'unchanged' | 'mismatch' | Exclude<Refusal, 'pending' | 'throttled'>;

/**
 * The six ways an application can be refused, closed, as `W49-PLAN.md` §3.5 lists them.
 *
 * `login_taken`, `request_pending` and `queue_full` are the API's own `conflict_reason`
 * values, carried across unchanged — that a login is taken or already applied for is an
 * accepted, registered disclosure (`W49-PLAN.md` §3.3). `validation` is the API's
 * `validation_failed`, and also everything this tier refuses before sending: a missing
 * field, or a password and its confirmation that disagree. `throttled` is the guest bucket.
 * `upstream` is every answer this tier does not understand, an unconfigured deployment
 * included — the screen has nothing more useful to say about either.
 */
type RegistrationRefusal =
  | 'validation'
  | 'login_taken'
  | 'request_pending'
  | 'queue_full'
  | 'throttled'
  | 'upstream';

/** The `conflict_reason` values `submitRegistration` can answer, each a refusal of its own name. */
const REGISTRATION_CONFLICTS: ReadonlySet<string> = new Set<RegistrationRefusal>([
  'login_taken',
  'request_pending',
  'queue_full',
]);

interface RouteContext {
  /** Next 15 hands route params as a promise. */
  readonly params: Promise<{ readonly path?: string[] }>;
}

/** What the API answers a successful exchange with. Read here, never returned. */
interface MintedToken {
  readonly token?: unknown;
  readonly expires_in?: unknown;
  /**
   * `R-50`. Required on the contract, so `unknown` here and checked below: a body that
   * does not carry it is an answer this tier does not understand, and is refused rather
   * than defaulted. The default would have to be `false` — the permissive value — which
   * would send a reviewer on the seeded password into the application.
   */
  readonly is_default_credential?: unknown;
}

/**
 * A deployment with no credential answers exactly what the API answers when it is handed
 * none: `401 authentication_required`.
 *
 * This is the fail-closed half, and it is the honest code rather than a convenient one.
 * The request genuinely was not authenticated — no credential was presented, because this
 * process has none to present — and the operator sees the 401 state the UI now has, which
 * says the deployment is unconfigured. Answering `500` would blame the API; answering
 * `200` is not available; inventing a code would put something outside the closed catalog
 * on the wire.
 */
function unconfigured(request: Request): Response {
  return envelopeResponse(
    401,
    synthesizedEnvelope(
      'authentication_required',
      'This deployment presented no credential to the API, because none is configured for ' +
        'its web tier. No request was sent.',
      false,
      request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
    ),
  );
}

/**
 * A cookie that names no live session: expired, ended elsewhere, or from a process that
 * has since restarted.
 *
 * The same catalog code the API uses, because it is the same fact — this request carried
 * nothing the API would accept — and the cookie is cleared so the next request is simply
 * an unauthenticated one rather than another of these.
 */
function staleSession(request: Request): Response {
  const response = envelopeResponse(
    401,
    synthesizedEnvelope(
      'authentication_required',
      'Сеанс на сервере уже закрыт или истёк, поэтому запрос не был отправлен. ' +
        'Войдите заново.',
      false,
      request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
    ),
  );
  response.headers.set('set-cookie', clearedSessionCookie(requestIsSecure(request)));
  return response;
}

/**
 * The answer to a verb the reserved segment does not offer.
 *
 * `not_found` and not a new code: the closed catalog has no "method not allowed", and
 * `D-18`'s rule is that a code is added to the contract by the contract's owner, never
 * invented at a seam.
 */
/**
 * The answer to a browser that asks for anything without a live session.
 *
 * **This replaces forwarding the deployment credential**, and the reason is that the
 * credential changed meaning under this wave. `AUDITMANAGER_API_TOKEN` used to be the
 * shared bearer every caller presented; it is now the **key the API signs credentials
 * with**. Forwarding it was already useless — the API answers `401` to it, measured — and
 * it put key material in an `Authorization` header on every anonymous page view, where a
 * request dump, a debugging proxy or a future access log would keep it.
 *
 * `JUDGE-SEC` found both halves: the header goes out, and the answer is `401` anyway.
 */
function noSession(request: Request): Response {
  return envelopeResponse(
    401,
    synthesizedEnvelope(
      'authentication_required',
      'Этот запрос требует входа. Откройте экран входа и войдите под своей учётной записью.',
      false,
      request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
    ),
  );
}

/**
 * The answer to a browser asking for the token exchange directly.
 *
 * The exchange is a contract path, so the catch-all forwarded it like any other and
 * **returned the minted token to the page** — `JUDGE-SEC` drove it and got
 * `200 {"token": …}` in a browser, which is the one thing this tier exists to prevent.
 * The exchange still happens, through `/bff/v1/session`, where the token is held in the
 * Node process and never serialised into an answer.
 *
 * `not_found` rather than a new code, for `D-18`'s reason: a seam does not invent codes.
 */
function noDirectExchange(request: Request): Response {
  return envelopeResponse(
    404,
    synthesizedEnvelope(
      'not_found',
      'Этот путь недоступен из браузера. Вход выполняется через /bff/v1/session.',
      false,
      request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
    ),
  );
}

/**
 * The answer to a browser asking for one of the two public registration operations directly.
 *
 * `submitRegistration` and `readRegistrationStatus` take no credential and cost the API a
 * password derivation each, so through the catch-all they would be reachable past the guest
 * throttle — and, from a signed-in browser, with a session's credential attached to an
 * operation that wants none. Refused before the session is read, so a signed-in browser is
 * refused exactly like a guest. Only these two: see {@link isPublicRegistrationOperation}.
 *
 * `not_found` rather than a new code, for `D-18`'s reason: a seam does not invent codes.
 */
function noDirectRegistration(request: Request): Response {
  return envelopeResponse(
    404,
    synthesizedEnvelope(
      'not_found',
      'Этот путь недоступен из браузера. Заявка на регистрацию подаётся через /bff/v1/registration.',
      false,
      request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
    ),
  );
}

function noSuchDoor(request: Request): Response {
  return envelopeResponse(
    404,
    synthesizedEnvelope(
      'not_found',
      'Этот адрес отвечает только на отправку формы.',
      false,
      request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
    ),
  );
}

/** A redirect the browser follows with a `GET`, carrying at most one cookie instruction. */
function seeOther(location: string, cookie?: string): Response {
  const headers = new Headers({ location });
  if (cookie !== undefined) headers.set('set-cookie', cookie);
  return new Response(null, { status: 303, headers });
}

/** Back to the sign-in screen, saying which of the six refusals happened. */
function withNext(path: string, next: string | null): string {
  return next === null ? path : `${path}${path.includes('?') ? '&' : '?'}${NEXT_FIELD}=${encodeURIComponent(next)}`;
}

function postedReturnPath(request: Request): string | null {
  return safeReturnPath(new URL(request.url).searchParams.get(NEXT_FIELD));
}

function refuseSignIn(refusal: Refusal, next: string | null = null): Response {
  return seeOther(withNext(`${SIGN_IN_SCREEN}?${REFUSAL_PARAM}=${refusal}`, next));
}

/** Back to the registration screen, saying which of the six refusals happened. */
function refuseRegistration(refusal: RegistrationRefusal): Response {
  return seeOther(`${REGISTER_SCREEN}?${REFUSAL_PARAM}=${refusal}`);
}

/**
 * Take one token from the caller's guest bucket. True when the request may go on.
 *
 * Asked before the form is read and before the configuration is, so a refused guest costs
 * this process a header read and the API nothing at all.
 */
function guestIsAdmitted(request: Request): boolean {
  return admitGuest(guestClientKey(request, isBehindProxy()));
}

/** The JSON headers every forward this tier builds itself carries, with the caller's correlation id. */
function jsonHeaders(request: Request): Headers {
  const headers = new Headers({ 'content-type': 'application/json', accept: 'application/json' });
  const correlationId = request.headers.get('x-correlation-id');
  if (correlationId !== null) headers.set('x-correlation-id', correlationId);
  return headers;
}

/**
 * Ask `getMe` who `credential` belongs to. `null` for any answer that is not a subject.
 *
 * A `401` and a body this tier does not understand are the same answer to every caller here:
 * there is no subject to record. Each caller says what that means for its own request.
 */
async function readTheAccount(
  request: Request,
  upstream: string,
  credential: string,
): Promise<SessionAccount | null> {
  const headers = jsonHeaders(request);
  headers.delete('content-type');
  const answer = await forwardWithCredential(
    new Request('http://web.invalid/bff/v1/me', { method: 'GET', headers }),
    [...ME_SEGMENTS],
    { upstream, token: credential },
  );
  if (answer.status !== 200) return null;
  try {
    return accountFromMe(await answer.json());
  } catch {
    return null;
  }
}

/**
 * After a refused exchange: does this pair prove a **pending** registration request?
 *
 * `R-56` with its 2026-10-06 addendum. `readRegistrationStatus` answers `{status: pending}`
 * for exactly that, and the same generic `401` for every other pair — an unknown login, a
 * wrong password, and a decided request, whose password columns were cleared at the decision
 * so nothing is left to prove the pair against. **Only a `200` naming `pending` is `true`.**
 * A `401`, any other status, a body that is not JSON, and a `200` naming anything else are
 * all `false`, and the caller answers the generic `credentials` refusal: a rejected applicant
 * sees exactly what a stranger sees.
 *
 * The pair is forwarded exactly as the exchange forwarded it — the second and last time the
 * password leaves this process — and the API does the same number of derivations either way,
 * so the time this takes says nothing about whether a request exists.
 */
async function applicationIsPending(
  request: Request,
  target: { readonly upstream: string; readonly token: string },
  credentials: { readonly login: string; readonly password: string },
): Promise<boolean> {
  const answer = await forwardWithCredential(
    new Request('http://web.invalid/bff/v1/registrations/status', {
      method: 'POST',
      headers: jsonHeaders(request),
      body: JSON.stringify({ login: credentials.login, password: credentials.password }),
    }),
    [...REGISTRATION_STATUS_SEGMENTS],
    target,
  );
  if (answer.status !== 200) return false;
  try {
    const body = (await answer.json()) as { readonly status?: unknown } | null;
    return body !== null && typeof body === 'object' && body.status === 'pending';
  } catch {
    return false;
  }
}

/**
 * The session is over: the row is deleted and the cookie cleared, on `answer` itself.
 *
 * Used when the API has refused the held credential (`401`) — its epoch was raised by a role
 * change, an archive or a reset — and when a subject refresh could not say who the session
 * belongs to now. The answer's status and body are left as they are: for a `401` that is the
 * API's own envelope, with the API's correlation id, which is what the client's 401 handling
 * reads and what an operator can trace.
 */
function endedOn(request: Request, sessionId: string, answer: Response): Response {
  closeSession(sessionId);
  answer.headers.set('set-cookie', clearedSessionCookie(requestIsSecure(request)));
  return answer;
}

/** Back to the password screen, saying how it ended. Carries a cookie only on success. */
function reportChange(outcome: ChangeOutcome, cookie?: string, next: string | null = null): Response {
  return seeOther(withNext(`${CHANGE_PASSWORD_SCREEN}?${OUTCOME_PARAM}=${outcome}`, next), cookie);
}

/**
 * Read the two fields out of a posted form.
 *
 * Form-encoded only. The screen posts a real `<form>` precisely so the password is never
 * a JavaScript value, and accepting a JSON body as well would invite the client-side
 * exchange this design exists to avoid.
 */
async function postedCredentials(
  request: Request,
): Promise<{ readonly login: string; readonly password: string; readonly next: unknown } | null> {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return null;
  }
  const login = form.get('login');
  const password = form.get('password');
  if (typeof login !== 'string' || typeof password !== 'string') return null;
  if (login.trim().length === 0 || password.length === 0) return null;
  // Read, never trusted: `openTheSession` validates it before it becomes an address.
  return { login: login.trim(), password, next: form.get(NEXT_FIELD) };
}

/**
 * Exchange a login and a password for a session.
 *
 * The password leaves this process exactly once, in the body of the forward to the API's
 * own exchange, and is held nowhere afterwards: it is a parameter, never a field, and the
 * `FormData` it came from goes out of scope with the request.
 *
 * The forward carries the deployment's `Authorization` header like every other, and the
 * exchange ignores it: `issueToken` is the one operation the contract publishes with an
 * empty security requirement, because requiring a credential to obtain one is a door with
 * a handle on the inside only. Stripping the header for this one call would mean a second
 * forwarding path through `credentialed-forward`, which is a wider seam bought for nothing.
 *
 * **Since `W49-BFF-01` the guest bucket is asked first**, and a refused exchange is followed
 * by the registration status read with the same pair (`applicationIsPending`), so a pending
 * applicant is told so and everybody else gets the one generic refusal. A successful exchange
 * is followed by `getMe`, and the row is opened with the subject it describes.
 */
async function openTheSession(request: Request): Promise<Response> {
  const returnPath = postedReturnPath(request);
  if (!guestIsAdmitted(request)) return refuseSignIn('throttled', returnPath);

  const credentials = await postedCredentials(request);
  if (credentials === null) return refuseSignIn('validation', returnPath);
  const next = safeReturnPath(credentials.next) ?? returnPath;

  let upstream: string;
  let token: string;
  try {
    upstream = getApiUpstreamUrl();
    token = getApiToken();
  } catch {
    // The message is deliberately not forwarded: `MissingConfigurationError` names an
    // environment variable, and a variable name on a public answer is a hint about the
    // deployment that nothing outside needs.
    return refuseSignIn('unconfigured', next);
  }

  const answer = await forwardWithCredential(
    new Request('http://web.invalid/bff/v1/auth/token', {
      method: 'POST',
      headers: jsonHeaders(request),
      body: JSON.stringify({ login: credentials.login, password: credentials.password }),
    }),
    [...EXCHANGE_SEGMENTS],
    { upstream, token },
  );

  // 401 alone, and deliberately not 403: the contract declares `permission_denied`
  // as a refusal to an authenticated subject, and this is the operation that creates one.
  // Reading a 403 here as "wrong password" would report a state the seam does not publish.
  if (answer.status === 401) {
    // `R-56`'s addendum: only a pending application is shown. Everything else — no request,
    // a wrong password, an approved or a rejected request — is the one generic refusal.
    const pending = await applicationIsPending(request, { upstream, token }, credentials);
    return refuseSignIn(pending ? 'pending' : 'credentials', next);
  }
  // A `429` reaches this tier only from a proxy placed in front of the API, which limits by
  // client address. That is the same fact as this tier's own bucket — about the caller,
  // never about an account — so it is the same refusal rather than an unexplained `upstream`.
  if (answer.status === 429) return refuseSignIn('throttled', next);
  if (answer.status !== 200) return refuseSignIn('upstream', next);

  let minted: MintedToken;
  try {
    minted = (await answer.json()) as MintedToken;
  } catch {
    return refuseSignIn('upstream', next);
  }
  if (
    typeof minted.token !== 'string' ||
    typeof minted.expires_in !== 'number' ||
    // `R-50`. Checked exactly as the other two are, and for the stronger reason: a missing
    // or non-boolean value here is refused rather than read as `false`, because `false` is
    // the answer that lets a reviewer past the screen the ruling exists to send them to.
    typeof minted.is_default_credential !== 'boolean'
  ) {
    return refuseSignIn('upstream', next);
  }

  // Who the credential belongs to, from the API and not from the form: the login typed is
  // not the subject (a legacy account's row may name it differently, and the label, roles
  // and profile state are nowhere in the form at all). No subject, no session.
  const described = await readTheAccount(request, upstream, minted.token);
  if (described === null) return refuseSignIn('upstream', next);
  // `R-50`. The exchange and `getMe` report the same column a moment apart; if either says
  // the password must change, it must. The stricter of two answers from the API, not a value
  // this tier made up.
  const account: SessionAccount = {
    ...described,
    isDefaultCredential: described.isDefaultCredential || minted.is_default_credential,
  };

  let id: string;
  try {
    id = openSession(account, minted.token, minted.expires_in);
  } catch {
    // A lifetime this tier will not hold is an answer it does not understand, and an
    // answer it does not understand is not a session. Refusing beats inventing a lifetime.
    return refuseSignIn('upstream', next);
  }

  // `R-50`, the signpost half. A reviewer whose account is still on the password this
  // deployment was seeded with lands on the change screen rather than on the application:
  // the API refuses them every other operation, so any other screen they would otherwise
  // land on is a screen that can only fail to load. The refusal is the lock and this is the
  // sign on it; neither stands in for the other, which is why the owner bought both.
  //
  // `W50-PLAN.md` §3.2. Everybody else lands where they were going — the form's `next`,
  // validated again here — or on `/`. Validation is the same pure function every time, so
  // repeating a sign-in with the same `next` lands on the same address.
  return seeOther(
    account.isDefaultCredential
      ? withNext(CHANGE_PASSWORD_SCREEN, next)
      : !account.profileComplete && next !== null
        ? withNext('/account', next)
        : (next ?? AFTER_SIGN_IN),
    sessionCookie(id, minted.expires_in, requestIsSecure(request)),
  );
}

/**
 * Read the three passwords out of a posted form: the current one, the new one, and `R-48`'s
 * confirmation -- the new one typed a second time.
 *
 * Form-encoded only, exactly as the sign-in exchange is, and for a reason that is stronger
 * here: this form carries three passwords, one of which is about to become live. Accepting a
 * JSON body as well would invite the client-side call this design exists to avoid.
 */
async function postedPasswords(
  request: Request,
): Promise<{ readonly current: string; readonly next: string; readonly confirm: string } | null> {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return null;
  }
  const current = form.get('current_password');
  const next = form.get('new_password');
  const confirm = form.get('confirm_new_password');
  if (typeof current !== 'string' || typeof next !== 'string' || typeof confirm !== 'string') {
    return null;
  }
  // None of the three is trimmed. A password is bytes somebody typed, and stripping a space
  // the reviewer meant to type would change the password behind their back — which is the
  // one thing a password field may never do. The login above is trimmed because a login is a
  // name and a leading space in one is always a copy-paste artifact.
  if (current.length === 0 || next.length === 0 || confirm.length === 0) return null;
  return { current, next, confirm };
}

/**
 * Change the password, and replace the credential this tier holds with the one that comes back.
 *
 * The order is the whole of it. The API revokes every credential for the account **in the
 * same write** that stores the new digest, so the moment it answers, the credential in the
 * register is dead. If this function returned before swapping it, the very next request
 * would meet `staleSession` and the reviewer would be signed out by a successful password
 * change — indistinguishable, from the browser, from a failed one.
 *
 * The replacement never reaches the browser. It is read here, put in a new row, and what
 * goes back is a redirect and an opaque cookie.
 */
async function changeThePassword(request: Request): Promise<Response> {
  const next = postedReturnPath(request);
  const sessionId = readSessionId(request.headers.get('cookie'));
  const held = sessionId === null ? null : credentialOf(sessionId);
  if (held === null) {
    // No live session: there is no credential to present and nothing to revoke. Back to the
    // sign-in screen rather than to the password screen, because signing in is the next
    // thing to do and a password screen with no session can only refuse.
    return seeOther(withNext(SIGN_IN_SCREEN, next), clearedSessionCookie(requestIsSecure(request)));
  }
  const subject = subjectOf(sessionId);
  if (subject === null) return seeOther(withNext(SIGN_IN_SCREEN, next), clearedSessionCookie(requestIsSecure(request)));

  const passwords = await postedPasswords(request);
  if (passwords === null) return reportChange('validation', undefined, next);
  if (passwords.next !== passwords.confirm) {
    // R-48's confirmation, checked before anything is sent and before the "must differ"
    // rule below: two passwords that disagree with each other are a typo to fix, which is
    // a different fact -- and a different next action -- from "that matches what you
    // already have".
    return reportChange('mismatch', undefined, next);
  }
  if (passwords.current === passwords.next) {
    // Refused here, before anything is sent, and refused independently by the API. The
    // API's rule is the one that counts; this one means no request carrying two passwords
    // goes out for nothing and the reviewer reads a Russian sentence rather than a
    // translated API message.
    return reportChange('unchanged', undefined, next);
  }

  let upstream: string;
  try {
    upstream = getApiUpstreamUrl();
  } catch {
    return reportChange('unconfigured', undefined, next);
  }

  // `getApiToken()` is deliberately NOT read here, and that is the difference from the
  // exchange above. The exchange has no reviewer credential yet, so it forwards the
  // deployment's; this operation is behind the seam and must present the REVIEWER's, which
  // is what makes the API change that reviewer's password and no one else's. The deployment
  // secret is the key the API signs with -- forwarding it would be the `W37CERT4-3` defect
  // again, one operation over.
  const correlationId = request.headers.get('x-correlation-id');
  const headers = new Headers({ 'content-type': 'application/json', accept: 'application/json' });
  if (correlationId !== null) headers.set('x-correlation-id', correlationId);

  const answer = await forwardWithCredential(
    new Request('http://web.invalid/bff/v1/auth/password', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        current_password: passwords.current,
        new_password: passwords.next,
      }),
    }),
    [...CHANGE_PASSWORD_SEGMENTS],
    { upstream, token: held },
  );

  // 401 is both "that is not the current password" and "this credential is no longer
  // accepted". One answer from the API, one outcome here: the reviewer is told the current
  // password did not match, which is the reading that costs them nothing if it is the other
  // one — they are about to meet the sign-in screen anyway.
  if (answer.status === 401) return reportChange('credentials', undefined, next);
  // 422 is the API's own copy of the "must differ" rule, plus the mechanical bounds.
  if (answer.status === 422) return reportChange('unchanged', undefined, next);
  if (answer.status !== 200) return reportChange('upstream', undefined, next);

  let minted: MintedToken;
  try {
    minted = (await answer.json()) as MintedToken;
  } catch {
    return reportChange('upstream', undefined, next);
  }
  if (
    typeof minted.token !== 'string' ||
    typeof minted.expires_in !== 'number' ||
    typeof minted.is_default_credential !== 'boolean'
  ) {
    return reportChange('upstream', undefined, next);
  }

  // `W49-PLAN.md` §3.5's refresh: the new row is opened with what `getMe` says about the
  // account now, read with the replacement credential. The password HAS changed -- the API
  // committed it -- so a `getMe` that cannot say who this is ends the session and sends the
  // reviewer to sign in with the new password, exactly as an unholdable lifetime does below.
  const described = await readTheAccount(request, upstream, minted.token);
  if (described === null) {
    closeSession(sessionId);
    return seeOther(withNext(SIGN_IN_SCREEN, next), clearedSessionCookie(requestIsSecure(request)));
  }

  let replacement: string;
  try {
    replacement = openSession(
      {
        ...described,
        // The API's answers, not a `false` written here. The change clears the column in the
        // same write that stores the digest, so this IS `false` -- and recording what came
        // back rather than what is expected is what would make a deployment where it stopped
        // being cleared visible instead of invisible. The stricter of the two, as at sign-in.
        isDefaultCredential: described.isDefaultCredential || minted.is_default_credential,
      },
      minted.token,
      minted.expires_in,
    );
  } catch {
    // A lifetime this tier will not hold is an answer it does not understand. The password
    // HAS changed -- the API committed it -- so the honest report is not `upstream`: the old
    // session is closed and the reviewer is sent to sign in with the new password rather
    // than told nothing happened.
    closeSession(sessionId);
    return seeOther(withNext(SIGN_IN_SCREEN, next), clearedSessionCookie(requestIsSecure(request)));
  }
  // The old row last, and only once the new one exists. Deleting first would leave a window
  // in which a concurrent request from the same browser met `staleSession`.
  closeSession(sessionId);
  const cookie = sessionCookie(replacement, minted.expires_in, requestIsSecure(request));
  if (next !== null) return seeOther(described.profileComplete ? next : withNext('/account', next), cookie);
  return reportChange(
    'changed',
    cookie,
  );
}

/** End the session: the register forgets the credential, the browser forgets the number. */
function closeTheSession(request: Request): Response {
  closeSession(readSessionId(request.headers.get('cookie')));
  return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
}

/** What an application form carries, once checked. `middleName` is absent when left blank. */
interface PostedApplication {
  readonly login: string;
  readonly password: string;
  readonly lastName: string;
  readonly firstName: string;
  readonly middleName?: string;
}

/**
 * Read an application out of a posted form: `login` (the e-mail), `password`,
 * `confirm_password`, `last_name`, `first_name` and the optional `middle_name`.
 *
 * Form-encoded only, for the exchange's reason: the password is never a JavaScript value.
 * `null` — answered `validation` with nothing sent — for a body that is not a form, a
 * required field missing or blank, or a confirmation that is not the password: `R-48`'s
 * confirmation, checked before anything leaves this process. The closed set has no separate
 * `mismatch` value, because the registration screen states the rule beside the two fields
 * and the fix is the same one either way — type it again.
 *
 * **Only presence and agreement are checked here.** The e-mail's shape, the names' alphabet
 * and length and the password policy are the API's rules (`auditmanager.access`), and a copy
 * of any of them here would be a second rule that drifts. The login is trimmed as at sign-in
 * and a password is never trimmed, for the reasons `postedPasswords` gives.
 */
async function postedApplication(request: Request): Promise<PostedApplication | null> {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return null;
  }
  const login = form.get('login');
  const password = form.get('password');
  const confirm = form.get('confirm_password');
  const lastName = form.get('last_name');
  const firstName = form.get('first_name');
  const middleName = form.get('middle_name');
  if (
    typeof login !== 'string' ||
    typeof password !== 'string' ||
    typeof confirm !== 'string' ||
    typeof lastName !== 'string' ||
    typeof firstName !== 'string'
  ) {
    return null;
  }
  if (login.trim().length === 0 || password.length === 0) return null;
  if (lastName.trim().length === 0 || firstName.trim().length === 0) return null;
  if (password !== confirm) return null;
  const application: PostedApplication = {
    login: login.trim(),
    password,
    lastName,
    firstName,
  };
  if (typeof middleName === 'string' && middleName.trim().length > 0) {
    return { ...application, middleName };
  }
  return application;
}

/**
 * Which of the six refusals an answer from `submitRegistration` is.
 *
 * `409` carries the API's closed `conflict_reason`, which is carried across by name; a `409`
 * without one of the three this operation can give is an answer this tier does not
 * understand. `422` is the API's `validation_failed`. Everything else is `upstream`.
 */
async function registrationRefusalOf(answer: Response): Promise<RegistrationRefusal> {
  if (answer.status === 422) return 'validation';
  // The proxy's per-client limit, if one is ever placed between this tier and the API: the
  // same fact as this tier's own bucket, so the same refusal (see the exchange above).
  if (answer.status === 429) return 'throttled';
  if (answer.status !== 409) return 'upstream';
  try {
    const envelope = (await answer.json()) as {
      readonly details?: { readonly conflict_reason?: unknown } | null;
    } | null;
    const reason = envelope?.details?.conflict_reason;
    if (typeof reason === 'string' && REGISTRATION_CONFLICTS.has(reason)) {
      return reason as RegistrationRefusal;
    }
  } catch {
    // Not JSON: an answer this tier does not understand, which is `upstream` below.
  }
  return 'upstream';
}

/**
 * Submit an application, exactly as the exchange is forwarded.
 *
 * The same credential handling as `openTheSession` — the deployment's header on an operation
 * that publishes an empty security requirement and ignores it — the form read here, the
 * password sent upstream once in a JSON body, and the answer's body never returned: the
 * browser gets a `303` and no cookie, because an application opens no session.
 */
async function submitTheApplication(request: Request): Promise<Response> {
  if (!guestIsAdmitted(request)) return refuseRegistration('throttled');

  const application = await postedApplication(request);
  if (application === null) return refuseRegistration('validation');

  let upstream: string;
  let token: string;
  try {
    upstream = getApiUpstreamUrl();
    token = getApiToken();
  } catch {
    // Not forwarded, for the exchange's reason; and `upstream` rather than a seventh value,
    // because the applicant can do nothing different about either.
    return refuseRegistration('upstream');
  }

  const answer = await forwardWithCredential(
    new Request('http://web.invalid/bff/v1/registrations', {
      method: 'POST',
      headers: jsonHeaders(request),
      body: JSON.stringify({
        login: application.login,
        password: application.password,
        last_name: application.lastName,
        first_name: application.firstName,
        ...(application.middleName === undefined ? {} : { middle_name: application.middleName }),
      }),
    }),
    [...SUBMIT_REGISTRATION_SEGMENTS],
    { upstream, token },
  );

  if (answer.status === 201) return seeOther(REGISTER_SUBMITTED_SCREEN);
  return refuseRegistration(await registrationRefusalOf(answer));
}

/** The registration door: one verb, one address, answered here and never forwarded as such. */
async function registrationDoor(request: Request, segments: readonly string[]): Promise<Response> {
  if (request.method !== 'POST' || segments.length !== 1) return noSuchDoor(request);
  return submitTheApplication(request);
}

/** The reserved segment, answered here and never forwarded. */
async function ownDoor(request: Request, segments: readonly string[]): Promise<Response> {
  if (request.method !== 'POST') return noSuchDoor(request);
  if (segments.length === 1) return openTheSession(request);
  if (segments.length === 2 && segments[1] === SESSION_END_SEGMENT) {
    return closeTheSession(request);
  }
  if (segments.length === 2 && segments[1] === SESSION_PASSWORD_SEGMENT) {
    return changeThePassword(request);
  }
  return noSuchDoor(request);
}

async function handle(request: Request, context: RouteContext): Promise<Response> {
  const { path } = await context.params;
  const segments = path ?? [];

  if (segments[0] === SESSION_SEGMENT) return ownDoor(request, segments);
  if (segments[0] === REGISTRATION_SEGMENT) return registrationDoor(request, segments);
  if (segments[0] === EXCHANGE_SEGMENT) return noDirectExchange(request);
  if (isPublicRegistrationOperation(request, segments)) return noDirectRegistration(request);

  let upstream: string;
  try {
    upstream = getApiUpstreamUrl();
  } catch {
    return unconfigured(request);
  }

  const sessionId = readSessionId(request.headers.get('cookie'));
  if (sessionId !== null) {
    const held = credentialOf(sessionId);
    if (held === null) return staleSession(request);
    const answer = await forwardWithCredential(request, segments, { upstream, token: held });
    // The API no longer accepts this credential: its epoch was raised. The session is over,
    // here as well as there, and the API's own envelope says so to the client.
    if (answer.status === 401) return endedOn(request, sessionId, answer);
    if (isProfileChange(request, segments) && answer.status === 200) {
      const account = await readTheAccount(request, upstream, held);
      if (account === null || !refreshSubject(sessionId, account)) {
        return endedOn(request, sessionId, answer);
      }
    }
    return answer;
  }

  return noSession(request);
}

/** True when the catch-all's segments are exactly `expected`, segment for segment. */
function sameSegments(segments: readonly string[], expected: readonly string[]): boolean {
  return (
    segments.length === expected.length &&
    segments.every((segment, index) => segment === expected[index])
  );
}

/** `PATCH /me` — `updateMyProfile`, after which the row's subject is read again. */
function isProfileChange(request: Request, segments: readonly string[]): boolean {
  return request.method === 'PATCH' && sameSegments(segments, ME_SEGMENTS);
}

/**
 * `POST /registrations` (`submitRegistration`) or `POST /registrations/status`
 * (`readRegistrationStatus`): under this segment, exactly the ones the contract publishes with
 * an empty security requirement, refused to the browser by **method and path**.
 *
 * Nothing else under `registrations` matches, deliberately: `GET /registrations`
 * (`listRegistrations`) and `POST /registrations/{request_id}/approve` and `…/reject` are
 * the administrator's, take the session's credential like every operation, and are refused by
 * the API to anyone without `admin` (`OPERATION_ROLES`). A rule here that matched the whole
 * segment would close them to the screens that need them, which is what `W49-PLAN.md` §3.5
 * said until `83987e5`.
 */
function isPublicRegistrationOperation(request: Request, segments: readonly string[]): boolean {
  return (
    request.method === 'POST' &&
    (sameSegments(segments, SUBMIT_REGISTRATION_SEGMENTS) ||
      sameSegments(segments, REGISTRATION_STATUS_SEGMENTS))
  );
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const HEAD = handle;
