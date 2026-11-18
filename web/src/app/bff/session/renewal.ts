/**
 * The sliding session's renewal: asking the API for a fresh credential before the held one is
 * old, so a reviewer who is working is not signed out (owner ruling of 2026-11-18).
 *
 * ## The rule
 *
 * Before the forwarder presents the held credential, it asks {@link renewIfDue}. A credential
 * issued more than {@link RENEW_AFTER_SECONDS} ago -- or one whose issue time the row does not
 * know -- is renewed: `renewToken` (`POST /auth/token/renew`) is called with the held
 * credential, and the answer is swapped into the **same row under the same id**
 * ({@link replaceCredential}), so the cookie is unchanged and `openedAt` is kept. A session at
 * its absolute cap is never renewed ({@link renewalDue} says no past it), and the register
 * ends it by itself.
 *
 * The API mints a credential that lives 8 h 10 min, the 8 hour idle window the owner ruled plus
 * this 10 minute cadence: a session with no request through the forwarder for 8 hours ends, and
 * any request through it counts, a poll of a run included. That is the whole of "idle".
 *
 * ## One renewal per session at a time
 *
 * Concurrent requests of one session **share one renewal promise** (single flight), keyed by
 * the session id. A page that fires five requests at once makes one `renewToken` call, not five:
 * five calls would mint five credentials, and the last to land would win a race nobody needs.
 * The promise lives on `globalThis` under a `Symbol.for` key, for the reason the register does
 * (`./store.ts`): Next compiles route handlers into module graphs of their own, and a
 * module-scope `Map` would let two graphs each believe they were the only caller.
 *
 * The promise carries an **outcome**, never the credential: each caller reads the new
 * credential from the register with `credentialOf`, so the secret travels through no value
 * this module returns, and a `401` is shared as a plain description each caller turns into its
 * own `Response` ({@link refusedAnswer}) -- a `Response` body can be read only once.
 *
 * ## Three ways it ends
 *
 * - **renewed** -- the row holds the new credential. The caller reads it and goes on.
 * - **refused** (`401`) -- the API no longer accepts the held credential: an administrator ended
 *   the account's sessions, its password or roles changed, it was archived. The caller ends
 *   the session **exactly as it does for an upstream `401` on any forwarded request**, with
 *   the API's own envelope.
 * - **degraded** -- the API could not be asked or did not answer in a way this tier understands:
 *   a network failure or a 5xx (the forward turns both into a 5xx envelope), any other status,
 *   or a `200` whose body is not a credential this tier will hold. **The request is forwarded
 *   with the credential already held**, which is still valid, and **one line is logged naming
 *   the failure**; the session lives on until its own expiry and the next request tries again.
 *   This is a deliberate degradation and not a silent fallback (`AGENTS.md` section 4): the
 *   held credential is the one the API issued to this very session and has not yet expired,
 *   nothing is invented, and the operator is told every time. Ending the session on a renewal
 *   that merely could not be asked would sign every reviewer out for a blip in the API.
 *
 * Executor and runner tokens are another mechanism and never come here.
 */

import { forwardWithCredential } from '@/shared/api/credentialed-forward';

import {
  MAX_LIFETIME_SECONDS,
  MIN_LIFETIME_SECONDS,
  credentialOf,
  renewalDue,
  replaceCredential,
  subjectOf,
} from './store';

export { RENEW_AFTER_SECONDS } from './store';

/** `renewToken`'s path, addressed by segments like the exchange and the password change. */
const RENEW_SEGMENTS = ['auth', 'token', 'renew'] as const;

/** What a renewal came to, for the caller to act on. Carries no credential. */
export type Renewal =
  | { readonly kind: 'not-due' }
  | { readonly kind: 'renewed' }
  /** The session ended while the renewal was in flight (or never existed): nothing was written. */
  | { readonly kind: 'gone' }
  | { readonly kind: 'degraded'; readonly reason: string }
  | { readonly kind: 'refused'; readonly body: string; readonly headers: readonly (readonly [string, string])[] };

/** What the renewal needs from the request that caused it. */
export interface RenewalTarget {
  /** The API's address, as the forwarder resolved it. */
  readonly upstream: string;
  /** The caller's `X-Correlation-Id`, passed on so a trace follows the renewal. */
  readonly correlationId: string | null;
}

const FLIGHTS_KEY = Symbol.for('auditmanager.web.session-renewals');

function flights(): Map<string, Promise<Renewal>> {
  const host = globalThis as unknown as Record<symbol, Map<string, Promise<Renewal>> | undefined>;
  const existing = host[FLIGHTS_KEY];
  if (existing !== undefined) return existing;
  const created = new Map<string, Promise<Renewal>>();
  host[FLIGHTS_KEY] = created;
  return created;
}

/**
 * Renew this session's credential if it is due, sharing one call among concurrent requests.
 *
 * `clock` is a parameter so a test can state the time instead of sleeping; the forwarder passes
 * nothing and the real clock is used.
 */
export function renewIfDue(
  sessionId: string,
  target: RenewalTarget,
  clock: () => number = Date.now,
): Promise<Renewal> {
  if (!renewalDue(sessionId, clock())) return Promise.resolve({ kind: 'not-due' });
  const held = flights();
  const inFlight = held.get(sessionId);
  if (inFlight !== undefined) return inFlight;
  // The check above and this `set` have no `await` between them, so two callers cannot both
  // pass the check and both start a flight.
  const flight = renew(sessionId, target, clock).finally(() => {
    held.delete(sessionId);
  });
  held.set(sessionId, flight);
  return flight;
}

/** The `401` a renewal was refused with, as a `Response` of this caller's own. */
export function refusedAnswer(refusal: Extract<Renewal, { kind: 'refused' }>): Response {
  return new Response(refusal.body, { status: 401, headers: [...refusal.headers] as [string, string][] });
}

/** Forget every renewal in flight. For tests, and for nothing else. */
export function forgetEveryRenewalInFlight(): void {
  flights().clear();
}

function degraded(sessionId: string, reason: string, now: number): Renewal {
  const until = subjectOf(sessionId, now)?.expiresAt;
  // One line, naming the failure. `console.warn` and not `info`: somebody has to look when the
  // API cannot be asked, and a reviewer's session is quietly depending on a credential that is
  // not being extended.
  console.warn(
    `[session-renew] renewToken failed (${reason}); the request goes on with the credential ` +
      `already held` +
      (until === undefined
        ? '.'
        : `, valid for ${String(Math.max(0, Math.round((until - now) / 60_000)))} more minutes.`) +
      ' The session lives on until then and the next request asks again.',
  );
  return { kind: 'degraded', reason };
}

async function renew(sessionId: string, target: RenewalTarget, clock: () => number): Promise<Renewal> {
  // The instant the renewal is **asked for**: see `replaceCredential` for why not the answer's.
  const asked = clock();
  const held = credentialOf(sessionId, asked);
  if (held === null) return { kind: 'gone' };

  const headers = new Headers({ accept: 'application/json' });
  if (target.correlationId !== null) headers.set('x-correlation-id', target.correlationId);
  const answer = await forwardWithCredential(
    new Request('http://web.invalid/bff/v1/auth/token/renew', { method: 'POST', headers }),
    [...RENEW_SEGMENTS],
    { upstream: target.upstream, token: held },
  );

  if (answer.status === 401) {
    // Not a failure to ask: the API says it no longer accepts this credential. The envelope is
    // the API's own and is handed to the caller to end the session with.
    return {
      kind: 'refused',
      body: await answer.text(),
      headers: [...answer.headers],
    };
  }
  if (answer.status !== 200) {
    // The forward never throws: a network failure arrives as a 503 envelope, so this is the
    // one branch for "could not be reached", "the API failed" and "the API said something else".
    await answer.text().catch(() => '');
    return degraded(sessionId, `HTTP ${String(answer.status)}`, asked);
  }

  let minted: { readonly token?: unknown; readonly expires_in?: unknown; readonly is_default_credential?: unknown };
  try {
    minted = (await answer.json()) as typeof minted;
  } catch {
    return degraded(sessionId, 'the answer was not JSON', asked);
  }
  if (
    typeof minted.token !== 'string' ||
    minted.token.trim().length === 0 ||
    typeof minted.expires_in !== 'number' ||
    !Number.isFinite(minted.expires_in) ||
    minted.expires_in < MIN_LIFETIME_SECONDS ||
    minted.expires_in > MAX_LIFETIME_SECONDS ||
    // Required by the contract, and checked as the exchange checks it: a body without it is an
    // answer this tier does not understand, and is not read as `false`.
    typeof minted.is_default_credential !== 'boolean'
  ) {
    return degraded(sessionId, 'the answer was not a credential this tier will hold', asked);
  }

  if (!replaceCredential(sessionId, minted.token, minted.expires_in, asked)) return { kind: 'gone' };
  return { kind: 'renewed' };
}
