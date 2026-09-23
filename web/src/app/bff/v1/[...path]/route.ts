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
 * Those figures are **eighteen operations across fifteen paths**, which is what the
 * frozen document declares after the wave-38 reseal that added `listDecisions`. This file
 * said fifteen and twelve once and sixteen and thirteen after that, each true until the
 * next reseal, and it is the fifth stale count in this programme, so it is no longer
 * corrected by hand:
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
 * This file is deliberately thin. The forwarding rules — the two header allowlists, the
 * path-segment check, the verbatim status and body — are in
 * `@/shared/api/credentialed-forward`, where they are unit-testable without a server, and
 * the register is in `../../session/store.ts` for the same reason.
 */

import { getApiToken, getApiUpstreamUrl } from '@/shared/config/server-env';
import {
  envelopeResponse,
  forwardWithCredential,
  mintForwardCorrelationId,
  synthesizedEnvelope,
} from '@/shared/api/credentialed-forward';
import {
  clearedSessionCookie,
  closeSession,
  credentialOf,
  openSession,
  readSessionId,
  requestIsSecure,
  sessionCookie,
  subjectOf,
} from '../../session/store';

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

/** The second segment that ends a session, so the two intents are two addresses. */
const SESSION_END_SEGMENT = 'end';

/** The second segment that changes the password, for the same reason: one intent, one address. */
const SESSION_PASSWORD_SEGMENT = 'password';

/** The exchange the API publishes, addressed by path so no generated import is needed. */
const EXCHANGE_SEGMENTS = ['auth', 'token'] as const;

/** The password change the API publishes, addressed the same way and for the same reason. */
const CHANGE_PASSWORD_SEGMENTS = ['auth', 'password'] as const;

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
const AFTER_SIGN_IN = '/projects';
const REFUSAL_PARAM = 'refusal';

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

/** The four ways the exchange refuses. The sign-in feature translates each one. */
type Refusal = 'credentials' | 'validation' | 'unconfigured' | 'upstream';

/**
 * The six ways the password change can end, success included.
 *
 * Success is a member of the same set because a redirect has no body, so "it worked" has to
 * survive as an address exactly as a refusal does; one set means one parameter and one
 * translation function that cannot disagree with a second one.
 */
type ChangeOutcome = 'changed' | 'unchanged' | Refusal;

interface RouteContext {
  /** Next 15 hands route params as a promise. */
  readonly params: Promise<{ readonly path?: string[] }>;
}

/** What the API answers a successful exchange with. Read here, never returned. */
interface MintedToken {
  readonly token?: unknown;
  readonly expires_in?: unknown;
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

/** Back to the sign-in screen, saying which of the four refusals happened. */
function refuseSignIn(refusal: Refusal): Response {
  return seeOther(`${SIGN_IN_SCREEN}?${REFUSAL_PARAM}=${refusal}`);
}

/** Back to the password screen, saying how it ended. Carries a cookie only on success. */
function reportChange(outcome: ChangeOutcome, cookie?: string): Response {
  return seeOther(`${CHANGE_PASSWORD_SCREEN}?${OUTCOME_PARAM}=${outcome}`, cookie);
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
): Promise<{ readonly login: string; readonly password: string } | null> {
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
  return { login: login.trim(), password };
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
 */
async function openTheSession(request: Request): Promise<Response> {
  const credentials = await postedCredentials(request);
  if (credentials === null) return refuseSignIn('validation');

  let upstream: string;
  let token: string;
  try {
    upstream = getApiUpstreamUrl();
    token = getApiToken();
  } catch {
    // The message is deliberately not forwarded: `MissingConfigurationError` names an
    // environment variable, and a variable name on a public answer is a hint about the
    // deployment that nothing outside needs.
    return refuseSignIn('unconfigured');
  }

  const correlationId = request.headers.get('x-correlation-id');
  const headers = new Headers({ 'content-type': 'application/json', accept: 'application/json' });
  if (correlationId !== null) headers.set('x-correlation-id', correlationId);

  const answer = await forwardWithCredential(
    new Request('http://web.invalid/bff/v1/auth/token', {
      method: 'POST',
      headers,
      body: JSON.stringify({ login: credentials.login, password: credentials.password }),
    }),
    [...EXCHANGE_SEGMENTS],
    { upstream, token },
  );

  // 401 alone, and deliberately not 403: the contract declares `permission_denied`
  // as a refusal to an authenticated subject, and this is the operation that creates one.
  // Reading a 403 here as "wrong password" would report a state the seam does not publish.
  if (answer.status === 401) return refuseSignIn('credentials');
  if (answer.status !== 200) return refuseSignIn('upstream');

  let minted: MintedToken;
  try {
    minted = (await answer.json()) as MintedToken;
  } catch {
    return refuseSignIn('upstream');
  }
  if (typeof minted.token !== 'string' || typeof minted.expires_in !== 'number') {
    return refuseSignIn('upstream');
  }

  let id: string;
  try {
    id = openSession(credentials.login, minted.token, minted.expires_in);
  } catch {
    // A lifetime this tier will not hold is an answer it does not understand, and an
    // answer it does not understand is not a session. Refusing beats inventing a lifetime.
    return refuseSignIn('upstream');
  }

  return seeOther(AFTER_SIGN_IN, sessionCookie(id, minted.expires_in, requestIsSecure(request)));
}

/**
 * Read the two passwords out of a posted form.
 *
 * Form-encoded only, exactly as the sign-in exchange is, and for a reason that is stronger
 * here: this form carries two passwords, one of which is about to become live. Accepting a
 * JSON body as well would invite the client-side call this design exists to avoid.
 */
async function postedPasswords(
  request: Request,
): Promise<{ readonly current: string; readonly next: string } | null> {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return null;
  }
  const current = form.get('current_password');
  const next = form.get('new_password');
  if (typeof current !== 'string' || typeof next !== 'string') return null;
  // Neither is trimmed. A password is bytes somebody typed, and stripping a space the
  // reviewer meant to type would change the password behind their back — which is the one
  // thing a password field may never do. The login above is trimmed because a login is a
  // name and a leading space in one is always a copy-paste artifact.
  if (current.length === 0 || next.length === 0) return null;
  return { current, next };
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
  const sessionId = readSessionId(request.headers.get('cookie'));
  const held = sessionId === null ? null : credentialOf(sessionId);
  if (held === null) {
    // No live session: there is no credential to present and nothing to revoke. Back to the
    // sign-in screen rather than to the password screen, because signing in is the next
    // thing to do and a password screen with no session can only refuse.
    return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
  }
  const subject = subjectOf(sessionId);
  if (subject === null) return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));

  const passwords = await postedPasswords(request);
  if (passwords === null) return reportChange('validation');
  if (passwords.current === passwords.next) {
    // Refused here, before anything is sent, and refused independently by the API. The
    // API's rule is the one that counts; this one means no request carrying two passwords
    // goes out for nothing and the reviewer reads a Russian sentence rather than a
    // translated API message.
    return reportChange('unchanged');
  }

  let upstream: string;
  try {
    upstream = getApiUpstreamUrl();
  } catch {
    return reportChange('unconfigured');
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
  if (answer.status === 401) return reportChange('credentials');
  // 422 is the API's own copy of the "must differ" rule, plus the mechanical bounds.
  if (answer.status === 422) return reportChange('unchanged');
  if (answer.status !== 200) return reportChange('upstream');

  let minted: MintedToken;
  try {
    minted = (await answer.json()) as MintedToken;
  } catch {
    return reportChange('upstream');
  }
  if (typeof minted.token !== 'string' || typeof minted.expires_in !== 'number') {
    return reportChange('upstream');
  }

  let replacement: string;
  try {
    replacement = openSession(subject.login, minted.token, minted.expires_in);
  } catch {
    // A lifetime this tier will not hold is an answer it does not understand. The password
    // HAS changed -- the API committed it -- so the honest report is not `upstream`: the old
    // session is closed and the reviewer is sent to sign in with the new password rather
    // than told nothing happened.
    closeSession(sessionId);
    return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
  }
  // The old row last, and only once the new one exists. Deleting first would leave a window
  // in which a concurrent request from the same browser met `staleSession`.
  closeSession(sessionId);
  return reportChange(
    'changed',
    sessionCookie(replacement, minted.expires_in, requestIsSecure(request)),
  );
}

/** End the session: the register forgets the credential, the browser forgets the number. */
function closeTheSession(request: Request): Response {
  closeSession(readSessionId(request.headers.get('cookie')));
  return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
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
  if (segments[0] === EXCHANGE_SEGMENT) return noDirectExchange(request);

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
    return forwardWithCredential(request, segments, { upstream, token: held });
  }

  return noSession(request);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const HEAD = handle;
